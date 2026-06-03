from __future__ import annotations

import base64
import json
import mimetypes
import os
import shutil
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .auth import PasswordAuth
from .config import DB_PATH, EXPORT_DIR, LLM_SETTINGS_PATH, STATIC_DIR, SUPPORTED_EXTENSIONS, UPLOAD_DIR
from .db import Database
from .exports import export_excel_report, export_pdf_summary, render_printable_summary
from .llm.client import LlmClient
from .llm.reviewer import LlmReviewer
from .llm.settings import LlmSettingsStore
from .qc.runner import run_qc
from .qc.versions import compare_documents, filename_similarity, should_suggest_comparison
from .parsers import parse_file


db = Database(DB_PATH)
db.initialize()
llm_settings = LlmSettingsStore(LLM_SETTINGS_PATH)
auth = PasswordAuth(
    os.getenv("WORLDPANEL_QC_ACCESS_PASSWORD", ""),
    secure_cookie=os.getenv("WORLDPANEL_QC_COOKIE_SECURE", "").strip().lower() in {"1", "true", "yes"},
)
MAX_REQUEST_BYTES = int(os.getenv("WORLDPANEL_QC_MAX_REQUEST_BYTES", str(150 * 1024 * 1024)))
LLM_SETTINGS_EDITABLE = os.getenv("WORLDPANEL_QC_ALLOW_LLM_SETTINGS", "0" if auth.enabled else "1").strip().lower() in {
    "1",
    "true",
    "yes",
}


class PayloadTooLarge(ValueError):
    pass


