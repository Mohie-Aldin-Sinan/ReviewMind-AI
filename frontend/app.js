const API_BASE_URL = "http://127.0.0.1:8000";
const MIN_REVIEWS = 3;

const analyzeButton = document.querySelector("#analyzeButton");
const exportButton = document.querySelector("#exportButton");
const chooseFileButton = document.querySelector("#chooseFileButton");
const csvFileInput = document.querySelector("#csvFile");
const uploadZone = document.querySelector("#uploadZone");
const fileStatus = document.querySelector("#fileStatus");
const productNameInput = document.querySelector("#productName");
const reviewsInput = document.querySelector("#reviews");
const formMessage = document.querySelector("#formMessage");
const importStatus = document.querySelector("#importStatus");
const reviewCount = document.querySelector("#reviewCount");
const reviewSource = document.querySelector("#reviewSource");
const issueCount = document.querySelector("#issueCount");
const criticalCount = document.querySelector("#criticalCount");
const candidateCount = document.querySelector("#candidateCount");

let selectedCsv = null;
let latestAnalysis = null;

analyzeButton.addEventListener("click", analyzeReviews);
exportButton.addEventListener("click", exportReleasePlan);
chooseFileButton.addEventListener("click", () => csvFileInput.click());
csvFileInput.addEventListener("change", handleFileSelection);
reviewsInput.addEventListener("input", handlePasteInput);
uploadZone.addEventListener("dragover", handleDragOver);
uploadZone.addEventListener("dragleave", handleDragLeave);
uploadZone.addEventListener("drop", handleDrop);

async function analyzeReviews() {
  const productName = productNameInput.value.trim();
  const rawText = reviewsInput.value.trim();

  if (!productName) {
    setMessage("Enter a product name before running analysis.", "error");
    return;
  }

  if (!selectedCsv && !rawText) {
    setMessage("Choose a CSV or paste at least a few app reviews to analyze.", "error");
    return;
  }

  setLoading(true);
  setMessage(`Cleaning ${selectedCsv ? "CSV" : "pasted"} reviews...`, "");

  try {
    const imported = selectedCsv
      ? await postJson("/api/import/csv", { csv_text: selectedCsv.text })
      : await postJson("/api/import/paste", { raw_text: rawText });

    if (imported.count < MIN_REVIEWS) {
      throw new Error(`At least ${MIN_REVIEWS} usable reviews are required after cleanup.`);
    }

    updateImportMetrics(imported);
    setMessage("Running AI analysis...", "");

    const analysis = await postJson("/api/analyze", {
      product_name: productName,
      reviews: imported.reviews,
    });

    latestAnalysis = analysis;
    renderAnalysis(analysis);
    exportButton.disabled = false;
    setMessage(`Analyzed ${analysis.review_count} reviews for ${analysis.product_name}.`, "success");
  } catch (error) {
    exportButton.disabled = !latestAnalysis;
    setMessage(error.message || "Analysis failed. Check that the backend is running.", "error");
  } finally {
    setLoading(false);
  }
}

function exportReleasePlan() {
  if (!latestAnalysis) {
    setMessage("Run an analysis before exporting a release plan.", "error");
    return;
  }

  const markdown = buildReleasePlan(latestAnalysis);
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const fileName = `${slugify(latestAnalysis.product_name || "reviewmind")}-release-plan.md`;

  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
  setMessage(`Exported ${fileName}.`, "success");
}

async function handleFileSelection(event) {
  const [file] = event.target.files;
  await loadCsvFile(file);
}

function handlePasteInput() {
  if (!reviewsInput.value.trim()) {
    return;
  }

  selectedCsv = null;
  csvFileInput.value = "";
  fileStatus.textContent = "Using pasted review text";
  reviewSource.textContent = "Bulk paste selected";
  importStatus.textContent = "Ready";
}

function handleDragOver(event) {
  event.preventDefault();
  uploadZone.classList.add("dragging");
}

function handleDragLeave() {
  uploadZone.classList.remove("dragging");
}

async function handleDrop(event) {
  event.preventDefault();
  uploadZone.classList.remove("dragging");

  const [file] = event.dataTransfer.files;
  await loadCsvFile(file);
}

async function loadCsvFile(file) {
  if (!file) {
    return;
  }

  if (!file.name.toLowerCase().endsWith(".csv")) {
    setMessage("Choose a CSV file exported from an app store, support tool, or survey platform.", "error");
    return;
  }

  const text = await file.text();
  selectedCsv = { name: file.name, text };
  reviewsInput.value = "";
  fileStatus.textContent = file.name;
  reviewSource.textContent = "CSV selected";
  importStatus.textContent = "CSV Ready";
  setMessage("CSV loaded. Run analysis when ready.", "success");
}

async function postJson(path, body) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || `Request failed with status ${response.status}.`);
  }

  return data;
}

function renderAnalysis(analysis) {
  const priorities = analysis.prioritized_issues || analysis.issues || [];
  renderPriorities(priorities);
  renderClusters(analysis.issues || []);

  issueCount.textContent = String(analysis.issues?.length || 0);
  criticalCount.textContent = String(
    (analysis.issues || []).filter((issue) => issue.severity === "critical" || issue.severity === "high").length,
  );
  candidateCount.textContent = String(priorities.length);
}

