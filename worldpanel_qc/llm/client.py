from __future__ import annotations

import base64
import json
import re
import urllib.error
import urllib.request
from urllib.parse import urlparse

from worldpanel_qc.cache import JsonCache, stable_hash
from worldpanel_qc.config import CACHE_DIR
from .category_templates import category_guidance


def _json_content(content: str) -> dict:
    cleaned = (content or "").strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        cleaned = fenced.group(1)
    return json.loads(cleaned)


class LlmClient:
    def __init__(self, endpoint: str, model: str, token: str, timeout_seconds: int = 60):
        self.endpoint = endpoint
        self.model = model
        self.token = token
        self.timeout_seconds = int(timeout_seconds)

    def test_connection(self) -> dict:
        return self._chat(
            [
                {
                    "role": "user",
                    "content": 'Synthetic connectivity test only. Reply exactly as JSON: {"status":"ok"}',
                }
            ]
        )

    def review_candidates(self, candidates: list[dict]) -> dict:
        prompt = (
            "You are reviewing minimized FMCG QC candidates. Return compact JSON with key issues. "
            "Each issue must contain severity, title, description, evidence, recommendation, confidence. "
            "Do not invent missing context. Candidates:\n"
            + json.dumps(candidates, ensure_ascii=False)
        )
        return self._chat([{"role": "user", "content": prompt}])

    def review_document_chunk(self, chunk: dict) -> dict:
        selected_category = str(chunk.get("category_template") or "general_fmcg")
        selected_guidance = str(chunk.get("category_guidance") or category_guidance(selected_category))
        prompt = (
            "You are a senior FMCG data QC reviewer. Review this complete parsed document batch, not only preselected "
            "candidates. Find data anomalies, trend breaks, peer inconsistencies, aggregation errors, units or decimal "
            "errors, annotation problems, and market-common-sense concerns. Return compact JSON with key issues. "
            "Each issue must contain severity, title, description, evidence, recommendation, confidence, and location. "
            "Treat market knowledge as an AI-assisted concern requiring human confirmation. Do not invent missing context. "
            "Use Worldpanel consumer-panel experience and check identities when comparable units are available: "
            "buyers = households * penetration; volume_per_buyer = frequency * volume_per_occasion; "
            "volume = buyers * volume_per_buyer; spend = volume * price; "
            "spend_per_buyer = volume_per_buyer * price; spend_per_occasion = volume_per_occasion * price. "
            f"Selected category template: {selected_category}. Category guidance: {selected_guidance} "
            "Document batch:\n"
            + json.dumps(chunk, ensure_ascii=False)
        )
        return self._chat([{"role": "user", "content": prompt}])

    def ocr_image(self, image_bytes: bytes, file_name: str, page: int) -> dict:
        data_url = "data:image/png;base64," + base64.b64encode(image_bytes).decode("ascii")
        return self._chat(
            [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"OCR and visually review the synthetic or approved intranet Slides screenshot from "
                                f"{file_name}, page {page}. Return compact JSON with keys lines and issues. "
                                "Each issue must contain severity, title, description, evidence, recommendation, confidence."
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ]
        )

    def _chat(self, messages: list[dict]) -> dict:
        payload_object = {"model": self.model, "messages": messages}
        cache_key = stable_hash(
            {
                "endpoint_host": urlparse(self.endpoint).netloc,
                "model": self.model,
                "messages": messages,
                "prompt_version": "2026-06-05",
            }
        )
        cache = JsonCache(CACHE_DIR)
        cached = cache.get("llm", cache_key)
        if cached is not None:
            return cached
        payload = json.dumps(payload_object, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                data = json.load(response)
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            result = {"ok": True, "status": "success", "data": _json_content(content), "model": data.get("model", self.model)}
            cache.set("llm", cache_key, result)
            return result
        except json.JSONDecodeError:
            return {"ok": False, "status": "invalid_response", "detail": "Model response was not valid JSON."}
        except TimeoutError:
            return {"ok": False, "status": "timeout", "detail": "Model request timed out."}
        except (OSError, urllib.error.URLError, urllib.error.HTTPError) as error:
            return {"ok": False, "status": "connection_failed", "detail": str(error)}
