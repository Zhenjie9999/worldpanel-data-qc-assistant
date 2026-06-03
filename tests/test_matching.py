import unittest

from worldpanel_qc.qc.matching import find_numeric_candidates


class NumericMatchingTests(unittest.TestCase):
    def test_matches_percentage_to_decimal_excel_value(self):
        candidates = find_numeric_candidates(
            {"value": 40.2, "is_percent": True, "context": "penetration top 5 cities"},
            [
                {
                    "value": 0.402,
                    "context": "penetration top 5 cities",
                    "location": "Summary!B2",
                    "file_name": "source.xlsx",
                }
            ],
        )
        self.assertEqual(candidates[0]["location"], "Summary!B2")
        self.assertGreaterEqual(candidates[0]["confidence"], 0.9)

    def test_preserves_alternative_candidates(self):
        candidates = find_numeric_candidates(
            {"value": 6.0, "is_percent": True, "context": "share"},
            [
                {"value": 0.0601, "context": "share", "location": "A!B2", "file_name": "a.xlsx"},
                {"value": 0.0604, "context": "share", "location": "B!B2", "file_name": "b.xlsx"},
            ],
        )
        self.assertEqual(len(candidates), 2)
        self.assertGreaterEqual(candidates[0]["confidence"], candidates[1]["confidence"])


if __name__ == "__main__":
    unittest.main()
