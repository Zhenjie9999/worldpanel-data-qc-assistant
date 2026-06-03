# Worldpanel Data QC Assistant - Product Design and Development Plan

Date: 2026-05-27

## 1. Product Definition

Worldpanel Data QC Assistant is a data quality control product for Worldpanel analysis and delivery teams. The first version focuses on two high-value workflows:

1. Data Output QC: checking Excel outputs generated from Powerview.
2. Delivery QC: checking final PPT and/or Excel files before client delivery.

The product supports Excel-only, PPT-only, multi-Excel, and PPT + Excel mixed uploads. It automatically identifies the uploaded file combination, runs the relevant QC checks, and produces a QC Report that helps users fix issues and keep an audit trail before delivery.

The product is not intended to replace Powerview, Excel, or PowerPoint. It acts as a quality control layer on top of the existing workflow:

```text
Powerview -> Excel output / working file -> PPT delivery -> QC Report
```

## 2. Target Users

Primary users:

- Analysts who export data from Powerview and prepare Excel working files.
- Project managers who review client-facing PPT decks before delivery.
- Delivery teams who need a consistent workplace-wide QC standard.

Secondary users:

- Team leads who want visibility into repeated QC issues.
- Administrators who maintain common QC rules and thresholds.

## 3. Core Use Cases

### 3.1 Data Output QC

The user uploads one or more Excel files exported from Powerview or prepared as working files.

The product answers:

```text
Is this Excel output internally reliable enough to use in analysis or delivery?
```

Main checks:

- Missing values, error values, abnormal zeros, and empty data blocks.
- Total and subtotal consistency.
- Share, contribution, percentage, and change calculations.
- Basic KPI relationships such as sales value, volume, price, penetration, frequency, buyers, occasions, and spend per buyer.
- Unit, percentage, decimal, sign, and rounding consistency.
- Hidden rows/columns, manual formula overwrites, and suspicious mixed formulas.
- File-level metadata risks such as unclear period, scope, or project name.

### 3.2 Delivery QC

The user uploads a PPT, or a PPT with one or more Excel files.

The product answers:

```text
Can this PPT or PPT + Excel package be safely delivered to the client?
```

Main checks:

- PPT numeric format consistency.
- KPI consistency across pages.
- Missing source, base, period, or footnote.
- Potential mismatch between page title/conclusion and data direction.
- Repeated numbers with conflicting values.
- In PPT + Excel mode, whether PPT numbers can be traced to Excel.
- In PPT + Excel mode, whether PPT numbers are stale, rounded incorrectly, or inconsistent with the latest Excel values.

## 4. File Combination Logic

The product should not force users to choose a mode manually. Users drag in files, and the system detects the file combination.

| Uploaded files | Automatic checks |
| --- | --- |
| Single Excel | Data Output QC |
| Multiple Excel files | Data Output QC + Excel-to-Excel consistency checks |
| Single PPT | Delivery QC with PPT-only checks |
| PPT + one or more Excel files | Delivery QC + Cross-file QC |

The upload screen should show a short confirmation before running checks, for example:

```text
You uploaded:
- 1 PPT
- 3 Excel files

The system will run:
- PPT Delivery QC
- Excel Data Output QC
- PPT-Excel Cross-file QC
```

## 5. MVP Scope

The MVP should include:

- Upload `.xlsx` and `.pptx` files.
- Detect file types and select the QC workflow automatically.
- Extract visible numbers, percentages, units, and surrounding text from Excel and PPT.
- Run Excel-only QC rules.
- Run PPT-only QC rules.
- Run PPT + Excel cross-file numeric matching.
- Support Chinese and English mixed business text.
- Generate an on-screen QC Report.
- Export the QC Report to Excel or PDF.
- Classify issues as High, Medium, or Low severity.
- Provide business-readable explanations and suggested actions.

The MVP should not include:

- Direct Powerview integration.
- Office add-ins.
- Automatic PPT modification.
- Full AI interpretation of every business conclusion.
- Guaranteed source tracing for every chart label or manually edited number.
- Complex project-specific rule configuration UI.

## 6. QC Report Design

The QC Report should be understandable by non-technical users.

Recommended sections:

1. Summary
2. High-risk issues
3. Excel QC issues
4. PPT QC issues
5. Cross-file QC issues
6. Unverified numbers
7. Export and audit information

Each issue should include:

