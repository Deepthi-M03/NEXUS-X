async function renderSystem() {
  const el = document.getElementById("view-system");
  const log = await apiGet("/audit");
  el.innerHTML = `
    <h2 class="section-title">System — Audit Log</h2>
    <p class="muted">Immutable-style trail of every investigator and AI action taken in this session.</p>
    <div class="panel">
      ${log.map(a => `
        <div class="audit-row">
          <span>${a.action.replace(/_/g," ")} ${a.object ? "· " + a.object : ""}</span>
          <span>${a.user} · ${new Date(a.timestamp).toLocaleString()}</span>
        </div>
      `).join("") || '<div class="muted">No actions logged yet.</div>'}
    </div>
    <div class="panel">
      <h3>About This Prototype</h3>
      <p class="muted" style="font-size:13px;">NEXUS-X is a Smart India Hackathon 2026 prototype (SIH26189) built for the NCRB Women Safety Division track.
      All data shown is 100% synthetic and fictional. No real individuals, phone numbers, or locations are represented.
      AI hypotheses are investigative leads requiring human review — never confirmed facts.</p>
    </div>
  `;
}
