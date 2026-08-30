"""
NEXUS-X Graph Engine
--------------------
All analytics here are deterministic, explainable, and derived from the
synthetic dataset — there is no black-box / random confidence generation.

Design note: this module is written against a small internal Repository
interface (DataStore) so the underlying implementation could be swapped
for Neo4j later without touching the analysis functions below.
"""
import os
import json
import math
from datetime import datetime
from itertools import combinations
from collections import defaultdict
import networkx as nx
from rapidfuzz import fuzz

DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "dataset.json"
)

class DataStore:
    """In-memory repository over the synthetic dataset. Swappable for Neo4j later:
    every method here would become a Cypher query against a graph DB instead."""

    def __init__(self, path=DATA_PATH):
        with open(path) as f:
            self.raw = json.load(f)
        self._reviews = {}   # hypothesis_id -> review dict
        self._audit_log = []
        self._merges = []    # list of {kept, merged, note}

    def entity_lookup(self, entity_id):
        for coll in ["people", "phones", "vehicles", "accounts", "locations", "organizations"]:
            for e in self.raw[coll]:
                if e["id"] == entity_id:
                    return e
        return None

    def log(self, action, actor="investigator@nexusx.demo", case_id="NX-2026-041", obj=None):
        self._audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": action, "user": actor, "case": case_id, "object": obj
        })


def build_graph(store: DataStore) -> nx.MultiDiGraph:
    """Builds the heterogeneous knowledge graph from raw records."""
    G = nx.MultiDiGraph()
    d = store.raw

    for p in d["people"]:
        extra = {k: v for k, v in p.items() if k not in ("id", "type", "name")}
        G.add_node(p["id"], type="PERSON", label=p["name"], **extra)
    for p in d["phones"]:
        G.add_node(p["id"], type="PHONE", label=p["number"])
        if p.get("owner_id"):
            G.add_edge(p["owner_id"], p["id"], type="OWNS", status="CONFIRMED", confidence=1.0,
                       evidence=[], timestamp=None)
    for v in d["vehicles"]:
        G.add_node(v["id"], type="VEHICLE", label=v["plate"])
        if v.get("owner_id"):
            G.add_edge(v["owner_id"], v["id"], type="OWNS", status="CONFIRMED", confidence=1.0,
                       evidence=[], timestamp=None)
    for a in d["accounts"]:
        G.add_node(a["id"], type="ACCOUNT", label=a["number"])
        if a.get("holder_id"):
            G.add_edge(a["holder_id"], a["id"], type="OWNS", status="CONFIRMED", confidence=1.0,
                       evidence=[], timestamp=None)
    for l in d["locations"]:
        G.add_node(l["id"], type="LOCATION", label=l["name"], city=l["city"])
    for o in d["organizations"]:
        G.add_node(o["id"], type="ORGANIZATION", label=o["name"])
    for e in d["events"]:
        G.add_node(e["id"], type="EVENT", label=e["description"], timestamp=e["timestamp"])
        if e.get("location_id"):
            G.add_edge(e["id"], e["location_id"], type="PRESENT_AT", status="CONFIRMED", confidence=1.0,
                       evidence=[e["id"]], timestamp=e["timestamp"])
        for ent in e.get("entities", []):
            G.add_edge(ent, e["id"], type="PRESENT_AT", status="CONFIRMED", confidence=0.9,
                       evidence=[e["id"]], timestamp=e["timestamp"])

    for c in d["communications"]:
        G.add_edge(c["from_phone"], c["to_phone"], type="CALLED" if c["mode"] == "CALL" else "MESSAGED",
                   status="CONFIRMED", confidence=1.0, evidence=[c["id"]], timestamp=c["timestamp"],
                   duration=c.get("duration_sec"))
    for t in d["transactions"]:
        G.add_edge(t["from_account"], t["to_account"], type="TRANSFERRED_TO", status="CONFIRMED",
                   confidence=1.0, evidence=[t["id"]], timestamp=t["timestamp"], amount=t["amount"])

    return G


