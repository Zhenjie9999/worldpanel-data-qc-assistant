from __future__ import annotations

import re
import statistics
from collections import defaultdict

from .business_rules import find_business_candidates


SHARE_PATTERN = re.compile(r"\b(?:share|contribution)\b|占比|份额", flags=re.IGNORECASE)
PRICE_PATTERN = re.compile(r"\b(?:average\s*price|avg\.?\s*price|price)\b|均价|单价", flags=re.IGNORECASE)


def _sheet(location: str) -> str:
    return str(location or "").split("!", 1)[0]


def _grouped_numbers(documents: list[dict], pattern: re.Pattern) -> dict[tuple[str, str, str], list[dict]]:
    groups = defaultdict(list)
    for document in documents:
        if document.get("file_type") not in {"xlsx", "xls"}:
            continue
        for number in document.get("numbers", []):
            context = str(number.get("context", "")).strip()
            if pattern.search(context):
                groups[(document.get("file_name", ""), _sheet(number.get("location", "")), context.lower())].append(number)
    return groups


def _price_groups(documents: list[dict]) -> dict[tuple[str, str, str], list[dict]]:
    groups = defaultdict(list)
    for document in documents:
        if document.get("file_type") not in {"xlsx", "xls"}:
            continue
        for number in document.get("numbers", []):
            measure = str(number.get("measure", "")).strip()
            product = str(number.get("column_label", "")).strip()
            context = str(number.get("context", "")).strip()
            if measure and product and PRICE_PATTERN.search(measure):
                groups[(document.get("file_name", ""), _sheet(number.get("location", "")), f"{measure} | {product}")].append(number)
            elif PRICE_PATTERN.search(context):
                groups[(document.get("file_name", ""), _sheet(number.get("location", "")), context.lower())].append(number)
    return groups


def find_logic_candidates(documents: list[dict]) -> list[dict]:
    candidates = find_business_candidates(documents)
    for (file_name, sheet, context), numbers in _grouped_numbers(documents, SHARE_PATTERN).items():
        if len(numbers) < 2 or not all(number.get("is_percent") for number in numbers):
            continue
        values = [float(number["value"]) for number in numbers]
        total_percent = sum(values) * 100 if max(abs(value) for value in values) <= 1.5 else sum(values)
        if abs(total_percent - 100) > 0.5:
            candidates.append(
                {
                    "type": "share_total",
                    "file_name": file_name,
                    "sheet": sheet,
                    "context": context,
                    "total_percent": round(total_percent, 3),
                    "expected_percent": 100.0,
                    "locations": [number.get("location", "") for number in numbers],
                    "values": values,
                }
            )
    for (file_name, sheet, context), numbers in _price_groups(documents).items():
        if len(numbers) < 4:
            continue
        values = [float(number["value"]) for number in numbers]
        median = statistics.median(values)
        deviations = [abs(value - median) for value in values]
        mad = statistics.median(deviations)
        for number, value in zip(numbers, values):
            robust_ratio = abs(value - median) / max(mad, abs(median) * 0.05, 1e-9)
            if robust_ratio >= 6 and (value > median * 3 or value < median / 3):
                candidates.append(
                    {
                        "type": "outlier",
                        "file_name": file_name,
                        "sheet": sheet,
                        "context": context,
                        "product": number.get("column_label", ""),
                        "location": number.get("location", ""),
                        "value": value,
                        "median": float(median),
                        "group_values": values,
                        "robust_ratio": round(robust_ratio, 2),
                    }
                )
    return candidates


def issues_from_candidates(candidates: list[dict]) -> list[dict]:
    issues = []
    for candidate in candidates:
        if candidate["type"] == "share_total":
            issues.append(
                {
                    "rule_id": "local_share_total",
                    "severity": "High",
                    "description": f"Share or contribution total is {candidate['total_percent']}%, outside the allowed 100% ± 0.5% range.",
                    "file_name": candidate["file_name"],
                    "location": candidate["sheet"],
                    "evidence": f"Values: {candidate['values']}",
                    "recommendation": "Review the scope, hierarchy, missing categories, and percentage units.",
                    "details": candidate,
                }
            )
        if candidate["type"] == "outlier":
            issues.append(
                {
                    "rule_id": "local_outlier",
                    "severity": "Medium",
                    "description": f"Possible price outlier: {candidate['value']} compared with group median {candidate['median']}.",
                    "file_name": candidate["file_name"],
                    "location": candidate["location"],
                    "evidence": f"Group values: {candidate['group_values']}",
                    "recommendation": "Review unit, decimal position, product scope, and source value.",
                    "details": candidate,
                }
            )
        if candidate["type"] == "percentage_range":
            issues.append(
                {
                    "rule_id": "local_percentage_range",
                    "severity": "High",
                    "description": (
                        f"{candidate['metric']} is {candidate['display_percent']}%, outside the valid 0% to 100% range."
                    ),
                    "file_name": candidate["file_name"],
                    "location": candidate["location"],
                    "evidence": f"Raw value: {candidate['value']}",
                    "recommendation": "Review percentage units, decimal position, and source value.",
                    "details": candidate,
                }
            )
        if candidate["type"] == "identity_mismatch":
            issues.append(
                {
                    "rule_id": "local_metric_identity",
                    "severity": "High",
                    "description": (
                        f"Metric relationship mismatch: {candidate['formula']}. "
                        f"Actual {candidate['actual']}; expected approximately {candidate['expected']}."
                    ),
                    "file_name": candidate["file_name"],
                    "location": candidate["location"],
                    "evidence": (
                        f"Relative difference: {candidate['relative_error_percent']}%; "
                        f"source cells: {candidate['source_locations']}"
                    ),
                    "recommendation": "Review scope, units, decimal position, and source values.",
                    "details": candidate,
                }
            )
    return issues
