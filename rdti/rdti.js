(function () {
  const m = (v) => (v == null ? '—' : '$' + (v / 1e6).toFixed(1) + 'm');
  const p = (v) => (v == null ? '—' : (v > 0 ? '+' : '') + v.toFixed(1) + '%');
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  fetch('../data/rdti/counts.json').then((r) => r.json()).then((d) => {
    const rows = Object.entries(d.counts).filter(([y]) => !y.startsWith('_'))
      .map(([y, c]) => `<tr><td>${y}</td><td>${c.entities.toLocaleString('en-AU')}</td><td>${c.amended_rows}</td><td>${c.effective_zero}</td><td>${m(c.total_effective_aud)}</td></tr>`).join('');
    document.getElementById('counts').innerHTML = `<table><thead><tr><th>Income year</th><th>Entities</th><th>Amended</th><th>Amended to nil</th><th>Total (effective)</th></tr></thead><tbody>${rows}</tbody></table>`;
  });
  fetch('../data/rdti/listed-matches.json').then((r) => r.json()).then((d) => {
    const rows = d.matches.slice(0, 50).map((r) => {
      const e = r.rd_expenditure_effective;
      return `<tr><td>${esc(r.asx_code)}</td><td>${esc(r.company_name)}</td><td>${esc(r.confidence)}</td><td>${m(e['2021-22'])}</td><td>${m(e['2022-23'])}</td><td>${m(e['2023-24'])}</td><td>${p(r.yoy_pct['2023-24'])}</td><td>${p(r.cagr_pct_2021_22_to_2023_24)}</td><td>${esc(r.flags.join(', '))}</td></tr>`;
    }).join('');
    document.getElementById('matches').innerHTML = `<p>${d.meta.matched_entities} entities matched to ${d.meta.matched_codes} tickers (ASX list as at ${esc(d.meta.asx_list_as_at)}).</p><table><thead><tr><th>Code</th><th>Claimant entity</th><th>Confidence</th><th>2021-22</th><th>2022-23</th><th>2023-24</th><th>YoY 23-24</th><th>CAGR</th><th>Flags</th></tr></thead><tbody>${rows}</tbody></table>`;
  });
})();
