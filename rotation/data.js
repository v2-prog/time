/* Static Rotation configuration. No prices are shipped: S&P/ASX index data is licensed,
 * so returns are entered by the reader or loaded later from a licensed source. */
window.ROTATION_DATA = {
  iteration: "042 + 040 review fixes",
  brackets: [
    { name: "Financials", benchmark: "S&P/ASX 200 Financials", code: "XFJ" },
    { name: "Healthcare", benchmark: "S&P/ASX 200 Health Care", code: "XHJ" },
    { name: "Resources", benchmark: "S&P/ASX 200 Materials", code: "XMJ", note: "Whitehaven (WHC) is GICS Energy, so it is measured against XEJ, not XMJ" },
    { name: "Energy", benchmark: "S&P/ASX 200 Energy", code: "XEJ" },
    { name: "Industrials", benchmark: "S&P/ASX 200 Industrials", code: "XNJ" }
  ],
  // Key sources whose silence lowers Resources confidence (ids match data/feed_health.json).
  keySources: { Resources: ["asx_announcements", "wa_dmpe_announcements", "wa_dmpe_tenements", "qld_nrmmrrd", "nsw_resources", "epbc_notices", "china_customs", "mofcom"] },
  // Rotation scope is the ASX 200. Names outside it are watch-list only.
  watchListOutsideScope: [
    { code: "NTU", name: "Northern Minerals Limited", why: "Small cap, outside ASX 200" },
    { code: "ARU", name: "Arafura Rare Earths Limited", why: "Reported added to ASX 300 in Mar 2026; ASX 200 membership unverified" }
  ],
  // Sector ETF entities: add only if Doug actually executes through ETFs. Left empty on purpose.
  etfEntities: [],
  // ASX non-trading days for T+2 (national). Confirm each year against the ASX trading calendar.
  asxHolidays: ["2026-12-25", "2026-12-28", "2027-01-01", "2027-01-26"],
  designFixes: [
    { gap: "Outcomes as spreads vs S&P/ASX 200 sector indices", status: "Implemented", where: "logic.js rotationSpread()" },
    { gap: "Direction tags with documented rules", status: "Implemented (draft rules for review)", where: "logic.js DIRECTION_RULES" },
    { gap: "Baseline-adjusted intensity (z-score)", status: "Implemented; needs >= 4 past windows", where: "logic.js intensityZ()" },
    { gap: "Magnitude units", status: "Set: percentage points of benchmark-relative return", where: "Signals tab" },
    { gap: "Momentum baseline next to every signal", status: "Implemented", where: "logic.js momentumBaseline()" },
    { gap: "Non-overlapping windows for hit rates", status: "Implemented", where: "logic.js hitRate()" },
    { gap: "Spillover to cash/bonds/offshore is a hypothesis", status: "Documented; not scored", where: "Rules tab" },
    { gap: "Mechanical confidence (freshness, cap coverage, silence)", status: "Implemented", where: "logic.js mechanicalConfidence()" },
    { gap: "T+2 settlement", status: "Implemented", where: "logic.js settlementDate()" },
    { gap: "Sector ETF entities", status: "Not needed unless ETFs are used", where: "data.js etfEntities" },
    { gap: "Backtest Resources on 2020-24 China dispute", status: "Blocked: needs licensed index history", where: "-" }
  ]
};
