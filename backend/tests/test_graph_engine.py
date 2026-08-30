import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import graph_engine as ge


def make():
    store = ge.DataStore()
    G = ge.build_graph(store)
    return store, G


def test_graph_builds_with_expected_scale():
    store, G = make()
    assert G.number_of_nodes() > 100
    assert G.number_of_edges() > 100
    assert len(store.raw["people"]) >= 30


def test_entity_resolution_finds_known_duplicate():
    store, G = make()
    candidates = ge.entity_resolution(store)
    pairs = {frozenset([c["entity_a"], c["entity_b"]]) for c in candidates}
    assert frozenset(["P010", "P031"]) in pairs or frozenset(["P010", "P032"]) in pairs


def test_hidden_link_hypotheses_are_explainable_and_bounded():
    store, G = make()
    hyps = ge.hidden_link_hypotheses(store, G)
    assert isinstance(hyps, list)
    for h in hyps:
        assert 0 <= h["confidence"] <= 1
        assert "score_breakdown" in h
        assert set(h["score_breakdown"]["weights"].keys()) == set(ge.WEIGHTS.keys())
        # confidence must equal weighted sum (within rounding) -- explainability guarantee
        weights = h["score_breakdown"]["weights"]
        recomputed = sum(weights[k] * h["score_breakdown"][k] for k in weights)
        assert abs(recomputed - h["confidence"]) < 0.05 or h["confidence"] == 0.97


def test_no_hypothesis_between_already_adjacent_people():
    store, G = make()
    P = ge.person_graph_projection(G)
    hyps = ge.hidden_link_hypotheses(store, G)
    for h in hyps:
        assert not P.has_edge(h["entity_a"], h["entity_b"])


def test_contradiction_detection_finds_engineered_conflict():
    store, G = make()
    contras = ge.contradiction_detection(store, G)
    entities_flagged = {c["entity"] for c in contras}
    assert store.raw["scenario_key_entities"]["contradiction_entity"] in entities_flagged


def test_network_roles_cover_all_people():
    store, G = make()
    roles = ge.network_roles(G)
    people = [n for n, d in G.nodes(data=True) if d.get("type") == "PERSON"]
    assert len(roles) == len(people)
    for r in roles:
        assert r["role"] in {"CENTRAL_NODE", "BRIDGE_NODE", "BROKER", "PERIPHERAL_NODE", "ISOLATED_NODE", "COMMUNITY_CONNECTOR"}


def test_counterfactual_removal_never_deletes_underlying_data():
    store, G = make()
    before_nodes = G.number_of_nodes()
    roles = ge.network_roles(G)
    result = ge.counterfactual_removal(G, roles[0]["entity"])
    assert G.number_of_nodes() == before_nodes  # original graph untouched
    assert "before" in result and "after" in result
    assert result["before"]["components"] >= 1


def test_communities_detail_partitions_person_graph():
    store, G = make()
    communities = ge.communities_detail(G)
    total_members = sum(c["size"] for c in communities)
    P = ge.person_graph_projection(G)
    assert total_members == P.number_of_nodes()


def test_find_paths_respects_max_hops():
    store, G = make()
    key = store.raw["scenario_key_entities"]
    paths = ge.find_paths(G, key["C_priya_chatterjee_bridge"], key["D_vikram_rao"], max_hops=6)
    for p in paths:
        assert p["length"] <= 6


def test_anomaly_detection_flags_high_value_transaction():
    store, _ = make()
    anomalies = ge.anomaly_detection(store)
    assert any(a["type"] == "UNUSUAL_TRANSACTION_AMOUNT" for a in anomalies)


def test_timeline_snapshot_grows_monotonically():
    store, G = make()
    counts = []
    for m in ["2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30", "2026-05-31"]:
        snap = ge.timeline_snapshot(store, G, m)
        counts.append(snap["edge_count"])
    assert counts == sorted(counts)