| Field | Description |
| --- | --- |
| Severity | High, Medium, or Low |
| File | Source file name |
| Location | Sheet/cell or PPT page/text box |
| Issue type | Calculation, format, missing source, mismatch, etc. |
| Description | Plain-language explanation |
| Evidence | The extracted values or comparison result |
| Suggested action | How the user should review or fix it |

Example:

```text
Severity: High
Location: PPT page 12
Issue: PPT value does not match Excel
Evidence: PPT shows 6.1%, Excel candidate value is 6.0%
Possible reason: PPT may not have been updated after the Excel refresh.
Suggested action: Confirm whether the current Excel value should replace the PPT number.
```

## 7. Rule Model

Rules should be organized into three layers.

### 7.1 General Rules

Rules that apply to any Excel or PPT:

- Empty cells in data areas.
- Error values such as `#DIV/0!`, `#N/A`, and `#VALUE!`.
- Inconsistent decimal places.
- Inconsistent percentage signs.
- Suspicious zeros.
- Subtotal and total mismatches.
- Missing source, base, period, or footnote in PPT.

### 7.2 Worldpanel Business Rules

Rules based on common Worldpanel metrics and deliverables:

- Sales value, volume, price, buyer, household, penetration, frequency, occasions, and spend relationship checks.
- Contribution and share sanity checks.
- Positive/negative direction consistency.
- Period and scope consistency.
- Category, channel, region, and demographic split consistency where structure is detectable.

### 7.3 Project Rules

Rules that may be added later for specific clients, reports, or templates:

- Client-specific KPI naming.
- Template-specific required footnotes.
- Project-specific rounding standards.
- Standard page structures for repeated deliverables.

For the MVP, project rules can be handled manually or through simple configuration files. A full rule management UI should be deferred.

## 8. Cross-file Matching Logic

Cross-file QC should match PPT numbers to possible Excel sources.

The matcher should consider:

- Numeric value after normalization.
- Percentage and decimal equivalence, such as `6%` and `0.06`.
- Rounding tolerance, such as `6.0469%` matching `6.0%`.
- Unit conversion where obvious, such as millions vs raw values.
- Surrounding labels, KPI names, brand names, categories, periods, and page context.
- Multiple candidate matches.

The output should avoid pretending that uncertain matches are exact. Suggested match confidence levels:

| Confidence | Meaning |
| --- | --- |
| High | Strong value and context match |
| Medium | Value match but weak context |
| Low | Possible match only |
| None | No plausible Excel source found |

High-risk cross-file issues:

- PPT number has no plausible Excel source.
- PPT number conflicts with the best Excel candidate.
- Same PPT KPI appears with different values across pages.
- Excel appears updated but PPT still contains an older value.

## 9. System Architecture

Recommended MVP architecture:

```text
Upload UI
  -> File Type Detector
  -> Excel Parser
  -> PPT Parser
  -> Number Normalizer
  -> Rule Engine
  -> Cross-file Matcher
  -> QC Report Generator
  -> Export Module
```

Module responsibilities:

| Module | Responsibility |
| --- | --- |
| Upload UI | Let users upload Excel/PPT files and review detected QC mode |
| File Type Detector | Identify file types and file combinations |
| Excel Parser | Extract sheets, cells, formulas, values, formats, hidden areas, and table-like regions |
| PPT Parser | Extract slide text, table text, chart labels where available, and surrounding context |
| Number Normalizer | Standardize numbers, percentages, signs, units, and rounded values |
| Rule Engine | Execute configured QC rules and assign severity |
| Cross-file Matcher | Match PPT values to Excel candidates |
| QC Report Generator | Produce structured issue lists and summary metrics |
| Export Module | Export QC results for sharing and audit trail |

## 10. Technical Recommendation

The first version should be a web or desktop upload-based tool rather than an Office add-in.

Recommended implementation:

- Frontend: simple web app for upload, progress, report review, and export.
- Backend: Python or Node.js service.
- Excel parsing: `openpyxl` for `.xlsx`, with optional Open XML fallback for advanced metadata.
- PPT parsing: `python-pptx`, with Open XML fallback for text, tables, and shape metadata.
- Rule engine: structured JSON/YAML rule definitions with Python execution.
- Storage: temporary local or internal server storage for uploaded files and generated reports.
- Deployment: internal web server for workplace distribution, or a packaged desktop version if file security requires local processing.

