const SUGGESTED_QUERIES = [
  "Why is Priya Chatterjee structurally important?",
  "Show all paths between Arjun Mehta and Vikram Rao",
  "What changed after March 2026?",
  "Which hypotheses have contradictory evidence?",
  "Which entities connect Cluster Alpha and Cluster Beta?",
  "Show high-confidence hypotheses above 50%",
];

function renderCopilot() {
  const el = document.getElementById("view-copilot");
  el.innerHTML = `
    <h2 class="section-title">AI Investigation Copilot</h2>
    <p class="muted">Answers are generated only from the currently loaded case graph — never invented. Every response is grounded and traceable.</p>
    <div class="chip-row">${SUGGESTED_QUERIES.map(q => `<span class="chip" data-q="${q}">${q}</span>`).join("")}</div>
    <div class="copilot-window" id="copilot-window">
      <div class="copilot-msg">
        <div class="who">NEXUS-X Copilot</div>
        <div class="bubble">Ask me about entities, hypotheses, contradictions, communities, or network changes in the currently loaded case. I only answer from verified graph data.</div>
      </div>
    </div>
    <div class="copilot-input-row">
      <input id="copilot-input" placeholder="Ask a question about this case..." />
      <button class="btn" id="copilot-send">Send</button>
    </div>
  `;

  const win = document.getElementById("copilot-window");
  const send = async (text) => {
    win.insertAdjacentHTML("beforeend", `<div class="copilot-msg user"><div class="who">Investigator</div><div class="bubble">${text}</div></div>`);
    win.scrollTop = win.scrollHeight;
    const result = await apiPost("/copilot/query", { query: text });
    win.insertAdjacentHTML("beforeend", `
      <div class="copilot-msg">
        <div class="who">NEXUS-X Copilot</div>
        <div class="bubble">${result.answer}</div>
        ${result.evidence && result.evidence.length ? `<div class="muted" style="font-size:11px;margin-top:4px;">Evidence: ${result.evidence.join(", ")}</div>` : ""}
        <div class="muted" style="font-size:11px;">Confidence basis: ${result.confidence}</div>
      </div>
    `);
    win.scrollTop = win.scrollHeight;
  };

  document.getElementById("copilot-send").onclick = () => {
    const input = document.getElementById("copilot-input");
    if (!input.value.trim()) return;
    send(input.value.trim());
    input.value = "";
  };
  document.getElementById("copilot-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") document.getElementById("copilot-send").click();
  });
  el.querySelectorAll("[data-q]").forEach(chip => {
    chip.onclick = () => send(chip.dataset.q);
  });
}
