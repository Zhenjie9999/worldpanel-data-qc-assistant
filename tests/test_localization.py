import unittest

from worldpanel_qc.reporting.localization import label, normalize_language


class LocalizationTests(unittest.TestCase):
    def test_normalizes_unknown_language_to_chinese(self):
        self.assertEqual(normalize_language("bad"), "zh")

    def test_bilingual_label_contains_both_languages(self):
        self.assertEqual(label("summary_sheet", "zh"), "摘要")
        self.assertEqual(label("summary_sheet", "en"), "Summary")
        self.assertIn("摘要", label("summary_sheet", "bilingual"))
        self.assertIn("Summary", label("summary_sheet", "bilingual"))


if __name__ == "__main__":
    unittest.main()
