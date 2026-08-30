async function renderStory() {
  const el = document.getElementById("view-story");
  el.innerHTML = `
    <h2 class="section-title">Investigation Story Mode</h2>
    <p class="muted">A guided walkthrough of Operation Silent Web, generated from real computed results in the current graph — suitable for a 2–3 minute demonstration.</p>
    <button class="btn" id="start-story-btn">START CASE RECONSTRUCTION</button>
    <div id="story-steps" style="margin-top:20px;"></div>
  `;
  document.getElementById("start-story-btn").onclick = async () => {
    const data = await apiGet(`/story/${CURRENT_CASE.id}`);
    const box = document.getElementById("story-steps");
    box.innerHTML = "";
    for (const step of data.steps) {
      await new Promise(r => setTimeout(r, 350));
      box.insertAdjacentHTML("beforeend", `
        <div class="step-card">
          <div class="step-num">STEP ${step.step}</div>
          <div style="font-weight:600;margin:4px 0;">${step.title}</div>
          <div class="muted" style="font-size:13px;">${step.detail}</div>
        </div>
      `);
      box.scrollTop = box.scrollHeight;
    }
  };
}
