import tempfile
import unittest
from pathlib import Path

from worldpanel_qc.cache import JsonCache, file_hash


class CacheTests(unittest.TestCase):
    def test_json_cache_round_trips_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = JsonCache(Path(tmp))

            cache.set("parse", "abc", {"ok": True})

            self.assertEqual(cache.get("parse", "abc"), {"ok": True})

    def test_corrupt_cache_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = JsonCache(Path(tmp))
            path = Path(tmp) / "parse" / "bad.json"
            path.parent.mkdir()
            path.write_text("{bad", encoding="utf-8")

            self.assertIsNone(cache.get("parse", "bad"))

    def test_file_hash_changes_with_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.txt"
            path.write_text("a", encoding="utf-8")
            first = file_hash(path)
            path.write_text("b", encoding="utf-8")

            self.assertNotEqual(first, file_hash(path))


if __name__ == "__main__":
    unittest.main()
