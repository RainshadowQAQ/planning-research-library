import { esc } from "./state.js";

const STATUS = {
  no_paper: "此範圍內未保存規劃署主文件（會議文件 · 主文件），未能讀取先例。可先「更新資料」搜集會議文件。",
  unreadable: "主文件無法讀取。",
  no_text: "主文件沒有可讀文字層（可能是掃描本），未能讀取先例。",
};
const TONE = {
  approved: "ok",
  approved_with_conditions: "ok",
  rejected: "bad",
};

export function renderPrecedents(container, payload, { onCitation, onFolder, onNew }) {
  if (payload.status !== "ready") {
    container.innerHTML = `<p class="meta">${esc(STATUS[payload.status] || payload.status)}</p>`;
    return;
  }
  const cites = [];
  const item = (i) => {
    const index = cites.push(i.citation) - 1;
    const open = i.folder_id
      ? `<button data-folder-open="${esc(i.folder_id)}">開啟資料夾</button>`
      : `<button data-new-case="${esc(i.case_no)}">＋ 建立資料夾</button>`;
    return `<article class="fact precedent">
      <div class="fact-head"><h4>${esc(i.case_no)}</h4><span class="decision ${TONE[i.decision] || ""}">${esc(i.decision_label)}${i.decision_date ? " · " + esc(i.decision_date) : ""}</span></div>
      <ul class="cites"><li class="cite"><button class="cite-open" data-cite="${index}">主文件 · p.${esc(i.page)}</button><q>${esc(i.excerpt)}</q><span class="cite-status" data-cite-status="${index}" aria-live="polite"></span></li></ul>
      <div class="precedent-actions">${open}</div>
    </article>`;
  };
  const group = (g) => `<section class="fact-group"><h3>${esc(g.label)}</h3>
    ${g.items.map(item).join("")}
    ${g.statements.map((s) => `<p class="meta">規劃署文件 p.${esc(s.page)}：<q>${esc(s.text)}</q></p>`).join("")}
    ${g.items.length || g.statements.length ? "" : '<p class="meta">主文件未見此部分</p>'}</section>`;
  const s = payload.summary;
  const total = s.approved + s.rejected + s.other;
  container.innerHTML = `<div class="banner">讀自 ${esc(payload.source.title)}${payload.source.event_date && !payload.source.title.includes(payload.source.event_date) ? "（" + esc(payload.source.event_date) + "）" : ""}。同類申請 ${total} 宗：批准 ${s.approved}、拒絕 ${s.rejected}、其他或未能判讀 ${s.other}。<br>這是規劃署在文件中挑選的先例，不是全區完整清單；決定以原文為準。</div>
    ${payload.groups.map(group).join("")}`;
  container.querySelectorAll("[data-cite]").forEach((b) => {
    b.onclick = async () => {
      const status = container.querySelector(`[data-cite-status="${b.dataset.cite}"]`);
      container.querySelectorAll(".cite-status").forEach((n) => (n.textContent = ""));
      status.textContent = "開啟原文…";
      const result = await onCitation(cites[Number(b.dataset.cite)]);
      status.textContent = result.ok ? "已在原文標示" : result.reason;
      status.classList.toggle("error", !result.ok);
    };
  });
  container.querySelectorAll("[data-folder-open]").forEach((b) => (b.onclick = () => onFolder(b.dataset.folderOpen)));
  container.querySelectorAll("[data-new-case]").forEach((b) => (b.onclick = () => onNew(b.dataset.newCase)));
}
