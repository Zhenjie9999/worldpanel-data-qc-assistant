import base64
import json
import tempfile
import threading
import time
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import worldpanel_qc.web as web
from worldpanel_qc.auth import PasswordAuth
from worldpanel_qc.db import Database


class WebProgressTests(unittest.TestCase):
    def setUp(self):
        self.original_db = web.db
        self.original_auth = web.auth
        self.tmp = tempfile.TemporaryDirectory()
        web.db = Database(Path(self.tmp.name) / "test.sqlite3")
        web.db.initialize()
        web.auth = PasswordAuth(password="")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), web.AppHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        web.db = self.original_db
        web.auth = self.original_auth
        self.tmp.cleanup()

    def post(self, path, payload):
        request = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            return json.load(response)

    def get(self, path):
        with urllib.request.urlopen(self.base_url + path, timeout=3) as response:
            return json.load(response)

    def test_run_creation_returns_while_worker_is_processing_and_can_be_polled(self):
        user_id = web.db.upsert_user("Zhen", "zhen@example.com")
        project_id = web.db.create_project("Progress test", user_id)
        release = threading.Event()

        def slow_qc(*_args, progress_callback=None, **_kwargs):
            progress_callback("AI data review", 62, "Reviewing data batch 2 / 3")
            release.wait(timeout=3)
            return {"documents": [], "issues": [], "coverage": [], "ai_logs": [], "matches": []}

        with patch.object(web, "run_qc", side_effect=slow_qc):
            started = time.monotonic()
            created = self.post(
                f"/api/projects/{project_id}/runs",
                {
                    "user_id": user_id,
                    "external_ai_enabled": False,
                    "files": [{"name": "source.xlsx", "content_base64": base64.b64encode(b"file").decode("ascii")}],
                },
            )
            elapsed = time.monotonic() - started
            self.assertLess(elapsed, 1)
            run_id = created["run"]["id"]
            for _ in range(20):
                polled = self.get(f"/api/runs/{run_id}")
                if polled["run"]["progress_stage"] == "AI data review":
                    break
                time.sleep(0.05)
            self.assertEqual(polled["run"]["processing_status"], "processing")
            self.assertEqual(polled["run"]["progress_percent"], 62)
            release.set()
            for _ in range(20):
                polled = self.get(f"/api/runs/{run_id}")
                if polled["run"]["processing_status"] == "completed":
                    break
                time.sleep(0.05)
            self.assertEqual(polled["run"]["processing_status"], "completed")
            self.assertEqual(polled["run"]["progress_percent"], 100)

    def test_worker_failure_is_visible_when_polled(self):
        user_id = web.db.upsert_user("Zhen", "zhen@example.com")
        project_id = web.db.create_project("Progress failure", user_id)

        with patch.object(web, "run_qc", side_effect=RuntimeError("Synthetic failure")):
            created = self.post(
                f"/api/projects/{project_id}/runs",
                {"user_id": user_id, "external_ai_enabled": False, "files": []},
            )
            run_id = created["run"]["id"]
            for _ in range(20):
                polled = self.get(f"/api/runs/{run_id}")
                if polled["run"]["processing_status"] == "failed":
                    break
                time.sleep(0.05)
            self.assertEqual(polled["run"]["processing_status"], "failed")
            self.assertIn("Synthetic failure", polled["run"]["processing_error"])

    def test_run_creation_persists_scope_metadata_from_payload(self):
        user_id = web.db.upsert_user("Zhen", "zhen@example.com")
        project_id = web.db.create_project("Scope metadata", user_id)

        with patch.object(web, "run_qc", return_value={"documents": [], "issues": [], "coverage": [], "ai_logs": [], "matches": []}):
            created = self.post(
                f"/api/projects/{project_id}/runs",
                {
                    "user_id": user_id,
                    "external_ai_enabled": False,
                    "output_language": "en",
                    "review_goal": "Check only pricing slides",
                    "scope_status": "confirmed",
                    "scope": {"mode": "focused", "pages": [2, 3]},
                    "scope_questions": [{"question": "Cross-check?", "answer": "No"}],
                    "files": [],
                },
            )

        run = created["run"]
        self.assertEqual(run["output_language"], "en")
        self.assertEqual(run["review_goal"], "Check only pricing slides")
        self.assertEqual(run["scope_status"], "confirmed")
        self.assertIn('"focused"', run["scope_json"])

    def test_scope_assist_returns_boundary_questions(self):
        user_id = web.db.upsert_user("Zhen", "zhen@example.com")
        project_id = web.db.create_project("Scope assist", user_id)

        result = self.post(
            f"/api/projects/{project_id}/scope-assist",
            {
                "review_goal": "Check pricing pages",
                "files": [
                    {"name": "deck.pptx"},
                    {"name": "source.xlsx"},
                ],
            },
        )

        self.assertIn("questions", result)
        self.assertTrue(any("PPT" in item["question"] and "Excel" in item["question"] for item in result["questions"]))


if __name__ == "__main__":
    unittest.main()
