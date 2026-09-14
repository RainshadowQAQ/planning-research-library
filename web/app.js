import { $, esc, api, getState, saveState } from "./state.js";
import { Reader } from "./reader.js";
const today = new Intl.DateTimeFormat("en-CA", {
  timeZone: "Asia/Hong_Kong",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
}).format(new Date());
const active = new Set(["queued", "searching", "collecting"]);
let folders = [],
  p = null,
  doc = null,
  readerKey = "",
  readerTimer,
  ui = {},
  prefs = {},
  loadToken = 0,
  viewBusy = 0,
  loading = false,
  exportView;
function toast(m) {
  $("toast").textContent = m;
  $("toast").hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => ($("toast").hidden = true), 7000);
}
function persist() {
  const writes = [];
  if (p) {
    prefs.search = $("search").value;
    prefs.scroll = $("main").scrollTop;
    prefs.selected = doc?.id;
    prefs.version = doc?.sha256;
    writes.push(saveState("folder:" + p.id, prefs));
  }
  writes.push(saveState("library", ui));
  return Promise.all(writes).catch((e) => toast(e.message));
}
function savePosition() {
  clearTimeout(readerTimer);
  return readerKey && reader.ready
    ? saveState(readerKey, reader.position()).catch((e) => toast(e.message))
    : Promise.resolve();
}
const reader = new Reader(
  $("reader-container"),
  (pos) => {
    $("page").value = pos.page || 1;
    $("zoom").value = String(pos.zoom || "page-width");
    clearTimeout(readerTimer);
    const key = readerKey;
    readerTimer = setTimeout(() => {
      if (key) saveState(key, pos).catch((e) => toast(e.message));
    }, 350);
  },
  (n) => {
    $("pages").textContent = "/ " + n;
    $("page").max = n;
    $("reader-message").hidden = true;
  },
  (m) => {
    $("reader-message").textContent = m;
    $("reader-message").hidden = false;
  },
);
function query() {
  const q = new URLSearchParams();
  if (prefs.run) q.set("run", prefs.run);
  else if (prefs.cutoff) q.set("cutoff", prefs.cutoff);
  return q.size ? "?" + q : "";
}
function link(url, label) {
  try {
    const u = new URL(url);
    if (
      u.protocol === "https:" &&
      ["www.tpb.gov.hk", "www.ozp.tpb.gov.hk"].includes(u.hostname)
    )
      return `<a href="${esc(url)}" target="_blank" rel="noopener">${label} ↗</a>`;
  } catch {}
  return "—";
}
const fileURL = (d) => `/api/folders/${p.id}/files/${d.source_run}/${d.id}`;
async function selectFolder(id) {
  ++viewBusy;
  try {
    const token = ++loadToken;
    ++docToken;
    await savePosition();
    await persist();
    const saved = await getState("folder:" + id);
    if (token !== loadToken) return;
    prefs = saved;
    ui.folder = id;
    $("search").value = prefs.search || "";
    try {
      const data = await api("/api/folders/" + id + query());
      if (token !== loadToken) return;
      p = data;
      ui.folder = p.id;
      await render(true);
      persist();
    } catch (e) {
      toast(e.message);
    }
  } finally {
    --viewBusy;
  }
}
async function refresh() {
  if (viewBusy) return;
  const token = loadToken;
  const nextFolders = await api("/api/folders");
  if (viewBusy || token !== loadToken) return;
  folders = nextFolders;
  renderFolders();
  if (p) {
    const data = await api("/api/folders/" + p.id + query());
    if (token !== loadToken) return;
    p = data;
    await render(false);
  } else if (folders.length)
    await selectFolder(
      folders.some((f) => f.id === ui.folder) ? ui.folder : folders[0].id,
    );
  else {
    $("empty").hidden = false;
    $("workspace").hidden = true;
  }
}
function renderFolders() {
  $("folders").innerHTML = folders
    .map(
      (f) =>
        `<button class="${p?.id === f.id ? "active" : ""}" data-folder="${f.id}">▤ ${esc(f.case_no)}</button>`,
    )
    .join("");
  document
    .querySelectorAll("[data-folder]")
    .forEach((b) => (b.onclick = () => selectFolder(b.dataset.folder)));
}
async function render(restore) {
  $("empty").hidden = true;
  $("workspace").hidden = false;
  renderFolders();
  $("case-title").textContent = p.case_no;
  $("reader-case").textContent = p.case_no;
  $("address").textContent =
    p.application?.subj
      ?.map((s) => s.locatAddrTC || s.locatAddrEN || "")
      .join("；") || "";
  const count = p.documents.filter((d) => d.status === "ready").length;
  $("file-count").textContent = count + " 份文件";
  $("scope").innerHTML =
    '<option value="all">全部已存文件</option><option value="date">截至日期…</option>' +
    p.runs
      .map(
        (r) =>
          `<option value="${r.id}">檢索 ${esc(r.created_at.slice(0, 16).replace("T", " "))} · 截至 ${esc(r.cutoff)}</option>`,
      )
      .join("");
  $("scope").value = prefs.run || (prefs.cutoff ? "date" : "all");
  $("date-filter").hidden = !prefs.cutoff;
  $("date-filter").value = prefs.cutoff || today;
  const busy = active.has(p.live_phase);
  $("update").disabled = busy;
  const labels = {
    queued: "等待搜集",
    searching: "查找申請",
    collecting: "搜集文件",
  };
  $("status").innerHTML = busy
    ? `<div class="banner">${labels[p.live_phase]}…</div>`
    : p.error
      ? `<div class="banner error">${esc(p.error)}</div>`
      : "";
  $("categories").innerHTML =
    '<div class="section-label">文件</div>' +
    ["全部文件", "Gist", "會議文件", "會議記錄"]
      .map(
        (k) =>
          `<button class="category ${(prefs.kind || "全部文件") === k ? "active" : ""}" data-kind="${k}">${k}<span class="count">${p.documents.filter((d) => d.status === "ready" && (k === "全部文件" || d.kind === k)).length}</span></button>`,
      )
      .join("");
  document.querySelectorAll("[data-kind]").forEach(
    (b) =>
      (b.onclick = () => {
        prefs.kind = b.dataset.kind;
        render(false);
        persist();
      }),
  );
  renderCandidates();
  renderRows();
  renderApplication();
  $("documents").hidden = prefs.tab === "application";
  $("application").hidden = prefs.tab !== "application";
  $("files-tab").classList.toggle("selected", prefs.tab !== "application");
  $("application-tab").classList.toggle(
    "selected",
    prefs.tab === "application",
  );
  $("export").disabled = !count;
  const selected =
    p.documents.find(
      (d) =>
        d.id === (restore ? prefs.selected : doc?.id) && d.status === "ready",
    ) || p.documents.find((d) => d.status === "ready");
  $("file-switch").innerHTML = p.documents
    .filter((d) => d.status === "ready")
    .map((d) => `<option value="${d.id}">${esc(d.title)}</option>`)
    .join("");
  if (selected) {
    const v = selected.versions?.find(
      (v) => v.sha256 === (restore ? prefs.version : doc?.sha256),
    );
    await selectDocument(v ? { ...selected, ...v } : selected);
  } else {
    await savePosition();
    readerKey = "";
    doc = null;
    await reader.clear();
    $("reader-message").textContent = "選取文件";
    $("reader-message").hidden = false;
    $("details").hidden = true;
    $("original").removeAttribute("href");
  }
  if (restore) $("main").scrollTop = prefs.scroll || 0;
}
function renderRows() {
  const term = $("search").value.toLowerCase();
  const ds = p.documents.filter(
    (d) =>
      (!prefs.kind || prefs.kind === "全部文件" || d.kind === prefs.kind) &&
      (d.title + " " + d.language).toLowerCase().includes(term),
  );
  $("documents").innerHTML =
    ds
      .map((d) =>
        d.status === "ready"
          ? `<button class="row ${doc?.id === d.id ? "selected" : ""}" data-doc="${d.id}"><div class="row-title"><span class="pdf-badge">PDF</span>${esc(d.title)}</div><div class="meta">${esc(d.kind)} · ${esc(d.language)}${d.event_date ? " · " + esc(d.event_date) : ""}</div></button>`
          : `<div class="failure">${d.status === "error" ? `<button data-retry="${d.id}" ${active.has(p.live_phase) ? "disabled" : ""}>重試</button>` : ""}<div>${esc(d.title)}</div><div class="meta ${d.status === "error" ? "error" : ""}">${esc(d.error || "取得文件中…")}</div></div>`,
      )
      .join("") || '<p class="meta">沒有符合的文件</p>';
  document.querySelectorAll("[data-doc]").forEach((b) => {
    b.onclick = async () => {
      await selectDocument(p.documents.find((d) => d.id === b.dataset.doc));
      persist();
      if (matchMedia("(max-width: 850px)").matches) await focus(true);
    };
    b.onkeydown = (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        b.ondblclick();
      }
    };
    b.ondblclick = async () => {
      await selectDocument(p.documents.find((d) => d.id === b.dataset.doc));
      await focus(true);
    };
  });
  document.querySelectorAll("[data-retry]").forEach(
    (b) =>
      (b.onclick = () =>
        collect({
          parent: p.documents.find((d) => d.id === b.dataset.retry).source_run,
          retry_file: b.dataset.retry,
        })),
  );
}
function renderCandidates() {
  const show =
    ["awaiting_selection", "no_match"].includes(p.phase) &&
    p.candidates?.length;
  $("candidates").innerHTML = show
    ? "<h3>確認申請</h3>" +
      p.candidates
        .map(
          (c, i) =>
            `<div class="candidate"><label><input type="radio" name="candidate" value="${i}" ${c.caseNo !== p.case_no ? "disabled" : ""}><span>${esc(c.caseNo)}<small>${esc(c.planNo)} · ${esc(c.aplyUseTC || c.aplyUseEN)}</small></span></label>${link("https://www.tpb.gov.hk/en/application-search.html?caseno=" + encodeURIComponent(c.caseNo) + "&type=permission", "官方記錄")}</div>`,
        )
        .join("") +
      '<button id="confirm-case" disabled>確認並繼續</button>'
    : "";
  if (show) {
    document
      .querySelectorAll("[name=candidate]")
      .forEach(
        (r) => (r.onchange = () => ($("confirm-case").disabled = false)),
      );
    $("confirm-case").onclick = () =>
      collect({
        parent: p.run_id,
        candidate_index: Number(
          document.querySelector("[name=candidate]:checked").value,
        ),
      });
  }
}
function renderApplication() {
  const a = p.application;
  $("application").innerHTML = a
    ? `<dl><dt>申請用途</dt><dd>${esc(a.aplyUseTC || a.aplyUseEN || "—")}</dd><dt>場地／規劃面積</dt><dd>${esc(a.subj?.map((s) => s.planArea + " m²").join("；") || "—")}</dd><dt>資料取得日期</dt><dd>${esc(a.retrieved_at || "—")}</dd></dl><h3>關聯申請</h3>${p.related.map((r) => `<button class="related" data-related="${esc(r)}">${esc(r)} ↗</button>`).join("") || "—"}<h3>會議與決定</h3>${p.events.map((e) => `<details><summary>${esc(e.event_date)} · ${esc(e.authTypeCode)} ${esc(e.meetNo)}</summary><p>${esc(e.deciTC || e.deciEN || "—")}</p></details>`).join("")}${prefs.run ? `<h3>研究問題</h3><p>${esc(p.question || "—")}</p>` : ""}${p.issues.length ? "<h3>未納入項目</h3><ul>" + p.issues.map((i) => "<li>" + esc(i) + "</li>").join("") + "</ul>" : ""}`
    : '<p class="meta">尚無申請詳情</p>';
  document
    .querySelectorAll("[data-related]")
    .forEach((b) => (b.onclick = () => openNew(b.dataset.related)));
}
let docToken = 0;
async function selectDocument(d) {
  if (!d) return;
  const token = ++docToken;
  const key = `reader:${p.id}:${d.id}:${d.sha256}`;
  $("file-switch").value = d.id;
  if (key !== readerKey) {
    await savePosition();
    const saved = await getState(key);
    if (token !== docToken) return;
    doc = d;
    readerKey = key;
    $("reader-message").textContent = "載入文件…";
    $("reader-message").hidden = false;
    $("original").href = fileURL(d);
    reader.open(
      fileURL(d),
      d.sha256,
      Object.keys(saved).length
        ? saved
        : { page: d.matched_pages?.[0] || 1, offset: 0, zoom: "page-width" },
    );
  } else doc = d;
  prefs.selected = d.id;
  prefs.version = d.sha256;
  document
    .querySelectorAll("[data-doc]")
    .forEach((b) => b.classList.toggle("selected", b.dataset.doc === d.id));
  renderDetails();
}
function renderDetails() {
  if (!doc) return;
  const versions = p.documents.find((d) => d.id === doc.id)?.versions || [];
  $("details").innerHTML =
    `<h3>${esc(doc.title)}</h3>${versions.length > 1 ? `<label>保存版本<select id="version">${versions.map((v) => `<option value="${v.sha256}" ${v.sha256 === doc.sha256 ? "selected" : ""}>${esc(v.retrieved_at || v.source_run)}</option>`).join("")}</select></label>` : ""}<dl><dt>官方來源</dt><dd>${link(doc.url, "原文件")}</dd><dt>發現來源</dt><dd>${link(doc.discovered_from, "來源頁面／接口")}</dd><dt>會議／事件日期</dt><dd>${esc(doc.event_date || "—")}</dd><dt>取得日期</dt><dd>${esc(doc.retrieved_at || "—")}</dd><dt>頁數</dt><dd>${doc.pages || "—"}</dd><dt>編號出現頁碼</dt><dd>${esc(doc.matched_pages?.join("、") || "—")}</dd><dt>歸屬依據</dt><dd>${esc(doc.verification || "—")}</dd><dt>SHA-256</dt><dd>${esc(doc.sha256)}</dd></dl>`;
  if ($("version"))
    $("version").onchange = async () => {
      await selectDocument({
        ...doc,
        ...versions.find((v) => v.sha256 === $("version").value),
      });
      persist();
    };
}
async function focus(value) {
  if (value && !doc) return;
  await savePosition();
  if (value) await persist();
  const pos = reader.position();
  document.body.classList.toggle("focus", value);
  $("back").hidden = !value;
  $("focus").hidden = value;
  await new Promise(requestAnimationFrame);
  reader.restore(pos);
  if (!value) $("main").scrollTop = prefs.scroll || 0;
}
async function scopeChanged() {
  ++viewBusy;
  try {
    const token = ++loadToken;
    ++docToken;
    const url = "/api/folders/" + p.id + query();
    await savePosition();
    try {
      const data = await api(url);
      if (token !== loadToken) return;
      p = data;
      await render(false);
      persist();
    } catch (e) {
      toast(e.message);
    }
  } finally {
    --viewBusy;
  }
}
$("scope").onchange = () => {
  const v = $("scope").value;
  prefs.run = v === "all" || v === "date" ? null : v;
  prefs.cutoff = v === "date" ? $("date-filter").value || today : null;
  scopeChanged();
};
$("date-filter").max = today;
$("date-filter").onchange = () => {
  prefs.cutoff = $("date-filter").value || null;
  prefs.run = null;
  scopeChanged();
};
$("search").oninput = () => {
  renderRows();
  persist();
};
$("files-tab").onclick = () => {
  prefs.tab = "files";
  render(false);
  persist();
};
$("application-tab").onclick = () => {
  prefs.tab = "application";
  render(false);
  persist();
};
$("file-switch").onchange = async () => {
  await selectDocument(
    p.documents.find((d) => d.id === $("file-switch").value),
  );
  persist();
};
$("focus").onclick = () => focus(true);
$("back").onclick = () => focus(false);
$("details-toggle").onclick = () => {
  $("details").hidden = !$("details").hidden;
};
$("page").onchange = () => reader.page(Number($("page").value));
$("zoom").onchange = () =>
  reader.zoom(
    $("zoom").value === "page-width" ? "page-width" : Number($("zoom").value),
  );