def entity_neighbors_people(G, person_id):
    """1-hop person-relevant neighborhood via owned phone/account/vehicle expansion (2-hop through device)."""
    neighbors = set()
    for _, dev, data in G.out_edges(person_id, data=True):
        if data.get("type") == "OWNS":
            for _, other, edata in G.out_edges(dev, data=True):
                if edata.get("type") in ("CALLED", "MESSAGED", "TRANSFERRED_TO"):
                    owner = _find_owner(G, other)
                    if owner and owner != person_id:
                        neighbors.add(owner)
            for other, _, edata in G.in_edges(dev, data=True):
                if edata.get("type") in ("CALLED", "MESSAGED", "TRANSFERRED_TO"):
                    owner = _find_owner(G, other)
                    if owner and owner != person_id:
                        neighbors.add(owner)
    return neighbors


def _find_owner(G, device_id):
    for owner, _, data in G.in_edges(device_id, data=True):
        if data.get("type") == "OWNS":
            return owner
    return None


def person_locations(G, person_id):
    locs = set()
    for _, ev, data in G.out_edges(person_id, data=True):
        if data.get("type") == "PRESENT_AT" and G.nodes[ev].get("type") == "EVENT":
            for _, loc, edata in G.out_edges(ev, data=True):
                if edata.get("type") == "PRESENT_AT":
                    locs.add(loc)
    return locs


def person_graph_projection(G):
    """Project the heterogeneous graph onto a simple Person-Person graph for centrality/community analysis,
    with an edge whenever two people share a device-mediated communication, financial transfer, or location."""
    P = nx.Graph()
    people = [n for n, d in G.nodes(data=True) if d.get("type") == "PERSON"]
    P.add_nodes_from(people)
    for p in people:
        for q in entity_neighbors_people(G, p):
            if q in people:
                P.add_edge(p, q, reason="communication/financial link")
    # shared-location edges
    loc_map = defaultdict(set)
    for p in people:
        for l in person_locations(G, p):
            loc_map[l].add(p)
    for loc, members in loc_map.items():
        for a, b in combinations(members, 2):
            if P.has_edge(a, b):
                P[a][b]["reason"] += "+shared_location"
            else:
                P.add_edge(a, b, reason="shared_location")
    return P


# ---------------------------------------------------------------------------
# 1. ENTITY RESOLUTION
# ---------------------------------------------------------------------------
def entity_resolution(store: DataStore):
    people = store.raw["people"]
    phones = store.raw["phones"]
    candidates = []
    for a, b in combinations(people, 2):
        name_sim = fuzz.token_sort_ratio(a["name"], b["name"]) / 100.0
        if name_sim < 0.55:
            continue
        reasons = []
        score = 0.0
        score += name_sim * 0.4
        reasons.append(f"Name similarity {round(name_sim*100)}%")
        a_phones = {p["number"] for p in phones if p["owner_id"] == a["id"]}
        b_phones = {p["number"] for p in phones if p["owner_id"] == b["id"]}
        if a_phones & b_phones:
            score += 0.35
            reasons.append("Same phone number")
        if a["city"] == b["city"]:
            score += 0.15
            reasons.append("Same city/address area")
        if abs(a["age"] - b["age"]) <= 1:
            score += 0.10
            reasons.append("Consistent age profile")
        if score >= 0.55:
            candidates.append({
                "entity_a": a["id"], "entity_a_name": a["name"],
                "entity_b": b["id"], "entity_b_name": b["name"],
                "confidence": round(min(score, 0.99), 2),
                "reasons": reasons,
                "status": store._reviews.get(f"ER-{a['id']}-{b['id']}", {}).get("status", "PENDING_REVIEW"),
            })
    candidates.sort(key=lambda c: -c["confidence"])
    return candidates


