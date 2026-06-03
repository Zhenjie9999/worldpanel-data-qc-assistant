# QC Run Progress Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make QC uploads return immediately and show a simple persisted progress bar with current stage and estimated remaining time.

**Architecture:** Persist run progress on `qc_runs`, execute analysis on a background thread, and report bounded stage updates through callbacks. The browser polls the existing run endpoint every two seconds while processing is active and renders one compact progress panel.

**Tech Stack:** Python stdlib `threading`, SQLite, vanilla JavaScript, CSS, unittest.

---

### Task 1: Persist Run Progress

**Files:**
- Modify: `worldpanel_qc/db.py`
- Test: `tests/test_db.py`

- [ ] Add failing tests for initial queued progress, progress updates, completion, and failure.
- [ ] Run focused tests and confirm missing progress fields fail.
- [ ] Add backward-compatible `qc_runs` columns and update methods.
- [ ] Run focused tests and confirm they pass.

### Task 2: Report Analysis Stages

**Files:**
- Modify: `worldpanel_qc/qc/runner.py`
- Modify: `worldpanel_qc/llm/reviewer.py`
- Test: `tests/test_runner.py`
- Test: `tests/test_llm_reviewer.py`

- [ ] Add failing tests for parsing, local-rule, AI-data, and Slides visual-review callbacks.
- [ ] Run focused tests and confirm callbacks are absent.
- [ ] Add optional progress callbacks without changing existing results.
- [ ] Run focused tests and confirm they pass.

### Task 3: Background Web Execution

**Files:**
- Modify: `worldpanel_qc/web.py`
- Test: `tests/test_web_progress.py`

- [ ] Add failing HTTP test proving run creation returns before a slow worker completes.
- [ ] Add background worker and persisted failure handling.
- [ ] Run focused HTTP tests and confirm progress can be polled.

### Task 4: Compact Progress UI

**Files:**
- Modify: `static/app.js`
- Modify: `static/styles.css`
- Modify: `README.md`

- [ ] Render a compact processing panel with stage, percentage, progress bar, detail, and approximate remaining time.
- [ ] Poll every two seconds only while the run is active.
- [ ] Reload the report automatically when processing completes.
- [ ] Document the behavior.
- [ ] Run the full suite and verify the local and temporary HTTPS trial URLs.

