import tempfile
import unittest
import sqlite3
from pathlib import Path

from worldpanel_qc.db import Database


class DatabaseTests(unittest.TestCase):
    def test_run_cannot_be_completed_while_processing(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.sqlite3")
            db.initialize()
            user_id = db.upsert_user("Zhen", "zhen@example.com")
            project_id = db.create_project("Zespri PanelVoice", user_id)
            run_id = db.create_run(project_id, user_id, external_ai_enabled=True)

            with self.assertRaises(ValueError):
                db.complete_run(run_id, user_id, "Ready")

    def test_new_run_is_queued_even_when_migrated_column_defaults_are_completed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy.sqlite3"
            conn = sqlite3.connect(path)
            conn.executescript(
                """
                CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, created_at TEXT);
                CREATE TABLE projects (id INTEGER PRIMARY KEY, name TEXT, category_template TEXT, created_by INTEGER, created_at TEXT);
                CREATE TABLE qc_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    created_by INTEGER,
                    external_ai_enabled INTEGER,
                    status TEXT DEFAULT 'Needs Review',
                    processing_status TEXT DEFAULT 'completed',
                    progress_stage TEXT DEFAULT 'Completed',
                    progress_percent INTEGER DEFAULT 100,
                    progress_detail TEXT DEFAULT '',
                    estimated_seconds_remaining INTEGER,
                    processing_error TEXT DEFAULT '',
                    completed_at TEXT,
                    created_at TEXT
                );
                INSERT INTO users VALUES (1, 'Zhen', 'zhen@example.com', '');
                INSERT INTO projects VALUES (1, 'Legacy', 'general_fmcg', 1, '');
                """
            )
            conn.commit()
            conn.close()
            db = Database(path)

            run_id = db.create_run(1, 1, external_ai_enabled=True)

            run = db.get_run(run_id)
            self.assertEqual(run["processing_status"], "queued")
            self.assertEqual(run["progress_stage"], "Queued")
            self.assertEqual(run["progress_percent"], 0)

    def test_run_progress_is_persisted_from_queue_to_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.sqlite3")
            db.initialize()
            user_id = db.upsert_user("Zhen", "zhen@example.com")
            project_id = db.create_project("Zespri PanelVoice", user_id)

            run_id = db.create_run(project_id, user_id, external_ai_enabled=True)
            queued = db.get_run(run_id)
            self.assertEqual(queued["processing_status"], "queued")
            self.assertEqual(queued["progress_percent"], 0)
            self.assertEqual(queued["progress_stage"], "Queued")

            db.update_run_progress(run_id, "AI data review", 62, "Reviewing batch 2 / 3", 48)
            processing = db.get_run(run_id)
            self.assertEqual(processing["processing_status"], "processing")
            self.assertEqual(processing["progress_percent"], 62)
            self.assertEqual(processing["progress_detail"], "Reviewing batch 2 / 3")
            self.assertEqual(processing["estimated_seconds_remaining"], 48)

            db.mark_run_processing_complete(run_id)
            completed = db.get_run(run_id)
            self.assertEqual(completed["processing_status"], "completed")
            self.assertEqual(completed["progress_percent"], 100)
            self.assertEqual(completed["progress_stage"], "Completed")

    def test_run_processing_failure_is_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.sqlite3")
            db.initialize()
            user_id = db.upsert_user("Zhen", "zhen@example.com")
            project_id = db.create_project("Zespri PanelVoice", user_id)
            run_id = db.create_run(project_id, user_id, external_ai_enabled=True)

            db.mark_run_processing_failed(run_id, "AI data review", "Model timed out")

            failed = db.get_run(run_id)
            self.assertEqual(failed["processing_status"], "failed")
            self.assertEqual(failed["progress_stage"], "AI data review")
            self.assertEqual(failed["processing_error"], "Model timed out")

    def test_category_template_mismatch_issue_is_listed_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.sqlite3")
            db.initialize()
            user_id = db.upsert_user("Zhen", "zhen@example.com")
            project_id = db.create_project("Zespri PanelVoice", user_id)
            run_id = db.create_run(project_id, user_id, external_ai_enabled=True)

            db.add_issue(run_id, {"rule_id": "local_share_total", "severity": "High", "description": "Share total is 92%."})
            db.add_issue(
                run_id,
                {
                    "rule_id": "llm_category_template_mismatch",
                    "severity": "Medium",
                    "description": "Uploaded file content may not match the selected category template.",
                },
            )

            issues = db.list_issues(run_id)

            self.assertEqual(issues[0]["rule_id"], "llm_category_template_mismatch")
            self.assertEqual(issues[1]["rule_id"], "local_share_total")

    def test_project_persists_category_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.sqlite3")
            db.initialize()
            user_id = db.upsert_user("Zhen", "zhen@example.com")

            project_id = db.create_project("Fresh Produce Tracking", user_id, "fresh_produce")

            self.assertEqual(db.get_project(project_id)["category_template"], "fresh_produce")
            self.assertEqual(db.list_projects()[0]["category_template"], "fresh_produce")

    def test_project_rejects_unknown_category_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.sqlite3")
            db.initialize()
            user_id = db.upsert_user("Zhen", "zhen@example.com")

            with self.assertRaises(ValueError):
                db.create_project("Unknown Category", user_id, "not-a-category")

    def test_records_issue_status_change_as_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.sqlite3")
            db.initialize()
            user_id = db.upsert_user("Zhen", "zhen@example.com")
            project_id = db.create_project("Zespri PanelVoice", user_id)
            run_id = db.create_run(project_id, user_id, external_ai_enabled=True)
            issue_id = db.add_issue(
                run_id,
                {
                    "severity": "High",
                    "rule_id": "placeholder_text",
                    "description": "Template placeholder remains",
                    "file_name": "deck.pptx",
                    "location": "Slide 20",
                },
            )
            db.update_issue_status(issue_id, "confirmed_error", "Remove placeholder", user_id)
            events = db.list_issue_events(issue_id)
            self.assertEqual(events[-1]["status"], "confirmed_error")
            self.assertEqual(events[-1]["note"], "Remove placeholder")

    def test_run_can_only_be_completed_after_issue_and_page_review_are_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.sqlite3")
            db.initialize()
            user_id = db.upsert_user("Zhen", "zhen@example.com")
            project_id = db.create_project("Zespri PanelVoice", user_id)
            run_id = db.create_run(project_id, user_id, external_ai_enabled=True)
            issue_id = db.add_issue(
                run_id,
                {
                    "severity": "High",
                    "rule_id": "placeholder_text",
                    "description": "Template placeholder remains",
                    "file_name": "deck.pptx",
                    "location": "Slide 20",
                },
            )
            coverage_id = db.add_coverage(
                run_id,
                {
                    "file_name": "deck.pptx",
                    "page": 4,
                    "coverage_percent": 70,
                    "numbers_found": 2,
                    "low_confidence_count": 1,
                    "review_required": True,
                },
            )
            self.assertEqual(db.refresh_run_status(run_id), "Not Ready")
            with self.assertRaises(ValueError):
                db.complete_run(run_id, user_id, "Checked")

            db.update_issue_status(issue_id, "fixed", "Removed placeholder", user_id)
            self.assertEqual(db.refresh_run_status(run_id), "Needs Review")
            db.review_coverage(coverage_id, user_id, "Checked slide image")
            self.assertEqual(db.refresh_run_status(run_id), "Ready for Delivery")
            db.mark_run_processing_complete(run_id)
            db.complete_run(run_id, user_id, "Ready to share")

            completion = db.get_run_completion(run_id)
            self.assertEqual(completion["note"], "Ready to share")
            self.assertEqual(completion["user_id"], user_id)

    def test_persists_numeric_source_candidates_and_manual_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.sqlite3")
            db.initialize()
            user_id = db.upsert_user("Zhen", "zhen@example.com")
            project_id = db.create_project("Zespri PanelVoice", user_id)
            run_id = db.create_run(project_id, user_id, external_ai_enabled=False)
            match_id = db.add_numeric_match(
                run_id,
                {
                    "observation": {"file_name": "deck.pptx", "location": "Slide 2", "value": 40.2},
                    "candidates": [{"file_name": "source.xlsx", "location": "Summary!B2", "value": 0.402, "confidence": 0.96}],
                },
            )
            db.confirm_numeric_match(match_id, 0, user_id)
            db.add_mapping_constraint(project_id, "deck.pptx", 2, "source.xlsx", "Summary", user_id)

            self.assertEqual(db.list_numeric_matches(run_id)[0]["selected_candidate_index"], 0)
            self.assertEqual(db.list_mapping_constraints(project_id)[0]["sheet_name"], "Summary")

    def test_version_link_and_project_rule_can_be_confirmed_or_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "test.sqlite3")
            db.initialize()
            user_id = db.upsert_user("Zhen", "zhen@example.com")
            project_id = db.create_project("Zespri PanelVoice", user_id)
            run_id = db.create_run(project_id, user_id, external_ai_enabled=False)
            link_id = db.add_version_link(run_id, "deck_0527V.pptx", "deck_0521V.pptx", 1.0)
            rule_id = db.add_project_rule(project_id, {"name": "Footnote", "rule_type": "required_text", "config": {"text": "Source"}})

            db.confirm_version_link(link_id, True, user_id)
            db.set_project_rule_active(rule_id, False)

            self.assertTrue(db.list_version_links(run_id)[0]["confirmed"])
            self.assertFalse(db.list_project_rules(project_id)[0]["active"])


if __name__ == "__main__":
    unittest.main()