class AppHandler(BaseHTTPRequestHandler):
    server_version = "WorldpanelQC/0.1"

    def _json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_REQUEST_BYTES:
            raise PayloadTooLarge("Request body is too large.")
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _authenticated(self) -> bool:
        return auth.is_authenticated(self.headers.get("Cookie", ""))

    def _remote_address(self) -> str:
        return self.headers.get("CF-Connecting-IP", "").strip() or self.client_address[0]

    def _require_auth(self, api: bool = True) -> bool:
        if self._authenticated():
            return True
        if api:
            self._json({"error": "Authentication required."}, HTTPStatus.UNAUTHORIZED)
        else:
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", "/login")
            self.end_headers()
        return False

    def _serve_file(self, path: Path, content_type: str | None = None):
        if not path.exists():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/health":
            return self._json({"status": "ok"})
        if path == "/login":
            return self._serve_file(STATIC_DIR / "login.html", "text/html; charset=utf-8")
        if path.startswith("/static/"):
            return self._serve_file(STATIC_DIR / Path(path).name)
        if path == "/api/auth/status":
            return self._json({"authentication_required": auth.enabled, "authenticated": self._authenticated()})
        if not self._require_auth(api=path.startswith("/api/")):
            return
        if path == "/":
            return self._serve_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
        if path == "/api/projects":
            return self._json({"projects": db.list_projects()})
        if path == "/api/runtime":
            return self._json({"authentication_required": auth.enabled, "llm_settings_editable": LLM_SETTINGS_EDITABLE})
        if path == "/api/llm/settings":
            if not LLM_SETTINGS_EDITABLE:
                return self._json({"error": "LLM settings are managed by the server administrator."}, HTTPStatus.FORBIDDEN)
            return self._json({"settings": llm_settings.public_settings()})
        if path.startswith("/api/projects/"):
            project_id = int(path.rsplit("/", 1)[-1])
            project = db.get_project(project_id)
            return self._json(
                {
                    "project": project,
                    "runs": db.list_runs(project_id),
                    "rules": db.list_project_rules(project_id),
                    "mappings": db.list_mapping_constraints(project_id),
                }
            )
        if path.startswith("/api/runs/") and path.endswith("/export.xlsx"):
            run_id = int(path.split("/")[3])
            return self._export_xlsx(run_id)
        if path.startswith("/api/runs/") and path.endswith("/export.pdf"):
            run_id = int(path.split("/")[3])
            return self._export_pdf(run_id)
        if path.startswith("/api/runs/") and path.endswith("/summary"):
            run_id = int(path.split("/")[3])
            return self._summary(run_id)
        if path.startswith("/api/runs/"):
            run_id = int(path.rsplit("/", 1)[-1])
            return self._json(self._run_payload(run_id))
        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            payload = self._body()
        except PayloadTooLarge as error:
            return self._json({"error": str(error)}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        if path == "/api/auth/login":
            result = auth.login(payload.get("password", ""), self._remote_address())
            if result.get("ok"):
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Set-Cookie", result["cookie"])
                body = json.dumps({"status": result["status"]}).encode("utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            status = HTTPStatus.TOO_MANY_REQUESTS if result["status"] == "rate_limited" else HTTPStatus.UNAUTHORIZED
            return self._json({"error": result["status"]}, status)
        if path == "/api/auth/logout":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Set-Cookie", auth.logout_cookie())
            body = b'{"status":"ok"}'
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if not self._require_auth():
            return
        if path == "/api/users":
            user_id = db.upsert_user(payload["name"], payload["email"])
            return self._json({"user": db.get_user(user_id)}, HTTPStatus.CREATED)
        if path == "/api/projects":
            project_id = db.create_project(
                payload["name"],
                int(payload["user_id"]),
                payload.get("category_template", "general_fmcg"),
            )
            return self._json({"project": db.get_project(project_id)}, HTTPStatus.CREATED)
        if path == "/api/llm/settings":
            if not LLM_SETTINGS_EDITABLE:
                return self._json({"error": "LLM settings are managed by the server administrator."}, HTTPStatus.FORBIDDEN)
            return self._json({"settings": llm_settings.save(payload)})
        if path == "/api/llm/test":
            if not LLM_SETTINGS_EDITABLE:
                return self._json({"error": "LLM settings are managed by the server administrator."}, HTTPStatus.FORBIDDEN)
            try:
                settings = self._merged_llm_settings(payload)
                result = LlmClient(
                    settings["endpoint"],
                    settings["model"],
                    settings["token"],
                    settings["timeout_seconds"],
                ).test_connection()
                return self._json(result, HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_GATEWAY)
            except (OSError, ValueError) as error:
                return self._json({"ok": False, "status": "configuration_error", "detail": str(error)}, HTTPStatus.BAD_REQUEST)
        if path.startswith("/api/projects/") and path.endswith("/rules"):
            project_id = int(path.split("/")[3])
            rule_id = db.add_project_rule(project_id, payload)
            return self._json({"rule_id": rule_id}, HTTPStatus.CREATED)
        if path.startswith("/api/rules/") and path.endswith("/active"):
            rule_id = int(path.split("/")[3])
            db.set_project_rule_active(rule_id, bool(payload["active"]))
            return self._json({"status": "ok"})
        if path.startswith("/api/projects/") and path.endswith("/mappings"):
            project_id = int(path.split("/")[3])
            mapping_id = db.add_mapping_constraint(
                project_id,
                payload["page_file_name"],
                int(payload["page"]) if payload.get("page") else None,
                payload["source_file_name"],
                payload.get("sheet_name", ""),
                int(payload["user_id"]),
            )
            return self._json({"mapping_id": mapping_id}, HTTPStatus.CREATED)
        if path.startswith("/api/projects/") and path.endswith("/runs"):
            project_id = int(path.split("/")[3])
            return self._create_run(project_id, payload)
        if path.startswith("/api/issues/") and path.endswith("/status"):
            issue_id = int(path.split("/")[3])
            db.update_issue_status(issue_id, payload["status"], payload.get("note", ""), int(payload["user_id"]))
            return self._json({"status": "ok"})
        if path.startswith("/api/coverage/") and path.endswith("/review"):
            coverage_id = int(path.split("/")[3])
            db.review_coverage(coverage_id, int(payload["user_id"]), payload.get("note", ""))
            return self._json({"status": "ok"})
        if path.startswith("/api/numeric-matches/") and path.endswith("/confirm"):
            match_id = int(path.split("/")[3])
            db.confirm_numeric_match(match_id, int(payload["candidate_index"]), int(payload["user_id"]))
            return self._json({"status": "ok"})
        if path.startswith("/api/version-links/") and path.endswith("/confirm"):
            link_id = int(path.split("/")[3])
            confirmed = bool(payload["confirmed"])
            db.confirm_version_link(link_id, confirmed, int(payload["user_id"]))
            if confirmed:
                self._generate_version_changes(link_id)
            return self._json({"status": "ok"})
        if path.startswith("/api/runs/") and path.endswith("/version-links"):
            run_id = int(path.split("/")[3])
            previous = db.get_run_file(int(payload["previous_file_id"]))
            if not previous:
                return self._json({"error": "Previous file not found."}, HTTPStatus.BAD_REQUEST)
            link_id = db.add_version_link(
                run_id,
                payload["current_file_name"],
                previous["file_name"],
                filename_similarity(payload["current_file_name"], previous["file_name"]),
                previous["id"],
            )
            db.confirm_version_link(link_id, True, int(payload["user_id"]))
            self._generate_version_changes(link_id)
            return self._json({"link_id": link_id}, HTTPStatus.CREATED)
        if path.startswith("/api/runs/") and path.endswith("/complete"):
            run_id = int(path.split("/")[3])
            try:
                db.complete_run(run_id, int(payload["user_id"]), payload.get("note", ""))
            except ValueError as error:
                return self._json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
            return self._json({"status": "ok"})
        self.send_error(404)

    def _create_run(self, project_id: int, payload: dict):
        run_id = db.create_run(project_id, int(payload["user_id"]), bool(payload.get("external_ai_enabled", True)))
        run_dir = UPLOAD_DIR / str(project_id) / str(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        paths = []
        for file in payload.get("files", []):
            name = Path(file["name"]).name
            suffix = Path(name).suffix.lower()
            if suffix not in SUPPORTED_EXTENSIONS:
                continue
            target = run_dir / name
            target.write_bytes(base64.b64decode(file["content_base64"]))
            paths.append(target)
        threading.Thread(
            target=self._process_run,
            args=(run_id, project_id, payload, paths, run_dir),
            daemon=True,
        ).start()
        return self._json(self._run_payload(run_id), HTTPStatus.CREATED)

    def _process_run(self, run_id: int, project_id: int, payload: dict, paths: list[Path], run_dir: Path) -> None:
        started = time.monotonic()

        def progress(stage: str, percent: int, detail: str = "", estimated_seconds_remaining: int | None = None) -> None:
            elapsed = max(time.monotonic() - started, 0.1)
            estimate = estimated_seconds_remaining
            if estimate is None and stage != "Slides visual review" and elapsed >= 2:
                estimate = max(1, round(elapsed * (100 - percent) / max(percent, 1)))
            db.update_run_progress(run_id, stage, percent, detail, estimate)

        try:
            progress("Queued", 1, "Waiting for QC processing")
            reviewer = self._llm_reviewer(payload, db.get_project(project_id), progress)
            result = run_qc(
                paths,
                db.list_project_rules(project_id),
                bool(payload.get("external_ai_enabled", True)),
                db.list_mapping_constraints(project_id),
                reviewer,
                run_dir / "visual-review",
                progress_callback=progress,
            )
            self._persist_run_result(run_id, project_id, paths, result)
            db.refresh_run_status(run_id)
            db.mark_run_processing_complete(run_id)
        except Exception as error:
            run = db.get_run(run_id) or {}
            db.mark_run_processing_failed(run_id, run.get("progress_stage", "Failed"), str(error))

    def _persist_run_result(self, run_id: int, project_id: int, paths: list[Path], result: dict) -> None:
        for document in result["documents"]:
            source = next(path for path in paths if path.name == document["file_name"])
            db.add_run_file(run_id, document["file_name"], document["file_type"], str(source), " | ".join(document.get("warnings", [])))
        for issue in result["issues"]:
            db.add_issue(run_id, issue)
        for item in result["coverage"]:
            db.add_coverage(run_id, item)
        for item in result["ai_logs"]:
            db.add_ai_log(run_id, item)
        for item in result["matches"]:
            db.add_numeric_match(run_id, item)
        previous_files = db.list_previous_files(project_id, run_id)
        for document in result["documents"]:
            candidate = next(
                (
                    previous
                    for previous in previous_files
                    if should_suggest_comparison(document["file_name"], previous["file_name"])
                ),
                None,
            )
            if candidate:
                db.add_version_link(
                    run_id,
                    document["file_name"],
                    candidate["file_name"],
                    filename_similarity(document["file_name"], candidate["file_name"]),
                    candidate["id"],
                )

    def _merged_llm_settings(self, payload: dict | None = None) -> dict:
        payload = payload or {}
        saved = llm_settings.load()
        settings = {
            "endpoint": str(payload.get("endpoint") or saved.get("endpoint") or "").strip(),
            "model": str(payload.get("model") or saved.get("model") or "").strip(),
            "token": str(payload.get("token") or saved.get("token") or "").strip(),
            "timeout_seconds": int(payload.get("timeout_seconds") or saved.get("timeout_seconds") or 60),
            "enabled": bool(saved.get("enabled", False)),
            "ocr_enabled": bool(saved.get("ocr_enabled", False)),
        }
        if not settings["endpoint"] or not settings["model"] or not settings["token"]:
            raise ValueError("Endpoint, model, and token are required.")
        return settings

    def _llm_reviewer(self, payload: dict, project: dict | None = None, progress_callback=None):
        logic_enabled = bool(payload.get("llm_logic_review_enabled", False))
        ocr_requested = bool(payload.get("external_ai_enabled", False))
        try:
            settings = self._merged_llm_settings()
        except (OSError, ValueError):
            return None
        if not settings["enabled"] or not (logic_enabled or (ocr_requested and settings["ocr_enabled"])):
            return None
        return LlmReviewer(
            LlmClient(settings["endpoint"], settings["model"], settings["token"], settings["timeout_seconds"]),
            endpoint_host=urlparse(settings["endpoint"]).netloc,
            logic_enabled=logic_enabled,
            ocr_enabled=ocr_requested and settings["ocr_enabled"],
            category_template=(project or {}).get("category_template", "general_fmcg"),
            progress_callback=progress_callback,
        )

    def _run_payload(self, run_id: int) -> dict:
        run = db.get_run(run_id)
        return {
            "run": run,
            "files": db.list_run_files(run_id),
            "issues": db.list_issues(run_id),
            "coverage": db.list_coverage(run_id),
            "ai_logs": db.list_ai_logs(run_id),
            "changes": db.list_run_changes(run_id),
            "matches": db.list_numeric_matches(run_id),
            "version_links": db.list_version_links(run_id),
            "previous_files": [
                {key: item[key] for key in ("id", "file_name", "file_type", "previous_run_id")}
                for item in db.list_previous_files(run["project_id"], run_id)
            ],
            "completion": db.get_run_completion(run_id),
        }

    def _generate_version_changes(self, link_id: int) -> None:
        link = db.get_version_link(link_id)
        if not link or not link.get("previous_run_file_id"):
            return
        previous = db.get_run_file(int(link["previous_run_file_id"]))
        current = next(
            (item for item in db.list_run_files(int(link["run_id"])) if item["file_name"] == link["current_file_name"]),
            None,
        )
        if not previous or not current:
            return
        db.clear_run_changes(int(link["run_id"]), link["current_file_name"])
        for change in compare_documents(parse_file(Path(current["stored_path"])), parse_file(Path(previous["stored_path"]))):
            db.add_run_change(int(link["run_id"]), change)

    def _export_xlsx(self, run_id: int):
        data = self._run_payload(run_id)
        run = data["run"]
        project = db.get_project(run["project_id"])
        path = EXPORT_DIR / f"worldpanel-qc-run-{run_id}.xlsx"
        export_excel_report(
            path,
            project,
            run,
            data["issues"],
            data["coverage"],
            data["ai_logs"],
            data["changes"],
            data["matches"],
            data["version_links"],
            data["completion"],
        )
        return self._serve_file(path, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    def _export_pdf(self, run_id: int):
        data = self._run_payload(run_id)
        run = data["run"]
        project = db.get_project(run["project_id"])
        path = EXPORT_DIR / f"worldpanel-qc-run-{run_id}.pdf"
        export_pdf_summary(path, project, run, data["issues"], data["coverage"])
        return self._serve_file(path, "application/pdf")

    def _summary(self, run_id: int):
        data = self._run_payload(run_id)
        run = data["run"]
        project = db.get_project(run["project_id"])
        html = render_printable_summary(project, run, data["issues"], data["coverage"]).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)


def serve(host: str = "127.0.0.1", port: int = 8765):
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Worldpanel Data QC Assistant running at http://{host}:{port}")
    server.serve_forever()
