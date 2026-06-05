from __future__ import annotations

from collections import defaultdict


SEVERITY_RANK = {"High": 3, "Medium": 2, "Low": 1}

CATEGORY_TITLES = {
    "price_outlier": "Price anomaly",
    "share_total": "Share total / composition issue",
    "unit_decimal": "Unit or decimal concern",
    "source_conflict": "PPT-Excel source conflict",
    "trend": "Trend or period movement concern",
    "annotation": "Annotation or labeling issue",
    "category_mismatch": "Category template mismatch",
    "file_structure": "File structure issue",
    "other": "Other QC issue",
}


def issue_category(issue: dict) -> str:
    rule_id = str(issue.get("rule_id", "")).lower()
    text = " ".join(str(issue.get(field, "")) for field in ("description", "evidence", "recommendation")).lower()
    if "category_template_mismatch" in rule_id:
        return "category_mismatch"
    if "share" in rule_id or "share" in text or "份额" in text or "占比" in text:
        return "share_total"
    if "outlier" in rule_id or "price" in text or "价格" in text or "均价" in text:
        return "price_outlier"
    if "match" in rule_id or "source" in text or "excel" in text or "来源" in text or "冲突" in text:
        return "source_conflict"
    if "unit" in text or "decimal" in text or "小数" in text or "单位" in text:
        return "unit_decimal"
    if "trend" in text or "yoy" in text or "mom" in text or "趋势" in text or "环比" in text or "同比" in text:
        return "trend"
    if "annotation" in text or "label" in text or "标注" in text or "注释" in text:
        return "annotation"
    if "formula" in rule_id or "hidden" in rule_id or "placeholder" in rule_id or "file" in text:
        return "file_structure"
    return "other"


def _max_severity(issues: list[dict]) -> str:
    return max((issue.get("severity", "Medium") for issue in issues), key=lambda value: SEVERITY_RANK.get(value, 2))


def group_issues(issues: list[dict]) -> list[dict]:
    grouped = defaultdict(list)
    for issue in issues:
        grouped[issue_category(issue)].append(issue)
    summaries = []
    for category, items in grouped.items():
        locations = [
            f"{item.get('file_name', '')} {item.get('location', '')}".strip()
            for item in items[:5]
            if item.get("file_name") or item.get("location")
        ]
        summaries.append(
            {
                "category": category,
                "title": CATEGORY_TITLES.get(category, CATEGORY_TITLES["other"]),
                "severity": _max_severity(items),
                "count": len(items),
                "locations": locations,
                "issue_ids": [item.get("id") for item in items if item.get("id") is not None],
            }
        )
    return sorted(summaries, key=lambda item: (-SEVERITY_RANK.get(item["severity"], 2), -item["count"], item["title"]))
