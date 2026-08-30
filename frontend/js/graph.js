let cyInstance = null;

const NODE_COLORS = {
  PERSON: "#5b8cff", PHONE: "#3ecfb4", VEHICLE: "#e0a94a",
  ACCOUNT: "#c084fc", LOCATION: "#f472b6", ORGANIZATION: "#94a3b8", EVENT: "#64748b",
};
const EDGE_COLORS = {
  CONFIRMED: "#3ecfb4", INFERRED: "#5b8cff", INVESTIGATIVE_HYPOTHESIS: "#e0a94a",
  CONTRADICTED: "#e2555a", UNVERIFIED: "#5c6577", REVIEW_REQUIRED: "#5c6577",
};

async function renderGraph() {
  const el = document.getElementById("view-graph");
  el.innerHTML = `
    <h2 class="section-title">Intelligence Graph</h2>
    ${statusLegendHTML()}
    <div class="chip-row">
      <input id="graph-search" placeholder="Search entity..." style="padding:8px 12px;border-radius:20px;border:1px solid var(--border);background:var(--panel2);color:var(--text);min-width:220px;" />
      <span class="chip" data-conf="0">All confidence</span>
      <span class="chip" data-conf="0.5">Confidence ≥ 50%</span>
      <span class="chip" data-conf="0.7">Confidence ≥ 70%</span>
      <button class="chip" id="path-finder-btn">Path Finder</button>
      <button class="chip" id="fit-btn">Fit View</button>
    </div>
    <div id="path-finder-panel" class="panel hidden">
      <h3>Network Path Explorer</h3>
      <div style="display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;">
        <div><label class="muted" style="font-size:11px;">Entity A</label><br/><select id="pf-a"></select></div>
        <div><label class="muted" style="font-size:11px;">Entity B</label><br/><select id="pf-b"></select></div>
        <div><label class="muted" style="font-size:11px;">Max hops</label><br/>
          <select id="pf-hops"><option>2</option><option selected>3</option><option>4</option><option>5</option></select>
        </div>
        <button class="btn small" id="pf-run">Find Paths</button>
      </div>
      <div id="pf-results" style="margin-top:12px;"></div>
    </div>
    <div class="two-col">
      <div class="cy-container" id="cy"></div>
      <div class="panel entity-panel" id="entity-detail">
        <h3>Entity Detail</h3>
        <div class="node-detail-empty">Click a node to view details, evidence, and network role.</div>
      </div>
    </div>
  `;

  const data = await apiGet(`/graph/${CURRENT_CASE.id}`);
  const elements = [
    ...data.nodes.map(n => ({ data: { id: n.id, label: n.label, type: n.type } })),
    ...data.edges.map((e, i) => ({
      data: {
        id: "e" + i, source: e.source, target: e.target, type: e.type,
        status: e.status, confidence: e.confidence, hypothesis_id: e.hypothesis_id || null,
      }
    })),
  ];

  cyInstance = cytoscape({
    container: document.getElementById("cy"),
    elements,
    style: [
      { selector: "node", style: {
        "background-color": ele => NODE_COLORS[ele.data("type")] || "#888",
        "label": "data(label)", "color": "#cfd6e2", "font-size": 9, "text-valign": "bottom", "text-margin-y": 4,
        "width": 22, "height": 22, "border-width": 1, "border-color": "#0a0d13",
      }},
      { selector: "edge", style: {
        "width": 1.6, "curve-style": "bezier",
        "line-color": ele => EDGE_COLORS[ele.data("status")] || "#5c6577",
        "target-arrow-color": ele => EDGE_COLORS[ele.data("status")] || "#5c6577",
        "target-arrow-shape": "triangle", "arrow-scale": 0.7,
        "line-style": ele => ele.data("status") === "INVESTIGATIVE_HYPOTHESIS" ? "dashed" : "solid",
        "opacity": 0.85,
      }},
      { selector: ".faded", style: { "opacity": 0.08 } },
      { selector: ".highlighted", style: { "opacity": 1, "width": 3 } },
    ],
    layout: { name: "cose", animate: false, nodeRepulsion: 9000, idealEdgeLength: 70 },
  });

  cyInstance.on("tap", "node", (evt) => showEntityDetail(evt.target.id()));

  document.getElementById("fit-btn").onclick = () => cyInstance.fit(undefined, 30);
  document.querySelectorAll(".chip[data-conf]").forEach(chip => {
    chip.onclick = async () => {
      const min = parseFloat(chip.dataset.conf);
      const filtered = await apiGet(`/graph/${CURRENT_CASE.id}?min_confidence=${min}`);
      cyInstance.elements().remove();
      cyInstance.add([
        ...filtered.nodes.map(n => ({ data: { id: n.id, label: n.label, type: n.type } })),
        ...filtered.edges.map((e, i) => ({ data: { id: "ef"+i, source: e.source, target: e.target, type: e.type, status: e.status, confidence: e.confidence } })),
      ]);
      cyInstance.layout({ name: "cose", animate: false }).run();
    };
  });

  document.getElementById("graph-search").addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase();
    cyInstance.nodes().forEach(n => {
      if (!q) { n.removeClass("faded"); return; }
      if (n.data("label").toLowerCase().includes(q)) n.removeClass("faded");
      else n.addClass("faded");
    });
  });

  document.getElementById("path-finder-btn").onclick = () => {
    const panel = document.getElementById("path-finder-panel");
    panel.classList.toggle("hidden");
    if (!panel.classList.contains("hidden")) {
      const people = data.nodes.filter(n => n.type === "PERSON");
      const opts = people.map(p => `<option value="${p.id}">${p.label}</option>`).join("");
      document.getElementById("pf-a").innerHTML = opts;
      document.getElementById("pf-b").innerHTML = opts;
    }
  };

  document.getElementById("pf-run").onclick = async () => {
    const source = document.getElementById("pf-a").value;
    const target = document.getElementById("pf-b").value;
    const maxHops = document.getElementById("pf-hops").value;
    const paths = await apiGet(`/analysis/path?source=${source}&target=${target}&max_hops=${maxHops}`);
    const box = document.getElementById("pf-results");
    if (!paths.length) { box.innerHTML = `<div class="muted">No path found within ${maxHops} hops.</div>`; return; }
    box.innerHTML = paths.map(p => `
      <div style="border:1px solid var(--border);border-radius:8px;padding:10px 12px;margin-bottom:8px;">
        <b>${p.length} hop(s)</b><br/>
        ${p.steps.map(s => `${s.from_label} —${s.relationship}→ ${s.to_label}`).join(" <br/>")}
        <div class="muted" style="margin-top:6px;font-size:11px;">Evidence: ${p.steps.flatMap(s=>s.evidence).join(", ") || "structural ownership"}</div>
      </div>
    `).join("");
  };
}

