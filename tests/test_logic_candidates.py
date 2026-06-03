import unittest

from worldpanel_qc.qc.logic_candidates import find_logic_candidates, issues_from_candidates


class LogicCandidateTests(unittest.TestCase):
    def test_flags_share_total_outside_tolerance(self):
        documents = [
            {
                "file_name": "source.xlsx",
                "file_type": "xlsx",
                "numbers": [
                    {"value": 0.4, "is_percent": True, "context": "Brand Share", "location": "Summary!B2"},
                    {"value": 0.3, "is_percent": True, "context": "Brand Share", "location": "Summary!C2"},
                    {"value": 0.2, "is_percent": True, "context": "Brand Share", "location": "Summary!D2"},
                ],
            }
        ]

        candidates = find_logic_candidates(documents)

        self.assertEqual(candidates[0]["type"], "share_total")
        self.assertEqual(candidates[0]["total_percent"], 90.0)
        self.assertEqual(issues_from_candidates(candidates)[0]["rule_id"], "local_share_total")

    def test_share_total_within_tolerance_is_clean(self):
        documents = [
            {
                "file_name": "source.xlsx",
                "file_type": "xlsx",
                "numbers": [
                    {"value": 0.4, "is_percent": True, "context": "Share", "location": "Summary!B2"},
                    {"value": 0.6, "is_percent": True, "context": "Share", "location": "Summary!C2"},
                ],
            }
        ]

        self.assertEqual(find_logic_candidates(documents), [])

    def test_flags_price_outlier_against_robust_group_baseline(self):
        documents = [
            {
                "file_name": "source.xlsx",
                "file_type": "xlsx",
                "numbers": [
                    {"value": 55, "context": "Average Price", "location": "Price!B2"},
                    {"value": 60, "context": "Average Price", "location": "Price!C2"},
                    {"value": 62, "context": "Average Price", "location": "Price!D2"},
                    {"value": 1000, "context": "Average Price", "location": "Price!E2"},
                ],
            }
        ]

        candidates = find_logic_candidates(documents)

        self.assertEqual(candidates[0]["type"], "outlier")
        self.assertEqual(candidates[0]["value"], 1000.0)
        self.assertEqual(candidates[0]["median"], 61.0)

    def test_flags_powerview_price_outlier_across_periods_for_same_product(self):
        documents = [
            {
                "file_name": "price.xlsx",
                "file_type": "xlsx",
                "numbers": [
                    {
                        "value": 47.6439,
                        "measure": "Weighted RESP Price per Volume",
                        "row_label": "52 w/e 2021/12/31",
                        "column_label": "Cherry",
                        "context": "Weighted RESP Price per Volume | 52 w/e 2021/12/31 | Cherry",
                        "location": "Sheet1!B3",
                    },
                    {
                        "value": 8000,
                        "measure": "Weighted RESP Price per Volume",
                        "row_label": "52 w/e 2022/12/30",
                        "column_label": "Cherry",
                        "context": "Weighted RESP Price per Volume | 52 w/e 2022/12/30 | Cherry",
                        "location": "Sheet1!B4",
                    },
                    {
                        "value": 63.7041,
                        "measure": "Weighted RESP Price per Volume",
                        "row_label": "52 w/e 2023/12/29",
                        "column_label": "Cherry",
                        "context": "Weighted RESP Price per Volume | 52 w/e 2023/12/29 | Cherry",
                        "location": "Sheet1!B5",
                    },
                    {
                        "value": 64.1638,
                        "measure": "Weighted RESP Price per Volume",
                        "row_label": "52 w/e 2024/12/27",
                        "column_label": "Cherry",
                        "context": "Weighted RESP Price per Volume | 52 w/e 2024/12/27 | Cherry",
                        "location": "Sheet1!B6",
                    },
                ],
            }
        ]

        candidates = find_logic_candidates(documents)

        outlier = next(candidate for candidate in candidates if candidate["type"] == "outlier")
        self.assertEqual(outlier["location"], "Sheet1!B4")
        self.assertEqual(outlier["value"], 8000.0)
        self.assertEqual(outlier["product"], "Cherry")


if __name__ == "__main__":
    unittest.main()
