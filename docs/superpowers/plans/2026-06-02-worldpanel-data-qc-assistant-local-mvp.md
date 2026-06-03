# Worldpanel Data QC Assistant Local MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows local web application that accepts Excel, PPTX, and PDF files, runs explainable QC checks, records issue review status, suggests prior-version comparisons, and exports an Excel detail report plus printable PDF summary.

**Architecture:** Use a dependency-light Python application with a local HTTP server, SQLite persistence, and a static browser UI. Parsing, rules, matching, version comparison, exports, and storage are isolated modules. External AI/OCR is represented by a configurable adapter with explicit logs and a local fallback; this allows the local MVP to run without credentials while preserving the production integration boundary.

**Tech Stack:** Python 3.12 standard library, SQLite, `openpyxl`, `python-pptx`, `pypdf`, vanilla HTML/CSS/JavaScript, `unittest`

---

## Scope Split

The complete product contains several independent systems. This plan produces a useful local MVP with clear extension points:

1. Local projects, lightweight identity, QC runs, issue workflow, and audit trail.
2. Structured parsing for `.xlsx`, `.pptx`, and `.pdf`; `.xls` conversion attempt with clear fallback warning.
3. Explainable built-in QC rules and project-level custom rules.
4. Numeric cross-file matching with candidate confidence.
5. Filename similarity and manual previous-version selection.
6. Excel detail export and printable HTML/PDF summary.
7. Page coverage records and external AI/OCR adapter logs.

Image-region OCR and complex visual-model integration are adapter-driven. The MVP records pages needing visual review when no configured OCR provider is available.

## File Structure

```text
app.py                              Local server entrypoint
start_worldpanel_qc.bat             Windows double-click launcher
worldpanel_qc/
  __init__.py
  config.py                         Paths and supported file types
  db.py                             SQLite schema and persistence helpers
  models.py                         Shared dictionaries and status constants
  parsers/
    __init__.py
    excel.py                        XLSX parsing and XLS conversion attempt
    pptx.py                         PPTX text, table, chart, and coverage parsing
    pdf.py                          PDF text extraction and coverage records
  qc/
    __init__.py
    rules.py                        Built-in and project custom rules
    matching.py                     Cross-file numeric matching
    versions.py                     Filename normalization and version diff
    runner.py                       QC orchestration
  exports.py                        XLSX detail and printable summary export
  web.py                            HTTP routes and JSON API
static/
  index.html                        Local application shell
  app.js                            UI interactions
  styles.css                        Work-focused interface styles
tests/
  test_versions.py
  test_rules.py
  test_matching.py
  test_db.py
```

## Task 1: Bootstrap Local Application

**Files:**
- Create: `app.py`
- Create: `start_worldpanel_qc.bat`
- Create: `worldpanel_qc/__init__.py`
- Create: `worldpanel_qc/config.py`
- Create: `worldpanel_qc/web.py`
- Create: `static/index.html`
- Create: `static/styles.css`
- Create: `static/app.js`

- [ ] Create a local HTTP server on `127.0.0.1:8765`.
- [ ] Add `GET /`, `GET /static/*`, and `GET /api/health`.
- [ ] Create a Windows launcher that starts the service and opens the browser.
- [ ] Verify `http://127.0.0.1:8765/api/health` returns `{"status":"ok"}`.

## Task 2: Add SQLite Persistence and Identity

**Files:**
- Create: `worldpanel_qc/db.py`
- Create: `worldpanel_qc/models.py`
- Create: `tests/test_db.py`
- Modify: `worldpanel_qc/web.py`

- [ ] Define tables: `users`, `projects`, `project_rules`, `qc_runs`, `run_files`, `issues`, `issue_events`, `coverage`, `ai_logs`, `version_links`.
- [ ] Add API routes for current user, project creation, project listing, and project detail.
- [ ] Store user name and company email locally.
- [ ] Add tests for project creation and issue-event audit records.

## Task 3: Parse Excel, PPTX, and PDF

**Files:**
- Create: `worldpanel_qc/parsers/__init__.py`
- Create: `worldpanel_qc/parsers/excel.py`
- Create: `worldpanel_qc/parsers/pptx.py`
- Create: `worldpanel_qc/parsers/pdf.py`

- [ ] Parse `.xlsx` sheets, cells, formulas, number formats, hidden rows, hidden columns, and visible numeric values.
- [ ] Attempt `.xls` conversion through installed Microsoft Excel COM automation; return an actionable warning if Excel conversion is unavailable.
- [ ] Parse `.pptx` slide text, tables, chart series, image counts, and per-slide coverage records.
- [ ] Parse `.pdf` page text and numeric tokens with `pypdf`; create review-required coverage records for image-heavy or low-text pages.
- [ ] Return normalized parser output with `documents`, `numbers`, `texts`, `pages`, and `warnings`.

