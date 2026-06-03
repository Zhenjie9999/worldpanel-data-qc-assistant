from __future__ import annotations


def _record(kind: str, item: dict, fields: tuple[str, ...]) -> dict:
    return {"kind": kind, **{field: item.get(field) for field in fields if item.get(field) not in (None, "")}}


def build_document_chunks(documents: list[dict], logic_candidates: list[dict], max_records: int = 120) -> list[dict]:
    chunks = []
    for document in documents:
        records = [
            _record("text", item, ("location", "text"))
            for item in document.get("texts", [])
        ]
        records.extend(
            _record(
                "number",
                item,
                ("location", "value", "is_percent", "measure", "row_label", "column_label", "context"),
            )
            for item in document.get("numbers", [])
        )
        records.extend(
            _record(
                "page",
                item,
                ("page", "coverage_percent", "numbers_found", "low_confidence_count", "review_required", "detail"),
            )
            for item in document.get("pages", [])
        )
        if not records:
            continue
        slices = [records[index : index + max_records] for index in range(0, len(records), max_records)]
        file_candidates = [
            candidate for candidate in logic_candidates if candidate.get("file_name") == document.get("file_name")
        ]
        for index, items in enumerate(slices, start=1):
            chunks.append(
                {
                    "file_name": document.get("file_name", ""),
                    "file_type": document.get("file_type", ""),
                    "batch": index,
                    "batch_count": len(slices),
                    "records": items,
                    "local_logic_candidates": file_candidates if index == 1 else [],
                }
            )
    return chunks
