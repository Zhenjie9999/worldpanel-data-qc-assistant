import unittest

from worldpanel_qc.qc.rules import run_builtin_rules, run_project_rules


class RuleTests(unittest.TestCase):
    def test_flags_placeholder_text_in_pptx(self):
        issues = run_builtin_rules(
            {
                "documents": [
                    {
                        "file_name": "deck.pptx",
                        "file_type": "pptx",
                        "pages": [{"page": 20, "text": "Report/Presentation Name"}],
                    }
                ]
            }
        )
        self.assertTrue(any(issue["rule_id"] == "placeholder_text" for issue in issues))

    def test_flags_missing_required_project_text(self):
        issues = run_project_rules(
            {
                "documents": [
                    {
                        "file_name": "deck.pptx",
                        "file_type": "pptx",
                        "pages": [{"page": 1, "text": "Zespri FY2025"}],
                    }
                ]
            },
            [
                {
                    "name": "Proxy footnote",
                    "rule_type": "required_text",
                    "config": {"text": "Imported Kiwi to proxy Zespri", "file_types": ["pptx"]},
                    "severity": "High",
                }
            ],
        )
        self.assertEqual(issues[0]["severity"], "High")
        self.assertEqual(issues[0]["rule_id"], "project_required_text")

    def test_flags_forbidden_project_text(self):
        issues = run_project_rules(
            {
                "documents": [
                    {
                        "file_name": "deck.pptx",
                        "file_type": "pptx",
                        "pages": [{"page": 1, "text": "Draft for internal review"}],
                    }
                ]
            },
            [
                {
                    "name": "No draft label",
                    "rule_type": "forbidden_text",
                    "config": {"text": "Draft", "file_types": ["pptx"]},
                    "severity": "High",
                }
            ],
        )
        self.assertEqual(issues[0]["rule_id"], "project_forbidden_text")

    def test_flags_excel_formula_error_values(self):
        issues = run_builtin_rules(
            {
                "documents": [
                    {
                        "file_name": "source.xlsx",
                        "file_type": "xlsx",
                        "formula_errors": ["Summary!B2"],
                        "pages": [],
                    }
                ]
            }
        )
        self.assertEqual(issues[0]["rule_id"], "excel_formula_error")
        self.assertEqual(issues[0]["location"], "Summary!B2")


if __name__ == "__main__":
    unittest.main()
