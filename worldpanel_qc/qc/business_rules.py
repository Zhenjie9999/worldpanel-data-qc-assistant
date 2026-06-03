from __future__ import annotations

import re
from collections import defaultdict


_ALIAS_PATTERNS = (
    ("spend_per_occasion", re.compile(r"spend\s*per\s*(?:occasion|trip|purchase)", re.I)),
    ("spend_per_buyer", re.compile(r"spend\s*per\s*buyer", re.I)),
    ("volume_per_occasion", re.compile(r"(?:volume|vol)\s*per\s*(?:occasion|trip|purchase\s*occ)", re.I)),
    ("volume_per_buyer", re.compile(r"(?:avg(?:e)?\s*)?(?:volume|vol)\s*per\s*buyer", re.I)),
    ("contribution_share", re.compile(r"contribution.*share|share.*contribution", re.I)),
    ("penetration", re.compile(r"penetration", re.I)),
    ("frequency", re.compile(r"frequency", re.I)),
    ("households", re.compile(r"households?|\bhh\b", re.I)),
    ("buyers", re.compile(r"buyers?", re.I)),
    ("price", re.compile(r"price", re.I)),
    ("spend", re.compile(r"spend|sales\s*value", re.I)),
    ("volume", re.compile(r"volume|\bvol\b", re.I)),
    ("share", re.compile(r"\bshare\b", re.I)),
)

_IDENTITIES = (
    ("buyers", ("households", "penetration"), "buyers = households * penetration"),
    ("volume_per_buyer", ("frequency", "volume_per_occasion"), "volume_per_buyer = frequency * volume_per_occasion"),
    ("volume", ("buyers", "volume_per_buyer"), "volume = buyers * volume_per_buyer"),
    ("spend", ("volume", "price"), "spend = volume * price"),
    ("spend_per_buyer", ("volume_per_buyer", "price"), "spend_per_buyer = volume_per_buyer * price"),
    ("spend_per_occasion", ("volume_per_occasion", "price"), "spend_per_occasion = volume_per_occasion * price"),
)


def normalize_metric_name(value: str) -> str:
    text = " ".join(str(value or "").replace("_", " ").split())
    for metric, pattern in _ALIAS_PATTERNS:
        if pattern.search(text):
            return metric
    return ""


def _sheet(location: str) -> str:
    return str(location or "").split("!", 1)[0]


def _coordinate_column(location: str) -> str:
    match = re.search(r"!([A-Z]+)\d+$", str(location or ""), flags=re.I)
    return match.group(1).upper() if match else ""


def _metric(number: dict) -> str:
    return normalize_metric_name(number.get("measure") or number.get("row_label") or number.get("context") or "")


def _observation_key(document: dict, number: dict) -> tuple[str, ...]:
    sheet = _sheet(number.get("location", ""))
    if number.get("measure"):
        return (
            document.get("file_name", ""),
            sheet,
            "powerview",
            str(number.get("row_label", "")).strip(),
            str(number.get("column_label", "")).strip(),
        )
    return (
        document.get("file_name", ""),
        sheet,
        "row-oriented",
        str(number.get("column_label") or _coordinate_column(number.get("location", ""))).strip(),
    )


def _fraction(number: dict) -> float:
    value = float(number["value"])
    if number.get("is_percent") or abs(value) <= 1:
        return value if abs(value) <= 1 else value / 100
    return value / 100


def _display_percent(number: dict) -> float:
    value = float(number["value"])
    if number.get("is_percent"):
        return value * 100
    if abs(value) <= 1:
        return value * 100
    return value


def find_business_candidates(documents: list[dict], tolerance: float = 0.08) -> list[dict]:
    candidates = []
    observations: dict[tuple[str, ...], dict[str, dict]] = defaultdict(dict)
    for document in documents:
        if document.get("file_type") not in {"xlsx", "xls"}:
            continue
        for number in document.get("numbers", []):
            metric = _metric(number)
            if not metric:
                continue
            if metric in {"penetration", "share", "contribution_share"}:
                display_percent = _display_percent(number)
                if display_percent < 0 or display_percent > 100:
                    candidates.append(
                        {
                            "type": "percentage_range",
                            "metric": metric,
                            "file_name": document.get("file_name", ""),
                            "sheet": _sheet(number.get("location", "")),
                            "location": number.get("location", ""),
                            "value": float(number["value"]),
                            "display_percent": round(display_percent, 3),
                        }
                    )
            observations[_observation_key(document, number)].setdefault(metric, number)

    for key, values in observations.items():
        for result_metric, input_metrics, formula in _IDENTITIES:
            if result_metric not in values or any(metric not in values for metric in input_metrics):
                continue
            actual = float(values[result_metric]["value"])
            factors = [
                _fraction(values[metric]) if metric == "penetration" else float(values[metric]["value"])
                for metric in input_metrics
            ]
            expected = factors[0] * factors[1]
            relative_error = abs(actual - expected) / max(abs(actual), abs(expected), 1e-9)
            if relative_error <= tolerance:
                continue
            candidates.append(
                {
                    "type": "identity_mismatch",
                    "file_name": key[0],
                    "sheet": key[1],
                    "context": " | ".join(part for part in key[3:] if part),
                    "formula": formula,
                    "actual": round(actual, 6),
                    "expected": round(expected, 6),
                    "relative_error_percent": round(relative_error * 100, 2),
                    "location": values[result_metric].get("location", ""),
                    "source_locations": [values[metric].get("location", "") for metric in (*input_metrics, result_metric)],
                }
            )
    return candidates