function buildReleasePlan(analysis) {
  const priorities = analysis.prioritized_issues || analysis.issues || [];
  const issues = analysis.issues || [];

  return [
    `# ${analysis.product_name || "Product"} Release Plan`,
    "",
    `Review count: ${analysis.review_count || 0}`,
    `Analysis mode: ${analysis.mode || "local"}`,
    "",
    "## Executive Summary",
    "",
    analysis.summary || "No summary was returned for this review set.",
    "",
    "## Prioritized Work",
    "",
    priorities.length ? priorities.map(formatPriority).join("\n\n") : "No prioritized issues were returned.",
    "",
    "## Issue Clusters",
    "",
    issues.length ? issues.map(formatIssueCluster).join("\n\n") : "No issue clusters were returned.",
    "",
    "## Positive Signals",
    "",
    formatList(analysis.positive_signals || []),
    "",
    "## Feature Requests",
    "",
    formatList(analysis.feature_requests || []),
    "",
  ].join("\n");
}

function formatPriority(issue, index) {
  const score = issue.rice_score ?? "-";
  const recommendation = issue.recommendation || "No recommendation provided.";
  const evidence = formatList(issue.evidence || []);

  return [
    `### ${index + 1}. ${issue.title || "Untitled issue"}`,
    "",
    `- Category: ${issue.category || "Other"}`,
    `- Severity: ${issue.severity || "medium"}`,
    `- Frequency: ${issue.frequency || 1}`,
    `- RICE score: ${score}`,
    `- Recommendation: ${recommendation}`,
    "- Evidence:",
    evidence,
  ].join("\n");
}

function formatIssueCluster(issue) {
  return [
    `### ${issue.title || issue.category || "Issue cluster"}`,
    "",
    `- Category: ${issue.category || "Other"}`,
    `- Severity: ${issue.severity || "medium"}`,
    `- Mentions: ${issue.frequency || 1}`,
    `- Action: ${issue.recommendation || "No recommendation provided."}`,
  ].join("\n");
}

function formatList(items) {
  if (!items.length) {
    return "- None captured";
  }

  return items.map((item) => `- ${item}`).join("\n");
}

function renderPriorities(priorityItems) {
  const list = document.querySelector("#priorityList");

  if (!priorityItems.length) {
    list.className = "priority-list empty";
    list.innerHTML = "<p>No prioritized issues were returned for this review set.</p>";
    return;
  }

  list.className = "priority-list";
  list.innerHTML = priorityItems
    .map(
      (item, index) => `
        <article class="priority-item">
          <span class="priority-rank">${index + 1}</span>
          <div class="priority-copy">
            <h4>${escapeHtml(item.title || "Untitled issue")}</h4>
            <p>${escapeHtml(item.recommendation || item.description || "No recommendation provided.")}</p>
            ${renderEvidence(item.evidence || [])}
          </div>
          <span class="priority-score">${item.rice_score ?? item.score ?? "-"}</span>
        </article>
      `,
    )
    .join("");
}

function renderClusters(clusters) {
  const grid = document.querySelector("#clusterGrid");

  if (!clusters.length) {
    grid.className = "cluster-grid empty";
    grid.innerHTML = "<p>No issue clusters were returned for this review set.</p>";
    return;
  }

  grid.className = "cluster-grid";
  grid.innerHTML = clusters
    .map(
      (cluster) => `
        <article class="cluster-card">
          <h4>${escapeHtml(cluster.title || cluster.category || "Issue cluster")}</h4>
          <p>${escapeHtml(cluster.recommendation || cluster.description || "Review theme detected.")}</p>
          <div class="cluster-meta">
            ${renderTags(cluster)}
          </div>
        </article>
      `,
    )
    .join("");
}

function renderEvidence(evidence) {
  const quotes = evidence.slice(0, 2);

  if (!quotes.length) {
    return "";
  }

  return `
    <ul class="evidence-list">
      ${quotes.map((quote) => `<li>${escapeHtml(quote)}</li>`).join("")}
    </ul>
  `;
}

function renderTags(cluster) {
  const tone = cluster.severity === "critical" || cluster.severity === "high" ? "bad" : "warn";
  const tags = [
    cluster.category || "Other",
    cluster.severity || "medium",
    `${cluster.frequency || 1} mentions`,
  ];

  return tags.map((tag) => `<span class="tag ${tone}">${escapeHtml(tag)}</span>`).join("");
}

function updateImportMetrics(imported) {
  reviewCount.textContent = String(imported.count);
  reviewSource.textContent = imported.source === "csv" ? selectedCsv?.name || "Cleaned from CSV" : "Cleaned from bulk paste";
  importStatus.textContent = "Imported";
}

function setLoading(isLoading) {
  analyzeButton.disabled = isLoading;
  analyzeButton.textContent = isLoading ? "Analyzing..." : "Analyze Reviews";
  exportButton.disabled = isLoading || !latestAnalysis;
  importStatus.textContent = isLoading ? "Working" : importStatus.textContent;
}

function slugify(value) {
  return String(value)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

function setMessage(message, type) {
  formMessage.textContent = message;
  formMessage.className = `form-message ${type}`.trim();
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
