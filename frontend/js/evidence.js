async function renderEvidence() {
  const el = document.getElementById("view-evidence");
  const samples = await apiGet("/documents/samples");
  el.innerHTML = `
    <h2 class="section-title">Data Ingestion &amp; Evidence Provenance</h2>

    <div class="panel">
      <h3>Ingest a Document</h3>
      <p class="muted">Select a sample document (for demo reliability) or upload your own TXT/CSV/JSON file. Extraction runs through a deterministic NLP fallback pipeline — no internet or paid API required.</p>
      <div class="chip-row">
        ${samples.map(s => `<span class="chip" data-sample="${s.id}">${s.category}: ${s.preview}</span>`).join("")}
      </div>
      <input type="file" id="doc-upload" style="margin-top:10px;color:var(--text-dim);" />
      <div id="ingest-result" style="margin-top:16px;"></div>
    </div>

    <div class="panel">
      <h3>Evidence Provenance Lookup</h3>
      <p class="muted">Trace any AI conclusion back to its exact source record. Try IDs like <code>FIR-001</code>, <code>CDR900</code>, <code>TXN900</code>.</p>
      <div style="display:flex;gap:10px;">
        <input id="evidence-id-input" placeholder="e.g. FIR-001" style="flex:1;padding:9px 12px;background:var(--panel2);border:1px solid var(--border);border-radius:8px;color:var(--text);" />
        <button class="btn small" id="evidence-lookup-btn">WHY?</button>
      </div>
      <div id="evidence-result" style="margin-top:14px;"></div>
    </div>
  `;

  el.querySelectorAll("[data-sample]").forEach(chip => {
    chip.onclick = () => runIngestion({ sample_id: chip.dataset.sample });
  });
  document.getElementById("doc-upload").onchange = (e) => {
    if (e.target.files[0]) runIngestion({ file: e.target.files[0] });
  };
  document.getElementById("evidence-lookup-btn").onclick = lookupEvidence;
}

async function runIngestion({ sample_id, file }) {
  const fd = new FormData();
  if (sample_id) fd.append("sample_id", sample_id);
  if (file) fd.append("file", file);
  const result = await apiPost("/documents/upload", fd);
  const box = document.getElementById("ingest-result");
  box.innerHTML = `
    <h3>Extraction Preview — ${result.category}</h3>
    <p class="muted" style="font-size:13px;">"${result.text_preview}"</p>
    <table>
      <tr><th>Type</th><th>Value</th><th>Confidence</th><th>Action</th></tr>
      ${result.extracted_entities.map((en, i) => `
        <tr>
          <td>${en.type}</td><td>${en.value}</td>
          <td><div class="progress-bar" style="width:80px;"><div style="width:${Math.round(en.confidence*100)}%"></div></div> ${Math.round(en.confidence*100)}%</td>
          <td>
            <button class="btn small" data-accept="${i}">Accept</button>
            <button class="btn secondary small" data-reject="${i}">Reject</button>
          </td>
        </tr>
      `).join("") || `<tr><td colspan="4" class="muted">No entities detected.</td></tr>`}
    </table>
    <button class="btn" id="confirm-entities-btn" style="margin-top:12px;">Confirm & Add to Graph</button>
    <div id="confirm-msg" class="muted" style="margin-top:8px;"></div>
  `;
  document.getElementById("confirm-entities-btn").onclick = async () => {
    await apiPost("/documents/confirm", { entities: result.extracted_entities });
    document.getElementById("confirm-msg").textContent = "Confirmed entities logged to audit trail and queued for graph integration.";
  };
}

async function lookupEvidence() {
  const id = document.getElementById("evidence-id-input").value.trim();
  const box = document.getElementById("evidence-result");
  if (!id) return;
  try {
    const rec = await apiGet(`/evidence/${id}`);
    box.innerHTML = `
      <div class="panel" style="background:var(--panel2);">
        <div class="muted" style="font-size:11px;text-transform:uppercase;">${rec.collection}</div>
        <pre style="white-space:pre-wrap;font-size:12.5px;color:var(--text);">${JSON.stringify(rec, null, 2)}</pre>
      </div>`;
  } catch (e) {
    box.innerHTML = `<div class="muted">No evidence record found for "${id}".</div>`;
  }
}
