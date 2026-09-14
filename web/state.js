export const $ = (id) => document.getElementById(id);
export const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
export async function api(url, body) {
  const r = await fetch(
    url,
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  if (!r.ok) {
    let j;
    try {
      j = await r.json();
    } catch {}
    throw Error(
      typeof j?.detail === "string" ? j.detail : "操作未完成，請稍後重試",
    );
  }
  return r.json();
}
export const stateURL = (key) => "/api/state/" + encodeURIComponent(key);
export const getState = (key) => api(stateURL(key));
// Serialize writes per key so a slow earlier request cannot overwrite a newer one.
const writes = new Map();
export function saveState(key, value) {
  const frozen = JSON.parse(JSON.stringify(value));
  const next = (writes.get(key) || Promise.resolve())
    .catch(() => {})
    .then(() => api(stateURL(key), { value: frozen }));
  writes.set(key, next);
  return next;
}
