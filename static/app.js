const state = {
  user: JSON.parse(localStorage.getItem("worldpanelQcUser") || "null"),
  projects: [],
  project: null,
  run: null,
  activeTab: "issues",
  matchFilter: "unmatched",
  runtime: null,
  progressTimer: null,
};

const $ = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
}[char]));
const statusClass = (value) => `status-${String(value).toLowerCase().replaceAll(" ", "-")}`;
const categoryLabel = (value) => ({
  general_fmcg: "General FMCG",
  fresh_produce: "Fresh produce",
  beverages: "Beverages",
  dairy: "Dairy",
  personal_care: "Personal care",
}[value] || "General FMCG");
const api = async (url, options = {}) => {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (response.status === 401 && url !== "/api/auth/login") {
    window.location.replace("/login");
    throw new Error("Authentication required.");
  }
  if (!response.ok) throw new Error(await response.text());
  return response.json();
};

async function boot() {
  state.runtime = await api("/api/runtime");
  $("llmSettingsButton").classList.toggle("hidden", !state.runtime.llm_settings_editable);
  $("logoutButton").classList.toggle("hidden", !state.runtime.authentication_required);
  if (!state.user) {
    $("identityBadge").textContent = state.runtime.authentication_required ? "Shared workspace" : "Local mode";
    $("identityDialog").showModal();
  }
  else $("identityBadge").textContent = `${state.user.name} / ${state.runtime.authentication_required ? "shared workspace" : "local mode"}`;
  await loadProjects();
}

async function openLlmSettings() {
  const data = await api("/api/llm/settings");
  const settings = data.settings;
  const form = $("llmSettingsForm");
  form.elements.endpoint.value = settings.endpoint || "";
  form.elements.model.value = settings.model || "";
  form.elements.token.value = "";
  form.elements.token.placeholder = settings.token_configured ? "Saved token configured. Leave blank to keep it." : "Enter API token";
  form.elements.timeoutSeconds.value = settings.timeout_seconds || 60;
  form.elements.enabled.checked = Boolean(settings.enabled);
  form.elements.ocrEnabled.checked = Boolean(settings.ocr_enabled);
  renderLlmWarning(settings.warning);
  $("llmTestResult").textContent = "";
  $("llmSettingsDialog").showModal();
}

function renderLlmWarning(warning) {
  $("llmWarning").textContent = warning || "";
  $("llmWarning").classList.toggle("hidden", !warning);
}

function llmSettingsPayload() {
  const form = new FormData($("llmSettingsForm"));
  return {
    endpoint: form.get("endpoint"),
    model: form.get("model"),
    token: form.get("token"),
    timeout_seconds: Number(form.get("timeoutSeconds")),
    enabled: Boolean(form.get("enabled")),
    ocr_enabled: Boolean(form.get("ocrEnabled")),
  };
}

async function loadProjects() {
  const data = await api("/api/projects");
  state.projects = data.projects;
  $("projectList").innerHTML = data.projects.map((project) =>
    `<button class="project-item" data-project="${project.id}"><strong>${escapeHtml(project.name)}</strong><br><small>${project.run_count} QC run(s)</small></button>`
  ).join("");
  document.querySelectorAll("[data-project]").forEach((button) => {
    button.addEventListener("click", () => openProject(Number(button.dataset.project)));
  });
}

async function openProject(projectId) {
  const data = await api(`/api/projects/${projectId}`);
  state.project = { ...data.project, rules: data.rules, mappings: data.mappings };
  $("welcomePanel").classList.add("hidden");
  $("runPanel").classList.add("hidden");
  $("projectPanel").classList.remove("hidden");
  $("projectTitle").textContent = data.project.name;
  $("projectCategory").textContent = `Category template: ${categoryLabel(data.project.category_template)}`;
  $("ruleSummary").textContent = `${data.rules.filter((rule) => rule.active).length} active project rule(s)`;
  $("ruleList").innerHTML = data.rules.map((rule) => `
    <div class="rule-item">
      <span><strong>${escapeHtml(rule.name)}</strong><br><small>${escapeHtml(rule.rule_type)} / ${escapeHtml(rule.severity)}</small></span>
      <button class="secondary-button compact-button" data-rule-toggle="${rule.id}" data-active="${rule.active ? "1" : "0"}">${rule.active ? "Disable" : "Enable"}</button>
    </div>`).join("");
  $("runList").innerHTML = data.runs.length ? data.runs.map((run) =>
    `<button class="run-item" data-run="${run.id}"><span><strong>Run #${run.id}</strong><br><small>${run.created_at}</small></span><span class="status ${statusClass(run.status)}">${run.status}</span></button>`
  ).join("") : `<div class="empty-state"><p>No QC runs yet.</p></div>`;
  document.querySelectorAll("[data-run]").forEach((button) => button.addEventListener("click", () => openRun(Number(button.dataset.run))));
  document.querySelectorAll("[data-rule-toggle]").forEach((button) => button.addEventListener("click", toggleRule));
}

