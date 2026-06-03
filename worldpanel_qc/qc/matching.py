from __future__ import annotations

import re


def _tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9\u4e00-\u9fff]+", (text or "").lower()) if len(token) > 1}


def _numeric_score(observed: dict, excel_value: float) -> float:
    value = float(observed["value"])
    excel_value = float(excel_value)
    if abs(value - excel_value) <= 1e-9:
        return 1.0
    if observed.get("is_percent") and abs(value / 100 - excel_value) <= 0.0005:
        return 0.94
    if abs(round(excel_value, 1) - value) <= 1e-9:
        return 0.9
    if observed.get("is_percent") and abs(round(excel_value * 100, 1) - value) <= 1e-9:
        return 0.9
    return 0.0


def find_numeric_candidates(observed: dict, excel_numbers: list[dict]) -> list[dict]:
    observed_tokens = _tokens(observed.get("context", ""))
    candidates = []
    for number in excel_numbers:
        score = _numeric_score(observed, number["value"])
        if not score:
            continue
        candidate_tokens = _tokens(number.get("context", ""))
        overlap = len(observed_tokens & candidate_tokens)
        confidence = min(1.0, score + min(overlap * 0.02, 0.06))
        candidates.append({**number, "confidence": round(confidence, 3)})
    return sorted(candidates, key=lambda item: item["confidence"], reverse=True)
