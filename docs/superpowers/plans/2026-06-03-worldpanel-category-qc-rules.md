# Worldpanel Category QC Rules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explainable Worldpanel FMCG business rules, AI category context, and Slides chart visual review coverage.

**Architecture:** Extend the existing local candidate engine with normalized Worldpanel metric aliases and relationship checks. Feed the resulting candidates plus category guidance into the existing bounded AI review pipeline. Keep every result as a reviewable issue and preserve the existing local and temporary-public workflows.

**Tech Stack:** Python standard library, openpyxl, python-pptx, unittest, existing OpenAI-compatible intranet model adapter.

---

### Task 1: Explainable Worldpanel Business Rules

**Files:**
- Create: `worldpanel_qc/qc/business_rules.py`
- Modify: `worldpanel_qc/qc/logic_candidates.py`
- Test: `tests/test_business_rules.py`

- [ ] Add failing tests for metric alias normalization, penetration range checks, share range checks, row-oriented KPI identity checks and PowerView block-oriented KPI identity checks.
- [ ] Run `python -m unittest tests.test_business_rules -v` and confirm the new tests fail because the module does not exist.
- [ ] Implement normalized metric aliases, observation grouping and conservative relative-error checks.
- [ ] Run `python -m unittest tests.test_business_rules tests.test_logic_candidates -v` and confirm all candidate tests pass.

### Task 2: AI Industry Guidance

**Files:**
- Modify: `worldpanel_qc/llm/client.py`
- Modify: `worldpanel_qc/llm/document_payloads.py`
- Test: `tests/test_llm_client.py`
- Test: `tests/test_llm_reviewer.py`

- [ ] Add failing tests that assert the AI prompt receives Worldpanel business identities and category guidance.
- [ ] Run the focused tests and confirm the new expectations fail.
- [ ] Add compact Worldpanel market-research guidance and category risk templates to each parsed-data review request.
- [ ] Run the focused tests and confirm they pass.

### Task 3: Slides Chart Visual Coverage

**Files:**
- Modify: `worldpanel_qc/parsers/pptx.py`
- Test: `tests/test_parsers.py`

- [ ] Add a failing parser test proving a structured chart page still requires visual review.
- [ ] Run the focused parser test and confirm it fails.
- [ ] Include chart shapes in Slides visual-review routing while preserving coverage metadata.
- [ ] Run parser and visual-review tests and confirm they pass.

### Task 4: Real-File Regression and Trial Release

**Files:**
- Modify: `README.md`

- [ ] Run the complete unit suite.
- [ ] Run the real `0528.xlsx` sample through the local app with AI enabled.
- [ ] Run the real Slides and source Excel sample through the local app with AI enabled.
- [ ] Start a fresh temporary HTTPS trial URL with a new shared password.
- [ ] Verify login, upload, analysis, report viewing and settings lock through the public URL.

