# NEXUS-X
### Explainable Temporal Criminal Network Intelligence & Hypothesis Engine

**Smart India Hackathon 2026 — SIH26189 · AI-Powered Criminal Network Analysis System**
Ministry of Home Affairs · National Crime Records Bureau (NCRB), Women Safety Division
Category: Software · Theme: Blockchain & Cybersecurity

> *"Don't just show investigators what is known. Show what relationships may
> be missing, why the system suspects them, what evidence supports or
> contradicts them, how the network evolved, and what additional evidence
> would best test the hypothesis."*

---

## Problem

Investigators working complex, multi-entity cases (financial fraud rings,
trafficking networks, coordinated harassment/stalking cases) must manually
cross-reference FIRs, call records, financial transactions, and surveillance
reports to find relationships that were never explicitly documented
anywhere. This is slow, error-prone, and entirely dependent on individual
investigator intuition.

## Proposed Solution

NEXUS-X ingests fragmented case records into a single explainable temporal
knowledge graph, then layers six analytical engines on top of it — hidden-link
hypothesis generation, entity resolution, contradiction detection, network
role discovery, counterfactual simulation, and anomaly detection — with a
hard requirement that **every AI output is labeled, scored, explained, and
requires human review** before it can be treated as fact.

See `docs/INNOVATION.md` for a full breakdown of what makes this different
from a conventional link-analysis dashboard.

---

## What's Actually Running (read this first)

This prototype **intentionally deviates from the originally-scoped
Next.js/TypeScript/shadcn frontend.** It ships as a dependency-free vanilla
JS single-page app (Cytoscape.js + Chart.js via CDN) talking to a Python
FastAPI backend. This was a deliberate reliability tradeoff for hackathon
demo conditions: zero `npm install`/build-step failure surface, works on any
machine with Python 3 installed, boots in seconds. See **Limitations**
below for the full list of scope decisions.

Everything else in this document describes what is genuinely implemented
and tested, not aspirational.

---

## Architecture

```
nexus-x/
├── backend/
│   ├── main.py            # FastAPI app — all REST endpoints
│   ├── graph_engine.py    # NetworkX-based analytics (the "AI" layer)
│   ├── copilot.py         # Deterministic NL query parser
│   ├── reports.py         # HTML report generator
│   ├── data_gen.py        # Synthetic dataset generator
│   ├── requirements.txt
│   ├── Dockerfile
│   └── tests/
│       └── test_graph_engine.py
├── data/
│   └── dataset.json       # Generated synthetic dataset (git-ignored recommended)
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/                # api.js, graph.js, hypotheses.js, copilot.js, ...
├── docs/
│   ├── architecture.md    # Mermaid diagrams
│   ├── SIH_DEMO.md         # 3-minute demo script
│   ├── INNOVATION.md
│   └── JUDGES_QA.md
├── scripts/run.sh
├── docker-compose.yml
├── .env.example
└── README.md
```

See `docs/architecture.md` for Mermaid diagrams of the system, ingestion
pipeline, AI pipeline, knowledge graph pipeline, hypothesis engine scoring,
and evidence provenance chain.

---

## Features (genuinely functional — see full list at bottom)

- Multi-source ingestion (sample documents + file upload) with deterministic
  entity extraction and investigator accept/reject/confirm flow
- Entity resolution (fuzzy name + phone/address overlap) with merge decisions
- Heterogeneous interactive knowledge graph (Cytoscape.js): 7 node types,
  11 relationship types, confidence filtering, search, path finder
- Hidden-link hypothesis engine: 6-feature transparent weighted scoring
  (common neighbors, temporal overlap, shared locations, communication
  correlation, financial correlation, source reliability), with visible
  score breakdown
- Contradiction detection (conflicting location/time records)
- Network role discovery (degree/betweenness centrality, PageRank, greedy
  modularity communities) with plain-English explanations
- Counterfactual network simulator (non-destructive node removal, before/after
  component count, density, fragmentation %, new bridge candidate)
- Temporal network reconstruction with a draggable/playable month slider and
  automatic structural-event detection
- Anomaly detection (statistical outlier transactions, communication spikes)
- Deterministic Investigation Copilot answering from the live graph only
- Investigation Story Mode (10-step guided reconstruction, real computed data)
- HTML investigation report generator with mandatory AI disclaimer
- Immutable-style audit log of every action
- Human-in-the-loop review status on every AI output (Confirm/Reject/Review)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vanilla JS SPA, Cytoscape.js (graph), Chart.js (analytics), plain CSS (dark command-center theme) |
| Backend | Python 3.12, FastAPI, Pydantic |
| Graph analytics | NetworkX (architected to be Neo4j-swappable — see `docs/architecture.md`) |
| Entity resolution | RapidFuzz (fuzzy string matching) + rule-based scoring |
| Data | In-memory `DataStore` over a generated synthetic `dataset.json` |
| Testing | Pytest (backend logic) |

No paid APIs are required anywhere in the core demo. An optional LLM
integration point exists in `copilot.py`/`.env.example` for translating
free-text questions into supported intents, but it is never required and
never allowed to invent graph facts.

---

## Installation & Running

### Prerequisites
- Python 3.10+
- (Optional) Docker, if you prefer `docker-compose up`

