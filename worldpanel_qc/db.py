from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from .llm.category_templates import validate_category_template
from .models import ISSUE_STATUSES


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize(self) -> None:
        with closing(self.connect()) as conn, conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category_template TEXT NOT NULL DEFAULT 'general_fmcg',
                    created_by INTEGER NOT NULL REFERENCES users(id),
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS project_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL REFERENCES projects(id),
                    name TEXT NOT NULL,
                    rule_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS qc_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL REFERENCES projects(id),
                    created_by INTEGER NOT NULL REFERENCES users(id),
                    external_ai_enabled INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Needs Review',
                    processing_status TEXT NOT NULL DEFAULT 'queued',
                    progress_stage TEXT NOT NULL DEFAULT 'Queued',
                    progress_percent INTEGER NOT NULL DEFAULT 0,
                    progress_detail TEXT NOT NULL DEFAULT '',
                    estimated_seconds_remaining INTEGER,
                    processing_error TEXT NOT NULL DEFAULT '',
                    completed_at TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS run_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL REFERENCES qc_runs(id),
                    file_name TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    stored_path TEXT NOT NULL,
                    parse_status TEXT NOT NULL DEFAULT 'pending',
                    warning TEXT
                );
                CREATE TABLE IF NOT EXISTS issues (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL REFERENCES qc_runs(id),
                    severity TEXT NOT NULL,
                    rule_id TEXT NOT NULL,
                    description TEXT NOT NULL,
                    file_name TEXT,
                    location TEXT,
                    evidence TEXT,
                    recommendation TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    note TEXT NOT NULL DEFAULT '',
                    details_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS issue_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    issue_id INTEGER NOT NULL REFERENCES issues(id),
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    status TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS coverage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL REFERENCES qc_runs(id),
                    file_name TEXT NOT NULL,
                    page INTEGER,
                    coverage_percent REAL NOT NULL,
                    numbers_found INTEGER NOT NULL,
                    low_confidence_count INTEGER NOT NULL,
                    review_required INTEGER NOT NULL,
                    detail TEXT,
                    reviewed INTEGER NOT NULL DEFAULT 0,
                    review_note TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS coverage_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    coverage_id INTEGER NOT NULL REFERENCES coverage(id),
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ai_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL REFERENCES qc_runs(id),
                    provider TEXT NOT NULL,
                    file_name TEXT,
                    page INTEGER,
                    status TEXT NOT NULL,
                    detail TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS version_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL REFERENCES qc_runs(id),
                    current_file_name TEXT NOT NULL,
                    previous_file_name TEXT NOT NULL,
                    previous_run_file_id INTEGER REFERENCES run_files(id),
                    similarity REAL NOT NULL,
                    confirmed INTEGER NOT NULL DEFAULT 0,
                    decision TEXT NOT NULL DEFAULT 'suggested'
                );
                CREATE TABLE IF NOT EXISTS version_link_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version_link_id INTEGER NOT NULL REFERENCES version_links(id),
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    confirmed INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS run_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL REFERENCES qc_runs(id),
                    change_type TEXT NOT NULL,
                    file_name TEXT,
                    location TEXT,
                    before_value TEXT,
                    after_value TEXT
                );
                CREATE TABLE IF NOT EXISTS numeric_matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL REFERENCES qc_runs(id),
                    observation_json TEXT NOT NULL,
                    candidates_json TEXT NOT NULL,
                    selected_candidate_index INTEGER,
                    confirmed_by INTEGER REFERENCES users(id),
                    confirmed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS mapping_constraints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL REFERENCES projects(id),
                    page_file_name TEXT NOT NULL,
                    page INTEGER,
                    source_file_name TEXT NOT NULL,
                    sheet_name TEXT NOT NULL DEFAULT '',
                    created_by INTEGER NOT NULL REFERENCES users(id),
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS run_completions (
                    run_id INTEGER PRIMARY KEY REFERENCES qc_runs(id),
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    note TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            self._ensure_column(conn, "coverage", "reviewed", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(conn, "coverage", "review_note", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "version_links", "previous_run_file_id", "INTEGER REFERENCES run_files(id)")
            self._ensure_column(conn, "version_links", "decision", "TEXT NOT NULL DEFAULT 'suggested'")
            self._ensure_column(conn, "projects", "category_template", "TEXT NOT NULL DEFAULT 'general_fmcg'")
            self._ensure_column(conn, "qc_runs", "processing_status", "TEXT NOT NULL DEFAULT 'completed'")
            self._ensure_column(conn, "qc_runs", "progress_stage", "TEXT NOT NULL DEFAULT 'Completed'")
            self._ensure_column(conn, "qc_runs", "progress_percent", "INTEGER NOT NULL DEFAULT 100")
            self._ensure_column(conn, "qc_runs", "progress_detail", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(conn, "qc_runs", "estimated_seconds_remaining", "INTEGER")
            self._ensure_column(conn, "qc_runs", "processing_error", "TEXT NOT NULL DEFAULT ''")

    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def upsert_user(self, name: str, email: str) -> int:
        with closing(self.connect()) as conn, conn:
            conn.execute(
                """
                INSERT INTO users(name, email, created_at) VALUES (?, ?, ?)
                ON CONFLICT(email) DO UPDATE SET name=excluded.name
                """,
                (name.strip(), email.strip().lower(), utc_now()),
            )
            return int(conn.execute("SELECT id FROM users WHERE email=?", (email.strip().lower(),)).fetchone()["id"])

    def create_project(self, name: str, user_id: int, category_template: str = "general_fmcg") -> int:
        category_template = validate_category_template(category_template)
        with closing(self.connect()) as conn, conn:
            cur = conn.execute(
                "INSERT INTO projects(name, category_template, created_by, created_at) VALUES (?, ?, ?, ?)",
                (name.strip(), category_template, user_id, utc_now()),
            )
            return int(cur.lastrowid)

    def create_run(self, project_id: int, user_id: int, external_ai_enabled: bool) -> int:
        with closing(self.connect()) as conn, conn:
            cur = conn.execute(
                """
                INSERT INTO qc_runs(
                    project_id, created_by, external_ai_enabled, processing_status,
                    progress_stage, progress_percent, progress_detail, created_at
                )
                VALUES (?, ?, ?, 'queued', 'Queued', 0, '', ?)
                """,
                (project_id, user_id, int(external_ai_enabled), utc_now()),
            )
            return int(cur.lastrowid)

    def update_run_progress(
        self,
        run_id: int,
        stage: str,
        percent: int,
        detail: str = "",
        estimated_seconds_remaining: int | None = None,
    ) -> None:
        with closing(self.connect()) as conn, conn:
            conn.execute(
                """
                UPDATE qc_runs
                SET processing_status='processing', progress_stage=?, progress_percent=?,
                    progress_detail=?, estimated_seconds_remaining=?, processing_error=''
                WHERE id=?
                """,
                (
                    stage.strip(),
                    max(0, min(99, int(percent))),
                    detail.strip(),
                    estimated_seconds_remaining,
                    run_id,
                ),
            )

    def mark_run_processing_complete(self, run_id: int) -> None:
        with closing(self.connect()) as conn, conn:
            conn.execute(
                """
                UPDATE qc_runs
                SET processing_status='completed', progress_stage='Completed', progress_percent=100,
                    progress_detail='QC report is ready.', estimated_seconds_remaining=0, processing_error=''
                WHERE id=?
                """,
                (run_id,),
            )

    def mark_run_processing_failed(self, run_id: int, stage: str, error: str) -> None:
        with closing(self.connect()) as conn, conn:
            conn.execute(
                """
                UPDATE qc_runs
                SET processing_status='failed', progress_stage=?, progress_detail='QC could not be completed.',
                    estimated_seconds_remaining=NULL, processing_error=?
                WHERE id=?
                """,
                (stage.strip() or "Failed", str(error).strip(), run_id),
            )

    def add_issue(self, run_id: int, issue: dict) -> int:
        with closing(self.connect()) as conn, conn:
            cur = conn.execute(
                """
                INSERT INTO issues(
                    run_id, severity, rule_id, description, file_name, location,
                    evidence, recommendation, details_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    issue.get("severity", "Medium"),
                    issue["rule_id"],
                    issue["description"],
                    issue.get("file_name"),
                    issue.get("location"),
                    issue.get("evidence"),
                    issue.get("recommendation"),
                    json.dumps(issue.get("details", {}), ensure_ascii=False),
                    utc_now(),
                ),
            )
            return int(cur.lastrowid)

    def update_issue_status(self, issue_id: int, status: str, note: str, user_id: int) -> None:
        if status not in ISSUE_STATUSES:
            raise ValueError(f"Unknown issue status: {status}")
        with closing(self.connect()) as conn, conn:
            row = conn.execute("SELECT run_id FROM issues WHERE id=?", (issue_id,)).fetchone()
            if not row:
                raise ValueError(f"Unknown issue: {issue_id}")
            run_id = int(row["run_id"])
            conn.execute("UPDATE issues SET status=?, note=? WHERE id=?", (status, note, issue_id))
            conn.execute(
                "INSERT INTO issue_events(issue_id, user_id, status, note, created_at) VALUES (?, ?, ?, ?, ?)",
                (issue_id, user_id, status, note, utc_now()),
            )
        self.refresh_run_status(run_id)

    def list_issue_events(self, issue_id: int) -> list[dict]:
        with closing(self.connect()) as conn, conn:
            rows = conn.execute(
                "SELECT * FROM issue_events WHERE issue_id=? ORDER BY id", (issue_id,)
            ).fetchall()
            return [dict(row) for row in rows]

    def get_user(self, user_id: int) -> dict | None:
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            return dict(row) if row else None

    def list_projects(self) -> list[dict]:
        with closing(self.connect()) as conn:
            rows = conn.execute(
                """
                SELECT p.*, COUNT(r.id) AS run_count
                FROM projects p LEFT JOIN qc_runs r ON r.project_id=p.id
                GROUP BY p.id ORDER BY p.id DESC
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def get_project(self, project_id: int) -> dict | None:
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
            return dict(row) if row else None

    def list_project_rules(self, project_id: int) -> list[dict]:
        with closing(self.connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM project_rules WHERE project_id=? ORDER BY id DESC", (project_id,)
            ).fetchall()
            return [
                {**dict(row), "config": json.loads(row["config_json"]), "active": bool(row["active"])}
                for row in rows
            ]

    def add_project_rule(self, project_id: int, rule: dict) -> int:
        with closing(self.connect()) as conn, conn:
            cur = conn.execute(
                """
                INSERT INTO project_rules(project_id, name, rule_type, severity, config_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    rule["name"],
                    rule["rule_type"],
                    rule.get("severity", "Medium"),
                    json.dumps(rule.get("config", {}), ensure_ascii=False),
                    utc_now(),
                ),
            )
            return int(cur.lastrowid)

    def set_project_rule_active(self, rule_id: int, active: bool) -> None:
        with closing(self.connect()) as conn, conn:
            conn.execute("UPDATE project_rules SET active=? WHERE id=?", (int(active), rule_id))

    def add_run_file(self, run_id: int, file_name: str, file_type: str, stored_path: str, warning: str = "") -> int:
        with closing(self.connect()) as conn, conn:
            cur = conn.execute(
                """
                INSERT INTO run_files(run_id, file_name, file_type, stored_path, parse_status, warning)
                VALUES (?, ?, ?, ?, 'parsed', ?)
                """,
                (run_id, file_name, file_type, stored_path, warning),
            )
            return int(cur.lastrowid)

    def add_coverage(self, run_id: int, item: dict) -> int:
        with closing(self.connect()) as conn, conn:
            cur = conn.execute(
                """
                INSERT INTO coverage(run_id, file_name, page, coverage_percent, numbers_found, low_confidence_count, review_required, detail)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    item["file_name"],
                    item.get("page"),
                    item.get("coverage_percent", 0),
                    item.get("numbers_found", 0),
                    item.get("low_confidence_count", 0),
                    int(bool(item.get("review_required"))),
                    item.get("detail", ""),
                ),
            )
            return int(cur.lastrowid)

    def add_ai_log(self, run_id: int, item: dict) -> int:
        with closing(self.connect()) as conn, conn:
            cur = conn.execute(
                """
                INSERT INTO ai_logs(run_id, provider, file_name, page, status, detail, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    item["provider"],
                    item.get("file_name"),
                    item.get("page"),
                    item.get("status", ""),
                    item.get("detail", ""),
                    utc_now(),
                ),
            )
            return int(cur.lastrowid)

    def list_runs(self, project_id: int) -> list[dict]:
        with closing(self.connect()) as conn:
            rows = conn.execute(
                "SELECT * FROM qc_runs WHERE project_id=? ORDER BY id DESC", (project_id,)
            ).fetchall()
            return [dict(row) for row in rows]

    def get_run(self, run_id: int) -> dict | None:
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT * FROM qc_runs WHERE id=?", (run_id,)).fetchone()
            return dict(row) if row else None

    def list_run_files(self, run_id: int) -> list[dict]:
        with closing(self.connect()) as conn:
            rows = conn.execute("SELECT * FROM run_files WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
            return [dict(row) for row in rows]

    def list_issues(self, run_id: int) -> list[dict]:
        with closing(self.connect()) as conn:
            rows = conn.execute("SELECT * FROM issues WHERE run_id=? ORDER BY CASE severity WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, id", (run_id,)).fetchall()
            return [dict(row) for row in rows]

    def list_coverage(self, run_id: int) -> list[dict]:
        with closing(self.connect()) as conn:
            rows = conn.execute("SELECT * FROM coverage WHERE run_id=? ORDER BY file_name, page", (run_id,)).fetchall()
            return [{**dict(row), "review_required": bool(row["review_required"]), "reviewed": bool(row["reviewed"])} for row in rows]

    def review_coverage(self, coverage_id: int, user_id: int, note: str) -> None:
        with closing(self.connect()) as conn, conn:
            row = conn.execute("SELECT run_id FROM coverage WHERE id=?", (coverage_id,)).fetchone()
            if not row:
                raise ValueError(f"Unknown coverage record: {coverage_id}")
            run_id = int(row["run_id"])
            conn.execute("UPDATE coverage SET reviewed=1, review_note=? WHERE id=?", (note.strip(), coverage_id))
            conn.execute(
                "INSERT INTO coverage_events(coverage_id, user_id, note, created_at) VALUES (?, ?, ?, ?)",
                (coverage_id, user_id, note.strip(), utc_now()),
            )
        self.refresh_run_status(run_id)

    def list_ai_logs(self, run_id: int) -> list[dict]:
        with closing(self.connect()) as conn:
            rows = conn.execute("SELECT * FROM ai_logs WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
            return [dict(row) for row in rows]

    def refresh_run_status(self, run_id: int) -> str:
        issues = self.list_issues(run_id)
        coverage = self.list_coverage(run_id)
        open_statuses = {"pending", "confirmed_error", "needs_review"}
        if any(i["severity"] == "High" and i["status"] in open_statuses for i in issues):
            status = "Not Ready"
        elif any(i["status"] in open_statuses for i in issues) or any(c["review_required"] and not c["reviewed"] for c in coverage):
            status = "Needs Review"
        else:
            status = "Ready for Delivery"
        with closing(self.connect()) as conn, conn:
            conn.execute("UPDATE qc_runs SET status=? WHERE id=?", (status, run_id))
        return status

    def complete_run(self, run_id: int, user_id: int, note: str) -> None:
        if not note.strip():
            raise ValueError("Completion note is required.")
        run = self.get_run(run_id)
        if not run or run.get("processing_status") != "completed":
            raise ValueError("QC processing is still in progress.")
        if self.refresh_run_status(run_id) != "Ready for Delivery":
            raise ValueError("Resolve open issues and confirm review pages before completing QC.")
        now = utc_now()
        with closing(self.connect()) as conn, conn:
            conn.execute(
                """
                INSERT INTO run_completions(run_id, user_id, note, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET user_id=excluded.user_id, note=excluded.note, created_at=excluded.created_at
                """,
                (run_id, user_id, note.strip(), now),
            )
            conn.execute("UPDATE qc_runs SET completed_at=? WHERE id=?", (now, run_id))

    def get_run_completion(self, run_id: int) -> dict | None:
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT * FROM run_completions WHERE run_id=?", (run_id,)).fetchone()
            return dict(row) if row else None

    def list_previous_files(self, project_id: int, before_run_id: int) -> list[dict]:
        with closing(self.connect()) as conn:
            rows = conn.execute(
                """
                SELECT f.*, r.id AS previous_run_id
                FROM run_files f JOIN qc_runs r ON r.id=f.run_id
                WHERE r.project_id=? AND r.id < ?
                ORDER BY r.id DESC, f.id
                """,
                (project_id, before_run_id),
            ).fetchall()
            return [dict(row) for row in rows]

    def add_version_link(
        self,
        run_id: int,
        current_file_name: str,
        previous_file_name: str,
        similarity: float,
        previous_run_file_id: int | None = None,
    ) -> int:
        with closing(self.connect()) as conn, conn:
            cur = conn.execute(
                """
                INSERT INTO version_links(run_id, current_file_name, previous_file_name, previous_run_file_id, similarity)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, current_file_name, previous_file_name, previous_run_file_id, similarity),
            )
            return int(cur.lastrowid)

    def list_version_links(self, run_id: int) -> list[dict]:
        with closing(self.connect()) as conn:
            rows = conn.execute("SELECT * FROM version_links WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
            return [{**dict(row), "confirmed": bool(row["confirmed"])} for row in rows]

    def confirm_version_link(self, link_id: int, confirmed: bool, user_id: int) -> None:
        with closing(self.connect()) as conn, conn:
            conn.execute(
                "UPDATE version_links SET confirmed=?, decision=? WHERE id=?",
                (int(confirmed), "accepted" if confirmed else "declined", link_id),
            )
            conn.execute(
                "INSERT INTO version_link_events(version_link_id, user_id, confirmed, created_at) VALUES (?, ?, ?, ?)",
                (link_id, user_id, int(confirmed), utc_now()),
            )

    def get_version_link(self, link_id: int) -> dict | None:
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT * FROM version_links WHERE id=?", (link_id,)).fetchone()
            return dict(row) if row else None

    def get_run_file(self, file_id: int) -> dict | None:
        with closing(self.connect()) as conn:
            row = conn.execute("SELECT * FROM run_files WHERE id=?", (file_id,)).fetchone()
            return dict(row) if row else None

    def clear_run_changes(self, run_id: int, file_name: str | None = None) -> None:
        with closing(self.connect()) as conn, conn:
            if file_name:
                conn.execute("DELETE FROM run_changes WHERE run_id=? AND file_name=?", (run_id, file_name))
            else:
                conn.execute("DELETE FROM run_changes WHERE run_id=?", (run_id,))

    def add_run_change(self, run_id: int, change: dict) -> int:
        with closing(self.connect()) as conn, conn:
            cur = conn.execute(
                """
                INSERT INTO run_changes(run_id, change_type, file_name, location, before_value, after_value)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    change.get("type", ""),
                    change.get("file_name"),
                    change.get("location"),
                    str(change.get("before", "")),
                    str(change.get("after", "")),
                ),
            )
            return int(cur.lastrowid)

    def list_run_changes(self, run_id: int) -> list[dict]:
        with closing(self.connect()) as conn:
            rows = conn.execute("SELECT * FROM run_changes WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
            return [
                {
                    "type": row["change_type"],
                    "file_name": row["file_name"],
                    "location": row["location"],
                    "before": row["before_value"],
                    "after": row["after_value"],
                }
                for row in rows
            ]

    def add_numeric_match(self, run_id: int, match: dict) -> int:
        with closing(self.connect()) as conn, conn:
            cur = conn.execute(
                "INSERT INTO numeric_matches(run_id, observation_json, candidates_json) VALUES (?, ?, ?)",
                (
                    run_id,
                    json.dumps(match["observation"], ensure_ascii=False),
                    json.dumps(match["candidates"], ensure_ascii=False),
                ),
            )
            return int(cur.lastrowid)

    def list_numeric_matches(self, run_id: int) -> list[dict]:
        with closing(self.connect()) as conn:
            rows = conn.execute("SELECT * FROM numeric_matches WHERE run_id=? ORDER BY id", (run_id,)).fetchall()
            return [
                {
                    **dict(row),
                    "observation": json.loads(row["observation_json"]),
                    "candidates": json.loads(row["candidates_json"]),
                    "status": "matched" if json.loads(row["candidates_json"]) else "unmatched",
                }
                for row in rows
            ]

    def confirm_numeric_match(self, match_id: int, candidate_index: int, user_id: int) -> None:
        with closing(self.connect()) as conn, conn:
            row = conn.execute("SELECT candidates_json FROM numeric_matches WHERE id=?", (match_id,)).fetchone()
            if not row:
                raise ValueError(f"Unknown numeric match: {match_id}")
            candidates = json.loads(row["candidates_json"])
            if candidate_index < 0 or candidate_index >= len(candidates):
                raise ValueError("Candidate index is out of range.")
            conn.execute(
                "UPDATE numeric_matches SET selected_candidate_index=?, confirmed_by=?, confirmed_at=? WHERE id=?",
                (candidate_index, user_id, utc_now(), match_id),
            )

    def add_mapping_constraint(
        self,
        project_id: int,
        page_file_name: str,
        page: int | None,
        source_file_name: str,
        sheet_name: str,
        user_id: int,
    ) -> int:
        with closing(self.connect()) as conn, conn:
            cur = conn.execute(
                """
                INSERT INTO mapping_constraints(project_id, page_file_name, page, source_file_name, sheet_name, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (project_id, page_file_name.strip(), page, source_file_name.strip(), sheet_name.strip(), user_id, utc_now()),
            )
            return int(cur.lastrowid)

    def list_mapping_constraints(self, project_id: int) -> list[dict]:
        with closing(self.connect()) as conn:
            rows = conn.execute("SELECT * FROM mapping_constraints WHERE project_id=? ORDER BY id DESC", (project_id,)).fetchall()
            return [dict(row) for row in rows]
