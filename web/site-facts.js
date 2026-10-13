import { esc } from "./state.js";

const NATURE = {
  existing: "現狀描述",
  application_proposal: "申請方案",
  approved: "批准內容",
  planning_limit: "規劃資料",
  historical_record: "歷史記錄",
  lease_record: "地契轉述",
  department_comment: "部門意見",
  unknown: "未知",
};
const STAGE = {
  application: "申請文件",
  supplementary_information: "補充資料後摘要",
  staff_paper: "規劃署文件",
  department_comment: "部門意見",
  meeting_decision: "會議決定",
  unknown: "未知",
};
const ASSERTED = {
  applicant: "申請人",
  planning_department: "規劃署",
  town_planning_board: "城規會",
  other_department: "其他部門",
  unknown: "未知",
};
const APPROX = {
  exact: "原文數值",
  approximate: "約數",
  upper_bound: "上限",
  lower_bound: "下限",
  range: "範圍",
  unknown: "未知",
};
const REVIEW = {
  pending: "待覆核",
  user_confirmed_source_value: "已確認",
};
const ISSUE = {
  not_researched: "未研究",
  to_compare: "待比對",
  missing_document: "缺文件",
};
const UNAVAILABLE = {
  missing_original: "此資料夾未保存所引原件版本",
  version_mismatch: "已保存文件與所引版本內容不同，不跳轉",
  outside_scope: "所引版本不在目前資料範圍",
};
const WARNING = {
  source_url_changed: "已存文件的網址與引用網址不同（內容相同）",
  source_url_missing: "已存文件沒有網址記錄（內容相同）",
};

function official(url, label) {
  try {
    const u = new URL(url);
    if (
      u.protocol === "https:" &&
      ["www.tpb.gov.hk", "www.ozp.tpb.gov.hk"].includes(u.hostname) &&
      !u.pathname.endsWith("/Detail/")
    )
      return `<a href="${esc(url)}" target="_blank" rel="noopener">${label} ↗</a>`;
  } catch {}
  return "";
}

function where(c) {
  if (c.json_path) return `JSON ${esc(c.json_path)}`;
  return `p.${esc(c.page)}${c.locator ? " · " + esc(c.locator) : ""}`;
}

function citationHTML(c, index) {
  const name = `${esc(c.source)} ${esc(c.source_title)}`;
  const quote = c.excerpt
    ? `<q>${esc(c.excerpt)}</q>`
    : c.json_path
      ? ""
      : '<span class="meta">只記錄頁碼，沒有原文摘錄</span>';
  const notes = (c.warnings || [])
    .map((w) => `<span class="cite-warning">${esc(WARNING[w] || w)}</span>`)
    .join("");
  let action;
  if (c.availability === "ready")
    action = `<button class="cite-open" data-cite="${index}">${name} · ${where(c)}</button>`;
  else if (c.availability === "not_pdf")
    action = `<span class="cite-label">${name} · ${where(c)}</span>`;
  else
    action = `<span class="cite-label">${name} · ${where(c)}</span><span class="cite-missing">${esc(UNAVAILABLE[c.availability] || "未能定位")}</span>${official(c.source_url, "官方原件")}`;
  return `<li class="cite">${action}${quote}${notes}<span class="cite-status" data-cite-status="${index}" aria-live="polite"></span></li>`;
}

function valueText(f) {
  return f.unit && !f.value.includes(f.unit) ? `${f.value} ${f.unit}` : f.value;
}

export function renderSiteFacts(container, payload, onCitation) {
  const cites = [];
  const list = (citations) =>
    citations.length
      ? `<ul class="cites">${citations.map((c) => citationHTML(c, cites.push(c) - 1)).join("")}</ul>`
      : "";
  const issues = Object.fromEntries(payload.issues.map((i) => [i.id, i]));
  const confirmed = payload.claims.filter((c) => c.review_status !== "pending").length;
  const fact = (f) => `<article class="fact" id="fact-${esc(f.id)}">
    <div class="fact-head"><h4>${esc(f.label)}</h4><span class="review ${f.review_status === "pending" ? "" : "confirmed"}">${esc(REVIEW[f.review_status] || f.review_status)}</span></div>
    <p class="fact-value">${esc(valueText(f))}</p>
    <p class="meta">${esc(f.time)} · ${esc(NATURE[f.nature] || f.nature)}</p>
    <details><summary>範圍與口徑</summary><dl>
      <dt>範圍</dt><dd>${esc(f.scope)}</dd>
      <dt>資料階段</dt><dd>${esc(STAGE[f.stage] || f.stage)}</dd>
      <dt>陳述者</dt><dd>${esc(ASSERTED[f.asserted_by] || f.asserted_by)}</dd>
      <dt>數值性質</dt><dd>${esc(APPROX[f.approximation] || f.approximation)}</dd>
      ${f.denominator ? `<dt>分母</dt><dd>${esc(f.denominator)}</dd>` : ""}
      ${f.review_note ? `<dt>覆核備註</dt><dd>${esc(f.review_note)}</dd>` : ""}
    </dl></details>
    ${list(f.citations)}
    ${f.issue_ids.length ? `<p class="fact-issues">待查：${f.issue_ids.map((id) => `<a href="#issue-${esc(id)}">${esc(issues[id]?.title || id)}</a>`).join("；")}</p>` : ""}
  </article>`;
  const group = (q) => {
    let body;
    if (q.id === "meaning")
      body = payload.interpretations
        .map((n) => `<article class="fact"><p>${esc(n.text)}</p>${list(n.citations)}</article>`)
        .join("");
    else if (q.id === "unknowns")
      body = [...payload.issues]
        .sort((a, b) => a.priority - b.priority)
        .map(
          (i) => `<article class="fact issue" id="issue-${esc(i.id)}">
          <div class="fact-head"><h4>${esc(i.title)}</h4><span class="review">${esc(ISSUE[i.status] || i.status)} · 優先 ${esc(i.priority)}</span></div>
          <p class="meta">已有線索：${esc(i.lead)}</p><p class="meta">需要：${esc(i.needed)}</p></article>`,
        )
        .join("");
    else body = payload.claims.filter((c) => c.question === q.id).map(fact).join("");
    return `<section class="fact-group"><h3>${esc(q.label)}</h3>${body || '<p class="meta">尚無資料</p>'}</section>`;
  };
  container.innerHTML = `<div class="banner">${esc(payload.case_no)} 人工整理樣板 · 資料截至 ${esc(payload.as_of)} · 官方文件取得於 ${esc(payload.acquired)}<br>${payload.claims.length} 項：已確認 ${confirmed}、待覆核 ${payload.claims.length - confirmed}；待查事項 ${payload.issues.length}。「現狀」只指 2022 年文件描述。</div>
    ${payload.questions.map(group).join("")}`;
  container.querySelectorAll("[data-cite]").forEach((b) => {
    b.onclick = async () => {
      const status = container.querySelector(`[data-cite-status="${b.dataset.cite}"]`);
      container.querySelectorAll(".cite-status").forEach((s) => (s.textContent = ""));
      status.textContent = "開啟原文…";
      const result = await onCitation(cites[Number(b.dataset.cite)]);
      status.textContent = result.ok ? "已在原文標示" : result.reason;
      status.classList.toggle("error", !result.ok);
    };
  });
}

export function renderSiteFactsUnavailable(container, message) {
  container.innerHTML = `<p class="meta">${esc(message)}</p>`;
}
