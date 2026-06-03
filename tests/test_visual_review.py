import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from worldpanel_qc.llm.visual_review import export_review_pages, review_page_numbers, system_exporter


class VisualReviewTests(unittest.TestCase):
    def test_selects_only_review_required_pages(self):
        document = {
            "pages": [
                {"page": 1, "review_required": False},
                {"page": 2, "review_required": True},
                {"page": 3, "review_required": True},
            ]
        }

        self.assertEqual(review_page_numbers(document), [2, 3])

    def test_exports_only_selected_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "deck.pptx"
            source.write_bytes(b"synthetic")

            def exporter(_source, export_dir):
                export_dir.mkdir(parents=True)
                for page in range(1, 4):
                    (export_dir / f"Slide{page}.PNG").write_bytes(f"page-{page}".encode())

            result = export_review_pages(source, [2], root / "review", exporter=exporter)

            self.assertEqual(list(result["images"]), [2])
            self.assertEqual(result["images"][2].read_bytes(), b"page-2")

    def test_export_failure_is_returned_as_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "deck.pptx"
            source.write_bytes(b"synthetic")

            result = export_review_pages(
                source,
                [1],
                Path(tmp) / "review",
                exporter=lambda *_: (_ for _ in ()).throw(OSError("PowerPoint unavailable")),
            )

            self.assertEqual(result["images"], {})
            self.assertIn("PowerPoint unavailable", result["warning"])

    def test_system_exporter_uses_libreoffice_when_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "deck.pptx"
            source.write_bytes(b"synthetic")
            export_dir = Path(tmp) / "rendered"
            calls = []

            def fake_run(command, check, capture_output, timeout, text):
                calls.append(command)
                export_dir.mkdir(parents=True, exist_ok=True)
                if command[0] == "soffice":
                    (export_dir / "deck.pdf").write_bytes(b"pdf")
                if command[0] == "pdftoppm":
                    (export_dir / "Slide-1.png").write_bytes(b"page-1")

            with patch("worldpanel_qc.llm.visual_review.os.name", "posix"):
                with patch(
                    "worldpanel_qc.llm.visual_review.shutil.which",
                    side_effect=lambda name: name if name in {"soffice", "pdftoppm"} else None,
                ):
                    with patch("worldpanel_qc.llm.visual_review.subprocess.run", side_effect=fake_run):
                        system_exporter(source, export_dir)

            self.assertEqual(calls[0][0], "soffice")
            self.assertIn("--headless", calls[0])
            self.assertEqual(calls[1][0], "pdftoppm")
            self.assertTrue((export_dir / "Slide-1.png").exists())

    def test_supports_localized_powerpoint_export_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "deck.pptx"
            source.write_bytes(b"synthetic")

            def exporter(_source, export_dir):
                export_dir.mkdir(parents=True)
                (export_dir / "幻灯片2.PNG").write_bytes(b"localized-page-2")

            result = export_review_pages(source, [2], root / "review", exporter=exporter)

            self.assertEqual(result["images"][2].read_bytes(), b"localized-page-2")

    def test_creates_parent_directory_before_powerpoint_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "deck.pptx"
            source.write_bytes(b"synthetic")

            def exporter(_source, export_dir):
                self.assertTrue(export_dir.parent.exists())
                export_dir.mkdir()
                (export_dir / "Slide1.PNG").write_bytes(b"page-1")

            result = export_review_pages(source, [1], root / "nested" / "review", exporter=exporter)

            self.assertEqual(result["images"][1].read_bytes(), b"page-1")


if __name__ == "__main__":
    unittest.main()
