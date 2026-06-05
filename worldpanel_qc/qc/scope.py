from __future__ import annotations

import re


FOCUS_METRICS = {
    "price": ("price", "价格", "均价", "单价"),
    "share": ("share", "份额", "占比"),
    "penetration": ("penetration", "渗透", "penetration"),
    "volume": ("volume", "销量", "购买量", "volume"),
    "spend": ("spend", "销售额", "花费", "spend"),
}


def default_scope() -> dict:
    return {
        "mode": "full",
        "pages": [],
        "sheets": [],
        "focus_metrics": [],
        "cross_check": True,
    }


def _parse_pages(text: str) -> list[int]:
    pages: set[int] = set()
    for start, end in re.findall(r"(?:第)?(\d+)\s*[-~到至]\s*(\d+)\s*页?", text, flags=re.IGNORECASE):
        first, last = int(start), int(end)
        if first > last:
            first, last = last, first
        pages.update(range(first, last + 1))
    for page in re.findall(r"(?:第|page\s*)\s*(\d+)\s*页?", text, flags=re.IGNORECASE):
        pages.add(int(page))
    return sorted(pages)


def _parse_sheets(text: str) -> list[str]:
    sheets: list[str] = []
    for match in re.findall(r"(?:sheet|Sheet|工作表)\s*[:：]?\s*([A-Za-z0-9_\-\u4e00-\u9fff ]+)", text):
        for item in re.split(r"[,，、和以及 ]+", match.strip()):
            if item and item not in sheets and item.lower() not in {"and", "sheet"}:
                sheets.append(item)
    return sheets


def _parse_focus_metrics(text: str) -> list[str]:
    lowered = text.lower()
    metrics = []
    for metric, aliases in FOCUS_METRICS.items():
        if any(alias.lower() in lowered for alias in aliases):
            metrics.append(metric)
    return metrics


def parse_scope_text(text: str) -> dict:
    scope = default_scope()
    text = text or ""
    pages = _parse_pages(text)
    sheets = _parse_sheets(text)
    focus_metrics = _parse_focus_metrics(text)
    if pages or sheets or focus_metrics:
        scope["mode"] = "focused"
    scope["pages"] = pages
    scope["sheets"] = sheets
    scope["focus_metrics"] = focus_metrics
    if re.search(r"不需要交叉|无需交叉|不对数|no\s+cross|without\s+cross", text, flags=re.IGNORECASE):
        scope["cross_check"] = False
    return scope


def _page_from_location(location: str) -> int | None:
    match = re.search(r"(?:Slide|Page)\s+(\d+)", str(location), flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def _matches_sheet(location: str, sheets: list[str]) -> bool:
    if not sheets:
        return True
    sheet = str(location).split("!", 1)[0].strip().lower()
    return sheet in {item.lower() for item in sheets}


def _matches_focus(item: dict, metrics: list[str]) -> bool:
    if not metrics:
        return True
    text = " ".join(str(item.get(field, "")) for field in ("measure", "row_label", "column_label", "context", "text")).lower()
    return any(any(alias.lower() in text for alias in FOCUS_METRICS[metric]) for metric in metrics if metric in FOCUS_METRICS)


def apply_scope_to_documents(documents: list[dict], scope: dict | None) -> list[dict]:
    scope = scope or default_scope()
    if scope.get("mode") != "focused":
        return documents
    pages = set(int(page) for page in scope.get("pages", []) if str(page).isdigit())
    sheets = [str(sheet) for sheet in scope.get("sheets", [])]
    metrics = [str(metric) for metric in scope.get("focus_metrics", [])]
    scoped = []
    for document in documents:
        copy = {**document}
        if pages and document.get("file_type") in {"pptx", "ppt", "pdf"}:
            copy["pages"] = [page for page in document.get("pages", []) if int(page.get("page", -1)) in pages]
            copy["numbers"] = [item for item in document.get("numbers", []) if _page_from_location(item.get("location", "")) in pages and _matches_focus(item, metrics)]
            copy["texts"] = [item for item in document.get("texts", []) if _page_from_location(item.get("location", "")) in pages]
        elif document.get("file_type") in {"xlsx", "xls"}:
            copy["numbers"] = [
                item for item in document.get("numbers", [])
                if _matches_sheet(item.get("location", ""), sheets) and _matches_focus(item, metrics)
            ]
            copy["texts"] = [item for item in document.get("texts", []) if _matches_sheet(item.get("location", ""), sheets)]
        scoped.append(copy)
    return scoped