async function openRun(runId) {
  state.run = await api(`/api/runs/${runId}`);
  $("projectPanel").classList.add("hidden");
  $("runPanel").classList.remove("hidden");
  $("runTitle").textContent = `Run #${runId} / ${state.run.run.status}`;
  const exportLanguage = encodeURIComponent(state.run.run.output_language || "zh");
  $("exportExcel").href = `/api/runs/${runId}/export.xlsx?lang=${exportLanguage}`;
  $("exportPdf").href = `/api/runs/${runId}/export.pdf?lang=${exportLanguage}`;
  const processing = ["queued", "processing"].includes(state.run.run.processing_status);
  $("completeRunButton").disabled = processing || Boolean(state.run.completion);
  $("completeRunButton").textContent = state.run.completion ? "QC completed" : "Complete QC";
  $("exportExcel").classList.toggle("disabled-link", processing);
  $("exportPdf").classList.toggle("disabled-link", processing);
  $("exportExcel").setAttribute("aria-disabled", String(processing));
  $("exportPdf").setAttribute("aria-disabled", String(processing));
  renderMetrics();
  renderTab();
  scheduleProgressRefresh();
}

function renderMetrics() {
  if (["queued", "processing", "failed"].includes(state.run.run.processing_status)) {
    $("metrics").innerHTML = renderProgressPanel();
    return;
  }
  const issues = state.run.issues;
  const reviewPages = state.run.coverage.filter((item) => item.review_required && !item.reviewed).length;
  const high = issues.filter((item) => item.severity === "High" && ["pending", "confirmed_error", "needs_review"].includes(item.status)).length;
  $("metrics").innerHTML = [
    [state.run.run.status, "Overall status"],
    [issues.length, "Issues"],
    [high, "Open high risk"],
    [reviewPages, "Open review pages"],
  ].map(([value, label]) => `<div class="metric"><strong>${escapeHtml(value)}</strong><span>${label}</span></div>`).join("");
}

function formatRemaining(seconds) {
  if (seconds === null || seconds === undefined) return "Estimating remaining time...";
  if (seconds < 60) return "Less than 1 minute remaining";
  const minutes = Math.max(1, Math.round(seconds / 60));
  return `About ${minutes} minute${minutes === 1 ? "" : "s"} remaining`;
}

function renderProgressPanel() {
  const run = state.run.run;
  const percent = Number(run.progress_percent || 0);
  const failed = run.processing_status === "failed";
  return `<section class="progress-panel ${failed ? "progress-failed" : ""}">
    <div class="progress-heading">
      <div>
        <strong>${escapeHtml(failed ? "QC check failed" : run.progress_stage || "Queued")}</strong>
        <span>${escapeHtml(failed ? run.processing_error : (run.progress_detail || "Preparing QC check"))}</span>
      </div>
      <b>${percent}%</b>
    </div>
    <div class="progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${percent}">
      <div class="progress-fill" style="width:${percent}%"></div>
    </div>
    <small>${escapeHtml(failed ? "Please start a new run or ask the administrator to review the error." : formatRemaining(run.estimated_seconds_remaining))}</small>
  </section>`;
}

function scheduleProgressRefresh() {
  clearTimeout(state.progressTimer);
  state.progressTimer = null;
  if (!["queued", "processing"].includes(state.run.run.processing_status)) return;
  state.progressTimer = setTimeout(async () => {
    try {
      await openRun(state.run.run.id);
    } catch {
      state.progressTimer = setTimeout(() => openRun(state.run.run.id), 2000);
    }
  }, 2000);
}

