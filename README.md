# Worldpanel Data QC Assistant

Windows local testing version for Excel, PPTX, and PDF quality control.

## Start

### Personal Local Mode

Double-click:

```text
start_worldpanel_qc.bat
```

Or run:

```powershell
python app.py
```

Then open:

```text
http://127.0.0.1:8765
```

### Company Intranet Mode

1. Right-click `configure_firewall_domain_as_admin.bat` and run it as Administrator once. It opens TCP `8765` only on Windows Domain networks.
2. Double-click `start_worldpanel_qc_intranet.bat`.
3. Enter a shared access password when prompted.
4. Keep the terminal window open and share the printed WLAN URL with colleagues, for example `http://172.20.130.157:8765`.

The password is held in the server process only. It is not written to a file. Colleagues sign in through the browser and receive an expiring signed session cookie.

### Temporary Public HTTPS Test

1. Double-click `install_cloudflared.bat` once. This requests installation of Cloudflare's `cloudflared` tunnel client through `winget`.
2. Open a new terminal after installation.
3. Double-click `start_worldpanel_qc_public_test.bat`.
4. Enter a shared access password when prompted.
5. Share only the temporary HTTPS URL printed by `cloudflared`.
6. Press `Ctrl+C` in the tunnel window to stop public access.

If the terminal window is no longer visible, double-click `stop_worldpanel_qc_public_test.bat` to stop the recorded temporary public service.

The public test tunnel forwards to a dedicated local-only port, `127.0.0.1:8877`. It does not expose the personal local service on port `8765`. The intranet LLM endpoint and credential remain on the backend computer and are not sent to browsers. For a permanent rollout, move the same backend behind a company-managed HTTPS domain, reverse proxy, and service account.

### Public Shared Access On This Computer

Use this when you want to keep this computer as the backend and open access to anyone who has the shared password.

Double-click:

```text
start_worldpanel_qc_public_shared.bat
```

Enter the shared access password and share the printed HTTPS URL. To stop access, double-click:

```text
stop_worldpanel_qc_public_shared.bat
```

### Free Cloud Server Rollout

Use this when you do not want this computer to act as the server. The recommended free path is Oracle Cloud Always Free VM plus Cloudflare Tunnel or a company domain.

Cloud deployment files are under:

```text
deploy/cloud/
```

Read:

```text
docs/cloud-deployment-oracle-free-cn.md
```

The cloud version supports Linux environment variables for the shared password and LLM configuration, LibreOffice-based `.xls` conversion, and LibreOffice + poppler Slides rendering for visual AI review.

### Shared-Workspace Protection

- Shared-password mode requires login for the workspace, APIs, reports, and exports. `/api/health` remains public for monitoring.
- Repeated incorrect passwords are temporarily rate-limited.
- LLM settings are locked for shared-password users and remain a server-administrator responsibility.
- JSON upload requests are limited to 150 MB by default.

## Use The Local Version

1. Double-click `start_worldpanel_qc.bat`.
2. Enter your name and company email the first time.
3. Create or open a project.
4. Select the closest FMCG category template when creating a project: General FMCG, Fresh produce, Beverages, Dairy, or Personal care.
5. Upload one or more `.xlsx`, `.xls`, `.pptx`, or `.pdf` files.
6. Follow the live progress bar while the files, local rules, AI review, and Slides pages are checked.
7. Review current-file issues, cross-file source matches, version suggestions, and page coverage.
8. Confirm each issue and every required visual-review page.
9. Complete QC when the overall status becomes `Ready for Delivery`.
10. Export the Excel detail report and PDF summary.

## Included Features

- Lightweight local identity: name and company email.
- Project creation and local QC history.
- Project-level FMCG category templates for General FMCG, Fresh produce, Beverages, Dairy, and Personal care AI review guidance.
- Upload `.xlsx`, `.xls`, `.pptx`, and `.pdf`.
- Explicit warning for unsupported legacy `.ppt`.
- Excel structured parsing: values, formats, formulas, error values, and hidden areas.
- PowerView-style Excel context recovery: measure heading, row label, and column label for each parsed value.
- PPTX parsing: visible text, tables, editable chart series, chart visual-review flags, image review flags, and grouped-shape review flags.
- PDF text-layer parsing with low-text and image-region review flags.
- Built-in checks for placeholders, unsupported files, Excel error values, hidden Excel areas, and visual-review pages.
- Built-in Worldpanel logic candidates for Share rows whose totals differ from 100%, percentage values outside 0% to 100%, price outliers, and comparable-unit KPI relationships such as `buyers = households x penetration`.
- Project-level required-text and forbidden-text rules with enable / disable controls.
- Excel-PPTX/PDF numeric candidate matching, unmatched visible-number reporting, alternative candidates, user confirmation, and reusable page-source constraints.
- Suggested previous-version comparisons for same-type files with filename similarity of at least 90%.
- Manual previous-version selection when a suggestion is not available.
- Separate current-file QC and confirmed previous-version changes.
- Issue notes, page review confirmation, final QC completion, and local audit records.
- Persisted live run progress with current stage, percentage, approximate remaining time, automatic refresh, and visible failure state.
- Page coverage and external-AI adapter logs without prompts or credentials.
- Excel detail report and downloadable PDF summary.

## LLM Logic Review And Slides OCR

Open `LLM Settings` in the sidebar to configure an OpenAI-compatible Chat Completions endpoint, model name, access token, and timeout. The token is encrypted with Windows DPAPI before it is written under `local_data/`; it is never returned by the settings API or written to QC logs.

Each QC run can enable two independent options:

- `Enable full parsed-content AI review`: sends parsed text, numbers, table context, local logic candidates, Worldpanel KPI relationships, and FMCG category guidance in bounded batches. The model reviews logic, trends, peer inconsistencies, possible unit or decimal errors, annotations, and market-common-sense concerns.
- `Enable Slides OCR`: renders and sends PPTX pages containing charts, pictures, or grouped layouts, then records page-level findings.

The configured model endpoint uses plain HTTP and must remain reachable from the backend computer. Public users access the application through HTTPS; browsers do not connect to the model endpoint directly. Before a permanent rollout, move the model endpoint to HTTPS and rotate the shared model credential.

## Tests

```powershell
python -W error::ResourceWarning -m unittest discover -s tests -v
```

## Local Data

Local state is written under:

```text
local_data/
```

This folder contains the SQLite database, uploaded test files, and exported reports.