Security requirements:

- Uploaded files should be stored temporarily.
- Users should understand whether files stay local or are processed on an internal server.
- Client names and sensitive data should not be sent to external APIs in the MVP.
- QC logs should avoid storing full report content unless required for audit.

## 11. Development Plan

### Phase 0: Rule and Sample Definition, 1 week

Goals:

- Collect 10-20 representative Excel/PPT examples.
- Define the top 30 high-frequency QC rules.
- Confirm rounding and tolerance standards.
- Define the QC Report structure.
- Confirm MVP success metrics.

Deliverables:

- Sample file inventory.
- Rule list v1.
- QC Report template.
- MVP acceptance criteria.

### Phase 1: File Parsing Prototype, 1-2 weeks

Goals:

- Extract Excel sheet names, cells, values, formulas, and formats.
- Extract PPT slide text, tables, numbers, and nearby labels.
- Normalize numbers, percentages, units, and signs.

Deliverables:

- Excel extraction JSON.
- PPT extraction JSON.
- Number normalization module.
- Parser accuracy review on real samples.

Acceptance criteria:

- At least 90% of visible business numbers are extracted from representative Excel/PPT files.

### Phase 2: Excel-only Data Output QC, 2 weeks

Goals:

- Implement core Excel QC rules.
- Detect calculation, format, and structure issues.
- Generate issue records with severity and suggested actions.

Deliverables:

- Excel QC engine.
- Excel QC issue list.
- Excel QC report view.

Acceptance criteria:

- Analysts can upload a Powerview Excel output and identify obvious data, formula, formatting, and total/subtotal issues.

### Phase 3: PPT-only Delivery QC, 2 weeks

Goals:

- Implement PPT numeric and delivery-quality checks.
- Detect missing source, base, period, and footnote.
- Detect inconsistent numeric formatting and repeated KPI conflicts.

Deliverables:

- PPT QC engine.
- PPT QC issue list.
- PPT QC report view.

Acceptance criteria:

- Project managers can upload a PPT and identify high-risk delivery issues before sending it to clients.

### Phase 4: PPT + Excel Cross-file QC, 2-3 weeks

Goals:

- Match PPT numbers to Excel candidates.
- Apply rounding and unit tolerance.
- Flag mismatches, stale values, and unverified numbers.

Deliverables:

- Cross-file matcher.
- Match confidence scoring.
- Cross-file QC report view.

Acceptance criteria:

- Users can find key PPT numbers that do not match, cannot be traced to, or may be stale versus the uploaded Excel files.

### Phase 5: Workplace Pilot Version, 1-2 weeks

Goals:

- Package the tool for pilot users.
- Add report export.
- Add basic user guidance and error messages.
- Run pilot with selected analysts and project managers.

Deliverables:

- Pilot-ready app.
- Exportable QC Report.
- Pilot feedback log.
- Revised rule backlog.

Acceptance criteria:

- Non-technical users can complete a QC run and understand the exported report without developer support.

## 12. MVP Success Metrics

The MVP is successful if:

- Analysts can find Excel output issues before using the data in analysis.
- Project managers can find delivery risks before sending PPTs to clients.
- PPT + Excel checks catch important stale or mismatched numbers.
- QC Reports are understandable and actionable for business users.
- The workflow is fast enough to become a standard pre-delivery step.

Suggested measurable targets:

- Extract at least 90% of visible business numbers from pilot files.
- Identify at least 70% of manually known high-risk numeric issues in pilot files.
- Keep a typical QC run under 5 minutes for common report packages.
- Reduce manual QC time for pilot users by at least 30%.

## 13. Open Decisions

These decisions should be made before implementation starts:

1. Deployment mode: internal web app or local desktop app.
2. File security policy: whether files can be uploaded to an internal server or must remain local.
3. First rule set: the top 30 rules for Data Output QC and Delivery QC.
4. Export format: Excel report, PDF report, or both.
5. Pilot users and pilot sample files.

## 14. Recommended Next Step

Start with Phase 0. The most important work is not coding yet; it is defining the first rule set and validating it against real Worldpanel files.

Recommended Phase 0 workshop output:

```text
1. 10-20 sample Excel/PPT files
2. Top 30 QC rules
3. Severity definitions
4. Rounding and tolerance standards
5. QC Report template
6. Pilot success criteria
```
