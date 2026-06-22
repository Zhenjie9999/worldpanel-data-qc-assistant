---
name: worldpanel-data-qc
description: Check Worldpanel consumer-panel FMCG deliverables for data, logic, annotation, and cross-file consistency. Use when reviewing Excel (.xlsx, .xls), PowerPoint (.pptx, .ppt), or PDF reports; when validating PowerView outputs; when comparing PPT/PDF figures with Excel sources; or when producing a structured Chinese, English, or bilingual QC report for FMCG category work.
---

# Worldpanel Data QC

Use the Worldpanel Data QC Assistant project when it is available in the workspace. It supports Excel-only, PPT/PDF-only, and Excel-to-PPT/PDF checks, with optional model-assisted logic review.

## Workflow

1. Confirm the scope before reading files.
   - Ask whether this is a full review or specific pages, sheets, measures, periods, brands, or products.
   - Treat files as a cross-check package only when they are from the same client/report delivery. Otherwise create separate checks.
   - Ask whether output should be Chinese, English, or bilingual.
2. Identify the input mode.
   - Excel only: inspect formulas, tables, hidden rows/columns, numeric consistency, and category logic.
   - PPT/PDF only: inspect visible labels, chart numbers, annotations, totals, period references, and visual pages requiring OCR.
   - Mixed files: perform the above checks and report only suspicious source matches, conflicts, missing matches, and low-confidence matches.
3. Apply deterministic rules first, then use the configured LLM for contextual business review. Do not present an LLM inference as a confirmed fact.
4. Group findings by issue type. Prioritize critical numeric conflicts, invalid metric identities, materially implausible values, and incorrect labels/periods.
5. Export the requested language and include file, page/sheet, evidence, impact, and suggested action for every reported issue.

## Use the Local Project

- Locate `app.py` and `worldpanel_qc/` in the current workspace. Use the existing application and its configured model settings rather than creating a second checker.
- If this repository is not available, clone or download `https://github.com/Zhenjie9999/worldpanel-data-qc-assistant` first, then run the local application according to its existing project instructions.
- Never commit API tokens, uploaded source files, output reports, or local databases. Keep model credentials in local configuration only.

## Review Standards

- Read [references/worldpanel-fmcg-qc-rules.md](references/worldpanel-fmcg-qc-rules.md) before a material FMCG data review.
- Prefer precise, evidence-backed issues over exhaustive lists of weak matches.
- Treat tolerance, units, bases, and period definitions as context. Do not flag a difference until checking whether it is caused by percent/decimal formatting, rounding, weighted versus unweighted measures, or a legitimate cut/filter.
- For a price anomaly, compare within a meaningful peer group and period before flagging it. State the benchmark and magnitude.
- For a share total, flag material deviations from 100% only after accounting for "Other", exclusions, multi-response bases, rounding, and incomplete universe coverage.

## Result Format

Use this structure unless the application export is requested:

| Priority | Category | File and location | Evidence | Recommended action |
| --- | --- | --- | --- | --- |
| Critical/High/Medium/Low | Data conflict, logic, label, source match, or coverage | Workbook/sheet/cell or slide/page | Exact values and comparison basis | What the analyst should verify or correct |

End with a compact issue summary: count by category and severity, items outside the requested scope, and any checks not completed.
