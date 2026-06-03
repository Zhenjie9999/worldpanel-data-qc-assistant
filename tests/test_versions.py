import unittest

from worldpanel_qc.qc.versions import compare_documents, filename_similarity, should_suggest_comparison


class VersionSuggestionTests(unittest.TestCase):
    def test_ignores_dates_and_version_markers(self):
        similarity = filename_similarity(
            "Zespri_PanelVoice_0527V.pptx",
            "Zespri PanelVoice 0521 V2.pptx",
        )
        self.assertEqual(similarity, 1.0)

    def test_does_not_suggest_unrelated_file(self):
        self.assertFalse(
            should_suggest_comparison(
                "Zespri_PanelVoice_0527V.pptx",
                "Zespri_Frequency_Study.pptx",
            )
        )

    def test_requires_same_extension(self):
        self.assertFalse(
            should_suggest_comparison(
                "Zespri_PanelVoice_0527V.pptx",
                "Zespri_PanelVoice_0521V.pdf",
            )
        )

    def test_compares_numeric_observations_by_location(self):
        changes = compare_documents(
            {"file_name": "deck_0527V.pptx", "numbers": [{"location": "Slide 2 / Shape 1", "value": 16.6}]},
            {"file_name": "deck_0521V.pptx", "numbers": [{"location": "Slide 2 / Shape 1", "value": 16.2}]},
        )
        self.assertEqual(changes[0]["type"], "numeric_change")
        self.assertEqual(changes[0]["before"], 16.2)
        self.assertEqual(changes[0]["after"], 16.6)

    def test_compares_multiple_numbers_in_same_shape_by_occurrence(self):
        changes = compare_documents(
            {
                "file_name": "deck_0527V.pptx",
                "numbers": [
                    {"location": "Slide 2 / Shape 1", "value": 1.0},
                    {"location": "Slide 2 / Shape 1", "value": 5.0},
                ],
            },
            {
                "file_name": "deck_0521V.pptx",
                "numbers": [
                    {"location": "Slide 2 / Shape 1", "value": 1.0},
                    {"location": "Slide 2 / Shape 1", "value": 5.0},
                ],
            },
        )
        self.assertEqual(changes, [])

    def test_flags_only_changed_occurrence_in_same_shape(self):
        changes = compare_documents(
            {
                "file_name": "deck_0527V.pptx",
                "numbers": [
                    {"location": "Slide 2 / Shape 1", "value": 1.0},
                    {"location": "Slide 2 / Shape 1", "value": 6.0},
                ],
            },
            {
                "file_name": "deck_0521V.pptx",
                "numbers": [
                    {"location": "Slide 2 / Shape 1", "value": 1.0},
                    {"location": "Slide 2 / Shape 1", "value": 5.0},
                ],
            },
        )
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]["before"], 5.0)
        self.assertEqual(changes[0]["after"], 6.0)


if __name__ == "__main__":
    unittest.main()