# ---------------------------------------------------------------------------
# 2. HIDDEN-LINK HYPOTHESIS ENGINE
# ---------------------------------------------------------------------------
WEIGHTS = {
    "common_neighbors": 0.25,
    "temporal_overlap": 0.20,
    "shared_locations": 0.20,
    "communication_correlation": 0.15,
    "financial_correlation": 0.10,
    "source_reliability": 0.10,
}

def _adamic_adar(P, a, b):
    common = set(P.neighbors(a)) & set(P.neighbors(b)) if a in P and b in P else set()
    score = 0.0
    for w in common:
        deg = P.degree(w)
        if deg > 1:
            score += 1 / math.log(deg)
    return score, common

def hidden_link_hypotheses(store: DataStore, G, top_n=8):
    P = person_graph_projection(G)
    people_ids = [n for n, d in G.nodes(data=True) if d.get("type") == "PERSON"]
    hypotheses = []
    seen_pairs = set()

    for a, b in combinations(people_ids, 2):
        if P.has_edge(a, b):
            continue  # only interested in NON-adjacent pairs (hidden links)
        aa_score, common = _adamic_adar(P, a, b)
        if not common:
            continue
        jaccard = len(common) / max(1, len(set(P.neighbors(a)) | set(P.neighbors(b)))) if a in P and b in P else 0

        # shared locations
        loc_a, loc_b = person_locations(G, a), person_locations(G, b)
        shared_locs = loc_a & loc_b

        # temporal overlap: events at shared location within +/- 7 days of each other
        temporal_hits = 0
        if shared_locs:
            ev_a = [G.nodes[ev].get("timestamp") for _, ev, ed in G.out_edges(a, data=True)
                    if ed.get("type") == "PRESENT_AT" and any(
                        edata.get("type") == "PRESENT_AT" and loc in shared_locs
                        for _, loc, edata in G.out_edges(ev, data=True))]
            ev_b = [G.nodes[ev].get("timestamp") for _, ev, ed in G.out_edges(b, data=True)
                    if ed.get("type") == "PRESENT_AT" and any(
                        edata.get("type") == "PRESENT_AT" and loc in shared_locs
                        for _, loc, edata in G.out_edges(ev, data=True))]
            for ta in ev_a:
                for tb in ev_b:
                    if ta and tb:
                        try:
                            dt = abs((datetime.fromisoformat(ta) - datetime.fromisoformat(tb)).days)
                            if dt <= 7:
                                temporal_hits += 1
                        except Exception:
                            pass

        if len(common) == 0 and not shared_locs:
            continue

        common_neighbors_score = min(1.0, len(common) / 3)
        temporal_score = min(1.0, temporal_hits / 2)
        shared_loc_score = min(1.0, len(shared_locs) / 2)
        comm_corr_score = min(1.0, jaccard * 2)
        financial_corr_score = 0.5 if _financial_correlated(store, G, a, b) else 0.0
        source_reliability_score = 0.8  # synthetic demo baseline; would derive from source metadata in prod

        final = (WEIGHTS["common_neighbors"] * common_neighbors_score +
                 WEIGHTS["temporal_overlap"] * temporal_score +
                 WEIGHTS["shared_locations"] * shared_loc_score +
                 WEIGHTS["communication_correlation"] * comm_corr_score +
                 WEIGHTS["financial_correlation"] * financial_corr_score +
                 WEIGHTS["source_reliability"] * source_reliability_score)

        if final < 0.25:
            continue

        supporting = []
        for w in list(common)[:3]:
            supporting.append(f"Common intermediary: {G.nodes[w].get('label', w)}")
        for loc in list(shared_locs)[:2]:
            supporting.append(f"Shared location: {G.nodes[loc].get('label', loc)}")

        contradicting = []
        if not _has_direct_comm(G, a, b):
            contradicting.append("No direct communication record found between the two entities")

        missing = ["Device ownership confirmation during overlapping location events",
                   "Independent verification of financial correlation window"]

        pair_key = tuple(sorted([a, b]))
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)

        hypotheses.append({
            "id": f"HYP-{a}-{b}",
            "entity_a": a, "entity_a_name": G.nodes[a].get("label"),
            "entity_b": b, "entity_b_name": G.nodes[b].get("label"),
            "confidence": round(min(final, 0.97), 2),
            "score_breakdown": {
                "common_neighbors": round(common_neighbors_score, 2),
                "temporal_overlap": round(temporal_score, 2),
                "shared_locations": round(shared_loc_score, 2),
                "communication_correlation": round(comm_corr_score, 2),
                "financial_correlation": round(financial_corr_score, 2),
                "source_reliability": round(source_reliability_score, 2),
                "weights": WEIGHTS,
            },
            "supporting_evidence": supporting,
            "contradicting_evidence": contradicting,
            "missing_evidence": missing,
            "status": store._reviews.get(f"HYP-{a}-{b}", {}).get("status", "INVESTIGATIVE_HYPOTHESIS"),
            "explanation": (f"{len(common)} common intermediar{'y' if len(common)==1 else 'ies'}, "
                             f"{len(shared_locs)} shared location(s), "
                             f"{temporal_hits} temporally-correlated event pair(s) detected."),
        })

    hypotheses.sort(key=lambda h: -h["confidence"])
    return hypotheses[:top_n]


