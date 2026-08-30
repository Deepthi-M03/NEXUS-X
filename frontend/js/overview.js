async function renderOverview() {
  const el = document.getElementById("view-overview");
  el.innerHTML = `<h2 class="section-title">Investigation Overview</h2><div class="muted">Loading...</div>`;
  const data = await apiGet("/overview");

  const cards = [
    ["ACTIVE CASES", data.active_cases],
    ["ENTITIES ANALYZED", data.entities_analyzed],
    ["RELATIONSHIPS", data.relationships],
    ["AI HYPOTHESES", data.ai_hypotheses],
    ["HIGH-RISK PATTERNS", data.high_risk_patterns],
    ["CONTRADICTIONS", data.contradictions],
    ["UNRESOLVED ENTITIES", data.unresolved_entities],
  ];

  el.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <h2 class="section-title">Investigation Overview</h2>
      <button class="btn" id="open-graph-cta">OPEN INTELLIGENCE GRAPH →</button>
    </div>
    <div class="grid grid-cards" style="margin-bottom:22px;">
      ${cards.map(([label, val]) => `
        <div class="card">
          <div class="stat-value">${val}</div>
          <div class="stat-label">${label}</div>
        </div>`).join("")}
    </div>
    <div class="two-col">
      <div>
        <div class="panel">
          <h3>High-Priority Hypotheses</h3>
          ${data.top_hypotheses.map(h => `
            <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border);">
              <span>${h.entity_a_name} ↔ ${h.entity_b_name}</span>
              <span style="color:var(--warn);font-weight:700;">${Math.round(h.confidence*100)}%</span>
            </div>`).join("") || '<div class="muted">No hypotheses generated yet.</div>'}
        </div>
        <div class="panel">
          <h3>Entity Distribution</h3>
          <canvas id="entity-dist-chart"></canvas>
        </div>
      </div>
      <div>
        <div class="panel">
          <h3>Recent Intelligence Activity</h3>
          ${data.recent_activity.map(a => `
            <div class="audit-row"><span>${a.action.replace(/_/g," ")}</span><span>${new Date(a.timestamp).toLocaleTimeString()}</span></div>
          `).join("") || '<div class="muted">No activity yet.</div>'}
        </div>
        <div class="panel">
          <h3>Network Alerts</h3>
          <div class="muted" style="font-size:13px;">${data.contradictions} contradiction(s) and ${data.high_risk_patterns} high-confidence hypothesis pattern(s) currently require investigator review.</div>
        </div>
      </div>
    </div>
  `;

  document.getElementById("open-graph-cta").onclick = () => switchView("graph");

  const ctx = document.getElementById("entity-dist-chart");
  new Chart(ctx, {
    type: "bar",
    data: {
      labels: Object.keys(data.entity_distribution),
      datasets: [{ data: Object.values(data.entity_distribution), backgroundColor: "#3ecfb4" }]
    },
    options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
  });
}
