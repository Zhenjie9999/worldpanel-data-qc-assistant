from __future__ import annotations

import re


PLACEHOLDER_PATTERNS = [
    r"report/presentation name",
    r"\bplaceholder\b",
    r"\b(?:todo|tbd)\b",
]


def _issue(rule_id: str, severity: str, description: str, file_name: str, location: str, **extra) -> dict:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "description": description,
        "file_name": file_name,
        "location": location,
        **extra,
    }


def run_builtin_rules(parsed: dict) -> list[dict]:
    issues = []
    for document in parsed.get("documents", []):
        file_name = document.get("file_name", "")
        file_type = document.get("file_type", "")
        if file_type == "ppt":
            issues.append(_issue("unsupported_ppt", "High", "Legacy .ppt is not supported; save as .pptx.", file_name, "File"))
        for location in document.get("formula_errors", []):
            issues.append(_issue("excel_formula_error", "High", "Excel contains an error value that requires correction.", file_name, location))
        for page in document.get("pages", []):
            text = page.get("text", "")
            location = f"Page {page.get('page', '?')}"
            if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in PLACEHOLDER_PATTERNS):
                issues.append(_issue("placeholder_text", "High", "Template placeholder remains in visible content.", file_name, location, evidence=text[:180]))
            if page.get("review_required"):
                issues.append(_issue("visual_review_required", "Medium", "Page contains content that requires manual visual review.", file_name, location))
    return issues


def run_project_rules(parsed: dict, rules: list[dict]) -> list[dict]:
    issues = []
    documents = parsed.get("documents", [])
    for rule in rules:
        if not rule.get("active", True):
            continue
        config = rule.get("config", {})
        types = set(config.get("file_types", []))
        relevant = [doc for doc in documents if not types or doc.get("file_type") in types]
        if rule["rule_type"] == "required_text":
            required = config.get("text", "")
            for document in relevant:
                joined = " ".join(page.get("text", "") for page in document.get("pages", []))
                if required.lower() not in joined.lower():
                    issues.append(
                        _issue(
                            "project_required_text",
                            rule.get("severity", "Medium"),
                            f"Required project text is missing: {required}",
                            document.get("file_name", ""),
                            "Document",
                        )
                    )
        if rule["rule_type"] == "forbidden_text":
            forbidden = config.get("text", "")
            for document in relevant:
                joined = " ".join(page.get("text", "") for page in document.get("pages", []))
                if forbidden and forbidden.lower() in joined.lower():
                    issues.append(
                        _issue(
                            "project_forbidden_text",
                            rule.get("severity", "Medium"),
                            f"Forbidden project text is present: {forbidden}",
                            document.get("file_name", ""),
                            "Document",
                        )
                    )
    return issues
