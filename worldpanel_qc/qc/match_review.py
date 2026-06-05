from __future__ import annotations


def _number(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _numeric_conflict(observed, candidate) -> bool:
    observed_value = _number(observed.get("value"))
    candidate_value = _number(candidate.get("value"))
    if observed_value is None or candidate_value is None:
        return False
    tolerance = max(abs(observed_value) * 0.005, 0.01)
    return abs(observed_value - candidate_value) > tolerance


def is_suspicious_match(match: dict, confidence_threshold: float = 0.75, close_gap: float = 0.05) -> bool:
    candidates = match.get("candidates") or []
    if not candidates or match.get("status") == "unmatched":
        return True
    selected = match.get("selected_candidate_index")
    if selected is not None:
        return True
    best = candidates[0]
    if float(best.get("confidence") or 0) < confidence_threshold:
        return True
    if _numeric_conflict(match.get("observation", {}), best):
        return True
    if len(candidates) > 1:
        first = float(candidates[0].get("confidence") or 0)
        second = float(candidates[1].get("confidence") or 0)
        if first - second <= close_gap:
            return True
    return False


def filter_suspicious_matches(matches: list[dict]) -> list[dict]:
    return [match for match in matches if is_suspicious_match(match)]
