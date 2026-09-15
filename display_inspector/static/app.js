const fileInput = document.getElementById("file");
const drop = document.getElementById("drop");
const thumbs = document.getElementById("thumbs");
const noteEl = document.getElementById("note");
const runBtn = document.getElementById("run");
const statusEl = document.getElementById("status");
const emptyEl = document.getElementById("empty");
const reportEl = document.getElementById("report");
const samplesEl = document.getElementById("samples");
const rulesEl = document.getElementById("rules");

let files = [];
let region = "全景";

document.querySelectorAll("#regions button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("#regions button").forEach((b) => b.classList.remove("on"));
    btn.classList.add("on");
    region = btn.dataset.value;
  });
});

function visionHeaders() {
  const headers = {};
  const key = document.getElementById("apiKey").value.trim();
  const url = document.getElementById("baseUrl").value.trim();
  const model = document.getElementById("model").value.trim();
  if (key) headers["X-Vision-Api-Key"] = key;
  if (url) headers["X-Vision-Base-Url"] = url;
  if (model) headers["X-Vision-Model"] = model;
  return headers;
}

function renderThumbs() {
  thumbs.innerHTML = "";
  files.forEach((file) => {
    const img = document.createElement("img");
    img.src = URL.createObjectURL(file);
    img.alt = file.name;
    thumbs.appendChild(img);
  });
}

drop.addEventListener("dragover", (e) => {
  e.preventDefault();
  drop.classList.add("drag");
});
drop.addEventListener("dragleave", () => drop.classList.remove("drag"));
drop.addEventListener("drop", (e) => {
  e.preventDefault();
  drop.classList.remove("drag");
  files = [...e.dataTransfer.files].filter((f) => f.type.startsWith("image/"));
  renderThumbs();
});
fileInput.addEventListener("change", () => {
  files = [...fileInput.files];
  renderThumbs();
});

function badge(status) {
  if (status === "合规") return `<span class="badge ok">合规</span>`;
  if (status === "不合规") return `<span class="badge bad">不合规</span>`;
  return `<span class="badge unk">${status}</span>`;
}

