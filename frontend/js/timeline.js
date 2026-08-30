const TIMELINE_MONTHS = ["2026-01-31","2026-02-28","2026-03-31","2026-04-30","2026-05-31"];
let timelinePlaying = false;

async function renderTimeline() {
  const el = document.getElementById("view-timeline");
  el.innerHTML = `
    <h2 class="section-title">Temporal Network Reconstruction</h2>
    <div class="panel">
      <div class="slider-row">
        <button class="btn secondary small" id="tl-play">▶ Play</button>
        <input type="range" id="tl-slider" min="0" max="${TIMELINE_MONTHS.length-1}" value="${TIMELINE_MONTHS.length-1}" />
        <span id="tl-label" style="min-width:90px;text-align:right;font-weight:600;"></span>
      </div>
      <div class="two-col">
        <div id="tl-stats"></div>
        <div>
          <h3>Detected Structural Events</h3>
          <div id="tl-events"></div>
        </div>
      </div>
    </div>
  `;

  const events = await apiGet(`/timeline/${CURRENT_CASE.id}/events`);
  document.getElementById("tl-events").innerHTML = events.length ? events.map(ev => `
    <div class="step-card">
      <div class="step-num">${ev.date}</div>
      <div><b>NETWORK EVENT DETECTED</b></div>
      <div class="muted" style="margin-top:4px;">${ev.description}</div>
      <div class="muted" style="font-size:11px;margin-top:4px;">Betweenness ${ev.betweenness_before} → ${ev.betweenness_after}</div>
    </div>
  `).join("") : `<div class="muted">No structural shift detected.</div>`;

  const slider = document.getElementById("tl-slider");
  const updateSnapshot = async () => {
    const idx = parseInt(slider.value);
    const asOf = TIMELINE_MONTHS[idx];
    document.getElementById("tl-label").textContent = asOf.slice(0,7);
    const snap = await apiGet(`/timeline/${CURRENT_CASE.id}?as_of=${asOf}`);
    document.getElementById("tl-stats").innerHTML = `
      <div class="grid grid-cards">
        <div class="card"><div class="stat-value">${snap.node_count}</div><div class="stat-label">Active Entities</div></div>
        <div class="card"><div class="stat-value">${snap.edge_count}</div><div class="stat-label">Active Relationships</div></div>
      </div>
      <div class="muted" style="margin-top:10px;font-size:12px;">Snapshot as of ${asOf}. Drag the slider to reconstruct the network at any point in the investigation timeline.</div>
    `;
  };
  slider.oninput = updateSnapshot;
  updateSnapshot();

  document.getElementById("tl-play").onclick = () => {
    timelinePlaying = !timelinePlaying;
    document.getElementById("tl-play").textContent = timelinePlaying ? "⏸ Pause" : "▶ Play";
    if (timelinePlaying) playTimeline();
  };
}

async function playTimeline() {
  const slider = document.getElementById("tl-slider");
  let idx = 0;
  slider.value = 0;
  const step = async () => {
    if (!timelinePlaying) return;
    slider.value = idx;
    slider.dispatchEvent(new Event("input"));
    idx++;
    if (idx > TIMELINE_MONTHS.length - 1) { timelinePlaying = false; document.getElementById("tl-play").textContent = "▶ Play"; return; }
    setTimeout(step, 1400);
  };
  step();
}
