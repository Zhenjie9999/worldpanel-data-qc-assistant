import unittest

from worldpanel_qc.qc.issue_grouping import group_issues


class IssueGroupingTests(unittest.TestCase):
    def test_groups_issues_by_category_and_rolls_up_severity(self):
        groups = group_issues(
            [
                {"rule_id": "local_outlier", "severity": "Medium", "description": "Price is unusual", "file_name": "a.xlsx", "location": "S!A1"},
                {"rule_id": "llm_logic_review", "severity": "High", "description": "价格异常", "file_name": "b.xlsx", "location": "S!A2"},
                {"rule_id": "local_share_total", "severity": "Low", "description": "Share total is 98%"},
            ]
        )

        price = next(group for group in groups if group["category"] == "price_outlier")
        share = next(group for group in groups if group["category"] == "share_total")
        self.assertEqual(price["count"], 2)
        self.assertEqual(price["severity"], "High")
        self.assertEqual(share["count"], 1)

    def test_category_mismatch_gets_stable_summary(self):
        groups = group_issues(
            [{"rule_id": "llm_category_template_mismatch", "severity": "Medium", "description": "Category mismatch"}]
        )

        self.assertEqual(groups[0]["category"], "category_mismatch")
        self.assertIn("Category", groups[0]["title"])


if __name__ == "__main__":
    unittest.main()
