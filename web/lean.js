import { esc } from "./state.js";

const TONE = { support: "ok", limit: "bad", conflict: "bad" };
const UNAVAILABLE = {
  missing_original: "此資料夾未保存所引原件版本",
  version_mismatch: "已保存文件與所引版本內容不同，不跳轉",
  outside_scope: "所引版本不在目前資料範圍",
};
const ISSUE = {
  not_researched: "未研究",
  to_compare: "待比對",
  missing_document: "缺文件",
};

function citationHTML(c, index) {
  const quote = c.excerpt ? `<q>${esc(c.excerpt)}</q>` : "";
  const action =
    c.availability === "ready"
      ? `<button class="cite-open" data-cite="${index}">${esc(c.label)}</button>`
      : `<span class="cite-label">${esc(c.label)}</span>${c.availability === "not_pdf" ? "" : `<span class="cite-missing">${esc(UNAVAILABLE[c.availability] || "未能定位")}</span>`}`;
  return `<li class="cite">${action}${quote}<span class="cite-status" data-cite-status="${index}" aria-live="polite"></span></li>`;
}

export function renderLean(container, payload, onCitation) {
  const cites = [];
  const finding = (f) => `<article class="fact finding">
    <div class="fact-head"><h4>${esc(f.check)} ${esc(f.check_label)}</h4><span class="decision ${TONE[f.outcome] || ""}">${esc(f.outcome_label)} · ${esc(f.severity_label)}${f.provisional ? " · 暫定" : ""}</span></div>
    <p>${esc(f.text)}</p>
    ${f.gaps.length ? `<p class="fact-issues">待查：${f.gaps.map(esc).join("；")}</p>` : ""}
    ${f.citations.length ? `<details><summary>證據 ${f.citations.length} 項</summary><ul class="cites">${f.citations.map((c) => citationHTML(c, cites.push(c) - 1)).join("")}</ul></details>` : ""}
  </article>`;
  const group = (g) => `<section class="fact-group"><h3>${esc(g.label)}</h3>
    ${g.findings.map(finding).join("") || '<p class="meta">此項檢查尚未建立</p>'}</section>`;
  const unknowns = payload.unknowns.items
    .map(
      (i) => `<article class="fact issue"><div class="fact-head"><h4>${esc(i.title)}</h4><span class="review">${esc(ISSUE[i.status] || i.status)} · 優先 ${esc(i.priority)}</span></div><p class="meta">需要：${esc(i.needed)}</p></article>`,
    )
    .join("");
  const l = payload.lean;
  container.innerHTML = `<div class="banner draft">草稿 · 僅供專業覆核的初步研究結果，不構成規劃、法律或建築合規意見。</div>
    <div class="lean ${esc(l.value)}"><span class="lean-label">初步傾向：${esc(l.label)}${l.provisional ? "（暫定）" : ""}</span><p>${esc(l.reason)}</p>
    <p class="meta">基準日 ${esc(payload.as_of)} · 規則版本 ${esc(payload.rules_version)} · 只數「支持」與「限制／衝突」的項數，不加權。${l.provisional ? "所用資料有待覆核或待查事項，所以標為暫定。" : ""}</p></div>
    ${payload.groups.map(group).join("")}
    <section class="fact-group"><h3>${esc(payload.unknowns.label)}</h3>${unknowns || '<p class="meta">沒有待查事項</p>'}</section>`;
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
}