$("zoom-in").onclick = () =>
  reader.zoom(Math.min(4, reader.viewer.currentScale * 1.2));
$("zoom-out").onclick = () =>
  reader.zoom(Math.max(0.25, reader.viewer.currentScale / 1.2));
function openNew(c = "") {
  $("case-input").value = c;
  $("question-input").value = "";
  $("cutoff-input").value = today;
  $("form-error").textContent = "";
  $("new-dialog").showModal();
  $("case-input").focus();
}
$("new-project").onclick = () => openNew();
$("cancel-new").onclick = () => $("new-dialog").close();
$("cutoff-input").max = today;
$("new-form").onsubmit = async (e) => {
  e.preventDefault();
  $("submit-new").disabled = true;
  try {
    const r = await api("/api/folders", {
      case_no: $("case-input").value,
      question: $("question-input").value,
      cutoff: $("cutoff-input").value,
    });
    $("new-dialog").close();
    folders = await api("/api/folders");
    await selectFolder(r.id);
  } catch (e) {
    $("form-error").textContent = e.message;
  } finally {
    $("submit-new").disabled = false;
  }
};
$("update").onclick = () => {
  $("update-question").value = p.question || "";
  $("update-cutoff").value = today;
  $("update-error").textContent = "";
  $("update-dialog").showModal();
};
$("update-cutoff").max = today;
$("cancel-update").onclick = () => $("update-dialog").close();
async function collect(extra = {}) {
  try {
    await api(`/api/folders/${p.id}/collect`, {
      question: p.question || "",
      cutoff: today,
      ...extra,
    });
    prefs.run = null;
    prefs.cutoff = null;
    await refresh();
  } catch (e) {
    toast(e.message);
  }
}
$("update-form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    await api(`/api/folders/${p.id}/collect`, {
      question: $("update-question").value,
      cutoff: $("update-cutoff").value,
    });
    $("update-dialog").close();
    prefs.run = null;
    prefs.cutoff = null;
    await refresh();
  } catch (e) {
    $("update-error").textContent = e.message;
  }
};
$("export").onclick = () => {
  exportView = {
    url: `/api/folders/${p.id}/archive` + query(),
    case: p.case_no,
  };
  const ds = p.documents.filter((d) => d.status === "ready");
  $("export-summary").textContent =
    `${p.case_no} · ${prefs.run ? "所選檢索記錄" : prefs.cutoff ? "截至 " + prefs.cutoff : "全部已存文件"} · ${ds.length} 份文件`;
  const issues = [
    ...p.issues,
    ...p.documents
      .filter((d) => d.status !== "ready")
      .map((d) => d.title + "：" + (d.error || "尚未取得")),
  ];
  $("export-issues").innerHTML = issues.length
    ? "<h3>未包含</h3><ul>" +
      issues.map((i) => "<li>" + esc(i) + "</li>").join("") +
      "</ul>"
    : "";
  $("export-error").textContent = "";
  $("export-dialog").showModal();
};
$("cancel-export").onclick = () => $("export-dialog").close();
$("download").onclick = async () => {
  const item = exportView;
  $("download").disabled = true;
  try {
    const r = await fetch(item.url);
    if (!r.ok) throw Error("資料包未能產生，請重試");
    const url = URL.createObjectURL(await r.blob());
    const a = document.createElement("a");
    a.href = url;
    a.download = item.case.replaceAll("/", "_") + ".zip";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
    $("export-dialog").close();
  } catch (e) {
    $("export-error").textContent = e.message;
  } finally {
    $("download").disabled = false;
  }
};
function widths() {
  if (ui.side) $("shell").style.setProperty("--side", ui.side + "px");
  if (ui.list) $("shell").style.setProperty("--list", ui.list + "px");
}
for (const [id, key, min, max] of [
  ["split-left", "side", 150, 310],
  ["split-right", "list", 300, 650],
]) {
  const el = $(id);
  el.addEventListener("keydown", (e) => {
    if (!["ArrowLeft", "ArrowRight"].includes(e.key)) return;
    e.preventDefault();
    ui[key] = Math.max(
      min,
      Math.min(
        max,
        (ui[key] || (key === "side" ? 204 : 440)) +
          (e.key === "ArrowRight" ? 10 : -10),
      ),
    );
    widths();
    reader.resize();
    persist();
  });
  el.onpointerdown = (e) => {
    el.setPointerCapture(e.pointerId);
    const x = e.clientX,
      start = ui[key] || (key === "side" ? 204 : 440);
    document.body.classList.add("resizing");
    el.onpointermove = (ev) => {
      ui[key] = Math.max(min, Math.min(max, start + ev.clientX - x));
      widths();
    };
    el.onpointerup = () => {
      el.onpointermove = null;
      document.body.classList.remove("resizing");
      reader.resize();
      persist();
    };
  };
}
let scrollTimer;
$("main").addEventListener("scroll", () => {
  clearTimeout(scrollTimer);
  scrollTimer = setTimeout(() => persist(), 200);
});
let resizeTimer;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => reader.resize(), 150);
});
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    savePosition();
    persist();
  }
});
try {
  ui = await getState("library");
  widths();
  const env = await api("/api/environment");
  $("environment").hidden = !env.test;
  await refresh();
} catch (e) {
  toast(e.message);
}
setInterval(async () => {
  if (loading) return;
  if (
    folders.some((f) => active.has(f.phase)) ||
    (p && active.has(p.live_phase))
  ) {
    loading = true;
    try {
      await refresh();
    } catch (e) {
      toast(e.message);
    } finally {
      loading = false;
    }
  }
}, 2000);