## Task 4: Implement Built-In and Project Rules

**Files:**
- Create: `worldpanel_qc/qc/__init__.py`
- Create: `worldpanel_qc/qc/rules.py`
- Create: `tests/test_rules.py`

- [ ] Add built-in file rules:
  - unsupported `.ppt`
  - Excel formula errors
  - hidden row/column warning
  - PPTX/PDF placeholder warning
  - corrupted-text heuristic
  - missing source warning for data-heavy PPTX/PDF pages
  - page requiring visual review
- [ ] Add project-rule types:
  - `required_text`
  - `forbidden_text`
  - `number_range`
  - `required_metadata`
- [ ] Add tests for placeholder detection, required-text rules, and page-review issues.

## Task 5: Implement Cross-File Numeric Matching

**Files:**
- Create: `worldpanel_qc/qc/matching.py`
- Create: `tests/test_matching.py`

- [ ] Normalize raw numbers, percentages, common units, and rounding tolerance.
- [ ] Match PPTX/PDF numeric observations to Excel candidates.
- [ ] Score exact, rounded, percentage-scale, and contextual matches.
- [ ] Preserve the highest-confidence source and alternative candidates.
- [ ] Emit review issues when no plausible source exists or the best match is low confidence.
- [ ] Add tests for exact, percentage, rounded, and ambiguous matches.

## Task 6: Implement Version Suggestions and Differences

**Files:**
- Create: `worldpanel_qc/qc/versions.py`
- Create: `tests/test_versions.py`

- [ ] Normalize filenames by removing dates, version markers, separators, and extensions.
- [ ] Compute similarity and only suggest comparison when type matches and similarity is at least `0.90`.
- [ ] Support manual previous-version selection.
- [ ] Compare extracted text and numeric observations.
- [ ] Produce separate change records for numeric changes, text changes, structure changes, new issues, fixed issues, and persistent issues.
- [ ] Add tests for similar filenames, unrelated filenames, and numeric diffs.

## Task 7: Orchestrate QC Runs

**Files:**
- Create: `worldpanel_qc/qc/runner.py`
- Modify: `worldpanel_qc/web.py`

- [ ] Add file upload API for a selected project.
- [ ] Copy uploaded files into project-local run storage.
- [ ] Parse files, run built-in rules, run project rules, run cross-file matching, compute coverage, and store issues.
- [ ] Add API routes for run detail, issue filtering, issue status update, notes, and QC completion.
- [ ] Derive overall status:
  - `Not Ready`: open High issues
  - `Needs Review`: unresolved review-required or low-confidence items
  - `Ready for Delivery`: no open High or review-required items

## Task 8: Export Reports

**Files:**
- Create: `worldpanel_qc/exports.py`
- Modify: `worldpanel_qc/web.py`

- [ ] Generate Excel workbook sheets:
  - `Summary`
  - `Current File QC`
  - `Changes vs Previous`
  - `Coverage`
  - `AI Logs`
- [ ] Generate a print-ready HTML summary.
- [ ] Add a browser print action so users can save the summary as PDF.
- [ ] Add export API routes.

## Task 9: Build the Browser UI

**Files:**
- Modify: `static/index.html`
- Modify: `static/styles.css`
- Modify: `static/app.js`

- [ ] Build lightweight identity setup.
- [ ] Build project list and create-project form.
- [ ] Build new-QC upload view with AI toggle.
- [ ] Build run summary metrics.
- [ ] Build tabs:
  - `Current File QC`
  - `Changes vs Previous Version`
  - `Coverage`
  - `AI Logs`
- [ ] Add issue status controls and notes.
- [ ] Add export buttons.
- [ ] Keep the layout dense, work-focused, and readable on common desktop widths.

## Task 10: Verify with Real Sample Files

**Files:**
- Use: `qc_input_0527.xlsx`
- Use: `qc_input_panelvoice_0527v.pptx`

- [ ] Run `python -m unittest discover -s tests -v`.
- [ ] Start `start_worldpanel_qc.bat`.
- [ ] Create a test user and project.
- [ ] Upload the Excel and PPTX sample files.
- [ ] Confirm the run produces issues, slide coverage records, and cross-file candidates.
- [ ] Export the Excel detail report.
- [ ] Open the printable summary and verify browser PDF save flow.
- [ ] Verify the local UI in a browser at desktop width.

## Delivery Notes

- The MVP runs without network credentials.
- External AI/OCR is configurable and logged, but a real provider requires a separately approved endpoint and credentials.
- Complex image charts without an active OCR provider are never silently skipped; they appear as review-required coverage items.
- Git commits are listed conceptually in the Superpowers workflow, but the current machine does not expose a working `git` executable.
