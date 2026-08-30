import graph_engine as ge
from datetime import datetime

DISCLAIMER = ("AI-generated hypotheses are investigative leads and must not be treated as "
              "established facts without independent verification.")

def generate_html_report(store: ge.DataStore, G, case_id="NX-2026-041"):
    case = next((c for c in store.raw["cases"] if c["id"] == case_id), store.raw["cases"][0])
    hyps = ge.hidden_link_hypotheses(store, G)
    contras = ge.contradiction_detection(store, G)
    roles = ge.network_roles(G)[:8]
    anomalies = ge.anomaly_detection(store)[:8]
    communities = ge.communities_detail(G)

    def rows(items, cols):
        out = "<tr>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr>"
        for it in items:
            out += "<tr>" + "".join(f"<td>{it.get(c,'')}</td>" for c in cols) + "</tr>"
        return out

    hyp_rows = "".join(
        f"<tr><td>{h['entity_a_name']} ↔ {h['entity_b_name']}</td><td>{round(h['confidence']*100)}%</td>"
        f"<td>{h['status']}</td><td>{'; '.join(h['supporting_evidence'])}</td>"
        f"<td>{'; '.join(h['contradicting_evidence']) or '—'}</td></tr>" for h in hyps)

    contra_rows = "".join(
        f"<tr><td>{c['entity_name']}</td><td>{c['record_1']['location']} @ {c['record_1']['timestamp']}</td>"
        f"<td>{c['record_2']['location']} @ {c['record_2']['timestamp']}</td><td>{c['confidence']}</td></tr>" for c in contras)

    role_rows = "".join(
        f"<tr><td>{r['entity_name']}</td><td>{r['role'].replace('_',' ').title()}</td>"
        f"<td>{r['betweenness_centrality']}</td><td>{r['reason']}</td></tr>" for r in roles)

    anomaly_rows = "".join(
        f"<tr><td>{a['type'].replace('_',' ').title()}</td><td>{a['severity']}</td><td>{a['reason']}</td></tr>" for a in anomalies)

    community_rows = "".join(
        f"<tr><td>{c['name']}</td><td>{c['size']}</td><td>{c['central_entity']['name'] if c['central_entity'] else '—'}</td></tr>" for c in communities)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>NEXUS-X Investigation Report — {case_id}</title>
<style>
body {{ font-family: 'Segoe UI', Arial, sans-serif; background:#0b0e14; color:#e6e9ef; margin:0; padding:40px; }}
h1 {{ color:#4fd1c5; border-bottom:2px solid #1f2733; padding-bottom:12px; }}
h2 {{ color:#8ab4f8; margin-top:36px; }}
table {{ width:100%; border-collapse:collapse; margin-top:10px; font-size:13px;}}
th, td {{ border:1px solid #263042; padding:8px 10px; text-align:left; }}
th {{ background:#141a24; color:#9aa5b1; }}
.disclaimer {{ background:#2a1f14; border:1px solid #6b4a1e; color:#f0c987; padding:14px; border-radius:6px; margin-top:24px;}}
.meta {{ color:#7f8ca0; font-size:13px; }}
.badge {{ display:inline-block; padding:2px 8px; border-radius:10px; font-size:11px; background:#1f2733; color:#4fd1c5; }}
</style></head><body>
<h1>NEXUS-X — Investigation Intelligence Report</h1>
<p class="meta">Case: <b>{case['id']} — {case['title']}</b> | Generated: {datetime.now().isoformat()} | Status: {case['status']} | Risk: {case['risk_level']}</p>
<p>{case['description']}</p>

<h2>1. Case Summary</h2>
<p>Assigned investigator: {case['assigned_investigator']} · Priority: {case['priority']} · Created: {case['created']}</p>

<h2>2. Entities Analyzed</h2>
<p>{len(store.raw['people'])} people, {len(store.raw['phones'])} phones, {len(store.raw['vehicles'])} vehicles,
{len(store.raw['accounts'])} accounts, {len(store.raw['locations'])} locations, {len(store.raw['organizations'])} organizations.</p>

<h2>3. AI Hypotheses (Hidden-Link Engine)</h2>
<table><tr><th>Entities</th><th>Confidence</th><th>Status</th><th>Supporting</th><th>Contradicting</th></tr>{hyp_rows}</table>

<h2>4. Contradictions Detected</h2>
<table><tr><th>Entity</th><th>Record 1</th><th>Record 2</th><th>Confidence</th></tr>{contra_rows or '<tr><td colspan=4>None detected</td></tr>'}</table>

<h2>5. Network Role Analysis</h2>
<table><tr><th>Entity</th><th>Role</th><th>Betweenness</th><th>Reason</th></tr>{role_rows}</table>

<h2>6. Communities Detected</h2>
<table><tr><th>Cluster</th><th>Size</th><th>Central Entity</th></tr>{community_rows}</table>

<h2>7. Anomalies</h2>
<table><tr><th>Type</th><th>Severity</th><th>Reason</th></tr>{anomaly_rows or '<tr><td colspan=3>None detected</td></tr>'}</table>

<h2>8. Investigator Notes</h2>
<p><i>(Space reserved for investigator annotations — not auto-populated by AI.)</i></p>

<div class="disclaimer"><b>Disclaimer:</b> {DISCLAIMER}</div>
</body></html>"""
    return html
