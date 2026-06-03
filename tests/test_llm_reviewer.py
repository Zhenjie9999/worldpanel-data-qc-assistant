import tempfile
import unittest
from pathlib import Path

from worldpanel_qc.llm.reviewer import LlmReviewer, estimate_page_seconds_remaining


class _Client:
    def __init__(self, review_result=None, document_result=None, ocr_result=None):
        self.review_result = review_result or {"ok": True, "status": "success", "data": {"issues": []}}
        self.document_result = document_result or {"ok": True, "status": "success", "data": {"issues": []}}
        self.ocr_result = ocr_result or {"ok": True, "status": "success", "data": {"lines": [], "issues": []}}
        self.review_calls = []
        self.document_calls = []
        self.ocr_calls = []

    def review_candidates(self, candidates):
        self.review_calls.append(candidates)
        return self.review_result

    def review_document_chunk(self, chunk):
        self.document_calls.append(chunk)
        return self.document_result

    def ocr_image(self, image_bytes, file_name, page):
        self.ocr_calls.append((image_bytes, file_name, page))
        return self.ocr_result


class LlmReviewerTests(unittest.TestCase):
    def test_slides_remaining_time_uses_completed_page_average(self):
        self.assertEqual(estimate_page_seconds_remaining(50, 2, 17), 375)
        self.assertIsNone(estimate_page_seconds_remaining(0, 0, 17))

    def test_reviewer_reports_ai_data_and_slides_progress(self):
        client = _Client()
        progress = []
        reviewer = LlmReviewer(
            client,
            endpoint_host="llm.internal",
            ocr_enabled=True,
            progress_callback=lambda stage, percent, detail="": progress.append((stage, percent, detail)),
        )
        documents = [
            {
                "file_name": "deck.pptx",
                "file_type": "pptx",
                "numbers": [{"value": 40.2, "location": "Slide 2"}],
                "pages": [{"page": 2, "review_required": True}],
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            def exporter(_source, pages, output_dir):
                image = output_dir / "page-2.png"
                image.parent.mkdir(parents=True)
                image.write_bytes(b"png")
                return {"images": {2: image}, "warning": ""}

            reviewer.visual_export = exporter
            reviewer.review(documents, [], {"deck.pptx": Path(tmp) / "deck.pptx"}, Path(tmp) / "review")

        self.assertTrue(any(stage == "AI data review" for stage, _, _ in progress))
        self.assertIn(("Slides visual review", 94, "Reviewing Slides page 1 / 1"), progress)
    def test_logic_findings_become_llm_issues(self):
        client = _Client(
            review_result={
                "ok": True,
                "status": "success",
                "data": {
                    "issues": [
                        {
                            "severity": "Medium",
                            "title": "Unusual price",
                            "description": "Price is far above peers.",
                            "evidence": "1000 vs median 61",
                            "recommendation": "Review unit.",
                            "confidence": 0.95,
                        }
                    ]
                },
            }
        )
        reviewer = LlmReviewer(client, endpoint_host="llm.internal", ocr_enabled=False)

        result = reviewer.review([], [{"type": "outlier", "file_name": "source.xlsx", "location": "Price!E2"}], {}, Path("."))

        self.assertEqual(result["issues"][0]["rule_id"], "llm_logic_review")
        self.assertEqual(result["issues"][0]["file_name"], "source.xlsx")
        self.assertEqual(result["ai_logs"][0]["status"], "success")

    def test_ocr_is_attempted_only_for_review_pages(self):
        client = _Client()
        reviewer = LlmReviewer(client, endpoint_host="llm.internal", ocr_enabled=True)
        documents = [
            {
                "file_name": "deck.pptx",
                "file_type": "pptx",
                "pages": [{"page": 1, "review_required": False}, {"page": 2, "review_required": True}],
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            def exporter(_source, pages, output_dir):
                image = output_dir / "page-2.png"
                image.parent.mkdir(parents=True)
                image.write_bytes(b"png")
                return {"images": {2: image}, "warning": ""}

            reviewer.visual_export = exporter
            result = reviewer.review(documents, [], {"deck.pptx": Path(tmp) / "deck.pptx"}, Path(tmp) / "review")

        self.assertEqual(client.ocr_calls, [(b"png", "deck.pptx", 2)])
        self.assertEqual(len(client.document_calls), 1)
        self.assertEqual(len(result["ai_logs"]), 2)

    def test_all_parsed_excel_records_are_reviewed_without_local_candidates(self):
        client = _Client()
        reviewer = LlmReviewer(client, endpoint_host="llm.internal", ocr_enabled=False)
        documents = [
            {
                "file_name": "price.xlsx",
                "file_type": "xlsx",
                "texts": [{"text": "Measures = Weighted RESP Price per Volume", "location": "Sheet1!A1"}],
                "numbers": [
                    {
                        "value": 8000,
                        "location": "Sheet1!B4",
                        "measure": "Weighted RESP Price per Volume",
                        "row_label": "52 w/e 2022/12/30",
                        "column_label": "Cherry",
                    }
                ],
            }
        ]

        result = reviewer.review(documents, [], {}, Path("."))

        self.assertEqual(len(client.document_calls), 1)
        self.assertEqual(client.document_calls[0]["records"][1]["location"], "Sheet1!B4")
        self.assertEqual(client.document_calls[0]["records"][1]["column_label"], "Cherry")
        self.assertEqual(result["ai_logs"][0]["detail"], "full-document-review; batch 1/1; parsed rows sent: 2")

    def test_selected_category_template_is_added_to_document_chunks(self):
        client = _Client()
        reviewer = LlmReviewer(client, endpoint_host="llm.internal", ocr_enabled=False, category_template="fresh_produce")
        documents = [{"file_name": "fruit.xlsx", "file_type": "xlsx", "numbers": [{"value": 80, "location": "Sheet1!B2"}]}]

        reviewer.review(documents, [], {}, Path("."))

        self.assertEqual(client.document_calls[0]["category_template"], "fresh_produce")
        self.assertIn("seasonality", client.document_calls[0]["category_guidance"].lower())

    def test_model_failure_is_logged_without_raising(self):
        client = _Client(review_result={"ok": False, "status": "connection_failed", "detail": "offline"})
        reviewer = LlmReviewer(client, endpoint_host="llm.internal", ocr_enabled=False)

        result = reviewer.review([], [{"type": "share_total", "file_name": "source.xlsx"}], {}, Path("."))

        self.assertEqual(result["issues"], [])
        self.assertEqual(result["ai_logs"][0]["status"], "connection_failed")

    def test_normalizes_lowercase_severity_and_object_evidence(self):
        client = _Client(
            review_result={
                "ok": True,
                "status": "success",
                "data": {
                    "issues": [
                        {
                            "severity": "high",
                            "title": "Share mismatch",
                            "description": "Total is low.",
                            "evidence": {"total": 90, "expected": 100},
                            "recommendation": "Review categories.",
                        }
                    ]
                },
            }
        )
        reviewer = LlmReviewer(client, endpoint_host="llm.internal", ocr_enabled=False)

        issue = reviewer.review([], [{"type": "share_total", "file_name": "source.xlsx"}], {}, Path("."))["issues"][0]

        self.assertEqual(issue["severity"], "High")
        self.assertIsInstance(issue["evidence"], str)
        self.assertIn('"total": 90', issue["evidence"])

    def test_normalizes_list_description_and_location(self):
        client = _Client(
            review_result={
                "ok": True,
                "status": "success",
                "data": {
                    "issues": [
                        {
                            "severity": "medium",
                            "title": "Multiple annotations",
                            "description": ["First concern", "Second concern"],
                            "location": ["Sheet1!B4", "Sheet1!H3"],
                            "recommendation": ["Review source", "Confirm annotation"],
                        }
                    ]
                },
            }
        )
        reviewer = LlmReviewer(client, endpoint_host="llm.internal", ocr_enabled=False)

        issue = reviewer.review([], [{"type": "outlier", "file_name": "source.xlsx"}], {}, Path("."))["issues"][0]

        self.assertIsInstance(issue["description"], str)
        self.assertIsInstance(issue["location"], str)
        self.assertIsInstance(issue["recommendation"], str)


if __name__ == "__main__":
    unittest.main()