def _financial_correlated(store, G, a, b):
    a_accts = [x["id"] for x in store.raw["accounts"] if x["holder_id"] == a]
    b_accts = [x["id"] for x in store.raw["accounts"] if x["holder_id"] == b]
    # correlated if any two txns touching a's/b's account graph neighborhood occur within 5 days
    times = []
    for t in store.raw["transactions"]:
        if t["from_account"] in a_accts or t["to_account"] in a_accts:
            times.append(("a", datetime.fromisoformat(t["timestamp"])))
        if t["from_account"] in b_accts or t["to_account"] in b_accts:
            times.append(("b", datetime.fromisoformat(t["timestamp"])))
    a_times = [t for tag, t in times if tag == "a"]
    b_times = [t for tag, t in times if tag == "b"]
    for ta in a_times:
        for tb in b_times:
            if abs((ta - tb).days) <= 5:
                return True
    return False


def _has_direct_comm(G, a, b):
    a_phones = [n for _, n, d in G.out_edges(a, data=True) if d.get("type") == "OWNS" and G.nodes[n]["type"] == "PHONE"]
    b_phones = [n for _, n, d in G.out_edges(b, data=True) if d.get("type") == "OWNS" and G.nodes[n]["type"] == "PHONE"]
    for pa in a_phones:
        for pb in b_phones:
            if G.has_edge(pa, pb) or G.has_edge(pb, pa):
                return True
    return False


# ---------------------------------------------------------------------------
# 3. CONTRADICTION DETECTION
# ---------------------------------------------------------------------------
def contradiction_detection(store: DataStore, G):
    contradictions = []
    people = [n for n, d in G.nodes(data=True) if d.get("type") == "PERSON"]
    for p in people:
        sightings = []
        for _, ev, ed in G.out_edges(p, data=True):
            if ed.get("type") == "PRESENT_AT" and G.nodes[ev].get("type") == "EVENT":
                ts = G.nodes[ev].get("timestamp")
                for _, loc, edata in G.out_edges(ev, data=True):
                    if edata.get("type") == "PRESENT_AT" and G.nodes[loc].get("type") == "LOCATION":
                        sightings.append((ts, loc, ev))
        for (t1, l1, e1), (t2, l2, e2) in combinations(sightings, 2):
            if l1 == l2:
                continue
            try:
                dt = abs((datetime.fromisoformat(t1) - datetime.fromisoformat(t2)).total_seconds()) / 60
            except Exception:
                continue
            if dt <= 60:  # within an hour, different locations -> conflict
                contradictions.append({
                    "id": f"CONTRA-{p}-{e1}-{e2}",
                    "entity": p, "entity_name": G.nodes[p].get("label"),
                    "record_1": {"location": G.nodes[l1].get("label"), "timestamp": t1, "event": e1},
                    "record_2": {"location": G.nodes[l2].get("label"), "timestamp": t2, "event": e2},
                    "minutes_apart": round(dt),
                    "possible_explanations": [
                        "Incorrect entity resolution (two different people merged)",
                        "Timestamp inconsistency in source record",
                        "Shared device between two individuals",
                        "Source-data transcription error",
                    ],
                    "confidence": "HIGH" if dt <= 30 else "MEDIUM",
                    "status": store._reviews.get(f"CONTRA-{p}-{e1}-{e2}", {}).get("status", "REVIEW_REQUIRED"),
                })
    return contradictions


