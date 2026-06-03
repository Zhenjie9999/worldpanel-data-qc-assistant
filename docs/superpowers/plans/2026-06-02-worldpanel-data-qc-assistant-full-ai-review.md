# Worldpanel Data QC Assistant Full AI Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Send complete parsed business blocks to the intranet model and detect PowerView price anomalies such as `Cherry / 2022 = 8000`.

**Architecture:** Extend Excel parsing with block, row, and column context. Add a focused document-payload builder that chunks complete parsed content. Keep deterministic local checks and AI review separate, then merge both issue types into the existing confirmation workflow.

**Tech Stack:** Python stdlib, openpyxl, unittest, existing Chat Completions adapter.

---

### Task 1: Preserve Excel block context

**Files:**
- Modify: `worldpanel_qc/parsers/excel.py`
- Test: `tests/test_parsers.py`

- [ ] Add a failing parser test for a PowerView-style block.
- [ ] Run the focused test and verify the metric name is missing.
- [ ] Track nearby measure headings and column headers while parsing numeric cells.
- [ ] Run parser tests.

### Task 2: Detect contextual price outliers

**Files:**
- Modify: `worldpanel_qc/qc/logic_candidates.py`
- Test: `tests/test_logic_candidates.py`
- Test: `tests/test_runner.py`

- [ ] Add a failing test for `Weighted RESP Price per Volume / Cherry / 2022 = 8000`.
- [ ] Run the focused test and verify no candidate is returned.
- [ ] Group price values using recovered metric context and run the robust outlier rule.
- [ ] Run logic and runner tests.

### Task 3: Send complete parsed blocks to AI

**Files:**
- Create: `worldpanel_qc/llm/document_payloads.py`
- Modify: `worldpanel_qc/llm/reviewer.py`
- Modify: `worldpanel_qc/llm/client.py`
- Test: `tests/test_llm_reviewer.py`
- Test: `tests/test_llm_client.py`

- [ ] Add failing tests proving all parsed Excel rows are sent even without local candidates.
- [ ] Run focused tests and verify the reviewer does not call the client.
- [ ] Build bounded document chunks and add `review_document_chunks`.
- [ ] Run LLM tests.

### Task 4: Real workbook verification

**Files:**
- Modify: `README.md`

- [ ] Restart the local app.
- [ ] Run QC with `qc_input_zespri_price_0528.xlsx`.
- [ ] Confirm deterministic detection of `Sheet1!B4 = 8000`.
- [ ] Review all returned AI findings for other workbook anomalies.
- [ ] Update README and run the full suite.
