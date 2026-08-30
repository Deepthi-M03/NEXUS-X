from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from datetime import datetime

import os
import re
import json

import graph_engine as ge
import copilot as cp
import reports as rp


# ---------------------------------------------------------------------------
# APP SETUP
# ---------------------------------------------------------------------------

app = FastAPI(
    title="NEXUS-X API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


# ---------------------------------------------------------------------------
# DATA / GRAPH
# ---------------------------------------------------------------------------

STORE = ge.DataStore()
GRAPH = ge.build_graph(STORE)

DEMO_USER = {
    "email": "investigator@nexusx.demo",
    "password": "demo123"
}


def refresh_graph():
    global GRAPH
    GRAPH = ge.build_graph(STORE)


# ---------------------------------------------------------------------------
# AUTH
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/auth/login")
def login(req: LoginRequest):
    if (
        req.email == DEMO_USER["email"]
        and req.password == DEMO_USER["password"]
    ):
        STORE.log("LOGIN", actor=req.email)

        return {
            "token": "demo-session-token",
            "user": {
                "email": req.email,
                "name": "Insp. A. Fernandes",
                "role": "Investigator"
            },
            "note": (
                "This is a prototype demo authentication system, "
                "not production-grade security."
            )
        }

    raise HTTPException(
        status_code=401,
        detail=(
            "Invalid demo credentials. "
            "Use investigator@nexusx.demo / demo123"
        )
    )


# ---------------------------------------------------------------------------
# CASES
# ---------------------------------------------------------------------------

@app.get("/cases")
def list_cases():
    return STORE.raw["cases"]


@app.get("/cases/{case_id}")
def get_case(case_id: str):
    case = next(
        (c for c in STORE.raw["cases"] if c["id"] == case_id),
        None
    )

    if not case:
        raise HTTPException(
            status_code=404,
            detail="Case not found"
        )

    stats = {
        "entities": len(STORE.raw["people"]),
        "relationships": GRAPH.number_of_edges(),
        "hypotheses": len(
            ge.hidden_link_hypotheses(STORE, GRAPH)
        ),
        "contradictions": len(
            ge.contradiction_detection(STORE, GRAPH)
        )
    }

    return {
        **case,
        "stats": stats
    }


class NewCase(BaseModel):
    title: str
    description: str = ""
    priority: str = "MEDIUM"


@app.post("/cases")
def create_case(nc: NewCase):
    new_id = (
        f"NX-2026-{len(STORE.raw['cases']) + 70:03d}"
    )

    case = {
        "id": new_id,
        "title": nc.title,
        "status": "ACTIVE",
        "priority": nc.priority,
        "created": datetime.now().date().isoformat(),
        "assigned_investigator": "Insp. A. Fernandes",
        "description": nc.description,
        "risk_level": "UNASSESSED"
    }

    STORE.raw["cases"].append(case)

    STORE.log(
        "CASE_CREATED",
        obj=new_id
    )

    return case


# ---------------------------------------------------------------------------
# OVERVIEW
# ---------------------------------------------------------------------------

@app.get("/overview")
def overview():
    hyps = ge.hidden_link_hypotheses(
        STORE,
        GRAPH
    )

    contras = ge.contradiction_detection(
        STORE,
        GRAPH
    )

    er = ge.entity_resolution(
        STORE
    )

    return {
        "active_cases": len([
            c
            for c in STORE.raw["cases"]
            if c["status"] == "ACTIVE"
        ]),

        "entities_analyzed": (
            len(STORE.raw["people"])
            + len(STORE.raw["phones"])
            + len(STORE.raw["vehicles"])
            + len(STORE.raw["accounts"])
        ),

        "relationships": GRAPH.number_of_edges(),

        "ai_hypotheses": len(hyps),

        "high_risk_patterns": len([
            h
            for h in hyps
            if h["confidence"] >= 0.7
        ]),

        "contradictions": len(contras),

        "unresolved_entities": len(er),

        "entity_distribution": {
            "PERSON": len(STORE.raw["people"]),
            "PHONE": len(STORE.raw["phones"]),
            "VEHICLE": len(STORE.raw["vehicles"]),
            "ACCOUNT": len(STORE.raw["accounts"]),
            "LOCATION": len(STORE.raw["locations"]),
            "ORGANIZATION": len(STORE.raw["organizations"])
        },

        "recent_activity": (
            STORE._audit_log[-10:][::-1]
        ),

        "top_hypotheses": hyps[:3]
    }


# ---------------------------------------------------------------------------
# GRAPH
# ---------------------------------------------------------------------------

@app.get("/graph/{case_id}")
def get_graph(
    case_id: str,
    min_confidence: float = 0.0
):
    nodes = []
    edges = []

    for node_id, data in GRAPH.nodes(
        data=True
    ):
        nodes.append({
            "id": node_id,
            "type": data.get("type"),
            "label": data.get("label")
        })

    for source, target, data in GRAPH.edges(
        data=True
    ):
        confidence = data.get(
            "confidence",
            1.0
        )

        if confidence < min_confidence:
            continue

        edges.append({
            "source": source,
            "target": target,
            "type": data.get("type"),
            "status": data.get(
                "status",
                "CONFIRMED"
            ),
            "confidence": confidence,
            "timestamp": data.get("timestamp")
        })

    hyps = ge.hidden_link_hypotheses(
        STORE,
        GRAPH
    )

    for hyp in hyps:
        edges.append({
            "source": hyp["entity_a"],
            "target": hyp["entity_b"],
            "type": "HYPOTHESIS",
            "status": hyp["status"],
            "confidence": hyp["confidence"],
            "timestamp": None,
            "hypothesis_id": hyp["id"]
        })

    return {
        "nodes": nodes,
        "edges": edges
    }


@app.get("/entities/{entity_id}")
def get_entity(entity_id: str):
    node = GRAPH.nodes.get(entity_id)

    if not node:
        raise HTTPException(
            status_code=404,
            detail="Entity not found"
        )

    neighbors = []

    for u, v, data in GRAPH.out_edges(
        entity_id,
        data=True
    ):
        neighbors.append({
            "id": v,
            "label": GRAPH.nodes[v].get(
                "label"
            ),
            "type": GRAPH.nodes[v].get(
                "type"
            ),
            "relationship": data.get(
                "type"
            )
        })

    for u, v, data in GRAPH.in_edges(
        entity_id,
        data=True
    ):
        neighbors.append({
            "id": u,
            "label": GRAPH.nodes[u].get(
                "label"
            ),
            "type": GRAPH.nodes[u].get(
                "type"
            ),
            "relationship": data.get(
                "type"
            )
        })

    roles = (
        ge.network_roles(GRAPH)
        if node.get("type") == "PERSON"
        else []
    )

    role = next(
        (
            r
            for r in roles
            if r["entity"] == entity_id
        ),
        None
    )

    return {
        "id": entity_id,
        **node,
        "neighbors": neighbors,
        "network_role": role
    }


# ---------------------------------------------------------------------------
# ANALYSIS
# ---------------------------------------------------------------------------

@app.post("/analysis/entity-resolution")
def analysis_entity_resolution():
    return ge.entity_resolution(STORE)


class MergeRequest(BaseModel):
    entity_a: str
    entity_b: str
    decision: str
    note: Optional[str] = None


@app.post(
    "/analysis/entity-resolution/decision"
)
def entity_resolution_decision(
    req: MergeRequest
):
    key = (
        f"ER-{req.entity_a}-{req.entity_b}"
    )

    STORE._reviews[key] = {
        "status": req.decision,
        "note": req.note
    }

    STORE.log(
        f"ENTITY_RESOLUTION_{req.decision}",
        obj=key
    )

    if req.decision == "MERGE":
        STORE._merges.append({
            "kept": req.entity_a,
            "merged": req.entity_b,
            "note": req.note
        })

    return {
        "ok": True
    }


@app.post("/analysis/hidden-links")
def analysis_hidden_links():
    return ge.hidden_link_hypotheses(
        STORE,
        GRAPH
    )


@app.post("/analysis/contradictions")
def analysis_contradictions():
    return ge.contradiction_detection(
        STORE,
        GRAPH
    )


@app.post("/analysis/counterfactual")
def analysis_counterfactual(
    entity_id: str = Form(...)
):
    STORE.log(
        "SIMULATION_PERFORMED",
        obj=entity_id
    )

    return ge.counterfactual_removal(
        GRAPH,
        entity_id
    )


@app.get("/analysis/network-roles")
def analysis_network_roles():
    return ge.network_roles(GRAPH)


@app.get(
    "/analysis/communities/{case_id}"
)
def analysis_communities(
    case_id: str
):
    return ge.communities_detail(
        GRAPH
    )


@app.get("/analysis/anomalies")
def analysis_anomalies():
    return ge.anomaly_detection(
        STORE
    )


@app.get("/analysis/path")
def analysis_path(
    source: str,
    target: str,
    max_hops: int = 4
):
    return ge.find_paths(
        GRAPH,
        source,
        target,
        max_hops
    )


# ---------------------------------------------------------------------------
# TIMELINE
# ---------------------------------------------------------------------------

@app.get("/timeline/{case_id}")
def timeline(
    case_id: str,
    as_of: str = "2026-05-31"
):
    return ge.timeline_snapshot(
        STORE,
        GRAPH,
        as_of
    )


@app.get(
    "/timeline/{case_id}/events"
)
def timeline_events(
    case_id: str
):
    return ge.detect_structural_events(
        STORE,
        GRAPH
    )


# ---------------------------------------------------------------------------
# HYPOTHESIS REVIEW
# ---------------------------------------------------------------------------

class ReviewRequest(BaseModel):
    decision: str
    note: Optional[str] = None


@app.post(
    "/hypotheses/{hyp_id}/review"
)
def review_hypothesis(
    hyp_id: str,
    req: ReviewRequest
):
    STORE._reviews[hyp_id] = {
        "status": req.decision,
        "note": req.note
    }

    STORE.log(
        f"HYPOTHESIS_{req.decision}",
        obj=hyp_id
    )

    return {
        "ok": True,
        "hypothesis_id": hyp_id,
        "status": req.decision
    }


# ---------------------------------------------------------------------------
# CONTRADICTION REVIEW
# ---------------------------------------------------------------------------

@app.post(
    "/contradictions/{contra_id}/review"
)
def review_contradiction(
    contra_id: str,
    req: ReviewRequest
):
    STORE._reviews[contra_id] = {
        "status": req.decision,
        "note": req.note
    }

    STORE.log(
        f"CONTRADICTION_{req.decision}",
        obj=contra_id
    )

    return {
        "ok": True
    }


# ---------------------------------------------------------------------------
# EVIDENCE
# ---------------------------------------------------------------------------

@app.get("/evidence/{evidence_id}")
def get_evidence(
    evidence_id: str
):
    collections = [
        "reports",
        "communications",
        "transactions",
        "events"
    ]

    for collection in collections:

        for record in STORE.raw[collection]:

            if record["id"] == evidence_id:
                return {
                    "collection": collection,
                    **record
                }

    raise HTTPException(
        status_code=404,
        detail="Evidence record not found"
    )


# ---------------------------------------------------------------------------
# DOCUMENT INGESTION
# ---------------------------------------------------------------------------

SAMPLE_DOCS = {
    "sample_fir_001": {
        "category": "FIR",
        "text": (
            "On 12 February 2026, a complaint was filed "
            "regarding suspicious financial activity linked "
            "to Arjun Mehta, contacted via phone in connection "
            "with Sanjay Iyer. Vehicle TN37-AX-1004 was sighted "
            "near Coimbatore Sector-8 around the same period."
        )
    },

    "sample_cdr_001": {
        "category": "CDR",
        "text": (
            "Call Detail Record excerpt: Phone PH001 contacted "
            "Phone PH002 on 2026-02-10 21:15, duration 340 seconds. "
            "Repeated contact on 2026-02-14."
        )
    },

    "sample_intel_001": {
        "category": "Intelligence Report",
        "text": (
            "Surveillance team reports Priya Chatterjee sighted "
            "at Coimbatore Sector-8 on multiple occasions in early "
            "March 2026, alongside Vikram Rao on a separate but "
            "proximate date."
        )
    }
}


def _extract_entities(text: str):
    found = []

    for person in STORE.raw["people"]:
        if person["name"].lower() in text.lower():
            found.append({
                "type": "PERSON",
                "value": person["name"],
                "confidence": 0.94,
                "entity_id": person["id"]
            })

    phone_matches = re.findall(
        r"PH\d{3}",
        text
    )

    for phone in phone_matches:
        found.append({
            "type": "PHONE",
            "value": phone,
            "confidence": 0.99,
            "entity_id": phone
        })

    vehicle_matches = re.findall(
        r"[A-Z]{2}\d{2}-[A-Z]{2}-\d{3,4}",
        text
    )

    for vehicle in vehicle_matches:
        found.append({
            "type": "VEHICLE",
            "value": vehicle,
            "confidence": 0.97
        })

    for location in STORE.raw["locations"]:
        if location["name"].lower() in text.lower():
            found.append({
                "type": "LOCATION",
                "value": location["name"],
                "confidence": 0.90,
                "entity_id": location["id"]
            })

    date_matches = re.findall(
        r"\d{4}-\d{2}-\d{2}",
        text
    )

    for date in date_matches:
        found.append({
            "type": "DATE",
            "value": date,
            "confidence": 0.98
        })

    return found


@app.get("/documents/samples")
def list_sample_docs():
    return [
        {
            "id": key,
            "category": value["category"],
            "preview": value["text"][:80] + "..."
        }
        for key, value in SAMPLE_DOCS.items()
    ]


@app.post("/documents/upload")
async def upload_document(
    category: str = Form(
        "Intelligence Report"
    ),
    sample_id: Optional[str] = Form(
        None
    ),
    file: Optional[UploadFile] = File(
        None
    )
):
    if (
        sample_id
        and sample_id in SAMPLE_DOCS
    ):
        text = SAMPLE_DOCS[
            sample_id
        ]["text"]

        category = SAMPLE_DOCS[
            sample_id
        ]["category"]

    elif file is not None:

        raw = await file.read()

        text = raw.decode(
            "utf-8",
            errors="ignore"
        )

    else:
        raise HTTPException(
            status_code=400,
            detail=(
                "Provide either sample_id "
                "or file"
            )
        )

    entities = _extract_entities(
        text
    )

    STORE.log(
        "DOCUMENT_UPLOADED",
        obj=(
            sample_id
            or (
                file.filename
                if file
                else "unknown"
            )
        )
    )

    return {
        "category": category,
        "text_preview": text[:400],
        "extracted_entities": entities,
        "instructions": (
            "Review extracted entities below, "
            "then Accept/Edit/Reject each before "
            "they are added to the graph."
        )
    }


class ConfirmEntities(BaseModel):
    entities: list


@app.post("/documents/confirm")
def confirm_entities(
    payload: ConfirmEntities
):
    STORE.log(
        "ENTITY_EXTRACTED_CONFIRMED",
        obj=str(
            len(payload.entities)
        )
    )

    return {
        "ok": True,
        "added": len(payload.entities)
    }


# ---------------------------------------------------------------------------
# COPILOT
# ---------------------------------------------------------------------------

class CopilotQuery(BaseModel):
    query: str


@app.post("/copilot/query")
def copilot_query(
    q: CopilotQuery
):
    STORE.log(
        "COPILOT_QUERY",
        obj=q.query
    )

    return cp.answer(
        q.query,
        STORE,
        GRAPH
    )


# ---------------------------------------------------------------------------
# REPORTS
# ---------------------------------------------------------------------------

@app.get(
    "/reports/{case_id}",
    response_class=HTMLResponse
)
def get_report(
    case_id: str
):
    STORE.log(
        "REPORT_GENERATED",
        obj=case_id
    )

    return rp.generate_html_report(
        STORE,
        GRAPH,
        case_id
    )


# ---------------------------------------------------------------------------
# AUDIT LOG
# ---------------------------------------------------------------------------

@app.get("/audit")
def audit_log():
    return STORE._audit_log[::-1]


# ---------------------------------------------------------------------------
# STORY MODE
# ---------------------------------------------------------------------------

@app.get("/story/{case_id}")
def story_mode(
    case_id: str
):
    hyps = ge.hidden_link_hypotheses(
        STORE,
        GRAPH
    )

    contras = ge.contradiction_detection(
        STORE,
        GRAPH
    )

    roles = ge.network_roles(
        GRAPH
    )

    events = ge.detect_structural_events(
        STORE,
        GRAPH
    )

    top_role = (
        roles[0]
        if roles
        else None
    )

    counterfactual = (
        ge.counterfactual_removal(
            GRAPH,
            top_role["entity"]
        )
        if top_role
        else None
    )

    top_hyp = (
        hyps[0]
        if hyps
        else None
    )

    key = STORE.raw[
        "scenario_key_entities"
    ]

    return {
        "steps": [
            {
                "step": 1,
                "title": "Initial FIR received",
                "detail": (
                    "FIR-001 flags suspicious "
                    "financial activity involving "
                    "Arjun Mehta."
                )
            },

            {
                "step": 2,
                "title": "Entities extracted",
                "detail": (
                    "NLP pipeline extracts PERSON, "
                    "PHONE, VEHICLE, LOCATION entities "
                    "with confidence scores for "
                    "investigator review."
                )
            },

            {
                "step": 3,
                "title": "CDR added",
                "detail": (
                    "Call detail records ingested, "
                    "revealing a communication path "
                    "from Arjun Mehta to Sanjay Iyer."
                )
            },

            {
                "step": 4,
                "title": "Financial data added",
                "detail": (
                    "Transaction records show a fund "
                    "transfer chain extending the "
                    "network further."
                )
            },

            {
                "step": 5,
                "title": "Knowledge graph expands",
                "detail": (
                    f"Graph now contains "
                    f"{GRAPH.number_of_nodes()} "
                    f"entities and "
                    f"{GRAPH.number_of_edges()} "
                    f"confirmed relationships."
                )
            },

            {
                "step": 6,
                "title": "Hidden relationship discovered",
                "detail": (
                    (
                        f"Hidden-link engine flags "
                        f"{top_hyp['entity_a_name']} ↔ "
                        f"{top_hyp['entity_b_name']} at "
                        f"{round(top_hyp['confidence'] * 100)}% "
                        f"confidence."
                    )
                    if top_hyp
                    else (
                        "No hidden link surfaced "
                        "in current data."
                    )
                )
            },

            {
                "step": 7,
                "title": "Contradiction detected",
                "detail": (
                    (
                        f"{contras[0]['entity_name']} has "
                        f"conflicting location records within "
                        f"{contras[0]['minutes_apart']} minutes."
                    )
                    if contras
                    else (
                        "No contradictions currently "
                        "detected."
                    )
                )
            },

            {
                "step": 8,
                "title": (
                    "Temporal analysis reveals "
                    "network evolution"
                ),
                "detail": (
                    events[0]["description"]
                    if events
                    else (
                        "No major structural shift "
                        "detected in this run."
                    )
                )
            },

            {
                "step": 9,
                "title": (
                    "Counterfactual simulation identifies "
                    "structural bridge"
                ),
                "detail": (
                    counterfactual["interpretation"]
                    if counterfactual
                    else "N/A"
                )
            },

            {
                "step": 10,
                "title": (
                    "Evidence-backed hypothesis generated"
                ),
                "detail": (
                    (
                        f"Final hypothesis: "
                        f"{top_hyp['entity_a_name']} ↔ "
                        f"{top_hyp['entity_b_name']} — "
                        f"{top_hyp['explanation']}"
                    )
                    if top_hyp
                    else "N/A"
                )
            }
        ],

        "key_entities": key
    }


# ---------------------------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "nodes": GRAPH.number_of_nodes(),
        "edges": GRAPH.number_of_edges()
    }


# ---------------------------------------------------------------------------
# FRONTEND
# KEEP THIS SECTION AT THE VERY BOTTOM OF THE FILE
# ---------------------------------------------------------------------------

if FRONTEND_DIR.exists():
    app.mount(
        "/",
        StaticFiles(
            directory=str(FRONTEND_DIR),
            html=True
        ),
        name="frontend"
    )
else:
    print(
        f"WARNING: Frontend directory not found: "
        f"{FRONTEND_DIR}"
    )