function renderTab() {
  document.querySelectorAll(".tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === state.activeTab));
  const content = $("tabContent");
  if (["queued", "processing"].includes(state.run.run.processing_status)) {
    content.innerHTML = `<div class="empty-state"><p>Your files are being checked. This page updates automatically.</p></div>`;
    return;
  }
  if (state.run.run.processing_status === "failed") {
    content.innerHTML = `<div class="empty-state"><p>The QC check could not be completed. Start a new run after reviewing the message above.</p></div>`;
    return;
  }
  if (state.activeTab === "issues") content.innerHTML = renderIssues();
  if (state.activeTab === "changes") content.innerHTML = renderChanges();
  if (state.activeTab === "matches") content.innerHTML = renderMatches();
  if (state.activeTab === "coverage") content.innerHTML = renderCoverage();
  if (state.activeTab === "ai") content.innerHTML = renderAiLogs();
  bindTabActions();
}

function renderIssues() {
  if (!state.run.issues.length) return `<div class="empty-state"><p>No issues found by the current rules.</p></div>`;
  const groups = (state.run.issue_groups || []).length ? `<div class="issue-groups">${state.run.issue_groups.map((group) => `
    <div class="issue-group">
      <strong>${escapeHtml(group.title)}</strong>
      <span>${escapeHtml(group.severity)} / ${group.count} issue(s)</span>
      <small>${escapeHtml((group.locations || []).join(" | "))}</small>
    </div>`).join("")}</div>` : "";
  return `${groups}<table><thead><tr><th>Severity</th><th>File</th><th>Location</th><th>Issue</th><th>Status</th><th>Note</th><th></th></tr></thead><tbody>${state.run.issues.map((issue) => `
    <tr>
      <td class="severity severity-${issue.severity.toLowerCase()}">${escapeHtml(issue.severity)}</td>
      <td>${escapeHtml(issue.file_name)}</td>
      <td>${escapeHtml(issue.location)}</td>
      <td>${escapeHtml(issue.description)}</td>
      <td><select data-issue-status="${issue.id}">
        ${[
          ["pending", "Pending"],
          ["confirmed_error", "Confirmed error"],
          ["fixed", "Fixed"],
          ["confirmed_ok", "Confirmed OK"],
          ["needs_review", "Needs review"],
        ].map(([value, label]) => `<option value="${value}" ${issue.status === value ? "selected" : ""}>${label}</option>`).join("")}
      </select></td>
      <td><textarea data-issue-note="${issue.id}" placeholder="Add review note">${escapeHtml(issue.note)}</textarea></td>
      <td><button class="secondary-button compact-button" data-save-issue="${issue.id}">Save</button></td>
    </tr>`).join("")}</tbody></table>`;
}

function renderCoverage() {
  if (!state.run.coverage.length) return `<div class="empty-state"><p>No page-based coverage records for this file package.</p></div>`;
  return `<table><thead><tr><th>File</th><th>Page</th><th>Coverage</th><th>Numbers</th><th>Low confidence</th><th>Manual review</th><th>Detail</th><th></th></tr></thead><tbody>${state.run.coverage.map((item) => `
    <tr><td>${escapeHtml(item.file_name)}</td><td>${item.page || ""}</td><td>${item.coverage_percent}%</td><td>${item.numbers_found}</td><td>${item.low_confidence_count}</td><td>${item.review_required ? (item.reviewed ? "Confirmed" : "Required") : "No"}</td><td>${escapeHtml(item.detail)}</td><td>${item.review_required && !item.reviewed ? `<button class="secondary-button compact-button" data-review-coverage="${item.id}">Confirm reviewed</button>` : ""}</td></tr>
  `).join("")}</tbody></table>`;
}

function renderAiLogs() {
  if (!state.run.ai_logs.length) return `<div class="empty-state"><p>No external AI adapter calls were needed.</p></div>`;
  return `<table><thead><tr><th>Provider</th><th>File</th><th>Page</th><th>Status</th><th>Detail</th></tr></thead><tbody>${state.run.ai_logs.map((item) => `
    <tr><td>${escapeHtml(item.provider)}</td><td>${escapeHtml(item.file_name)}</td><td>${item.page || ""}</td><td>${escapeHtml(item.status)}</td><td>${escapeHtml(item.detail)}</td></tr>
  `).join("")}</tbody></table>`;
}

function renderChanges() {
  const suggestions = state.run.version_links.map((link) => `
    <div class="version-item">
      <span><strong>${escapeHtml(link.current_file_name)}</strong><br><small>${escapeHtml(link.previous_file_name)} / ${Math.round(link.similarity * 100)}% similar / ${escapeHtml(link.decision)}</small></span>
      ${link.decision === "suggested" ? `<span class="inline-actions"><button class="secondary-button compact-button" data-version-link="${link.id}" data-version-decision="0">Skip</button><button class="primary-button compact-button" data-version-link="${link.id}" data-version-decision="1">Compare</button></span>` : ""}
    </div>`).join("");
  const manual = state.run.previous_files.length ? `<form id="manualVersionForm" class="inline-form"><strong>Manual comparison</strong><select name="currentFile">${state.run.files.map((file) => `<option>${escapeHtml(file.file_name)}</option>`).join("")}</select><select name="previousFile">${state.run.previous_files.map((file) => `<option value="${file.id}">${escapeHtml(file.file_name)} / Run #${file.previous_run_id}</option>`).join("")}</select><button class="secondary-button" type="submit">Compare selected files</button></form>` : "";
  const table = state.run.changes.length ? `<table><thead><tr><th>Type</th><th>File</th><th>Location</th><th>Previous</th><th>Current</th></tr></thead><tbody>${state.run.changes.map((item) => `
    <tr><td>${escapeHtml(item.type)}</td><td>${escapeHtml(item.file_name)}</td><td>${escapeHtml(item.location)}</td><td>${escapeHtml(item.before)}</td><td>${escapeHtml(item.after)}</td></tr>
  `).join("")}</tbody></table>` : `<div class="empty-state"><p>No confirmed previous-version differences yet. Suggestions only appear for same-type filenames with at least 90% similarity.</p></div>`;
  return `<div class="stack">${suggestions}${manual}${table}</div>`;
}

function renderMatches() {
  const mappings = (state.project.mappings || []).map((item) => `<div class="mapping-item">${escapeHtml(item.page_file_name)} ${item.page ? `page ${item.page}` : ""} -> ${escapeHtml(item.source_file_name)} ${escapeHtml(item.sheet_name)}</div>`).join("");
  const mappingForm = `<form id="mappingForm" class="inline-form"><strong>Page source constraint</strong><input name="pageFile" required placeholder="deck.pptx"><input name="page" type="number" min="1" placeholder="Page"><input name="sourceFile" required placeholder="source.xlsx"><input name="sheet" placeholder="Sheet"><button class="secondary-button" type="submit">Add constraint</button></form>`;
  if (!state.run.matches.length) return `<div class="stack">${mappingForm}${mappings}<div class="empty-state"><p>No cross-file numeric matches were found for this package.</p></div></div>`;
  const matched = state.run.matches.filter((item) => item.status === "matched").length;
  const unmatched = state.run.matches.length - matched;
  const visibleMatches = state.matchFilter === "all" ? state.run.matches : state.run.matches.filter((item) => item.status === state.matchFilter);
  const filter = `<div class="filter-row"><strong>Visible numbers: ${state.run.matches.length}</strong><button class="secondary-button compact-button ${state.matchFilter === "unmatched" ? "selected-filter" : ""}" data-match-filter="unmatched">Unmatched ${unmatched}</button><button class="secondary-button compact-button ${state.matchFilter === "matched" ? "selected-filter" : ""}" data-match-filter="matched">Matched ${matched}</button><button class="secondary-button compact-button ${state.matchFilter === "all" ? "selected-filter" : ""}" data-match-filter="all">All</button></div>`;
  return `<div class="stack">${mappingForm}${mappings}${filter}<table><thead><tr><th>Visible number</th><th>Best Excel sources</th><th></th></tr></thead><tbody>${visibleMatches.map((match) => `
    <tr><td>${escapeHtml(match.observation.file_name)}<br><small>${escapeHtml(match.observation.location)} / ${escapeHtml(match.observation.value)}</small></td>
    <td>${match.candidates.length ? `<select data-match-select="${match.id}">${match.candidates.map((candidate, index) => `<option value="${index}" ${match.selected_candidate_index === index ? "selected" : ""}>${escapeHtml(candidate.file_name)} / ${escapeHtml(candidate.location)} / ${escapeHtml(candidate.value)} / ${Math.round(candidate.confidence * 100)}%</option>`).join("")}</select>` : `<span class="unmatched">No Excel source candidate</span>`}</td>
    <td>${match.candidates.length ? `<button class="secondary-button compact-button" data-confirm-match="${match.id}">${match.selected_candidate_index === null ? "Confirm" : "Confirmed"}</button>` : ""}</td></tr>
  `).join("")}</tbody></table></div>`;
}

function bindTabActions() {
  document.querySelectorAll("[data-save-issue]").forEach((button) => button.addEventListener("click", updateIssue));
  document.querySelectorAll("[data-review-coverage]").forEach((button) => button.addEventListener("click", reviewCoverage));
  document.querySelectorAll("[data-confirm-match]").forEach((button) => button.addEventListener("click", confirmMatch));
  document.querySelectorAll("[data-version-link]").forEach((button) => button.addEventListener("click", confirmVersion));
  document.querySelectorAll("[data-match-filter]").forEach((button) => button.addEventListener("click", (event) => {
    state.matchFilter = event.target.dataset.matchFilter;
    renderTab();
  }));
  $("manualVersionForm")?.addEventListener("submit", addManualVersion);
  $("mappingForm")?.addEventListener("submit", addMapping);
}

async function updateIssue(event) {
  const id = event.target.dataset.saveIssue;
  await api(`/api/issues/${id}/status`, { method: "POST", body: JSON.stringify({
    status: document.querySelector(`[data-issue-status="${id}"]`).value,
    note: document.querySelector(`[data-issue-note="${id}"]`).value,
    user_id: state.user.id,
  }) });
  await openRun(state.run.run.id);
}

async function reviewCoverage(event) {
  const note = prompt("Optional review note", "Checked visible page content");
  if (note === null) return;
  await api(`/api/coverage/${event.target.dataset.reviewCoverage}/review`, { method: "POST", body: JSON.stringify({ user_id: state.user.id, note }) });
  await openRun(state.run.run.id);
}

async function confirmMatch(event) {
  const id = event.target.dataset.confirmMatch;
  await api(`/api/numeric-matches/${id}/confirm`, { method: "POST", body: JSON.stringify({
    user_id: state.user.id,
    candidate_index: Number(document.querySelector(`[data-match-select="${id}"]`).value),
  }) });
  await openRun(state.run.run.id);
}

async function confirmVersion(event) {
  await api(`/api/version-links/${event.target.dataset.versionLink}/confirm`, { method: "POST", body: JSON.stringify({
    user_id: state.user.id,
    confirmed: event.target.dataset.versionDecision === "1",
  }) });
  await openRun(state.run.run.id);
}

async function addManualVersion(event) {
  event.preventDefault();
  const form = new FormData(event.target);
  await api(`/api/runs/${state.run.run.id}/version-links`, { method: "POST", body: JSON.stringify({
    user_id: state.user.id,
    current_file_name: form.get("currentFile"),
    previous_file_id: Number(form.get("previousFile")),
  }) });
  await openRun(state.run.run.id);
}

async function addMapping(event) {
  event.preventDefault();
  const form = new FormData(event.target);
  const runId = state.run.run.id;
  await api(`/api/projects/${state.project.id}/mappings`, { method: "POST", body: JSON.stringify({
    user_id: state.user.id,
    page_file_name: form.get("pageFile"),
    page: form.get("page"),
    source_file_name: form.get("sourceFile"),
    sheet_name: form.get("sheet"),
  }) });
  await openProject(state.project.id);
  await openRun(runId);
}

async function toggleRule(event) {
  await api(`/api/rules/${event.target.dataset.ruleToggle}/active`, { method: "POST", body: JSON.stringify({ active: event.target.dataset.active !== "1" }) });
  await openProject(state.project.id);
}

const readFile = (file) => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.onload = () => resolve({ name: file.name, content_base64: reader.result.split(",")[1] });
  reader.onerror = reject;
  reader.readAsDataURL(file);
});

