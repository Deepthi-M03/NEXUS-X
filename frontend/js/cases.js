async function renderCases() {
  const el = document.getElementById("view-cases");
  const cases = await apiGet("/cases");
  el.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;">
      <h2 class="section-title">Case Management</h2>
      <button class="btn" id="new-case-btn">+ New Case</button>
    </div>
    <div id="cases-list"></div>
  `;
  const list = document.getElementById("cases-list");
  list.innerHTML = cases.map(c => `
    <div class="case-card" data-id="${c.id}">
      <div class="case-top">
        <div><span class="case-id">${c.id}</span><br/><b style="font-size:16px;">${c.title}</b></div>
        <div>${tag(c.priority)} ${tag(c.risk_level)}</div>
      </div>
      <p class="muted" style="margin:10px 0 6px;">${c.description}</p>
      <div class="muted" style="font-size:12px;">Assigned: ${c.assigned_investigator} · Created: ${c.created} · Status: ${c.status}</div>
    </div>
  `).join("");

  list.querySelectorAll(".case-card").forEach(card => {
    card.onclick = () => {
      CURRENT_CASE.id = card.dataset.id;
      document.getElementById("case-select").value = CURRENT_CASE.id;
      switchView("graph");
    };
  });

  document.getElementById("new-case-btn").onclick = async () => {
    const title = prompt("New case title:");
    if (!title) return;
    await apiPost("/cases", { title, description: "Newly created investigation case.", priority: "MEDIUM" });
    renderCases();
    populateCaseSelector();
  };
}
