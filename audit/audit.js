(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
  const get = (p) => fetch(p, { cache: "no-cache" }).then((r) => (r.ok ? r.json() : null)).catch(() => null);
  function vStatus(v) { return v && typeof v === "object" ? v.status : v; }
  function vItems(v) { return v && typeof v === "object" ? (v.items || []) : []; }
  const LABELS = { confirmed_primary: "confirmed", secondary_only: "secondary only", needs_human_verification: "needs check" };
  function niceDate(iso) {
    if (!iso) return "";
    const d = new Date(/T/.test(iso) ? iso : iso + "T00:00:00+11:00");
    if (isNaN(d)) return String(iso);
    return d.toLocaleString("en-AU", { timeZone: "Australia/Sydney", dateStyle: "medium", timeStyle: /T/.test(iso) ? "short" : undefined }) + (/T/.test(iso) ? " Sydney time" : "");
  }
  function pill(st) {
    const kind = st === "Confirmed" || st === "confirmed_primary" || st === "ok" ? "ok"
      : (st === "Corrected" || st === "secondary_only" || st === "needs_human_verification" || st === "Unverifiable" ? "warn" : "");
    return `<span class="pill ${kind}">${esc(LABELS[st] || st)}</span>`;
  }
  function codes(sig) {
    return (sig.affected || []).map((a) => a.code).filter(Boolean);
  }
  function src(sig) {
    const u = sig.source_url, lab = (sig.sources && sig.sources[0] && sig.sources[0].label) || "source";
    return u ? `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(lab)}</a>` : "";
  }

  function renderSignals(doc) {
    const list = (doc && doc.signals) || [];
    if (!list.length) { $("signals").innerHTML = "<h2>Signals</h2><p>No signals loaded.</p>"; return; }
    const cards = list.map((s) => {
      const st = vStatus(s.verification) || "";
      const strength = s.strength && s.strength.value != null ? s.strength.value : "";
      const tickers = codes(s).join(", ") || (s.gics_sectors || []).join(", ") || "—";
      const open = vItems(s.verification);
      const why = `
        <details class="why"><summary>Why</summary>
          <p>${esc(s.reasoning || "")}</p>
          ${open.length ? `<ul>${open.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>` : ""}
          <p class="meta">${src(s)}</p>
        </details>`;
      return `<article class="card signal-card">
        <h3>${esc(s.event)}</h3>
        <p class="meta">${esc(niceDate(s.date))} · ${esc(tickers)} · strength ${esc(strength)} · ${esc(s.direction || "")} ${pill(st)}</p>
        ${why}
      </article>`;
    }).join("");
    $("signals").innerHTML = `<h2>Signals (${list.length})</h2>
      <p class="meta">Generated ${esc(niceDate((doc && doc.generated_at) || ""))}. Each “Why” panel starts closed.</p>${cards}`;
  }

  function renderExcluded(doc) {
    const list = (doc && doc.excluded) || [];
    if (!list.length) { $("excluded").innerHTML = "<h2>Excluded items</h2><p>None listed.</p>"; return; }
    $("excluded").innerHTML = `<h2>Excluded items (${list.length})</h2><ul>` + list.map((x) => {
      const srcLink = x.source ? ` <a href="${esc(x.source)}" target="_blank" rel="noopener">source</a>` : "";
      return `<li><strong>${esc(x.item)}</strong> — ${esc(x.reason || "")}${srcLink}</li>`;
    }).join("") + "</ul>";
  }

  function renderVerification(ver) {
    const items = (ver && ver.items) || [];
    if (!items.length) { $("verification").innerHTML = "<h2>Fact-check log</h2><p>No log loaded.</p>"; return; }
    const order = ["Corrected", "Unverifiable", "Confirmed"];
    const groups = order.map((st) => {
      const rows = items.filter((i) => i.status === st);
      if (!rows.length) return "";
      const table = `<table><thead><tr><th>Claim</th><th>Value</th><th>Check</th></tr></thead><tbody>` +
        rows.map((i) => `<tr><td>${esc(i.claim)}</td><td>${esc(i.corrected_value || i.value || "")}</td><td>${pill(i.status)}${i.verify ? ' <span class="pill warn">verify</span>' : ""}${i.source ? ` <a href="${esc(i.source)}" target="_blank" rel="noopener">source</a>` : ""}</td></tr>`).join("") +
        "</tbody></table>";
      return `<h3>${esc(st)} (${rows.length})</h3>${table}`;
    }).join("");
    $("verification").innerHTML = `<h2>Fact-check log</h2><p class="meta">Checked ${esc((ver && ver.checked_at) || "")}. ${items.filter((i) => i.verify).length} still flagged for a human check.</p>${groups}`;
  }

  function renderMatches(matches) {
    if (!matches) { $("matches").innerHTML = "<h2>Matches</h2><p>No matches loaded.</p>"; return; }
    const seeded = matches.seeded || [], engine = matches.engine || [];
    const card = (m) => {
      const isEng = m.origin === "engine";
      const rec = isEng ? m.record : m.commercial;
      const title = rec && rec.title ? rec.title : "";
      const href = rec && rec.source ? rec.source : "";
      return `<div class="card">
        <p><strong>${isEng ? "Engine" : "Seeded"} #${esc(m.rank)}</strong> ${isEng ? `<span class="pill ok">engine-generated</span>` : `<span class="pill">hand-seeded</span>`}${m.verify ? ' <span class="pill warn">verify</span>' : ""}</p>
        <p><b>Record:</b> ${href ? `<a href="${esc(href)}" target="_blank" rel="noopener">${esc(title)}</a>` : esc(title)} · ${esc(rec && rec.entity)}</p>
        <p><b>Policy:</b> ${esc(m.policy && m.policy.title)}</p>
        <p><b>Why linked:</b> ${esc(m.rationale)}</p>
      </div>`;
    };
    $("matches").innerHTML = `<h2>Matches</h2>
      <p class="meta">Only matches with a sourced commercial record are listed; the Northern Minerals example in the brief is a synthetic test fixture and is not shown.</p>
      <h3>Engine-generated (${engine.length})</h3>
      ${engine.length ? engine.map(card).join("") : "<p>No live record cleared the gates this run.</p>"}
      <h3>Hand-seeded (${seeded.length})</h3>
      ${seeded.map(card).join("")}`;
  }

  Promise.all([
    get("../data/signals/signals.json"),
    get("../data/verification.json"),
    get("../data/matches.json")
  ]).then(([sig, ver, matches]) => {
    renderSignals(sig);
    renderExcluded(sig);
    renderVerification(ver);
    renderMatches(matches);
  });
})();
