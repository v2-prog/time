(function () {
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  fetch("../data/chips.json", { cache: "no-cache" }).then((r) => r.json()).then((d) => {
    document.getElementById("feeds").innerHTML = `<h2>Feed health</h2><table><thead><tr><th>Feed</th><th>Status</th></tr></thead><tbody>${d.feeds.map((f) => `<tr><td>${esc(f.label)}</td><td><span class="pill warn">${esc(f.status)}</span></td></tr>`).join("")}</tbody></table>`;
    document.getElementById("events").innerHTML = `<h2>Seeded timeline</h2><p class="meta">${esc(d.note)}</p><table><thead><tr><th>Date</th><th>Side</th><th>Event</th><th>Check</th></tr></thead><tbody>${d.events.map((e) => `<tr><td>${esc(e.date)}</td><td>${esc(e.side)}</td><td>${esc(e.title)}</td><td><a href="${esc(e.source)}" target="_blank" rel="noopener">source</a> ${e.verify ? '<span class="pill warn">verify</span>' : ""}</td></tr>`).join("")}</tbody></table>`;
  }).catch(() => { document.getElementById("events").innerHTML += "<p>chips.json missing</p>"; });
})();
