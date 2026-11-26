/* Rotation logic (iteration 042 + iteration 040 review fixes).
 * Pure functions, no network. Describes evidence; never recommends buying, selling or switching.
 * Works in the browser (window.RotationLogic) and in Node (module.exports) for tests.
 */
(function (root) {
  "use strict";

  // 1. Outcomes are spreads versus the S&P/ASX 200 sector benchmark, not absolute returns.
  function pctReturn(start, end) {
    if (!(start > 0) || !(end > 0)) return null;
    return (end / start - 1) * 100;
  }
  // Relative return of a bracket against its sector index, in percentage points.
  function relativeToBenchmark(bracketReturnPct, benchmarkReturnPct) {
    if (bracketReturnPct == null || benchmarkReturnPct == null) return null;
    return bracketReturnPct - benchmarkReturnPct;
  }
  // Rotation outcome: spread between two brackets' benchmark-relative returns over the same window.
  function rotationSpread(a, b) {
    const ra = relativeToBenchmark(a.returnPct, a.benchmarkPct);
    const rb = relativeToBenchmark(b.returnPct, b.benchmarkPct);
    return ra == null || rb == null ? null : ra - rb;
  }

  // 2. Direction tags with documented rules. Returns positive | negative | mixed | unassigned.
  const DIRECTION_RULES = [
    { when: (e) => e.kind === "rate_decision" && e.change_bp > 0, bracket: "Financials", tag: "mixed", why: "Hikes widen bank margins but raise credit risk" },
    { when: (e) => e.kind === "rate_decision" && e.change_bp < 0, bracket: "Financials", tag: "mixed", why: "Cuts compress margins but ease credit risk" },
    { when: (e) => e.kind === "trade_restriction" && e.imposed === true, bracket: "Resources", tag: "negative", why: "Restriction on an export market for the bracket's commodity" },
    { when: (e) => e.kind === "trade_restriction" && e.imposed === false, bracket: "Resources", tag: "positive", why: "Removal of a restriction on an export market" },
    { when: (e) => e.kind === "production_incentive", bracket: "Resources", tag: "positive", why: "Tax offset for eligible processing" },
    { when: (e) => e.kind === "export_control_suspension", bracket: "Resources", tag: "mixed", why: "Competitor supply eases; prices for non-China supply may soften" },
    { when: (e) => e.kind === "pbs_delisting", bracket: "Healthcare", tag: "negative", why: "Loss of subsidised listing for a product" },
  ];
  function directionTag(event, bracket) {
    for (const r of DIRECTION_RULES) {
      if (r.bracket === bracket && r.when(event)) return { tag: r.tag, rule: r.why };
    }
    return { tag: "unassigned", rule: "No documented rule; a human must tag it" };
  }

  // 3. Baseline-adjusted intensity: z-score of this window's event count vs the bracket's own history.
  function mean(xs) { return xs.reduce((s, x) => s + x, 0) / xs.length; }
  function stdev(xs) {
    if (xs.length < 2) return null;
    const m = mean(xs);
    return Math.sqrt(xs.reduce((s, x) => s + (x - m) * (x - m), 0) / (xs.length - 1));
  }
  function intensityZ(current, history) {
    if (!history || history.length < 4) return null; // too little history to say
    const sd = stdev(history);
    if (!sd) return null;
    return (current - mean(history)) / sd;
  }

  // 4. Mechanical confidence (0-1), kept separate from score. No human-style judgement.
  //    freshness: 1 if the newest key-feed record is <= staleHours old, falling linearly to 0 at 4x.
  //    coverage: share of the bracket's market cap with at least one event in the window (0-1).
  //    silence: each silent/never-run key source removes an equal share of 0.5.
  function mechanicalConfidence({ feedAgeHours, staleHours = 36, capCoverage, keySources = [] }) {
    const freshness = feedAgeHours == null ? 0 : Math.max(0, Math.min(1, 1 - (feedAgeHours - staleHours) / (3 * staleHours)));
    const cov = Math.max(0, Math.min(1, capCoverage || 0));
    const silent = keySources.filter((s) => s.status !== "ok" && s.status !== "partial").length;
    const silencePenalty = keySources.length ? 0.5 * silent / keySources.length : 0.5;
    const value = Math.max(0, (freshness + cov) / 2 - silencePenalty);
    return { value: Math.round(value * 100) / 100, freshness: Math.round(freshness * 100) / 100, coverage: cov, silentSources: silent };
  }

  // 5. Momentum baseline: the bracket with the best prior 3-month relative return is the naive call.
  function momentumBaseline(brackets) {
    const ranked = brackets.filter((b) => b.prior3mRelPct != null).sort((x, y) => y.prior3mRelPct - x.prior3mRelPct);
    return ranked.length ? { leader: ranked[0].name, laggard: ranked[ranked.length - 1].name } : null;
  }

  // 6. Non-overlapping windows for hit rates.
  function nonOverlapping(signals, windowDays) {
    const sorted = signals.slice().sort((a, b) => a.date.localeCompare(b.date));
    const out = [];
    let nextFree = null;
    for (const s of sorted) {
      const d = new Date(s.date + "T00:00:00Z");
      if (nextFree && d < nextFree) continue;
      out.push(s);
      nextFree = new Date(d.getTime() + windowDays * 86400000);
    }
    return out;
  }
  function hitRate(signals, windowDays) {
    const used = nonOverlapping(signals.filter((s) => s.outcome != null), windowDays);
    if (!used.length) return { n: 0, rate: null, momentumRate: null };
    const hits = used.filter((s) => s.outcome === "hit").length;
    const mom = used.filter((s) => s.momentumOutcome === "hit").length;
    return { n: used.length, rate: hits / used.length, momentumRate: mom / used.length };
  }

  // 7. ASX settlement: T+2 business days (weekends and listed ASX non-trading days skipped).
  function settlementDate(tradeDate, holidays = []) {
    const hs = new Set(holidays);
    const d = new Date(tradeDate + "T00:00:00Z");
    let added = 0;
    while (added < 2) {
      d.setUTCDate(d.getUTCDate() + 1);
      const iso = d.toISOString().slice(0, 10);
      const wd = d.getUTCDay();
      if (wd !== 0 && wd !== 6 && !hs.has(iso)) added++;
    }
    return d.toISOString().slice(0, 10);
  }

  const api = { pctReturn, relativeToBenchmark, rotationSpread, directionTag, DIRECTION_RULES, intensityZ,
    mechanicalConfidence, momentumBaseline, nonOverlapping, hitRate, settlementDate };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.RotationLogic = api;
})(typeof window !== "undefined" ? window : globalThis);
