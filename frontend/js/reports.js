function renderReports() {
  const el = document.getElementById("view-reports");
  el.innerHTML = `
    <h2 class="section-title">Investigation Intelligence Report</h2>
    <div class="panel">
      <p class="muted">Generates a full investigation report from the current case graph: entities, AI hypotheses, contradictions, network roles, communities, and anomalies — with the mandatory disclaimer on AI-generated content.</p>
      <button class="btn" id="gen-report-btn">GENERATE INVESTIGATION INTELLIGENCE REPORT</button>
      <span class="muted" id="report-status" style="margin-left:12px;"></span>
    </div>
    <div class="panel">
      <iframe id="report-frame" style="width:100%;height:640px;border:1px solid var(--border);border-radius:8px;background:#fff;"></iframe>
    </div>
  `;
  document.getElementById("gen-report-btn").onclick = async () => {
    document.getElementById("report-status").textContent = "Generating...";
    const res = await fetch(`${API_BASE}/reports/${CURRENT_CASE.id}`);
    const html = await res.text();
    document.getElementById("report-frame").srcdoc = html;
    document.getElementById("report-status").textContent = "Report generated. Use your browser's print dialog inside the frame to save as PDF.";
  };
}
