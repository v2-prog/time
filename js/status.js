(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
  const SYD = "Australia/Sydney";
  const get = (p) => fetch(p, { cache: "no-cache" }).then((r) => (r.ok ? r.json() : null)).catch(() => null);

  function todayISO() {
    return new Date().toLocaleDateString("en-CA", { timeZone: SYD });
  }
  function syd(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d)) return String(iso);
    const long = String(iso).length > 10;
    return d.toLocaleString("en-AU", {
      timeZone: SYD,
      dateStyle: "medium",
      timeStyle: long ? "short" : undefined
    }) + (long ? " Sydney time" : "");
  }
  function sydShort(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d)) return String(iso);
    return d.toLocaleString("en-AU", { timeZone: SYD, day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
  }
  function shortDate(iso) {
    if (!iso) return "";
    const d = new Date(iso + (String(iso).length === 10 ? "T00:00:00+11:00" : ""));
    if (isNaN(d)) return esc(iso);
    return d.toLocaleDateString("en-AU", { timeZone: SYD, day: "numeric", month: "short" });
  }
  function vStatus(v) {
    return v && typeof v === "object" ? v.status : v;
  }
  function pill(st) {
    const kind = st === "ok" ? "ok" : (st === "never_run" || st === "partial" || st === "stale" ? "warn" : "bad");
    return `<span class="pill ${kind}">${esc(st)}</span>`;
  }

  function newToday(signals, today) {
    return (signals || []).filter((s) => s.date === today).length;
  }
  function needsCheck(signals, ver) {
    const flagged = [], unstated = [];
    (signals || []).forEach((s) => {
      if (vStatus(s.verification) === "needs_human_verification") flagged.push(s.id);
      else if ((s.affected || []).some((a) => a.exposure_in_source === false)) unstated.push(s.id);
    });
    const fact = ((ver && ver.items) || []).filter((i) => i.verify);
    return { flagged, unstated, fact };
  }
  function upcoming(signals, today, limit) {
    const rows = [];
    const seen = new Set();
    (signals || []).forEach((s) => {
      const dates = new Set();
      (s.key_dates || []).forEach((k) => {
        if (k && k.date && k.date >= today) {
          const key = k.date + "|" + (k.label || "");
          if (!seen.has(key)) { seen.add(key); dates.add(k.date); rows.push({ date: k.date, label: k.label || s.event }); }
        }
      });
      if (s.effect_date && s.effect_date >= today && !dates.has(s.effect_date)) {
        const key = s.effect_date + "|effect|" + s.id;
        if (!seen.has(s.effect_date + "|" + (s.event || ""))) {
          seen.add(key);
          rows.push({ date: s.effect_date, label: s.event });
        }
      }
    });
    rows.sort((a, b) => a.date < b.date ? -1 : a.date > b.date ? 1 : 0);
    return rows.slice(0, limit || 8);
  }

  function render(health, sig, ver) {
    const today = todayISO();
    const signals = (sig && sig.signals) || [];
    const nNew = newToday(signals, today);
    const chk = needsCheck(signals, ver);
    const nSignalsNeed = chk.flagged.length + chk.unstated.length;
    const nFact = chk.fact.length;
    const dates = upcoming(signals, today, 8);
    const feeds = ((health && health.feeds) || []).filter((f) => f.status !== "never_run");
    const never = health && health.summary ? health.summary.never_run : 0;
    const liveOk = health && health.summary ? health.summary.live_ok : feeds.filter((f) => f.status === "ok").length;
    const lastRun = health && health.generated_at ? syd(health.generated_at) : "unknown";

    const feedList = feeds.map((f) => `<li><div>${esc(f.label)} ${pill(f.status)}</div><div class="when">${esc(sydShort(f.last_success || f.last_run) || "—")}</div></li>`).join("");
    const dateList = dates.length
      ? dates.map((d) => `<li><span class="d">${esc(shortDate(d.date))}</span><span>${esc(d.label)}</span></li>`).join("")
      : "<li><span class=\"d\">—</span><span>No upcoming dates in the feed.</span></li>";

    $("status").innerHTML = `
      <p class="meta">As at ${esc(lastRun || today)}.</p>
      <h2>Today</h2>
      <div class="stats">
        <div class="stat"><span class="n">${nNew}</span><span class="lbl">new signals today</span></div>
        <div class="stat"><span class="n">${signals.length}</span><span class="lbl">signals in the feed</span></div>
        <div class="stat"><span class="n${nSignalsNeed || nFact ? " warn" : ""}">${nSignalsNeed}</span><span class="lbl">signals need a check</span></div>
        <div class="stat"><span class="n${nFact ? " warn" : ""}">${nFact}</span><span class="lbl">fact-check items still flagged</span></div>
      </div>
      <p class="meta">${chk.flagged.length || chk.unstated.length ? `${chk.flagged.length} flagged in the feed, ${chk.unstated.length} with ticker exposure the source does not state.` : "No open signal checks."}</p>
      <h2>Feed health</h2>
      <p>${liveOk} of ${feeds.length || liveOk} live feeds OK${never ? `; ${never} feeds have no fetcher yet` : ""}. Last run ${esc(lastRun)}.</p>
      <ul class="feeds">${feedList || "<li>No live fetcher data.</li>"}</ul>
      <h2>Next dates</h2>
      <ul class="dates">${dateList}</ul>
    `;
  }

  function renderTic(ok) {
    const href = "https://tic.vilo.au/";
    if (ok) {
      $("tic").innerHTML = `<a class="tic-link" href="${href}">Open Tic</a><p class="meta">Tic is where the distilled signals are meant to be read.</p>`;
    } else {
      $("tic").innerHTML = `<a class="tic-link soon" href="${href}">Tic — coming soon</a><p class="meta">The link is ready; the site is not reachable yet.</p>`;
    }
  }

  Promise.all([
    get("data/feed_health.json"),
    get("data/signals/signals.json"),
    get("data/verification.json")
  ]).then(([health, sig, ver]) => {
    if (!health && !sig) {
      $("status").innerHTML = `<p class="pill bad">Status data could not be loaded.</p>`;
      return;
    }
    render(health, sig, ver);
  });

  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), 4000);
  fetch("https://tic.vilo.au/", { mode: "no-cors", cache: "no-store", signal: ctrl.signal })
    .then(() => renderTic(true))
    .catch(() => renderTic(false))
    .finally(() => clearTimeout(t));
})();
