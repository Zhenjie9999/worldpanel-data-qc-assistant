from __future__ import annotations

import re
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path


VERSION_WORDS = r"(?:final|updated?|draft|rev(?:ision)?|ver(?:sion)?|v)\s*\d*"


def normalize_filename(file_name: str) -> str:
    stem = Path(file_name).stem.lower()
    stem = re.sub(r"\d{6,8}", " ", stem)
    stem = re.sub(r"(?<!\d)\d{4}(?!\d)", " ", stem)
    stem = re.sub(r"(?<!\d)\d{3,4}(?!\d)", " ", stem)
    stem = re.sub(VERSION_WORDS, " ", stem, flags=re.IGNORECASE)
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", stem)


def filename_similarity(left: str, right: str) -> float:
    a, b = normalize_filename(left), normalize_filename(right)
    if not a or not b:
        return 0.0
    return round(SequenceMatcher(None, a, b).ratio(), 4)


def should_suggest_comparison(current: str, previous: str, threshold: float = 0.9) -> bool:
    if Path(current).suffix.lower() != Path(previous).suffix.lower():
        return False
    return filename_similarity(current, previous) >= threshold


def compare_documents(current: dict, previous: dict) -> list[dict]:
    previous_by_location = defaultdict(list)
    for item in previous.get("numbers", []):
        previous_by_location[item.get("location")].append(item)
    occurrence_by_location = defaultdict(int)
    changes = []
    for item in current.get("numbers", []):
        location = item.get("location")
        occurrence = occurrence_by_location[location]
        occurrence_by_location[location] += 1
        previous_items = previous_by_location.get(location, [])
        if occurrence >= len(previous_items):
            continue
        before = previous_items[occurrence]
        if abs(float(before["value"]) - float(item["value"])) > 1e-9:
            changes.append(
                {
                    "type": "numeric_change",
                    "file_name": current.get("file_name", ""),
                    "location": f"{location} / Number {occurrence + 1}" if len(previous_items) > 1 else location,
                    "before": before["value"],
                    "after": item["value"],
                }
            )
    return changes
