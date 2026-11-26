const assert = require("assert");
const L = require("../rotation/logic.js");
assert.strictEqual(Math.round(L.pctReturn(100, 110) * 100) / 100, 10);
assert.strictEqual(L.rotationSpread({ returnPct: 5, benchmarkPct: 2 }, { returnPct: -1, benchmarkPct: -3 }), 1);
assert.strictEqual(L.directionTag({ kind: "trade_restriction", imposed: true }, "Resources").tag, "negative");
assert.strictEqual(L.directionTag({ kind: "unknown" }, "Resources").tag, "unassigned");
assert.strictEqual(L.intensityZ(5, [1, 2]), null);
assert.ok(Math.abs(L.intensityZ(6, [2, 3, 4, 3, 3]) - 4.243) < 0.01);
const c = L.mechanicalConfidence({ feedAgeHours: 10, capCoverage: 0.6, keySources: [{ status: "ok" }, { status: "never_run" }] });
assert.strictEqual(c.value, 0.55);
assert.strictEqual(L.momentumBaseline([{ name: "A", prior3mRelPct: 1 }, { name: "B", prior3mRelPct: 3 }]).leader, "B");
const sigs = [{ date: "2026-01-01", outcome: "hit" }, { date: "2026-01-20", outcome: "miss" }, { date: "2026-04-05", outcome: "miss" }];
assert.strictEqual(L.nonOverlapping(sigs, 90).length, 2);
assert.strictEqual(L.hitRate(sigs, 90).rate, 0.5);
assert.strictEqual(L.settlementDate("2026-11-27"), "2026-12-01"); // Fri -> Tue
assert.strictEqual(L.settlementDate("2026-12-24", ["2026-12-25", "2026-12-28"]), "2026-12-30");
console.log("logic.js tests passed");