function table(rows, columns) {
  if (!rows.length) return "<p class='hint'>无</p>";
  const head = columns.map((c) => `<th>${c.label}</th>`).join("");
  const body = rows
    .map((row) => {
      const tds = columns
        .map((c) => {
          let val = row[c.key] ?? "";
          if (c.key === "severity" && val) val = `<span class="sev-${val}">${val}</span>`;
          return `<td>${val || "—"}</td>`;
        })
        .join("");
      return `<tr>${tds}</tr>`;
    })
    .join("");
  return `<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function renderReport(data) {
  emptyEl.hidden = true;
  reportEl.hidden = false;
  const q = data.photo_validity || {};
    const json = JSON.stringify(data, null, 2);
    const cacheNote = data.from_selftest_cache
      ? `<p class="hint">这是已实地跑通并固化的自测结果，便于面试官立即查看。上传新照片会走实时检查。</p>`
      : "";
  reportEl.innerHTML = `
    <div class="meta">
      ${badge(data.overall_status)}
      <span>是否合规：${data.overall_compliant === true ? "是" : data.overall_compliant === false ? "否" : "无法判断"}</span>
      <span>模型：${data.model_used || "—"}</span>
    </div>
    <div class="summary">${data.summary || ""}</div>
    ${cacheNote}
    <p class="hint">${q.note || ""}</p>
    <h3>不合规问题</h3>
    ${table(data.issues || [], [
      { key: "problem", label: "具体问题" },
      { key: "rule_id", label: "规则" },
      { key: "rule_text", label: "对应检查标准" },
      { key: "area", label: "所在区域" },
      { key: "severity", label: "严重程度" },
      { key: "suggestion", label: "整改建议" },
    ])}
    <h3>无法判断</h3>
    ${table(data.undetermined_items || [], [
      { key: "rule_id", label: "规则" },
      { key: "rule_text", label: "对应检查标准" },
      { key: "undetermined_reason", label: "无法判断原因" },
    ])}
    <h3>全部检查项</h3>
    ${table(data.findings || [], [
      { key: "category", label: "类别" },
      { key: "rule_id", label: "规则" },
      { key: "status", label: "判定" },
      { key: "severity", label: "严重程度" },
      { key: "problem", label: "问题" },
      { key: "suggestion", label: "建议" },
    ])}
    <div class="json-actions">
      <button type="button" id="copyJson">复制 JSON</button>
      <a id="downloadJson" download="display-inspect.json" href="#">下载 JSON</a>
    </div>
    <pre>${json.replace(/[<>]/g, "")}</pre>
  `;
  const blob = new Blob([json], { type: "application/json" });
  document.getElementById("downloadJson").href = URL.createObjectURL(blob);
  document.getElementById("copyJson").onclick = async () => {
    await navigator.clipboard.writeText(json);
    statusEl.textContent = "已复制 JSON。";
  };
}

async function inspectUpload() {
  if (!files.length) {
    statusEl.textContent = "请先上传至少一张照片。";
    return;
  }
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  form.append("note", noteEl.value);
  form.append("region", region);
  await postInspect("/api/inspect", form);
}

async function postInspect(url, body) {
  runBtn.disabled = true;
  statusEl.textContent = "正在按规则库核验，请稍候…";
  try {
    const opts = { method: "POST", headers: visionHeaders() };
    if (body instanceof FormData) opts.body = body;
    const res = await fetch(url, opts);
    const text = await res.text();
    let data;
    try {
      data = JSON.parse(text);
    } catch {
      if (/no tunnel/i.test(text) || text.trim().startsWith("<")) {
        throw new Error("临时入口已断开（隧道失效）。请换用最新链接，或点页面上的内置样例。");
      }
      throw new Error(text.slice(0, 160) || res.statusText);
    }
    if (!res.ok) throw new Error(data.detail || data.error || res.statusText);
    renderReport(data);
    statusEl.textContent = "检查完成。";
  } catch (err) {
    statusEl.textContent = "检查失败：" + err.message;
  } finally {
    runBtn.disabled = false;
  }
}

runBtn.addEventListener("click", inspectUpload);

async function loadRules() {
  const res = await fetch("/api/rules");
  const data = await res.json();
  const sev = data.severity_definition || {};
  rulesEl.innerHTML = `
    <div class="rule-card">
      <h3>照片有效性 · ${data.photo_validity.id}</h3>
      <p>${data.photo_validity.text}</p>
    </div>
    <div class="rule-card">
      <h3>严重程度</h3>
      <ul>
        <li>高：${sev["高"] || ""}</li>
        <li>中：${sev["中"] || ""}</li>
        <li>低：${sev["低"] || ""}</li>
      </ul>
    </div>
  ` + data.categories.map((cat) => `
    <div class="rule-card">
      <h3>${cat.name}</h3>
      <ul>${cat.rules.map((r) => `<li><code>${r.id}</code> ${r.text}（${r.severity}）</li>`).join("")}</ul>
    </div>
  `).join("");
}

async function loadSamples() {
  const res = await fetch("/api/samples");
  const data = await res.json();
  samplesEl.innerHTML = "";
  (data.samples || []).forEach((s) => {
    if (!s.available) return;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = s.title;
    btn.addEventListener("click", async () => {
      const img = document.createElement("img");
      img.src = s.url;
      img.alt = s.title;
      thumbs.innerHTML = "";
      thumbs.appendChild(img);
      noteEl.value = s.note || "";
      await postInspect(`/api/inspect-sample/${s.id}`);
    });
    samplesEl.appendChild(btn);
  });
}

loadRules().catch(() => {});
loadSamples().catch(() => {});
fetch("/api/health").then((r) => r.json()).then((h) => {
  if (h.local_vlm && h.local_vlm.loaded) statusEl.textContent = "本地视觉模型已就绪。";
  else if (h.cloud_vision_configured) {
    statusEl.textContent = h.vision_model
      ? `已配置云端视觉：${h.vision_model}。上传清晰照片会走该模型。`
      : "已配置云端视觉接口。";
  } else statusEl.textContent = "可直接上传或点自测样例。未填云端视觉接口时，本地模型逐项核验约 1–3 分钟。";
}).catch(() => {});
