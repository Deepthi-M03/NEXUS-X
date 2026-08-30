# NEXUS-X — Architecture

## 1. System Architecture

```mermaid
flowchart LR
    subgraph Client["Frontend (Browser)"]
        UI[Dark Command-Center SPA<br/>vanilla JS + Cytoscape.js + Chart.js]
    end
    subgraph Server["Backend (FastAPI)"]
        API[REST API Layer]
        Engine[Graph Engine<br/>NetworkX]
        Copilot[Deterministic Copilot<br/>Query Parser]
        Reports[Report Generator]
        Store[(In-Memory DataStore<br/>+ synthetic dataset.json)]
    end
    UI -- HTTP/JSON --> API
    API --> Engine
    API --> Copilot
    API --> Reports
    Engine --> Store
    Copilot --> Engine
    Reports --> Engine
```

The `DataStore` class is the single seam between the API and the underlying
data representation. Every analytics function takes a `DataStore` and/or the
built `networkx.MultiDiGraph` as input — nothing queries a specific database
engine directly. Swapping NetworkX for Neo4j later means reimplementing the
functions in `graph_engine.py` against Cypher, without touching `main.py`'s
route contracts.

## 2. Data Ingestion Pipeline

```mermaid
flowchart TD
    A[Sample doc OR uploaded TXT/CSV/JSON] --> B[Deterministic regex + dictionary NLP extractor]
    B --> C[Entity candidates: PERSON, PHONE, VEHICLE, LOCATION, DATE]
    C --> D{Investigator Review}
    D -- Accept --> E[Queued for Graph Integration]
    D -- Reject --> F[Discarded, logged to audit trail]
    D -- Edit --> C
```

## 3. AI / Analysis Pipeline

```mermaid
flowchart TD
    G[Heterogeneous Knowledge Graph] --> R1[Entity Resolution<br/>fuzzy name + phone/address overlap]
    G --> R2[Hidden-Link Hypothesis Engine<br/>Adamic-Adar, Jaccard, temporal &amp; financial correlation]
    G --> R3[Contradiction Detection<br/>conflicting location/time]
    G --> R4[Network Role Discovery<br/>centrality, betweenness, PageRank, communities]
    G --> R5[Counterfactual Simulator<br/>node removal, before/after stats]
    G --> R6[Anomaly Detection<br/>statistical z-score outliers]
    R1 & R2 & R3 & R4 & R5 & R6 --> H[Explainable, Reviewable Outputs]
```

## 4. Knowledge Graph Pipeline

```mermaid
flowchart LR
    People --> Graph
    Phones --> Graph
    Vehicles --> Graph
    Accounts --> Graph
    Locations --> Graph
    Organizations --> Graph
    Events --> Graph
    Communications -->|CALLED / MESSAGED| Graph
    Transactions -->|TRANSFERRED_TO| Graph
    Graph[("MultiDiGraph<br/>(NetworkX)")]
```

## 5. Hidden-Link Hypothesis Engine (Scoring)

```mermaid
flowchart LR
    CN[Common Neighbors / Adamic-Adar] -->|weight 0.25| Score
    TO[Temporal Overlap] -->|weight 0.20| Score
    SL[Shared Locations] -->|weight 0.20| Score
    CC[Communication Correlation] -->|weight 0.15| Score
    FC[Financial Correlation] -->|weight 0.10| Score
    SR[Source Reliability] -->|weight 0.10| Score
    Score[Weighted Sum] --> Confidence[Displayed Confidence %]
    Confidence --> Breakdown["VIEW SCORE BREAKDOWN"]
```

## 6. Evidence Provenance Chain

```mermaid
flowchart TD
    Conclusion["AI Conclusion (e.g. Hidden Link)"] --> Path[Supporting Graph Path]
    Path --> Records[Source Records: FIR / CDR / TXN / Event]
    Records --> Snippet[Exact Evidence Snippet]
    Snippet --> Investigator["Investigator opens source record via /evidence/{id}"]
```

## Why NetworkX now, Neo4j later

For a hackathon prototype, NetworkX gives zero-setup graph analytics
in-process, in Python, with no separate database server to install or
demo-fail on. The repository boundary (`DataStore` + the functions in
`graph_engine.py`) is deliberately the only place that touches the
in-memory representation, so a production rewrite would move to Neo4j by:

1. Replacing `DataStore.raw` JSON access with Cypher `MATCH` queries.
2. Replacing `person_graph_projection()` with a Cypher projection or GDS
   graph catalog projection.
3. Replacing NetworkX centrality/community calls with Neo4j Graph Data
   Science library equivalents (`gds.betweenness.stream`, `gds.louvain.stream`, etc).
4. Leaving `main.py`'s route signatures and response shapes untouched.