# ---------------------------------------------------------------------------
# 4. NETWORK ROLE DISCOVERY
# ---------------------------------------------------------------------------
def network_roles(G):
    P = person_graph_projection(G)
    if P.number_of_nodes() == 0:
        return []
    degree_c = nx.degree_centrality(P)
    between_c = nx.betweenness_centrality(P)
    try:
        pagerank = nx.pagerank(P)
    except Exception:
        pagerank = {n: 0 for n in P.nodes()}

    communities = list(nx.community.greedy_modularity_communities(P)) if P.number_of_edges() > 0 else []
    comm_of = {}
    for idx, c in enumerate(communities):
        for n in c:
            comm_of[n] = idx

    roles = []
    for n in P.nodes():
        deg = degree_c.get(n, 0)
        bet = between_c.get(n, 0)
        pr = pagerank.get(n, 0)
        if bet > 0.15:
            role = "BRIDGE_NODE"
            reason = "Connects otherwise weakly-connected communities."
        elif deg > 0.25 and pr > (sum(pagerank.values()) / max(1, len(pagerank))) * 1.5:
            role = "CENTRAL_NODE"
            reason = "High degree and PageRank relative to network average."
        elif P.degree(n) == 0:
            role = "ISOLATED_NODE"
            reason = "No detected connections in the current graph."
        elif P.degree(n) <= 1:
            role = "PERIPHERAL_NODE"
            reason = "Minimal connectivity to the rest of the network."
        elif bet > 0.05:
            role = "BROKER"
            reason = "Sits on several shortest paths between other entities."
        else:
            role = "COMMUNITY_CONNECTOR"
            reason = "Well connected within its own community cluster."
        roles.append({
            "entity": n, "entity_name": G.nodes[n].get("label"),
            "role": role, "reason": reason,
            "degree_centrality": round(deg, 3),
            "betweenness_centrality": round(bet, 3),
            "pagerank": round(pr, 3),
            "community": comm_of.get(n),
        })
    roles.sort(key=lambda r: -r["betweenness_centrality"])
    return roles


def communities_detail(G):
    P = person_graph_projection(G)
    if P.number_of_edges() == 0:
        return []
    communities = list(nx.community.greedy_modularity_communities(P))
    greek = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta"]
    between_c = nx.betweenness_centrality(P)
    result = []
    for idx, c in enumerate(communities):
        members = list(c)
        central = max(members, key=lambda n: between_c.get(n, 0)) if members else None
        result.append({
            "id": f"cluster_{greek[idx % len(greek)].lower()}",
            "name": f"Cluster {greek[idx % len(greek)]}",
            "size": len(members),
            "members": [{"id": m, "name": G.nodes[m].get("label")} for m in members],
            "central_entity": {"id": central, "name": G.nodes[central].get("label")} if central else None,
        })
    return result


