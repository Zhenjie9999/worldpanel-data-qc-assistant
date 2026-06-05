import unittest

from worldpanel_qc.qc.match_review import filter_suspicious_matches, is_suspicious_match


class MatchReviewTests(unittest.TestCase):
    def test_clean_high_confidence_match_is_not_suspicious(self):
        match = {
            "observation": {"value": 100},
            "candidates": [{"value": 100, "confidence": 0.96}],
            "status": "matched",
        }

        self.assertFalse(is_suspicious_match(match))

    def test_unmatched_low_confidence_and_conflict_are_suspicious(self):
        self.assertTrue(is_suspicious_match({"observation": {"value": 100}, "candidates": [], "status": "unmatched"}))
        self.assertTrue(is_suspicious_match({"observation": {"value": 100}, "candidates": [{"value": 100, "confidence": 0.55}], "status": "matched"}))
        self.assertTrue(is_suspicious_match({"observation": {"value": 100}, "candidates": [{"value": 97, "confidence": 0.95}], "status": "matched"}))

    def test_close_competing_candidates_are_suspicious(self):
        match = {
            "observation": {"value": 100},
            "candidates": [{"value": 100, "confidence": 0.92}, {"value": 100, "confidence": 0.9}],
            "status": "matched",
        }

        self.assertTrue(is_suspicious_match(match))

    def test_filter_returns_only_suspicious_matches(self):
        matches = [
            {"observation": {"value": 1}, "candidates": [{"value": 1, "confidence": 0.99}], "status": "matched"},
            {"observation": {"value": 2}, "candidates": [], "status": "unmatched"},
        ]

        self.assertEqual(filter_suspicious_matches(matches), [matches[1]])


if __name__ == "__main__":
    unittest.main()
