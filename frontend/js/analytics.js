async function renderAnalytics() {
  const el = document.getElementById("view-analytics");
  el.innerHTML = `<h2 class="section-title">Analytics</h2><div class="muted">Loading...</div>`;

  const [contras, roles, communities, anomalies, hyps] = await Promise.all([
    apiPost("/analysis/contradictions"),
    apiGet("/analysis/network-roles"),
    apiGet(`/analysis/communities/${CURRENT_CASE.id}`),
    apiGet("/analysis/anomalies"),
    apiPost("/analysis/hidden-links"),
  ]);

  el.innerHTML = `
    <h2 class="section-title">Analytics</h2>

    <div class="two-col">
      <div class="panel"><h3>Hypothesis Confidence Distribution</h3><canvas id="chart-conf"></canvas></div>
      <div class="panel"><h3>Community Sizes</h3><canvas id="chart-comm"></canvas></div>
    </div>

    <div class="panel">
      <h3>Contradictions Detected</h3>
      <div id="contra-list"></div>
    </div>

    <div class="panel">
      <h3>Network Role Discovery — Centrality Rankings</h3>
      <p class="muted" style="font-size:12.5px;">Analytical structural labels only. NEXUS-X never labels an entity as a criminal based on network position.</p>
      <table>
        <tr><th>Entity</th><th>Role</th><th>${tooltip("Betweenness","Measures how frequently an entity lies on paths connecting other entities.")}</th><th>Degree</th><th>PageRank</th></tr>
        ${roles.slice(0, 12).map(r => `
          <tr><td>${r.entity_name}</td><td>${r.role.replace(/_/g," ")}</td><td>${r.betweenness_centrality}</td><td>${r.degree_centrality}</td><td>${r.pagerank}</td></tr>
        `).join("")}
      </table>
    </div>

    <div class="panel">
      <h3>Community Detection</h3>
      <div class="grid grid-cards">
        ${communities.map(c => `
          <div class="card">
            <div class="stat-value">${c.size}</div>
            <div class="stat-label">${c.name}</div>
            <div class="muted" style="font-size:12px;margin-top:6px;">Central: ${c.central_entity ? c.central_entity.name : "—"}</div>
          </div>
        `).join("")}
      </div>
    </div>

    <div class="panel">
      <h3>Counterfactual Network Simulator</h3>
      <p class="muted">Temporarily simulate removing an entity from the analytical graph. No data is deleted.</p>
      <div style="display:flex;gap:10px;align-items:flex-end;">
        <div><label class="muted" style="font-size:11px;">Select entity</label><br/>
          <select id="cf-entity">${roles.map(r=>`<option value="${r.entity}">${r.entity_name}</option>`).join("")}</select>
        </div>
        <button class="btn small" id="cf-run">REMOVE FROM ANALYTICAL GRAPH</button>
      </div>
      <div id="cf-result" style="margin-top:14px;"></div>
    </div>

    <div class="panel">
      <h3>Anomaly Feed</h3>
      <div id="anomaly-list"></div>
    </div>
  `;

  document.getElementById("contra-list").innerHTML = contras.map(c => `
    <div class="hypothesis-card">
      <div class="hypothesis-head">
        <div class="hypothesis-title">INTELLIGENCE CONFLICT — ${c.entity_name}</div>
        <div>${tag(c.confidence)}</div>
      </div>
      <div class="evidence-col">
        <div><b>Record 1</b><div class="muted">${c.record_1.location} @ ${c.record_1.timestamp}</div></div>
        <div><b>Record 2</b><div class="muted">${c.record_2.location} @ ${c.record_2.timestamp}</div></div>
      </div>
      <p style="font-size:12.5px;margin-top:8px;">${c.minutes_apart} minutes apart at different locations.</p>
      <b style="font-size:12.5px;">Possible explanations:</b>
      <ul style="margin:4px 0 8px;padding-left:18px;font-size:12.5px;">${c.possible_explanations.map(x=>`<li>${x}</li>`).join("")}</ul>
      <div>${tag(c.status)}</div>
      <div class="review-actions">
        <button class="btn small" data-contra="${c.id}" data-decision="RESOLVED">Mark Resolved</button>
        <button class="btn secondary small" data-contra="${c.id}" data-decision="ESCALATED">Escalate</button>
      </div>
    </div>
  `).join("") || `<div class="muted">No contradictions currently detected.</div>`;

  el.querySelectorAll("[data-contra]").forEach(btn => {
    btn.onclick = async () => {
      await apiPost(`/contradictions/${btn.dataset.contra}/review`, { decision: btn.dataset.decision });
      renderAnalytics();
    };
  });

  document.getElementById("anomaly-list").innerHTML = anomalies.map(a => `
    <div class="audit-row">
      <span>${tag(a.severity)} ${a.type.replace(/_/g," ")}</span>
      <span class="muted">${Math.round(a.confidence*100)}% conf.</span>
    </div>
    <div class="muted" style="font-size:12px;margin:2px 0 10px;">${a.reason}</div>
  `).join("") || `<div class="muted">No anomalies detected.</div>`;

  document.getElementById("cf-run").onclick = async () => {
    const entityId = document.getElementById("cf-entity").value;
    const fd = new FormData(); fd.append("entity_id", entityId);
    const result = await apiPost("/analysis/counterfactual", fd);
    document.getElementById("cf-result").innerHTML = `
      <div class="panel" style="background:var(--panel2);">
        <b>COUNTERFACTUAL ANALYSIS — Removing ${result.removed_entity.name}</b>
        <div class="evidence-col">
          <div><b>Before</b>
            <div class="muted">Components: ${result.before.components}</div>
            <div class="muted">Density: ${result.before.density}</div>
            <div class="muted">Avg shortest path: ${result.before.avg_shortest_path ?? "N/A"}</div>
          </div>
          <div><b>After</b>
            <div class="muted">Components: ${result.after.components}</div>
            <div class="muted">Density: ${result.after.density}</div>
            <div class="muted">Avg shortest path: ${result.after.avg_shortest_path ?? "N/A"}</div>
          </div>
        </div>
        <p style="margin-top:10px;font-size:13px;"><b>Fragmentation:</b> ${result.fragmentation_pct >= 0 ? "+" : ""}${result.fragmentation_pct}% ·
        <b>Alternative paths preserved:</b> ${result.alternative_paths_preserved} ·
        <b>New bridge candidate:</b> ${result.new_bridge_candidate ? result.new_bridge_candidate.name : "—"}</p>
        <p class="muted" style="font-size:12.5px;margin-top:8px;">${result.interpretation}</p>
      </div>
    `;
  };

  new Chart(document.getElementById("chart-conf"), {
    type: "bar",
    data: { labels: hyps.map(h => `${h.entity_a_name.split(" ")[0]}↔${h.entity_b_name.split(" ")[0]}`),
            datasets: [{ data: hyps.map(h => Math.round(h.confidence*100)), backgroundColor: "#e0a94a" }] },
    options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, max: 100 } } }
  });
  new Chart(document.getElementById("chart-comm"), {
    type: "doughnut",
    data: { labels: communities.map(c => c.name), datasets: [{ data: communities.map(c => c.size),
            backgroundColor: ["#3ecfb4","#5b8cff","#e0a94a","#c084fc","#f472b6","#94a3b8","#64748b","#e2555a"] }] },
    options: { plugins: { legend: { position: "bottom", labels: { color: "#8b96a8", font: { size: 10 } } } } }
  });
}
