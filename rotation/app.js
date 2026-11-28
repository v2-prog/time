(function () {
  "use strict";
  const D = window.ROTATION_DATA, L = window.RotationLogic;
  const main = document.getElementById("main"), live = document.getElementById("live");
  const KEY = "time.vilo.au/rotation/v1";
  let state = load(), history = [];
  let verification = { items: [] }, health = { feeds: [] }, matches = { engine: [], seeded: [], bracket_activity: {} };

  function load() { try { return JSON.parse(localStorage.getItem(KEY)) || { reviewed: {}, notes: {} }; } catch (e) { return { reviewed: {}, notes: {} }; } }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} }
  function push() { history.push(JSON.stringify(state)); if (history.length > 50) history.shift(); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
  function link(u, t) { return u ? `<a href="${esc(u)}" rel="noopener" target="_blank">${esc(t || "source")}</a>` : "<span class=meta>no source</span>"; }
  function today() { return document.getElementById("today").value; }

  function overview() {
    const counts = {};
    verification.items.forEach((i) => (counts[i.status] = (counts[i.status] || 0) + 1));
    const flagged = verification.items.filter((i) => i.verify).length;
    return `<section class="band"><h2>Status</h2>
      <p>Verification pass of ${esc(verification.checked_at || "")}: ${Object.entries(counts).map(([k, v]) => `${v} ${esc(k)}`).join(", ")}. ${flagged} items still carry a verification flag.</p>
      <h2>Design fixes from the iteration 040 review</h2>
      <table><thead><tr><th>Gap</th><th>Status</th><th>Where</th></tr></thead><tbody>
      ${D.designFixes.map((f) => `<tr><td>${esc(f.gap)}</td><td>${esc(f.status)}</td><td><code>${esc(f.where)}</code></td></tr>`).join("")}
      </tbody></table>
      <h2>Engine activity by bracket</h2>
      ${activity()}
      <h2>Scope</h2><p>Brackets are measured against S&amp;P/ASX 200 sector indices. Outside scope (watch list only): ${D.watchListOutsideScope.map((w) => `${esc(w.code)} (${esc(w.why)})`).join("; ")}.</p></section>`;
  }

  function activity() {
    const ba = matches.bracket_activity || {}, names = Object.keys(ba);
    if (!names.length) return `<p class="meta">No engine matches yet.</p>`;
    return `<table><thead><tr><th>Bracket</th><th>Matches per ${esc(ba[names[0]].window_days)}-day window (non-overlapping, oldest first)</th><th>Latest window z-score</th><th>Direction tags (policy side)</th></tr></thead><tbody>` +
      names.map((b) => {
        const c = ba[b].counts, z = L.intensityZ(c[c.length - 1], c.slice(0, -1));
        const dirs = {};
        (matches.engine || []).filter((m) => m.bracket === b).forEach((m) => { const d = m.policy.direction || "unassigned"; dirs[d] = (dirs[d] || 0) + 1; });
        return `<tr><td>${esc(b)}</td><td>${c.map(esc).join(" · ")} <span class="meta">from ${esc(ba[b].start)}</span></td><td>${z == null ? "n/a (needs 4+ past windows)" : z.toFixed(2)}</td><td>${Object.entries(dirs).map(([k, v]) => `${esc(k)} ${v}`).join(", ")}</td></tr>`;
      }).join("") + `</tbody></table><p class="meta">Counts come from engine matches in <code>/data/matches.json</code>. They measure activity, not direction or outcome.</p>`;
  }

  function queues() {
    const order = ["Unverifiable", "Corrected", "Confirmed"];
    return `<section class="band"><p class="meta">Your review ticks and notes stay in this browser only.</p>` + order.map((st) => {
      const items = verification.items.filter((i) => i.status === st);
      if (!items.length) return "";
      return `<h2>${esc(st)} (${items.length})</h2>` + items.map((i) => `
        <article class="card q ${i.verify ? "flag" : ""}">
          <h3>${esc(i.claim)}</h3>
          <p>${esc(i.corrected_value || i.value || "")}</p>
          ${i.note ? `<p class="meta">${esc(i.note)}</p>` : ""}
          <p class="meta">${i.verify ? "Needs human verification" : "Primary source checked"} · ${link(i.source)}</p>
          <label><input type="checkbox" data-rev="${esc(i.id)}" ${state.reviewed[i.id] ? "checked" : ""}> Reviewed by me</label>
          <textarea data-note="${esc(i.id)}" rows="2" placeholder="Reviewer note (stays in this browser)">${esc(state.notes[i.id] || "")}</textarea>
        </article>`).join("");
    }).join("") + `</section>`;
  }

  function feedAgeHours() {
    const ok = health.feeds.filter((f) => f.last_success).map((f) => new Date(f.last_success).getTime());
    if (!ok.length) return null;
    const ref = today() ? new Date(today() + "T23:59:59").getTime() : Date.now();
    return Math.max(0, (ref - Math.max.apply(null, ok)) / 3600000);
  }

  function signals() {
    const ks = (D.keySources.Resources || []).map((id) => health.feeds.find((f) => f.id === id) || { id, status: "never_run" });
    const conf = L.mechanicalConfidence({ feedAgeHours: feedAgeHours(), staleHours: health.stale_after_hours || 36, capCoverage: Number(state.capCoverage || 0), keySources: ks });
    const opts = D.brackets.map((b) => `<option>${esc(b.name)}</option>`).join("");
    return `<section class="band"><h2>Spread calculator</h2>
      <p class="meta">Enter window returns from your own licensed data.</p>
      <form id="calc" class="calc">
        ${["a", "b"].map((k, n) => `<fieldset><legend>Bracket ${n + 1}</legend>
          <select name="${k}n">${opts}</select>
          <label>Bracket return % <input name="${k}r" type="number" step="0.01"></label>
          <label>Sector index return % <input name="${k}i" type="number" step="0.01"></label>
          <label>Prior 3-month relative % <input name="${k}m" type="number" step="0.01"></label></fieldset>`).join("")}
        <button class="btn" type="submit">Calculate</button>
      </form>
      <div id="calcOut" aria-live="polite"></div>
      <h2>Resources confidence (mechanical)</h2>
      <p>Confidence <strong>${conf.value}</strong> = average of feed freshness ${conf.freshness} and market-cap coverage ${conf.coverage}, minus a silence penalty for ${conf.silentSources} of ${ks.length} key sources silent or never run.</p>
      <label>Share of Resources market cap with an event this window (0-1) <input id="cap" type="number" min="0" max="1" step="0.05" value="${esc(state.capCoverage || 0)}"></label>
      <h2>Settlement</h2>
      <p>ASX settles T+2. A trade on <strong>${esc(today())}</strong> settles on <strong>${esc(L.settlementDate(today(), D.asxHolidays))}</strong> (holiday list in data.js; confirm against the ASX calendar).</p></section>`;
  }

  function rules() {
    return `<section class="band"><h2>Direction rules (draft, for review)</h2>
      <table><thead><tr><th>Bracket</th><th>Tag</th><th>Why</th></tr></thead><tbody>
      ${L.DIRECTION_RULES.map((r) => `<tr><td>${esc(r.bracket)}</td><td>${esc(r.tag)}</td><td>${esc(r.why)}</td></tr>`).join("")}
      </tbody></table><p class="meta">Events with no matching rule are tagged "unassigned" and must be tagged by a person.</p>
      <h2>Method</h2><ul>
      <li>Outcome = (bracket A return − its sector index return) − (bracket B return − its sector index return), in percentage points.</li>
      <li>Intensity = z-score of this window's event count against the bracket's own past windows (needs at least 4).</li>
      <li>Hit rates use non-overlapping windows only, and are always shown next to the momentum baseline.</li>
      <li>Money leaving one bracket may go to cash, bonds or offshore; spillover is a hypothesis to test and is not scored.</li>
      <li>Confidence is mechanical and separate from any score.</li></ul>
      <h2>Benchmarks</h2><ul>${D.brackets.map((b) => `<li>${esc(b.name)}: ${esc(b.benchmark)} (${esc(b.code)})${b.note ? " · " + esc(b.note) : ""}</li>`).join("")}</ul>
      <h2>Data</h2><p>Feed health and verification come from same-origin JSON (<code>/data/feed_health.json</code>, <code>/data/verification.json</code>) refreshed by a scheduled job. No keys or third-party calls run in this page.</p></section>`;
  }

  const views = { overview, queues, signals, rules };
  function render() {
    const v = (location.hash || "#overview").slice(1);
    main.innerHTML = (views[v] || overview)();
    document.querySelectorAll(".tabs a").forEach((a) => a.classList.toggle("active", a.getAttribute("href") === "#" + v));
  }

  main.addEventListener("change", (e) => {
    const t = e.target;
    if (t.dataset.rev) { push(); state.reviewed[t.dataset.rev] = t.checked; save(); live.textContent = "Saved"; }
    if (t.id === "cap") { push(); state.capCoverage = t.value; save(); render(); }
  });
  main.addEventListener("input", (e) => { const t = e.target; if (t.dataset.note) { state.notes[t.dataset.note] = t.value; save(); } });
  main.addEventListener("submit", (e) => {
    if (e.target.id !== "calc") return;
    e.preventDefault();
    const f = new FormData(e.target), n = (k) => (f.get(k) === "" ? null : Number(f.get(k)));
    const a = { name: f.get("an"), returnPct: n("ar"), benchmarkPct: n("ai"), prior3mRelPct: n("am") };
    const b = { name: f.get("bn"), returnPct: n("br"), benchmarkPct: n("bi"), prior3mRelPct: n("bm") };
    const s = L.rotationSpread(a, b), mom = L.momentumBaseline([a, b]);
    document.getElementById("calcOut").innerHTML = s == null ? "<p>Enter both returns and both index returns.</p>" :
      `<p>Spread ${esc(a.name)} vs ${esc(b.name)}: <strong>${s.toFixed(2)} pp</strong>. ${mom ? `Momentum baseline would have favoured ${esc(mom.leader)}.` : "Add prior 3-month figures to log the momentum baseline."}</p>`;
  });
  document.getElementById("undo").addEventListener("click", () => { if (history.length) { state = JSON.parse(history.pop()); save(); render(); live.textContent = "Undone"; } });
  const t = document.getElementById("today");
  t.value = new Date().toLocaleDateString("en-CA", { timeZone: "Australia/Sydney" });
  t.addEventListener("change", render);
  window.addEventListener("hashchange", render);

  Promise.all([
    fetch("../data/verification.json").then((r) => r.json()).catch(() => ({ items: [] })),
    fetch("../data/feed_health.json").then((r) => r.json()).catch(() => ({ feeds: [] })),
    fetch("../data/matches.json").then((r) => r.json()).catch(() => ({ engine: [] })),
  ]).then(([v, h, m]) => { verification = v; health = h; matches = m; render(); });
  render();
})();
