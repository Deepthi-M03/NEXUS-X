"""
NEXUS-X Investigation Copilot
-----------------------------
A deterministic query parser that answers a fixed set of investigator
question patterns using ONLY the loaded case graph/data. This guarantees
the demo works fully offline with zero LLM dependency.

If ANTHROPIC_API_KEY (or another LLM key) is set as an environment variable,
main.py may optionally use it to translate free-text into one of the intents
below -- but the LLM is never allowed to invent graph facts; it only selects
an intent + entities, and this module still does all the actual answering.
"""
import re
import graph_engine as ge


def answer(query: str, store: ge.DataStore, G):
    q = query.lower().strip()

    # -- "why is X structurally important" ------------------------------
    m = re.search(r"why is ([a-z .]+?) (structurally important|a bridge|important)", q)
    if m:
        name = m.group(1).strip()
        roles = ge.network_roles(G)
        match = _find_by_name(roles, name)
        if match:
            return {
                "answer": f"{match['entity_name']} is classified as a {match['role'].replace('_',' ').title()}. {match['reason']}",
                "confidence": "Derived directly from graph centrality metrics (not a probabilistic guess).",
                "evidence": [f"Betweenness centrality: {match['betweenness_centrality']}",
                             f"Degree centrality: {match['degree_centrality']}",
                             f"PageRank: {match['pagerank']}"],
                "source_records": [],
            }
        return _not_found(name)

    # -- "show all paths between X and Y" --------------------------------
    m = re.search(r"paths? between ([a-z .]+?) and ([a-z .]+)", q)
    if m:
        a_name, b_name = m.group(1).strip(), m.group(2).strip()
        a_id = _resolve_person(G, a_name)
        b_id = _resolve_person(G, b_name)
        if not a_id or not b_id:
            return _not_found(a_name if not a_id else b_name)
        paths = ge.find_paths(G, a_id, b_id, max_hops=5)
        if not paths:
            return {"answer": f"No path found between {a_name.title()} and {b_name.title()} within 5 hops in the current graph.",
                    "confidence": "N/A", "evidence": [], "source_records": []}
        best = paths[0]
        desc = " → ".join([f"{s['from_label']} --{s['relationship']}--> {s['to_label']}" for s in best["steps"]])
        return {
            "answer": f"Found {len(paths)} path(s) between {a_name.title()} and {b_name.title()}. Shortest ({best['length']} hops): {desc}",
            "confidence": "Structural result from the current graph; not an inference.",
            "evidence": [e for s in best["steps"] for e in s["evidence"]],
            "source_records": [e for s in best["steps"] for e in s["evidence"]],
        }

    # -- "what changed after <date>" --------------------------------------
    m = re.search(r"chang(?:ed|es).*(?:after|since)\s+([a-z0-9 ,]+)", q)
    if m:
        events = ge.detect_structural_events(store, G)
        if not events:
            return {"answer": "No significant structural changes were detected in the analyzed time window.",
                    "confidence": "N/A", "evidence": [], "source_records": []}
        lines = [f"{e['date']}: {e['description']} (betweenness {e['betweenness_before']} → {e['betweenness_after']})" for e in events]
        return {"answer": "Detected structural network changes:\n" + "\n".join(lines),
                "confidence": "Derived from month-over-month centrality recomputation.",
                "evidence": [e["entity"] for e in events], "source_records": []}

    # -- "which hypotheses have contradictory evidence" --------------------
    if "contradictory evidence" in q or ("hypothes" in q and "contradict" in q):
        hyps = ge.hidden_link_hypotheses(store, G)
        flagged = [h for h in hyps if h["contradicting_evidence"]]
        if not flagged:
            return {"answer": "No current hypotheses have contradicting evidence on file.",
                    "confidence": "N/A", "evidence": [], "source_records": []}
        lines = [f"{h['entity_a_name']} ↔ {h['entity_b_name']} ({round(h['confidence']*100)}%): {'; '.join(h['contradicting_evidence'])}" for h in flagged]
        return {"answer": "Hypotheses with contradicting evidence:\n" + "\n".join(lines),
                "confidence": "Directly read from stored hypothesis records.",
                "evidence": [h["id"] for h in flagged], "source_records": []}

    # -- "which entities connect cluster X and cluster Y" ------------------
    m = re.search(r"connect(?:s)? cluster ([a-z]+) and cluster ([a-z]+)", q)
    if m:
        c1, c2 = m.group(1), m.group(2)
        communities = ge.communities_detail(G)
        members1 = _members_of(communities, c1)
        members2 = _members_of(communities, c2)
        if members1 is None or members2 is None:
            return {"answer": f"Could not find both Cluster {c1.title()} and Cluster {c2.title()} in the current community detection results.",
                    "confidence": "N/A", "evidence": [], "source_records": []}
        P = ge.person_graph_projection(G)
        bridges = []
        for m1 in members1:
            for neighbor in P.neighbors(m1) if m1 in P else []:
                if neighbor in members2:
                    bridges.append((m1, neighbor))
        if not bridges:
            return {"answer": f"No direct bridging entities found between Cluster {c1.title()} and Cluster {c2.title()} in the current graph.",
                    "confidence": "N/A", "evidence": [], "source_records": []}
        lines = [f"{G.nodes[a].get('label')} ↔ {G.nodes[b].get('label')}" for a, b in bridges]
        return {"answer": f"Entities bridging Cluster {c1.title()} and Cluster {c2.title()}:\n" + "\n".join(lines),
                "confidence": "Structural graph adjacency result.", "evidence": [], "source_records": []}

    # -- "high-confidence hypotheses above N%" ------------------------------
    m = re.search(r"above (\d+)%", q)
    if m and "hypothes" in q:
        threshold = int(m.group(1)) / 100
        hyps = ge.hidden_link_hypotheses(store, G)
        flagged = [h for h in hyps if h["confidence"] >= threshold]
        if not flagged:
            return {"answer": f"No hypotheses currently exceed {m.group(1)}% confidence.",
                    "confidence": "N/A", "evidence": [], "source_records": []}
        lines = [f"{h['entity_a_name']} ↔ {h['entity_b_name']}: {round(h['confidence']*100)}%" for h in flagged]
        return {"answer": f"Hypotheses above {m.group(1)}% confidence:\n" + "\n".join(lines),
                "confidence": "Directly read from stored hypothesis confidence scores.",
                "evidence": [h["id"] for h in flagged], "source_records": []}

    # -- "which records support the relationship between X and Y" ---------
    m = re.search(r"records? support.*between ([a-z .]+?) and ([a-z .]+)", q)
    if m:
        a_name, b_name = m.group(1).strip(), m.group(2).strip()
        a_id, b_id = _resolve_person(G, a_name), _resolve_person(G, b_name)
        if not a_id or not b_id:
            return _not_found(a_name if not a_id else b_name)
        hyps = ge.hidden_link_hypotheses(store, G)
        match = next((h for h in hyps if {h["entity_a"], h["entity_b"]} == {a_id, b_id}), None)
        if match:
            return {"answer": f"Supporting evidence for {a_name.title()} ↔ {b_name.title()}: " + "; ".join(match["supporting_evidence"]),
                    "confidence": f"{round(match['confidence']*100)}% (hypothesis, not confirmed fact)",
                    "evidence": match["supporting_evidence"], "source_records": []}
        paths = ge.find_paths(G, a_id, b_id, max_hops=4)
        if paths:
            ev = [e for s in paths[0]["steps"] for e in s["evidence"]]
            return {"answer": f"No standing hypothesis, but a graph path exists supported by records: {', '.join(ev) if ev else 'structural ownership links'}.",
                    "confidence": "Structural, not probabilistic.", "evidence": ev, "source_records": ev}
        return {"answer": f"No supporting records found connecting {a_name.title()} and {b_name.title()} in the current graph.",
                "confidence": "N/A", "evidence": [], "source_records": []}

    return {
        "answer": ("I can answer questions about this case's graph, such as: "
                   "'Why is <name> structurally important?', 'Show all paths between <name> and <name>', "
                   "'What changed after March 2026?', 'Which hypotheses have contradictory evidence?', "
                   "'Which entities connect Cluster Alpha and Cluster Beta?', 'Show high-confidence hypotheses above 80%'."),
        "confidence": "N/A", "evidence": [], "source_records": [],
    }


def _find_by_name(roles, name):
    name = name.strip().lower()
    best = None
    for r in roles:
        rn = r["entity_name"].lower()
        if name in rn or rn in name:
            return r
        if any(part in rn for part in name.split() if len(part) > 2):
            best = best or r
    return best


def _resolve_person(G, name):
    name = name.strip().lower()
    for n, d in G.nodes(data=True):
        if d.get("type") == "PERSON" and d.get("label", "").lower() == name:
            return n
    for n, d in G.nodes(data=True):
        if d.get("type") == "PERSON" and name in d.get("label", "").lower():
            return n
    return None


def _members_of(communities, greek):
    for c in communities:
        if greek.lower() in c["name"].lower():
            return {m["id"] for m in c["members"]}
    return None


def _not_found(name):
    return {"answer": f"Could not resolve an entity named '{name.title()}' in the current case graph.",
            "confidence": "N/A", "evidence": [], "source_records": []}
