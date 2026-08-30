async function renderHypotheses() {
  const el = document.getElementById("view-hypotheses");
  el.innerHTML = `<h2 class="section-title">Hidden-Link Hypothesis Engine</h2><div class="muted">Loading...</div>`;
  const hyps = await apiPost("/analysis/hidden-links");
  const er = await apiPost("/analysis/entity-resolution");

  el.innerHTML = `
    <h2 class="section-title">Hidden-Link Hypothesis Engine</h2>
    <p class="muted">Every hypothesis below is an <b>investigative lead</b>, not a confirmed relationship. Confidence is derived from explainable, weighted graph features — never randomly generated.</p>
    <div id="hyp-list"></div>

    <h2 class="section-title" style="margin-top:30px;">Entity Resolution — Possible Duplicate Identities</h2>
    <p class="muted">The system never silently merges records. Every match below requires investigator confirmation.</p>
    <div id="er-list"></div>
  `;

  document.getElementById("hyp-list").innerHTML = hyps.map(h => hypothesisCardHTML(h)).join("") ||
    `<div class="muted">No hidden-link hypotheses currently exceed the confidence threshold.</div>`;

  document.getElementById("er-list").innerHTML = er.map(c => `
    <div class="hypothesis-card">
      <div class="hypothesis-head">
        <div class="hypothesis-title">${c.entity_a_name} ↔ ${c.entity_b_name}</div>
        <div class="confidence-badge">${Math.round(c.confidence*100)}%</div>
      </div>
      <div class="muted">POSSIBLE DUPLICATE ENTITY</div>
      <ul style="margin:8px 0 10px;padding-left:18px;font-size:13px;">${c.reasons.map(r=>`<li>${r}</li>`).join("")}</ul>
      <div>${tag(c.status)}</div>
      <div class="review-actions">
        <button class="btn small" data-action="MERGE" data-a="${c.entity_a}" data-b="${c.entity_b}">Merge</button>
        <button class="btn secondary small" data-action="KEEP_SEPARATE" data-a="${c.entity_a}" data-b="${c.entity_b}">Keep Separate</button>
        <button class="btn secondary small" data-action="REVIEW_LATER" data-a="${c.entity_a}" data-b="${c.entity_b}">Review Later</button>
      </div>
    </div>
  `).join("") || `<div class="muted">No probable duplicate identities detected.</div>`;

  el.querySelectorAll("[data-action][data-a]").forEach(btn => {
    btn.onclick = async () => {
      await apiPost("/analysis/entity-resolution/decision", {
        entity_a: btn.dataset.a, entity_b: btn.dataset.b, decision: btn.dataset.action
      });
      renderHypotheses();
    };
  });

  wireHypothesisActions(el);
}

function hypothesisCardHTML(h) {
  return `
    <div class="hypothesis-card" id="hcard-${h.id}">
      <div class="hypothesis-head">
        <div class="hypothesis-title">${h.entity_a_name} ↔ ${h.entity_b_name}</div>
        <div class="confidence-badge">${Math.round(h.confidence*100)}%</div>
      </div>
      <div>${tag(h.status)}</div>
      <p style="margin:10px 0 4px;font-size:13px;">${h.explanation}</p>
      <div class="evidence-col">
        <div>
          <b>Supporting Evidence</b>
          <ul>${h.supporting_evidence.map(x=>`<li>${x}</li>`).join("") || "<li>None</li>"}</ul>
        </div>
        <div>
          <b>Contradicting Evidence</b>
          <ul>${h.contradicting_evidence.map(x=>`<li>${x}</li>`).join("") || "<li>None</li>"}</ul>
        </div>
      </div>
      <p style="font-size:12.5px;margin-top:8px;"><b>Missing Evidence:</b> ${h.missing_evidence.join("; ")}</p>
      <details style="margin-top:8px;">
        <summary style="cursor:pointer;color:var(--accent);font-size:12.5px;">VIEW SCORE BREAKDOWN</summary>
        <div style="margin-top:8px;">
          ${Object.entries(h.score_breakdown.weights).map(([k,w]) => `
            <div class="breakdown-row"><span>${k.replace(/_/g," ")} (weight ${w})</span><span>${h.score_breakdown[k]}</span></div>
          `).join("")}
        </div>
      </details>
      <div class="review-actions">
        <button class="btn small" data-hyp="${h.id}" data-decision="CONFIRMED">Confirm</button>
        <button class="btn secondary small" data-hyp="${h.id}" data-decision="REJECTED">Reject Hypothesis</button>
        <button class="btn secondary small" data-hyp="${h.id}" data-decision="REVIEWED">Mark Reviewed</button>
        <button class="btn secondary small" data-path-a="${h.entity_a}" data-path-b="${h.entity_b}">Show Graph Path</button>
      </div>
      <div id="path-${h.id}" style="margin-top:10px;"></div>
    </div>
  `;
}

function wireHypothesisActions(el) {
  el.querySelectorAll("[data-hyp]").forEach(btn => {
    btn.onclick = async () => {
      await apiPost(`/hypotheses/${btn.dataset.hyp}/review`, { decision: btn.dataset.decision });
      renderHypotheses();
    };
  });
  el.querySelectorAll("[data-path-a]").forEach(btn => {
    btn.onclick = async () => {
      const paths = await apiGet(`/analysis/path?source=${btn.dataset.pathA}&target=${btn.dataset.pathB}&max_hops=5`);
      const container = btn.closest(".hypothesis-card").querySelector('[id^="path-"]');
      container.innerHTML = paths.length ? paths.map(p => `
        <div class="muted" style="font-size:12px;border-top:1px solid var(--border);padding-top:8px;margin-top:6px;">
          ${p.steps.map(s => `${s.from_label} —${s.relationship}→ ${s.to_label}`).join(" · ")}
        </div>
      `).join("") : `<div class="muted">No direct path found within 5 hops.</div>`;
    };
  });
}
