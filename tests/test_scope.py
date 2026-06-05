import unittest

from worldpanel_qc.qc.scope import apply_scope_to_documents, default_scope, parse_scope_text


class ScopeTests(unittest.TestCase):
    def test_parse_pages_sheets_and_focus_metrics(self):
        scope = parse_scope_text("只检查第3-5页和第8页，Sheet Summary 和 Price，重点看价格、share，不需要交叉检查")

        self.assertEqual(scope["mode"], "focused")
        self.assertEqual(scope["pages"], [3, 4, 5, 8])
        self.assertIn("Summary", scope["sheets"])
        self.assertIn("Price", scope["sheets"])
        self.assertIn("price", scope["focus_metrics"])
        self.assertIn("share", scope["focus_metrics"])
        self.assertFalse(scope["cross_check"])

    def test_default_scope_is_full_check(self):
        scope = default_scope()

        self.assertEqual(scope["mode"], "full")
        self.assertEqual(scope["pages"], [])
        self.assertTrue(scope["cross_check"])

    def test_apply_scope_filters_pages_and_sheet_records_for_ai(self):
        documents = [
            {
                "file_name": "deck.pptx",
                "file_type": "pptx",
                "pages": [{"page": 2}, {"page": 8}],
                "numbers": [{"location": "Slide 2"}, {"location": "Slide 8"}],
                "texts": [{"location": "Slide 8", "text": "Keep"}],
            },
            {
                "file_name": "source.xlsx",
                "file_type": "xlsx",
                "numbers": [{"location": "Price!A1"}, {"location": "Other!A1"}],
                "texts": [],
                "pages": [],
            },
        ]

        scoped = apply_scope_to_documents(documents, {"mode": "focused", "pages": [8], "sheets": ["Price"], "focus_metrics": []})

        self.assertEqual(scoped[0]["pages"], [{"page": 8}])
        self.assertEqual(scoped[0]["numbers"], [{"location": "Slide 8"}])
        self.assertEqual(scoped[1]["numbers"], [{"location": "Price!A1"}])


if __name__ == "__main__":
    unittest.main()
