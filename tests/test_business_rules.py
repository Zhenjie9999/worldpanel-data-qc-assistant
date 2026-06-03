import unittest

from worldpanel_qc.qc.business_rules import find_business_candidates, normalize_metric_name


class BusinessRuleTests(unittest.TestCase):
    def test_normalizes_worldpanel_metric_aliases(self):
        self.assertEqual(normalize_metric_name("Weighted RESPONSE Spend (M.RMB)"), "spend")
        self.assertEqual(normalize_metric_name("Weighted RESP Price per Volume"), "price")
        self.assertEqual(normalize_metric_name("Weighted RESP Avg Volume per Purchase Occ"), "volume_per_occasion")
        self.assertEqual(normalize_metric_name("Penetration %"), "penetration")

    def test_flags_penetration_outside_valid_range(self):
        documents = [
            {
                "file_name": "source.xlsx",
                "file_type": "xlsx",
                "numbers": [
                    {
                        "value": 1.2,
                        "is_percent": True,
                        "row_label": "Penetration %",
                        "column_label": "FY2025",
                        "location": "Summary!B2",
                    }
                ],
            }
        ]

        candidates = find_business_candidates(documents)

        self.assertEqual(candidates[0]["type"], "percentage_range")
        self.assertEqual(candidates[0]["metric"], "penetration")
        self.assertEqual(candidates[0]["display_percent"], 120.0)

    def test_flags_row_oriented_buyers_identity_mismatch(self):
        documents = [
            {
                "file_name": "source.xlsx",
                "file_type": "xlsx",
                "numbers": [
                    {"value": 10, "row_label": "Households (mn)", "column_label": "FY2025", "location": "Summary!B2"},
                    {"value": 0.4, "is_percent": True, "row_label": "Penetration", "column_label": "FY2025", "location": "Summary!B3"},
                    {"value": 7, "row_label": "Buyers (mn)", "column_label": "FY2025", "location": "Summary!B4"},
                ],
            }
        ]

        candidates = find_business_candidates(documents)

        mismatch = next(candidate for candidate in candidates if candidate["type"] == "identity_mismatch")
        self.assertEqual(mismatch["formula"], "buyers = households * penetration")
        self.assertEqual(mismatch["actual"], 7.0)
        self.assertEqual(mismatch["expected"], 4.0)

    def test_flags_powerview_volume_per_buyer_identity_mismatch(self):
        documents = [
            {
                "file_name": "source.xlsx",
                "file_type": "xlsx",
                "numbers": [
                    {
                        "value": 4,
                        "measure": "Weighted RESP Frequency",
                        "row_label": "52 w/e 2025/12/26",
                        "column_label": "Total Market",
                        "location": "Sheet1!B3",
                    },
                    {
                        "value": 2,
                        "measure": "Weighted RESP Avg Volume per Purchase Occ",
                        "row_label": "52 w/e 2025/12/26",
                        "column_label": "Total Market",
                        "location": "Sheet1!B8",
                    },
                    {
                        "value": 20,
                        "measure": "Weighted RESP Avge Volume per Buyer",
                        "row_label": "52 w/e 2025/12/26",
                        "column_label": "Total Market",
                        "location": "Sheet1!B13",
                    },
                ],
            }
        ]

        candidates = find_business_candidates(documents)

        mismatch = next(candidate for candidate in candidates if candidate["type"] == "identity_mismatch")
        self.assertEqual(mismatch["formula"], "volume_per_buyer = frequency * volume_per_occasion")
        self.assertEqual(mismatch["expected"], 8.0)
        self.assertEqual(mismatch["actual"], 20.0)


if __name__ == "__main__":
    unittest.main()
