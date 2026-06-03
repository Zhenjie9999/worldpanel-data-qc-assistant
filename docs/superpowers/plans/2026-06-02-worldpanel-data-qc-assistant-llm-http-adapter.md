# Worldpanel Data QC Assistant LLM HTTP Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a configurable trusted-intranet HTTP LLM adapter that reviews minimized structured QC candidates and OCRs only Slides pages requiring visual review.

**Architecture:** Keep deterministic logic in local Python modules and use the LLM only as a second-pass reviewer. Store the API key with Windows DPAPI in a local settings file, never in source, logs, exports, or API responses. Render PPTX review pages to PNG with PowerPoint COM when available, then send only selected screenshots to the existing Chat Completions-compatible endpoint.

**Tech Stack:** Python standard library, Windows DPAPI via `ctypes`, PowerPoint COM via PowerShell, SQLite, existing `ThreadingHTTPServer`, HTML/CSS/JavaScript, `unittest`.

---

### Task 1: Local encrypted model settings

**Files:**
- Create: `worldpanel_qc/llm/settings.py`
- Create: `worldpanel_qc/llm/__init__.py`
- Test: `tests/test_llm_settings.py`

- [ ] Write failing tests for DPAPI-backed round-trip storage, safe public settings, and the HTTP warning.
- [ ] Run `python -m unittest tests.test_llm_settings -v` and confirm missing module failure.
- [ ] Implement `LlmSettingsStore` with `save()`, `load()`, `public_settings()`, and `http_warning()`.
- [ ] Store the protected token under `local_data/llm-settings.json`; never return the token from `public_settings()`.
- [ ] Run `python -m unittest tests.test_llm_settings -v`.

### Task 2: Chat Completions-compatible client

**Files:**
- Create: `worldpanel_qc/llm/client.py`
- Test: `tests/test_llm_client.py`

- [ ] Write failing tests with a local fake HTTP server for successful JSON responses, invalid JSON content, timeout-safe failure, and image `data:` URL payload shape.
- [ ] Run `python -m unittest tests.test_llm_client -v` and confirm missing client failure.
- [ ] Implement `LlmClient.test_connection()`, `review_candidates()`, and `ocr_image()`.
- [ ] Send `Authorization: Bearer <token>` only in the request header.
- [ ] Parse fenced or plain JSON content without logging the prompt or token.
- [ ] Run `python -m unittest tests.test_llm_client -v`.

### Task 3: Deterministic logic candidate generation

**Files:**
- Create: `worldpanel_qc/qc/logic_candidates.py`
- Modify: `worldpanel_qc/qc/runner.py`
- Test: `tests/test_logic_candidates.py`

- [ ] Write failing tests for share totals outside `100 ± 0.5`, price outliers such as `55, 60, 62, 1000`, and normal groups that remain clean.
- [ ] Run `python -m unittest tests.test_logic_candidates -v`.
- [ ] Implement local candidate generators that use Excel row labels, cell locations, percent formats, and robust median/MAD comparisons.
- [ ] Return minimized structured candidate payloads and local rule issues.
- [ ] Run `python -m unittest tests.test_logic_candidates -v`.

### Task 4: PPTX visual-review page rendering

**Files:**
- Create: `worldpanel_qc/llm/visual_review.py`
- Test: `tests/test_visual_review.py`

- [ ] Write failing tests for selecting only `review_required` PPTX pages and graceful fallback when PowerPoint export is unavailable.
- [ ] Run `python -m unittest tests.test_visual_review -v`.
- [ ] Implement `review_page_numbers()` and PowerPoint COM PNG export into each run upload directory.
- [ ] Ensure full files are not sent to the LLM; only rendered PNG bytes are eligible for `ocr_image()`.
- [ ] Run `python -m unittest tests.test_visual_review -v`.

### Task 5: LLM orchestration and auditable results

**Files:**
- Create: `worldpanel_qc/llm/reviewer.py`
- Modify: `worldpanel_qc/qc/runner.py`
- Modify: `worldpanel_qc/web.py`
- Test: `tests/test_llm_reviewer.py`

- [ ] Write failing tests that verify minimized logic candidates become `llm_logic_review` issues, OCR is attempted only for review pages, and failures produce AI logs without breaking local QC.
- [ ] Run `python -m unittest tests.test_llm_reviewer -v`.
- [ ] Implement a reviewer that combines local candidates, structured LLM findings, OCR findings, and redacted AI logs.
- [ ] Pass the reviewer into `run_qc()` only when enabled and configured.
- [ ] Run `python -m unittest tests.test_llm_reviewer -v`.

### Task 6: Local settings API and UI

**Files:**
- Modify: `worldpanel_qc/web.py`
- Modify: `static/index.html`
- Modify: `static/app.js`
- Modify: `static/styles.css`
- Test: `tests/test_llm_settings_api.py`

- [ ] Write failing HTTP handler tests for reading redacted settings, saving settings, and testing a synthetic connection.
- [ ] Run `python -m unittest tests.test_llm_settings_api -v`.
- [ ] Add `GET /api/llm/settings`, `POST /api/llm/settings`, and `POST /api/llm/test`.
- [ ] Add `LLM Settings`, HTTP risk warning, API address, model, token, timeout, connection test, and `Enable LLM logic review`.
- [ ] Keep OCR opt-in visible in the new-run dialog.
- [ ] Run `python -m unittest tests.test_llm_settings_api -v`.

### Task 7: Documentation and end-to-end verification

**Files:**
- Modify: `README.md`

- [ ] Document intranet-only HTTP usage, DPAPI token storage, minimized payloads, OCR screenshot boundary, and HTTPS migration path.
- [ ] Run `python -W error::ResourceWarning -m unittest discover -s tests -v`.
- [ ] Run `python -m compileall -q app.py worldpanel_qc tests`.
- [ ] Restart the local service and verify `/api/health`.
- [ ] Use synthetic model calls to verify connection, structured logic response, and image OCR.
- [ ] Use the local browser to verify settings, warning text, new-run controls, AI logs, and no console errors.

## Self-review

- Covers every approved design section: encrypted configuration, HTTP warning, minimized payloads, deterministic checks, LLM JSON output, OCR screenshot boundary, failure handling, UI, and verification.
- Contains no token value and no instruction to persist the token in source.
- Keeps local QC working when the model is unavailable.