### Quick start (recommended)
```bash
cd nexus-x
bash scripts/run.sh
```
This installs backend dependencies, regenerates the synthetic dataset, runs
the backend test suite, then starts both servers.

### Manual start
```bash
# Terminal 1 — backend
cd nexus-x/backend
pip install -r requirements.txt --break-system-packages   # omit the flag if using a venv
python data_gen.py            # generates data/dataset.json
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2 — frontend
cd nexus-x/frontend
python -m http.server 5173
```

Then open **http://localhost:5173** in your browser. The backend API and
interactive OpenAPI docs are at **http://localhost:8000/docs**.

### Docker
```bash
docker-compose up --build
```

### Environment Variables
See `.env.example`. Every variable is optional — the full demo runs with
none of them set.

---

## Demo Login

```
Email:    investigator@nexusx.demo
Password: demo123
```

This is clearly labeled in-app as a prototype/demo authentication system,
not production-grade security.

---

## Demo Walkthrough

See `docs/SIH_DEMO.md` for the exact 3-minute judge-facing sequence. Short
version: Login → Overview → Intelligence Graph → Story Mode → Hypotheses
(score breakdown) → Analytics (contradiction + counterfactual simulation) →
AI Copilot → Reports.

---

## API Documentation

Full interactive OpenAPI docs are auto-generated by FastAPI at
`http://localhost:8000/docs` once the backend is running. Key endpoints:

| Method | Path | Purpose |
|---|---|---|
| POST | `/auth/login` | Demo authentication |
| GET | `/cases`, `/cases/{id}` | Case management |
| GET | `/overview` | Dashboard stats |
| GET | `/graph/{case_id}` | Full graph (nodes + confirmed edges + hypotheses) |
| GET | `/entities/{id}` | Entity detail, neighbors, network role |
| POST | `/analysis/entity-resolution` | Duplicate-identity candidates |
| POST | `/analysis/hidden-links` | Hidden-link hypotheses |
| POST | `/analysis/contradictions` | Contradiction detection |
| GET | `/analysis/network-roles` | Centrality-based role labels |
| GET | `/analysis/communities/{case_id}` | Community detection |
| POST | `/analysis/counterfactual` | Node-removal simulation |
| GET | `/analysis/anomalies` | Anomaly feed |
| GET | `/analysis/path` | Path finder |
| GET | `/timeline/{case_id}` | Timeline snapshot |
| GET | `/timeline/{case_id}/events` | Structural event detection |
| POST | `/hypotheses/{id}/review` | Human-in-the-loop review |
| POST | `/documents/upload`, `/documents/confirm` | Ingestion pipeline |
| GET | `/evidence/{id}` | Evidence provenance lookup |
| POST | `/copilot/query` | Investigation Copilot |
| GET | `/reports/{case_id}` | HTML investigation report |
| GET | `/audit` | Audit log |
| GET | `/story/{case_id}` | Story Mode script |

---

## Testing

```bash
cd backend
python -m pytest tests/ -v
```
11 tests cover entity resolution, hidden-link scoring bounds and
explainability, contradiction detection, network-role coverage,
counterfactual non-destructiveness, community partitioning, path-hop
limits, anomaly detection, and timeline monotonicity. All passing at time
of writing.

---

## Limitations

- **Frontend stack deviation**: vanilla JS instead of Next.js/TypeScript/
  shadcn/Framer Motion, for zero-build-step demo reliability (see above).
- **In-memory data store**: the backend loads `dataset.json` into memory on
  startup; there is no persistent PostgreSQL/SQLite-backed case database in
  this prototype. Restarting the backend resets review decisions, merges,
  and the audit log (the underlying synthetic dataset itself is
  regenerated deterministically from a fixed seed).
- **No spaCy/sentence-transformers models loaded**: entity extraction uses a
  deterministic regex + dictionary-lookup pipeline against the known
  synthetic entity list, chosen for zero-dependency reliability rather than
  a general-purpose NLP model. This is documented as a fallback, not passed
  off as a trained model.
- **No PDF ingestion**: TXT/CSV/JSON sample and upload flows are implemented;
  PDF parsing was descoped for time.
- **No authentication beyond the single demo account**: there is no
  multi-user/role-based access control.
- **Community detection** uses NetworkX's greedy modularity algorithm on a
  person-to-person projection of the graph; it is not tuned against any
  real-world criminal network topology (impossible to validate without
  real data, by design).
- **LLM integration point exists but is unused by default** — see
  `copilot.py` and `.env.example`.

## Ethical Safeguards

- 100% synthetic, fictional data — no real individuals, phone numbers, or
  locations.
- No facial recognition, anywhere.
- Never infers race, religion, political ideology, sexual orientation,
  health status, or other protected characteristics.
- Never labels an entity "criminal" — uses "entity," "person of interest,"
  "analytical hypothesis," and "network role" throughout.
- Every AI-generated relationship is explicitly labeled CONFIRMED / INFERRED
  / HYPOTHESIS / CONTRADICTED / UNVERIFIED and requires investigator review.
- Counterfactual simulation output is a structural observation only — never
  an operational recommendation.

## Future Scope

Neo4j + Graph Data Science backend for production scale; live NCRB/CCTNS
ingestion integration; RBAC and multi-investigator collaboration;
hash-chained/blockchain-backed audit log integrity; full Next.js/TypeScript
frontend rebuild; dynamic (not month-snapshot) community tracking.
