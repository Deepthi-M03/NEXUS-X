function statusLegendHTML() {
  return `
  <div class="legend-row">
    <div class="legend-item"><span class="legend-dot" style="background:#3ecfb4"></span> Confirmed</div>
    <div class="legend-item"><span class="legend-dot" style="background:#5b8cff"></span> Inferred</div>
    <div class="legend-item"><span class="legend-dot" style="background:#e0a94a"></span> AI Hypothesis</div>
    <div class="legend-item"><span class="legend-dot" style="background:#e2555a"></span> Contradicted</div>
    <div class="legend-item"><span class="legend-dot" style="background:#5c6577"></span> Unverified</div>
  </div>`;
}

function tag(status) {
  return `<span class="tag ${status}">${(status||"").replace(/_/g," ")}</span>`;
}

function tooltip(term, text) {
  return `<span class="tooltip-term" title="${text}">${term}</span>`;
}
