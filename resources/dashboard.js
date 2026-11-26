(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const get = (p) => fetch(p, { cache: "no-cache" }).then((r) => (r.ok ? r.json() : null)).catch(() => null);
  const syd = (iso) => { if (!iso) return ""; const d = new Date(iso); return isNaN(d) ? esc(iso) : d.toLocaleString("en-AU", { timeZone: "Australia/Sydney", dateStyle: "medium", timeStyle: iso.length > 10 ? "short" : undefined }) + (iso.length > 10 ? " Sydney time" : ""); };
  const pill = (st) => `<span class="pill ${st === "ok" ? "ok" : st === "partial" || st === "never_run" ? "warn" : "bad"}">${esc(st)}</span>`;
  const VOL = { low: 1.0, medium: 0.9, high: 0.8 };
  function score(i) {
    const t = Math.max(0, 1 - Math.abs(i.lag_days) / 30), e = i.entity_overlap === "same_entity" ? 1 : 0.6, c = i.commodity_match ? 1 : 0;
    return Math.round(((t + e + c) / 3) * (VOL[i.policy_volatility] || 0.8) * 100) / 100;
  }

  Promise.all([get("../data/feed_health.json"), get("../data/matches.json"), get("../data/policy_timeline.json"), get("../data/verification.json"),
    get("../data/feeds/asx_announcements.json"), get("../data/feeds/wa_dmpe_announcements.json"), get("../data/feeds/wa_dmpe_tenements.json")])
  .then(([health, matches, timeline, ver, asx, dmpeA, dmpeT]) => {
    const vmap = {}; ((ver && ver.items) || []).forEach((i) => (vmap[i.id] = i));
    if (health) {
      const stale = health.stale_after_hours || 36, now = Date.now();
      $("health").innerHTML = `<h2>Feed health</h2><p>${health.summary.live_ok} of ${health.summary.total - health.summary.never_run} live feeds OK; ${health.summary.never_run} feeds have no fetcher yet (never run). Generated ${syd(health.generated_at)}.</p>
      <table><thead><tr><th>Feed</th><th>Status</th><th>Last success</th><th>Records</th><th>Latest event</th></tr></thead><tbody>${health.feeds.map((f) => {
        let st = f.status; if (st === "ok" && f.last_success && now - new Date(f.last_success) > stale * 3600000) st = "stale";
        return `<tr><td>${esc(f.label)}</td><td>${pill(st)}${f.errors && f.errors.length ? `<details><summary>errors</summary>${f.errors.map(esc).join("<br>")}</details>` : ""}</td><td>${syd(f.last_success)}</td><td>${f.records || ""}</td><td>${syd(f.latest_event)}</td></tr>`; }).join("")}</tbody></table>`;
    } else $("health").innerHTML = `<h2>Feed health</h2><p class="pill bad">feed_health.json missing</p>`;

    if (matches) $("matches").innerHTML = `<h2>Matches</h2><p class="meta">${esc(matches.note)}</p><p class="meta">Scoring: ${esc(matches.scoring)}</p>` + matches.matches.map((m) => `
      <div class="card"><strong>#${m.rank} · score ${score(m.score_inputs)}</strong> ${m.verify ? '<span class="pill warn">verify</span>' : ""}
      <p><b>Commercial:</b> ${esc(m.commercial.date)} · ${esc(m.commercial.entity)} · ${esc(m.commercial.title)} · <a href="${esc(m.commercial.source)}" target="_blank" rel="noopener">source</a></p>
      <p><b>Policy:</b> ${esc(m.policy.title)}</p><p><b>Why linked:</b> ${esc(m.rationale)}</p>
      <p class="meta">Window ±${m.window_days} days · lag ${m.score_inputs.lag_days} d · flags: ${m.flags.map(esc).join(", ")}</p></div>`).join("");

    const recs = [].concat((asx && asx.records) || [], (dmpeA && dmpeA.records) || [], (dmpeT && dmpeT.records) || [])
      .sort((a, b) => new Date(b.occurred_at) - new Date(a.occurred_at));
    const ents = Array.from(new Set(recs.map((r) => r.entity).filter(Boolean))).sort();
    $("live").innerHTML = `<h2>Latest live records</h2>
      <div class="controls"><label>Entity <select id="fEnt"><option value="">All</option>${ents.map((e) => `<option>${esc(e)}</option>`).join("")}</select></label>
      <label><input type="checkbox" id="fPS"> Price-sensitive only</label>
      <label>Feed <select id="fFeed"><option value="">All</option><option value="asx_announcements">ASX</option><option value="wa_dmpe_announcements">DMPE announcements</option><option value="wa_dmpe_tenements">DMPE tenements</option></select></label></div>
      <p class="meta">ASX headlines are withheld (ASX site terms); follow the link to read them on asx.com.au. Every record is unverified until someone opens the source. Times shown in Sydney time.</p><div id="liveRows"></div>`;
    function rows() {
      const e = $("fEnt").value, ps = $("fPS").checked, fd = $("fFeed").value;
      const list = recs.filter((r) => (!e || r.entity === e) && (!ps || r.price_sensitive) && (!fd || r.feed === fd)).slice(0, 80);
      $("liveRows").innerHTML = `<table><thead><tr><th>When</th><th>Entity</th><th>Event</th><th>Headline</th></tr></thead><tbody>${list.map((r) =>
        `<tr><td>${syd(r.occurred_at)}</td><td>${esc(r.entity || r.entity_name || "unresolved")}</td><td>${esc(r.event_type)}${r.event_subtype ? "<br><span class=meta>" + esc(r.event_subtype) + "</span>" : ""}${r.price_sensitive ? ' <span class="pill warn">price sensitive</span>' : ""}</td><td><a href="${esc(r.source_url)}" target="_blank" rel="noopener">${esc(r.title)}</a></td></tr>`).join("")}</tbody></table>`;
    }
    ["fEnt", "fPS", "fFeed"].forEach((id) => $(id).addEventListener("change", rows)); rows();

    if (timeline) $("timeline").innerHTML = `<h2>Policy timeline</h2><p class="meta">${esc(timeline.note)}</p><table><thead><tr><th>Date</th><th>Event</th><th>Lifecycle</th><th>Direction (Resources)</th><th>Check</th></tr></thead><tbody>${timeline.events.map((p) => {
      const v = vmap[p.ref]; return `<tr><td>${esc(p.date)}<br><span class=meta>${esc(p.date_kind)}</span></td><td>${esc(p.title)}${p.watch ? `<br><span class="pill warn">watch ${esc(p.watch)}</span>` : ""}</td><td>${esc(p.lifecycle)} · ${esc(p.volatility)} volatility${p.boundary_class ? " · boundary" : ""}</td><td>${esc(p.direction_for_resources)}</td><td>${v ? `${esc(v.status)} ${v.source ? `<a href="${esc(v.source)}" target="_blank" rel="noopener">source</a>` : ""}` : ""} ${p.verify ? '<span class="pill warn">verify</span>' : ""}</td></tr>`; }).join("")}</tbody></table>`;
  });
})();
