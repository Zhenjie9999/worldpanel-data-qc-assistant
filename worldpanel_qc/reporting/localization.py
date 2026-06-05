from __future__ import annotations


LABELS = {
    "summary_sheet": {"zh": "摘要", "en": "Summary"},
    "current_qc_sheet": {"zh": "当前文件QC", "en": "Current File QC"},
    "issue_summary_sheet": {"zh": "问题汇总", "en": "Issue Summary"},
    "source_matching_sheet": {"zh": "来源匹配疑点", "en": "Source Matching Concerns"},
    "coverage_sheet": {"zh": "覆盖率", "en": "Coverage"},
    "ai_logs_sheet": {"zh": "AI日志", "en": "AI Logs"},
    "severity": {"zh": "严重度", "en": "Severity"},
    "status": {"zh": "状态", "en": "Status"},
    "file": {"zh": "文件", "en": "File"},
    "location": {"zh": "位置", "en": "Location"},
    "rule": {"zh": "规则", "en": "Rule"},
    "description": {"zh": "问题描述", "en": "Description"},
    "evidence": {"zh": "证据", "en": "Evidence"},
    "recommendation": {"zh": "建议", "en": "Recommendation"},
    "note": {"zh": "备注", "en": "Note"},
}


def normalize_language(language: str | None) -> str:
    value = str(language or "zh").strip().lower()
    return value if value in {"zh", "en", "bilingual"} else "zh"


def label(key: str, language: str | None = "zh") -> str:
    language = normalize_language(language)
    values = LABELS.get(key, {"zh": key, "en": key})
    if language == "bilingual":
        return f"{values.get('zh', key)} / {values.get('en', key)}"
    return values.get(language, values.get("zh", key))
