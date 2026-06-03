from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

from .category_templates import category_guidance, validate_category_template
from .document_payloads import build_document_chunks
from .visual_review import export_review_pages, review_page_numbers


def estimate_page_seconds_remaining(elapsed_seconds: float, reviewed_pages: int, total_pages: int) -> int | None:
    if reviewed_pages <= 0:
        return None
    return max(0, round((elapsed_seconds / reviewed_pages) * max(total_pages - reviewed_pages, 0)))


class LlmReviewer:
    def __init__(
        self,
        client,
        endpoint_host: str,
        ocr_enabled: bool,
        logic_enabled: bool = True,
        category_template: str = "general_fmcg",
        progress_callback=None,
        visual_export: Callable = export_review_pages,
    ):
        self.client = client
        self.endpoint_host = endpoint_host
        self.ocr_enabled = ocr_enabled
        self.logic_enabled = logic_enabled
        self.category_template = validate_category_template(category_template)
        self.progress = progress_callback or (lambda _stage, _percent, _detail="": None)
        self.visual_export = visual_export

    def _progress(self, stage: str, percent: int, detail: str = "", estimated_seconds_remaining: int | None = None) -> None:
        try:
            self.progress(
                stage,
                percent,
                detail,
                estimated_seconds_remaining=estimated_seconds_remaining,
            )
        except TypeError:
            self.progress(stage, percent, detail)

    def review(
        self,
        documents: list[dict],
        logic_candidates: list[dict],
        file_paths: dict[str, Path],
        output_dir: Path,
    ) -> dict:
        issues, ai_logs = [], []
        if self.logic_enabled and logic_candidates:
            self._progress("AI data review", 42, "Reviewing local logic candidates")
            response = self.client.review_candidates(logic_candidates)
            ai_logs.append(self._log("logic-review", response, rows=len(logic_candidates)))
            if response.get("ok"):
                issues.extend(self._issues(response.get("data", {}).get("issues", []), logic_candidates[0]))
        if self.logic_enabled:
            chunks = build_document_chunks(documents, logic_candidates)
            for index, chunk in enumerate(chunks, start=1):
                self._progress("AI data review", 45 + round(30 * index / max(len(chunks), 1)), f"Reviewing data batch {index} / {len(chunks)}")
                chunk["category_template"] = self.category_template
                chunk["category_guidance"] = category_guidance(self.category_template)
                response = self.client.review_document_chunk(chunk)
                ai_logs.append(
                    {
                        "provider": self.endpoint_host,
                        "file_name": chunk["file_name"],
                        "page": None,
                        "status": response.get("status", "unknown"),
                        "detail": (
                            f"full-document-review; batch {chunk['batch']}/{chunk['batch_count']}; "
                            f"parsed rows sent: {len(chunk['records'])}"
                        ),
                    }
                )
                if response.get("ok"):
                    issues.extend(
                        self._issues(
                            response.get("data", {}).get("issues", []),
                            {"file_name": chunk["file_name"], "location": "Document"},
                            rule_id="llm_full_document_review",
                        )
                    )
        if self.ocr_enabled:
            all_pages = [
                (document, page)
                for document in documents
                if document.get("file_type") == "pptx"
                for page in review_page_numbers(document)
            ]
            reviewed_pages = 0
            slides_started = time.monotonic()
            for document in documents:
                if document.get("file_type") != "pptx":
                    continue
                pages = review_page_numbers(document)
                if not pages:
                    continue
                rendered = self.visual_export(file_paths[document["file_name"]], pages, output_dir / document["file_name"])
                if rendered.get("warning"):
                    ai_logs.append(
                        {
                            "provider": self.endpoint_host,
                            "file_name": document["file_name"],
                            "page": None,
                            "status": "render_failed",
                            "detail": rendered["warning"],
                        }
                    )
                for page, image_path in rendered.get("images", {}).items():
                    self._progress(
                        "Slides visual review",
                        78 + round(16 * (reviewed_pages + 1) / max(len(all_pages), 1)),
                        f"Reviewing Slides page {reviewed_pages + 1} / {len(all_pages)}",
                        estimate_page_seconds_remaining(
                            time.monotonic() - slides_started,
                            reviewed_pages,
                            len(all_pages),
                        ),
                    )
                    response = self.client.ocr_image(Path(image_path).read_bytes(), document["file_name"], page)
                    reviewed_pages += 1
                    ai_logs.append(self._log("slides-ocr", response, file_name=document["file_name"], page=page, rows=1))
                    if response.get("ok"):
                        issues.extend(
                            self._issues(
                                response.get("data", {}).get("issues", []),
                                {"file_name": document["file_name"], "location": f"Page {page}"},
                                rule_id="llm_visual_review",
                            )
                        )
        return {"issues": issues, "ai_logs": ai_logs}

    def _issues(self, findings: list[dict], source: dict, rule_id: str = "llm_logic_review") -> list[dict]:
        def text(value) -> str:
            return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)

        def severity(value) -> str:
            normalized = str(value or "Medium").strip().lower()
            return {"high": "High", "medium": "Medium", "low": "Low"}.get(normalized, "Medium")

        return [
            {
                "rule_id": rule_id,
                "severity": severity(finding.get("severity")),
                "description": text(finding.get("description") or finding.get("title", "LLM review finding")),
                "file_name": text(finding.get("file_name") or source.get("file_name", "")),
                "location": text(finding.get("location") or source.get("location") or source.get("sheet", "Document")),
                "evidence": text(finding.get("evidence", "")),
                "recommendation": text(finding.get("recommendation", "")),
                "details": {
                    "title": finding.get("title", ""),
                    "confidence": finding.get("confidence"),
                    "source": "llm",
                },
            }
            for finding in findings
        ]

    def _log(self, operation: str, response: dict, file_name: str = "", page: int | None = None, rows: int = 0) -> dict:
        return {
            "provider": self.endpoint_host,
            "file_name": file_name,
            "page": page,
            "status": response.get("status", "unknown"),
            "detail": f"{operation}; minimized rows sent: {rows}",
        }
