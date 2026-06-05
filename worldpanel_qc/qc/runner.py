from __future__ import annotations

import re
from pathlib import Path

from worldpanel_qc.cache import JsonCache, file_hash
from worldpanel_qc.config import CACHE_DIR
from worldpanel_qc.parsers import parse_file

from .matching import find_numeric_candidates
from .logic_candidates import find_logic_candidates, issues_from_candidates
from .match_review import filter_suspicious_matches
from .rules import run_builtin_rules, run_project_rules
from .scope import apply_scope_to_documents


PARSER_CACHE_VERSION = "2026-06-05"


def cached_parse_file(path: Path) -> dict:
    cache = JsonCache(CACHE_DIR)
    key = f"{PARSER_CACHE_VERSION}-{file_hash(path)}"
    cached = cache.get("parse", key)
    if isinstance(cached, dict):
        return cached
    parsed = parse_file(Path(path))
    cache.set("parse", key, parsed)
    return parsed


def _constrained_sources(observation: dict, excel_numbers: list[dict], constraints: list[dict]) -> list[dict]:
    location = observation.get("location", "")
    page_match = re.search(r"(?:Slide|Page)\s+(\d+)", location, flags=re.IGNORECASE)
    page = int(page_match.group(1)) if page_match else None
    relevant = [
        item
        for item in constraints
        if item.get("page_file_name") == observation.get("file_name")
        and (not item.get("page") or int(item["page"]) == page)
    ]
    if not relevant:
        return excel_numbers
    allowed = []
    for number in excel_numbers:
        for item in relevant:
            same_file = number.get("file_name") == item.get("source_file_name")
            same_sheet = not item.get("sheet_name") or str(number.get("location", "")).startswith(f"{item['sheet_name']}!")
            if same_file and same_sheet:
                allowed.append(number)
                break
    return allowed


def run_qc(
    paths: list[Path],
    project_rules: list[dict],
    external_ai_enabled: bool,
    mapping_constraints: list[dict] | None = None,
    llm_reviewer=None,
    visual_output_dir: Path | None = None,
    progress_callback=None,
    run_scope: dict | None = None,
) -> dict:
    mapping_constraints = mapping_constraints or []
    progress = progress_callback or (lambda _stage, _percent, _detail="": None)
    documents = []
    for index, path in enumerate(paths, start=1):
        progress("Reading files", 5 + round(3 * index / max(len(paths), 1)), f"Reading file {index} / {len(paths)}")
        documents.append(cached_parse_file(Path(path)))
    parsed = {"documents": documents}
    scoped_documents = apply_scope_to_documents(documents, run_scope)
    progress("Running local rules", 12, "Checking file structure and Worldpanel business rules")
    logic_candidates = find_logic_candidates(documents)
    issues = run_builtin_rules(parsed) + run_project_rules(parsed, project_rules) + issues_from_candidates(logic_candidates)
    coverage = []
    excel_numbers = []
    observations = []
    ai_logs = []
    for document in scoped_documents:
        if document["file_type"] in {"xlsx", "xls"}:
            excel_numbers.extend(document.get("numbers", []))
            if document.get("hidden_rows") or document.get("hidden_columns"):
                issues.append(
                    {
                        "rule_id": "hidden_excel_area",
                        "severity": "Low",
                        "description": "Excel contains hidden rows or columns.",
                        "file_name": document["file_name"],
                        "location": "Workbook",
                    }
                )
        else:
            observations.extend(document.get("numbers", []))
        for page in document.get("pages", []):
            coverage.append({"file_name": document["file_name"], **page})
            if external_ai_enabled and not llm_reviewer and page.get("review_required"):
                ai_logs.append(
                    {
                        "provider": "external-ai-adapter",
                        "file_name": document["file_name"],
                        "page": page["page"],
                        "status": "not_configured",
                        "detail": "External AI is enabled, but no approved provider endpoint is configured.",
                    }
                )
    matches = []
    for observation in observations:
        candidates = find_numeric_candidates(observation, _constrained_sources(observation, excel_numbers, mapping_constraints))
        matches.append(
            {
                "observation": observation,
                "candidates": candidates[:5],
                "status": "matched" if candidates else "unmatched",
            }
        )
    matches = filter_suspicious_matches(matches)
    if llm_reviewer:
        progress("AI data review", 35, "Preparing parsed data for AI review")
        reviewed = llm_reviewer.review(
            scoped_documents,
            logic_candidates,
            {Path(path).name: Path(path) for path in paths},
            visual_output_dir or Path(paths[0]).parent / "visual-review",
        )
        issues.extend(reviewed["issues"])
        ai_logs.extend(reviewed["ai_logs"])
    progress("Preparing report", 98, "Preparing issues, matches, and coverage report")
    return {
        "documents": documents,
        "issues": issues,
        "coverage": coverage,
        "matches": matches,
        "ai_logs": ai_logs,
        "logic_candidates": logic_candidates,
    }
