const state = { document: null, jobId: null, pollTimer: null };
const $ = (id) => document.getElementById(id);

function show(id, visible = true) { $(id).classList.toggle("hidden", !visible); }
function toast(message) {
  $("toast").textContent = message;
  show("toast");
  window.setTimeout(() => show("toast", false), 4200);
}
async function api(url, options = {}) {
  const response = await fetch(url, options);
  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json") ? await response.json() : await response.blob();
  if (!response.ok || body?.ok === false) throw new Error(body?.error?.message || `请求失败 (${response.status})`);
  return body;
}

async function checkRuntime() {
  try {
    const data = await api("/health");
    $("runtimeText").textContent = `${data.parser.name} ${data.parser.version} · 本地可用`;
    document.querySelector(".runtime").classList.add("ready");
  } catch (error) {
    $("runtimeText").textContent = "本地解析器不可用";
    toast(error.message);
  }
}

async function parseFile(file) {
  if (!file) return;
  state.document = null;
  $("submitButton").disabled = true;
  $("fileName").textContent = file.name;
  $("fileMeta").textContent = `${(file.size / 1024 / 1024).toFixed(2)} MB · 仅本地处理`;
  $("parseState").textContent = "解析中…";
  show("fileRow");
  show("warningBox", false);
  const form = new FormData();
  form.append("document", file);
  try {
    const data = await api("/api/documents/parse", { method: "POST", body: form });
    state.document = data.document;
    $("parseState").textContent = data.document.cached ? "缓存命中" : "解析完成";
    $("markdownPreview").textContent = data.document.markdownPreview;
    $("previewMeta").textContent = `${data.document.textLength.toLocaleString()} 字符 · ${data.document.chunkPaths.length} 分块`;
    show("resultEmpty", false);
    show("resultJson", false);
    show("previewPanel");
    if (data.document.warnings.length) {
      $("warningBox").innerHTML = data.document.warnings.map((item) => `<p>⚠ ${escapeHtml(item)}</p>`).join("");
      show("warningBox");
    }
    show("lowQualityLabel", data.document.needsOcr);
    updateSubmitState();
  } catch (error) {
    $("parseState").textContent = "解析失败";
    toast(error.message);
  }
}

function propertyList() {
  return $("properties").value.split(/[\n,，]/).map((value) => value.trim()).filter(Boolean);
}
function updateSubmitState() { $("submitButton").disabled = !state.document || propertyList().length === 0; }

async function submitExtraction() {
  if (!state.document) return;
  $("submitButton").disabled = true;
  try {
    const data = await api("/api/extractions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        document_id: state.document.documentId,
        properties: propertyList(),
        allow_low_quality: $("allowLowQuality").checked,
      }),
    });
    state.jobId = data.submission.jobId;
    show("previewPanel", false);
    show("progress");
    $("jobSummary").textContent = `任务 ${state.jobId.slice(0, 8)} 已进入队列`;
    await pollExtraction();
  } catch (error) {
    toast(error.message);
    updateSubmitState();
  }
}

async function pollExtraction() {
  if (!state.jobId) return;
  try {
    const data = await api(`/api/extractions/${state.jobId}`);
    const job = data.extraction.job;
    const processed = job.completed_items + job.failed_items;
    const percent = job.total_items ? Math.round(processed / job.total_items * 100) : 4;
    $("progressBar").style.width = `${Math.max(4, percent)}%`;
    $("jobSummary").textContent = `${statusLabel(job.status)} · ${processed}/${job.total_items} 个文档`;
    if (["completed", "failed", "cancelled"].includes(job.status)) {
      window.clearTimeout(state.pollTimer);
      $("resultJson").textContent = JSON.stringify(data.extraction.items, null, 2);
      show("resultJson");
      show("exportButton", job.status === "completed");
      updateSubmitState();
      return;
    }
    state.pollTimer = window.setTimeout(pollExtraction, 2000);
  } catch (error) {
    toast(error.message);
    state.pollTimer = window.setTimeout(pollExtraction, 4000);
  }
}

async function exportResult() {
  try {
    const response = await fetch(`/api/extractions/${state.jobId}/export`, { method: "POST" });
    if (!response.ok) {
      const problem = await response.json();
      throw new Error(problem?.error?.message || "导出失败");
    }
    const blob = await response.blob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `deep-dig-${state.jobId}.xlsx`;
    link.click();
    URL.revokeObjectURL(link.href);
  } catch (error) { toast(error.message); }
}

function statusLabel(status) {
  return ({ pending: "等待处理", running: "正在提取", completed: "提取完成", failed: "任务失败", cancelled: "任务已取消" })[status] || status;
}
function escapeHtml(value) {
  return value.replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
}

$("fileInput").addEventListener("change", (event) => parseFile(event.target.files[0]));
$("properties").addEventListener("input", updateSubmitState);
$("submitButton").addEventListener("click", submitExtraction);
$("exportButton").addEventListener("click", exportResult);
for (const eventName of ["dragenter", "dragover"]) {
  $("dropzone").addEventListener(eventName, (event) => { event.preventDefault(); $("dropzone").classList.add("drag"); });
}
for (const eventName of ["dragleave", "drop"]) {
  $("dropzone").addEventListener(eventName, (event) => { event.preventDefault(); $("dropzone").classList.remove("drag"); });
}
$("dropzone").addEventListener("drop", (event) => parseFile(event.dataTransfer.files[0]));
checkRuntime();