# ---------------------------------------------------------------------------
# 5. COUNTERFACTUAL SIMULATOR
# ---------------------------------------------------------------------------
def counterfactual_removal(G, node_id):
    P = person_graph_projection(G)
    if node_id not in P:
        return {"error": "entity not found in person-projection graph"}

    def stats(graph):
        comps = list(nx.connected_components(graph))
        density = nx.density(graph)
        try:
            largest = max(comps, key=len)
            sub = graph.subgraph(largest)
            avg_path = nx.average_shortest_path_length(sub) if len(largest) > 1 else 0
        except Exception:
            avg_path = None
        between_c = nx.betweenness_centrality(graph) if graph.number_of_nodes() > 0 else {}
        top_bridge = max(between_c, key=between_c.get) if between_c else None
        return {
            "components": len(comps),
            "density": round(density, 4),
            "avg_shortest_path": round(avg_path, 3) if avg_path is not None else None,
            "top_bridge": {"id": top_bridge, "name": G.nodes[top_bridge].get("label")} if top_bridge else None,
        }

    before = stats(P)
    P2 = P.copy()
    P2.remove_node(node_id)
    after = stats(P2)

    fragmentation_pct = round(((after["components"] - before["components"]) / max(1, before["components"])) * 100, 1)

    # alternative paths: for each pair that was connected only through node_id, check if still connected
    alt_paths = 0
    neighbors = list(P.neighbors(node_id))
    for x, y in combinations(neighbors, 2):
        if P2.has_node(x) and P2.has_node(y) and nx.has_path(P2, x, y):
            alt_paths += 1

    interpretation = (
        f"Removing {G.nodes[node_id].get('label')} changes network components from {before['components']} to "
        f"{after['components']} ({'+' if fragmentation_pct>=0 else ''}{fragmentation_pct}% fragmentation). "
        f"This node appears {'structurally important' if fragmentation_pct > 20 else 'to have limited structural impact'} "
        f"for connectivity in the observed network. This is a structural observation only — it is not an "
        f"operational recommendation."
    )

    return {
        "removed_entity": {"id": node_id, "name": G.nodes[node_id].get("label")},
        "before": before,
        "after": after,
        "fragmentation_pct": fragmentation_pct,
        "alternative_paths_preserved": alt_paths,
        "new_bridge_candidate": after["top_bridge"],
        "interpretation": interpretation,
    }


# ---------------------------------------------------------------------------
# 6. PATH FINDER
# ---------------------------------------------------------------------------
def find_paths(G, source, target, max_hops=4):
    try:
        UG = G.to_undirected()
        all_paths = list(nx.all_simple_paths(UG, source, target, cutoff=max_hops))
    except (nx.NodeNotFound, nx.NetworkXNoPath):
        return []
    results = []
    for path in all_paths[:10]:
        steps = []
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            edge_data = None
            if G.has_edge(u, v):
                edge_data = list(G.get_edge_data(u, v).values())[0]
            elif G.has_edge(v, u):
                edge_data = list(G.get_edge_data(v, u).values())[0]
            steps.append({
                "from": u, "from_label": G.nodes[u].get("label"),
                "to": v, "to_label": G.nodes[v].get("label"),
                "relationship": edge_data.get("type") if edge_data else "RELATED_TO",
                "evidence": edge_data.get("evidence", []) if edge_data else [],
                "timestamp": edge_data.get("timestamp") if edge_data else None,
            })
        results.append({"length": len(path) - 1, "steps": steps})
    results.sort(key=lambda r: r["length"])
    return results


