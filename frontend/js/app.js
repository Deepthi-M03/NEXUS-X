const VIEW_RENDERERS = {
  overview: renderOverview, cases: renderCases, graph: renderGraph, timeline: renderTimeline,
  hypotheses: renderHypotheses, evidence: renderEvidence, analytics: renderAnalytics,
  copilot: renderCopilot, reports: renderReports, story: renderStory, system: renderSystem,
};

function switchView(view) {
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
  document.getElementById("view-" + view).classList.add("active");
  document.querySelectorAll("#nav button").forEach(b => b.classList.toggle("active", b.dataset.view === view));
  VIEW_RENDERERS[view]();
}

async function populateCaseSelector() {
  const cases = await apiGet("/cases");
  const sel = document.getElementById("case-select");
  sel.innerHTML = cases.map(c => `<option value="${c.id}">${c.id} — ${c.title}</option>`).join("");
  sel.value = CURRENT_CASE.id;
  sel.onchange = () => { CURRENT_CASE.id = sel.value; switchView(document.querySelector("#nav button.active").dataset.view); };
}

document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = document.getElementById("login-email").value;
  const password = document.getElementById("login-password").value;
  const errBox = document.getElementById("login-error");
  errBox.textContent = "";
  try {
    await apiPost("/auth/login", { email, password });
    document.getElementById("login-screen").classList.add("hidden");
    document.getElementById("app").classList.remove("hidden");
    await populateCaseSelector();
    switchView("overview");
  } catch (err) {
    errBox.textContent = "Invalid demo credentials. Use investigator@nexusx.demo / demo123";
  }
});

document.getElementById("logout-btn").onclick = () => {
  document.getElementById("app").classList.add("hidden");
  document.getElementById("login-screen").classList.remove("hidden");
};

document.querySelectorAll("#nav button").forEach(btn => {
  btn.onclick = () => switchView(btn.dataset.view);
});

// subtle animated network background dots on login screen
(function animateLoginBg(){
  const bg = document.getElementById("login-bg");
  let t = 0;
  setInterval(() => {
    t += 0.5;
    bg.style.backgroundPosition = `${Math.sin(t/20)*20}px ${Math.cos(t/20)*20}px`;
  }, 100);
})();