async function showEntityDetail(id) {
  const panel = document.getElementById("entity-detail");
  panel.innerHTML = `<h3>Entity Detail</h3><div class="muted">Loading...</div>`;
  const e = await apiGet(`/entities/${id}`);
  panel.innerHTML = `
    <h3>Entity Detail</h3>
    <div style="font-size:16px;font-weight:700;">${e.label}</div>
    <div class="muted" style="margin-bottom:10px;">${e.type}</div>
    ${e.network_role ? `
      <div style="margin-bottom:10px;">
        <span class="tag CONFIRMED">${e.network_role.role.replace(/_/g," ")}</span>
        <div class="muted" style="font-size:12px;margin-top:6px;">${e.network_role.reason}</div>
        <div class="breakdown-row"><span>${tooltip("Betweenness Centrality","Measures how frequently an entity lies on paths connecting other entities.")}</span><span>${e.network_role.betweenness_centrality}</span></div>
        <div class="breakdown-row"><span>Degree Centrality</span><span>${e.network_role.degree_centrality}</span></div>
        <div class="breakdown-row"><span>PageRank</span><span>${e.network_role.pagerank}</span></div>
      </div>` : ""}
    <h3 style="margin-top:16px;">Connected Entities (${e.neighbors.length})</h3>
    <div>
      ${e.neighbors.slice(0, 20).map(n => `
        <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border);font-size:12.5px;">
          <span>${n.label} <span class="muted">(${n.type})</span></span>
          <span class="muted">${n.relationship}</span>
        </div>
      `).join("")}
    </div>
  `;
}