# ---------------------------------------------------------------------------
# 7. ANOMALY DETECTION
# ---------------------------------------------------------------------------
def anomaly_detection(store: DataStore):
    d = store.raw
    anomalies = []
    amounts = [t["amount"] for t in d["transactions"]]
    mean = sum(amounts) / len(amounts)
    std = (sum((x - mean) ** 2 for x in amounts) / len(amounts)) ** 0.5
    for t in d["transactions"]:
        if std > 0 and (t["amount"] - mean) / std > 1.8:
            anomalies.append({
                "id": f"ANOM-{t['id']}", "type": "UNUSUAL_TRANSACTION_AMOUNT",
                "severity": "HIGH" if (t["amount"] - mean) / std > 2.5 else "MEDIUM",
                "timestamp": t["timestamp"],
                "entities": [t["from_account"], t["to_account"]],
                "reason": f"Transaction amount ₹{t['amount']} is {round((t['amount']-mean)/std,1)} std-dev above network mean (₹{round(mean)}).",
                "source_evidence": [t["id"]],
                "confidence": round(min(0.95, 0.6 + (t["amount"] - mean) / std * 0.1), 2),
            })

    # communication spike: phone with unusually high comm count
    counts = defaultdict(int)
    for c in d["communications"]:
        counts[c["from_phone"]] += 1
    if counts:
        cmean = sum(counts.values()) / len(counts)
        for phone, cnt in counts.items():
            if cnt > cmean * 2.2:
                anomalies.append({
                    "id": f"ANOM-COMM-{phone}", "type": "COMMUNICATION_SPIKE",
                    "severity": "MEDIUM",
                    "timestamp": None,
                    "entities": [phone],
                    "reason": f"{cnt} outgoing communications vs network average of {round(cmean,1)}.",
                    "source_evidence": [c["id"] for c in d["communications"] if c["from_phone"] == phone][:5],
                    "confidence": 0.72,
                })
    anomalies.sort(key=lambda a: -a["confidence"])
    return anomalies


# ---------------------------------------------------------------------------
# 8. TEMPORAL RECONSTRUCTION
# ---------------------------------------------------------------------------
def timeline_snapshot(store: DataStore, G, up_to_date: str):
    """Return the subgraph of relationships/events active up to a given ISO date."""
    cutoff = datetime.fromisoformat(up_to_date)
    active_edges = []
    for u, v, data in G.edges(data=True):
        ts = data.get("timestamp")
        if ts is None:
            active_edges.append((u, v, data))  # structural (OWNS) edges always active
            continue
        try:
            if datetime.fromisoformat(ts) <= cutoff:
                active_edges.append((u, v, data))
        except Exception:
            active_edges.append((u, v, data))
    active_nodes = set()
    for u, v, _ in active_edges:
        active_nodes.add(u)
        active_nodes.add(v)
    return {
        "as_of": up_to_date,
        "node_count": len(active_nodes),
        "edge_count": len(active_edges),
        "nodes": [{"id": n, "type": G.nodes[n].get("type"), "label": G.nodes[n].get("label")} for n in active_nodes],
        "edges": [{"from": u, "to": v, "type": d.get("type"), "status": d.get("status", "CONFIRMED"),
                    "timestamp": d.get("timestamp")} for u, v, d in active_edges],
    }


def detect_structural_events(store: DataStore, G):
    """Scan month-by-month snapshots for a jump in a person's betweenness centrality (bridge emergence)."""
    months = ["2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30", "2026-05-31"]
    events = []
    prev_roles = {}
    for m in months:
        snap = timeline_snapshot(store, G, m)
        SG = nx.MultiDiGraph()
        for n in snap["nodes"]:
            SG.add_node(n["id"], type=n["type"], label=n["label"])
        for e in snap["edges"]:
            SG.add_edge(e["from"], e["to"], type=e["type"])
        P = person_graph_projection(SG)
        if P.number_of_nodes() > 1:
            bet = nx.betweenness_centrality(P)
        else:
            bet = {}
        for node, score in bet.items():
            prev = prev_roles.get(node, 0)
            if score - prev > 0.15:
                events.append({
                    "date": m,
                    "entity": node,
                    "entity_name": G.nodes[node].get("label"),
                    "description": f"{G.nodes[node].get('label')} became a structural bridge between previously "
                                    f"weakly-connected communities.",
                    "betweenness_before": round(prev, 3),
                    "betweenness_after": round(score, 3),
                })
        prev_roles = bet
    return events