$("identityForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const data = await api("/api/users", { method: "POST", body: JSON.stringify({ name: form.get("name"), email: form.get("email") }) });
  state.user = data.user;
  localStorage.setItem("worldpanelQcUser", JSON.stringify(data.user));
  $("identityBadge").textContent = `${data.user.name} / ${state.runtime?.authentication_required ? "shared workspace" : "local mode"}`;
  $("identityDialog").close();
});
$("newProjectButton").addEventListener("click", () => $("projectDialog").showModal());
$("llmSettingsButton").addEventListener("click", openLlmSettings);
$("logoutButton").addEventListener("click", async () => {
  await api("/api/auth/logout", { method: "POST", body: "{}" });
  window.location.replace("/login");
});
$("llmSettingsForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = await api("/api/llm/settings", { method: "POST", body: JSON.stringify(llmSettingsPayload()) });
  renderLlmWarning(data.settings.warning);
  $("llmTestResult").textContent = "Settings saved locally.";
  $("llmSettingsDialog").close();
});
$("testLlmButton").addEventListener("click", async () => {
  $("llmTestResult").textContent = "Testing connection...";
  try {
    const result = await api("/api/llm/test", { method: "POST", body: JSON.stringify(llmSettingsPayload()) });
    $("llmTestResult").textContent = result.ok ? "Connection successful." : `Connection failed: ${result.detail || result.status}`;
  } catch (error) {
    $("llmTestResult").textContent = "Connection failed. Check endpoint, token, and intranet access.";
  }
});
$("projectForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const data = await api("/api/projects", { method: "POST", body: JSON.stringify({
    name: form.get("name"),
    category_template: form.get("categoryTemplate"),
    user_id: state.user.id,
  }) });
  $("projectDialog").close();
  await loadProjects();
  await openProject(data.project.id);
});
$("newRunButton").addEventListener("click", () => $("runDialog").showModal());
$("newRuleButton").addEventListener("click", () => $("ruleDialog").showModal());
$("ruleForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  await api(`/api/projects/${state.project.id}/rules`, { method: "POST", body: JSON.stringify({
    name: form.get("name"),
    rule_type: form.get("ruleType"),
    severity: form.get("severity"),
    config: { text: form.get("text"), file_types: [form.get("fileType")] },
  }) });
  $("ruleDialog").close();
  await openProject(state.project.id);
});
$("runForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const selectedFiles = [...$("fileInput").files];
  const hasSlides = selectedFiles.some((file) => /\.(pptx|ppt|pdf)$/i.test(file.name));
  const hasWorkbook = selectedFiles.some((file) => /\.(xlsx|xls)$/i.test(file.name));
  if (hasSlides && hasWorkbook && !window.confirm("This upload mixes PPT/PDF and Excel files. Continue only if they belong to the same report package and need cross-checking.")) {
    return;
  }
  const assist = await api(`/api/projects/${state.project.id}/scope-assist`, { method: "POST", body: JSON.stringify({
    review_goal: form.get("reviewGoal"),
    use_ai_scope_assist: true,
    files: selectedFiles.map((file) => ({ name: file.name })),
  }) });
  const boundaryText = (assist.questions || []).map((item, index) => `${index + 1}. ${item.question}`).join("\n");
  const boundaryAnswer = boundaryText ? window.prompt(`Please clarify the QC boundary before starting:\n\n${boundaryText}`, form.get("reviewGoal") || "Full check") : "";
  if (boundaryText && boundaryAnswer === null) return;
  const files = await Promise.all(selectedFiles.map(readFile));
  const submitButton = event.target.querySelector('[type="submit"]');
  submitButton.disabled = true;
  submitButton.textContent = "Uploading...";
  try {
    const data = await api(`/api/projects/${state.project.id}/runs`, { method: "POST", body: JSON.stringify({
      user_id: state.user.id,
      llm_logic_review_enabled: Boolean(form.get("llmLogicReview")),
      external_ai_enabled: Boolean(form.get("externalAi")),
      output_language: form.get("outputLanguage"),
      review_goal: form.get("reviewGoal"),
      scope_status: "confirmed",
      scope: { mode: form.get("scopeMode"), raw_goal: form.get("reviewGoal"), boundary_answer: boundaryAnswer },
      scope_questions: (assist.questions || []).map((item) => ({ ...item, answer: boundaryAnswer })),
      files,
    }) });
    $("runDialog").close();
    await openRun(data.run.id);
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Run QC";
  }
});
$("backToProject").addEventListener("click", () => openProject(state.project.id));
$("exportExcel").addEventListener("click", (event) => {
  if (event.currentTarget.getAttribute("aria-disabled") === "true") event.preventDefault();
});
$("exportPdf").addEventListener("click", (event) => {
  if (event.currentTarget.getAttribute("aria-disabled") === "true") event.preventDefault();
});
$("completeRunButton").addEventListener("click", () => $("completeDialog").showModal());
$("completeForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  try {
    await api(`/api/runs/${state.run.run.id}/complete`, { method: "POST", body: JSON.stringify({ user_id: state.user.id, note: form.get("note") }) });
    $("completeDialog").close();
    await openRun(state.run.run.id);
  } catch {
    alert("QC cannot be completed yet. Resolve open issues and confirm all review pages first.");
  }
});
document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => {
  state.activeTab = tab.dataset.tab;
  renderTab();
}));
document.querySelectorAll("[data-close-dialog]").forEach((button) => button.addEventListener("click", () => $(button.dataset.closeDialog).close()));

boot();

