# Worldpanel Smart QC Scope Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add smart run scope, localized export, grouped issue summaries, suspicious-only source matching, and safe caching without breaking the current QC flow.

**Architecture:** Keep the existing `run_qc` pipeline intact and add optional layers around it: run metadata in SQLite, scope helpers before AI review, issue grouping after issue creation, matching filtering before persistence, localization in export functions, and cache wrappers around parsing/AI calls. All new behavior must fall back to the current full-check behavior.

**Tech Stack:** Python standard library, SQLite, `unittest`, existing HTML/CSS/JavaScript frontend, existing OpenAI-compatible LLM client.

---

### Task 1: Run Metadata And Scope Persistence

**Files:**
- Modify: `worldpanel_qc/db.py`
- Modify: `worldpanel_qc/web.py`
- Modify: `static/index.html`
- Modify: `static/app.js`
- Test: `tests/test_db.py`
- Test: `tests/test_web_progress.py`

- [ ] Add `output_language`, `review_goal`, `scope_status`, `scope_json`, and `scope_questions_json` columns to `qc_runs`.
- [ ] Make `create_run` accept those values with safe defaults: Chinese output, full check, confirmed scope when no assistant is used.
- [ ] Send the fields from the New QC run dialog.
- [ ] Include the fields in run detail responses.
- [ ] Test that old run creation still works and new metadata round-trips.

### Task 2: Scope Parsing And AI Boundary Assistant

**Files:**
- Create: `worldpanel_qc/qc/scope.py`
- Create: `worldpanel_qc/llm/scope_assistant.py`
- Modify: `worldpanel_qc/web.py`
- Test: `tests/test_scope.py`
- Test: `tests/test_scope_assistant.py`

- [ ] Parse user scope text into page ranges, sheet names, focus metrics, cross-check preference, and mode.
- [ ] Build lightweight file overview from uploaded file names and already parsed documents when available.
- [ ] Add an endpoint that can return up to 3 boundary questions, with deterministic fallback questions when LLM is unavailable.
- [ ] Store confirmed scope in `scope_json`.
- [ ] Test malformed AI output and missing model fallback.

### Task 3: Suspicious-Only Source Matching

**Files:**
- Create: `worldpanel_qc/qc/match_review.py`
- Modify: `worldpanel_qc/qc/runner.py`
- Modify: `static/app.js`
- Modify: `worldpanel_qc/exports.py`
- Test: `tests/test_match_review.py`
- Test: `tests/test_runner.py`

- [ ] Classify matches as suspicious when no candidate, low confidence, close competing candidates, numeric conflict, or manual confirmation exists.
- [ ] Persist only suspicious matches by default while keeping the calculation logic unchanged.
- [ ] Update UI wording from all source matches to source matching concerns.
- [ ] Test that clean high-confidence matches are omitted and conflicts remain.

### Task 4: Issue Grouping

**Files:**
- Create: `worldpanel_qc/qc/issue_grouping.py`
- Modify: `worldpanel_qc/web.py`
- Modify: `static/app.js`
- Modify: `static/styles.css`
- Modify: `worldpanel_qc/exports.py`
- Test: `tests/test_issue_grouping.py`

- [ ] Categorize issues by rule id and LLM content into price, share, unit/decimal, source conflict, trend, annotation, category mismatch, file structure, and other.
- [ ] Return grouped issue summaries in run detail.
- [ ] Render grouped summaries above the issue table.
- [ ] Include grouped summaries in exports.
- [ ] Test category assignment, severity rollup, and detail counts.

### Task 5: Localized Export

**Files:**
- Create: `worldpanel_qc/reporting/localization.py`
- Modify: `worldpanel_qc/exports.py`
- Modify: `worldpanel_qc/web.py`
- Modify: `static/index.html`
- Modify: `static/app.js`
- Test: `tests/test_localization.py`
- Test: `tests/test_exports.py`

- [ ] Add Chinese, English, and bilingual labels for report headings, sheet names, columns, status labels, and recommendation headings.
- [ ] Allow export URLs to include `?lang=zh|en|bilingual`.
- [ ] Use run default language when no export language is provided.
- [ ] Test exported workbook sheet names and summary labels by language.

### Task 6: Cache Layer

**Files:**
- Create: `worldpanel_qc/cache.py`
- Modify: `worldpanel_qc/qc/runner.py`
- Modify: `worldpanel_qc/llm/client.py`
- Modify: `worldpanel_qc/llm/visual_review.py`
- Test: `tests/test_cache.py`
- Test: `tests/test_runner.py`

- [ ] Add JSON file cache under `local_data/cache`.
- [ ] Cache parsed file results by file hash and parser version.
- [ ] Cache LLM responses by endpoint host, model, prompt payload hash, category template, and scope.
- [ ] Cache rendered PPT page images by file hash and page.
- [ ] Make cache failure non-fatal.
- [ ] Test cache hit/miss behavior and safe fallback when cache files are corrupt.

### Task 7: Verification And Deployment Sync

**Files:**
- Modify as needed based on test failures.

- [ ] Run targeted tests for each task.
- [ ] Run `python -m unittest discover -s tests -v`.
- [ ] Restart local/public app services only after active runs finish or when safe.
- [ ] Push the completed version to GitHub.
