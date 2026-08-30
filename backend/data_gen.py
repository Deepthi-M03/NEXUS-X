"""
NEXUS-X Synthetic Dataset Generator
------------------------------------
Generates a fully fictional demo dataset for CASE NX-2026-041 "Operation Silent Web"
(plus two lighter secondary cases) with intentionally engineered:
  - hidden multi-hop relationships (no direct edge, but strong indirect signal)
  - duplicate identity records (near-duplicate names sharing phone/address)
  - contradictory location/time records for one entity
  - shared phones/vehicles (bridge signals)
  - a structurally important "bridge" node that is NOT the obvious suspect
  - financial anomalies and communication spikes for anomaly detection

ALL data is synthetic and fictional. No real persons, phone numbers, or
locations are used. Phone numbers use the reserved fictional format.
"""
import os
import json
import random
from datetime import datetime, timedelta

random.seed(42)

OUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "dataset.json")

FIRST_NAMES = ["Arjun","Vikram","Rohan","Aditya","Karan","Sanjay","Rahul","Nikhil","Suresh","Manoj",
               "Priya","Anjali","Neha","Divya","Pooja","Kavya","Meera","Ritu","Sneha","Isha",
               "Raj","Amit","Vivek","Deepak","Ashok","Farhan","Imran","Zoya","Alia","Sameer",
               "Gaurav","Harish","Kunal","Naveen","Pankaj","Ramesh","Sunil","Tarun","Uday","Yogesh"]
LAST_NAMES = ["Mehta","Rao","Sharma","Kumar","Verma","Singh","Nair","Iyer","Reddy","Gupta",
              "Khan","Malhotra","Chatterjee","Bose","Pillai","Desai","Kapoor","Joshi","Bhatt","Menon"]
ORGS = ["Silverline Traders Pvt Ltd","Nightfall Logistics","Crosslink Freight Co","BlueHarbor Exports",
        "Vertex Textiles","Coastal Shipping Agency","Metro Finserve","Falcon Holdings"]
CITIES = ["Coimbatore","Chennai","Bengaluru","Hyderabad","Madurai","Salem","Kochi","Trichy",
          "Erode","Vellore","Pondicherry","Nagercoil","Tirunelveli","Karur","Namakkal"]

def rand_phone(i):
    return f"+91-9{str(100000000 + i*137).zfill(9)[:9]}"

def rand_vehicle(i):
    codes = ["TN37","TN66","TN45","KA05","AP09","TN23","TN72"]
    return f"{random.choice(codes)}-{random.choice('ABCDEFGH')}{random.choice('XYZQR')}-{1000+i}"

def rand_account(i):
    return f"AC-{9000+i}-{random.choice(['SBI','HDFC','ICICI','PNB','CANARA'])}"

def rand_date(start="2026-01-01", end="2026-05-31"):
    s = datetime.fromisoformat(start)
    e = datetime.fromisoformat(end)
    delta = (e - s).days
    d = s + timedelta(days=random.randint(0, delta), hours=random.randint(0,23), minutes=random.randint(0,59))
    return d.isoformat()

def gen():
    people = []
    for i in range(30):
        fn = FIRST_NAMES[i % len(FIRST_NAMES)]
        ln = LAST_NAMES[(i*3) % len(LAST_NAMES)]
        people.append({
            "id": f"P{i+1:03d}",
            "type": "PERSON",
            "name": f"{fn} {ln}",
            "age": random.randint(21, 55),
            "city": random.choice(CITIES),
            "notes": "Synthetic demo identity",
        })

    # --- Intentional duplicate identities (entity resolution demo) ---
    dup_base = people[9]  # e.g. Raj Kumar-ish
    dup_base["name"] = "Raj Kumar"
    dup_base["city"] = "Coimbatore"
    duplicates = [
        {"id": "P031", "type": "PERSON", "name": "R. Kumar", "age": dup_base["age"], "city": "Coimbatore", "notes": "Possible duplicate of P010"},
        {"id": "P032", "type": "PERSON", "name": "Rajkumar R", "age": dup_base["age"]+1, "city": "Coimbatore", "notes": "Possible duplicate of P010"},
    ]
    people += duplicates

    phones = []
    for i in range(20):
        phones.append({"id": f"PH{i+1:03d}", "type": "PHONE", "number": rand_phone(i), "owner_id": None})

    vehicles = []
    for i in range(10):
        vehicles.append({"id": f"V{i+1:03d}", "type": "VEHICLE", "plate": rand_vehicle(i), "owner_id": None})

    accounts = []
    for i in range(15):
        accounts.append({"id": f"AC{i+1:03d}", "type": "ACCOUNT", "number": rand_account(i), "holder_id": None})

    locations = []
    for i in range(15):
        locations.append({"id": f"L{i+1:03d}", "type": "LOCATION", "name": f"{random.choice(CITIES)} Sector-{i+1}", "city": CITIES[i % len(CITIES)]})

    organizations = []
    for i in range(8):
        organizations.append({"id": f"O{i+1:03d}", "type": "ORGANIZATION", "name": ORGS[i]})

    # assign ownership: each person gets 0-1 phone (first 20 people), duplicates share phone with P010
    for idx, p in enumerate(people[:20]):
        phones[idx]["owner_id"] = p["id"]
    # duplicates share P010's phone number (entity-resolution signal) -- use a spare phone, not P001's
    phones[19]["owner_id"] = "P010"
    dup_shared_phone = phones[19]["id"]

    for idx, v in enumerate(vehicles):
        v["owner_id"] = people[idx*2 % 28]["id"]

    for idx, a in enumerate(accounts):
        a["holder_id"] = people[idx % 28]["id"]

    # -----------------------------------------------------------------
    # ENGINEERED HIDDEN-LINK SCENARIO (Person A <-> Person D, no direct edge)
    # A = P001 Arjun Mehta ; B = P002 ; C = P003 (the true structural bridge) ;
    # D = P006 Vikram Rao (target of hidden hypothesis) ; F = P007 (emerges in counterfactual)
    # -----------------------------------------------------------------
    A, B, C, Dp, Fp = people[0], people[1], people[2], people[5], people[6]
    A["name"], B["name"], C["name"], Dp["name"], Fp["name"] = "Arjun Mehta","Sanjay Iyer","Priya Chatterjee","Vikram Rao","Rohan Bose"

    events = []
    for i in range(20):
        events.append({
            "id": f"E{i+1:03d}", "type": "EVENT",
            "description": random.choice(["Surveillance sighting","Border checkpoint log","CCTV flag","Informant tip","Routine patrol stop"]),
            "location_id": random.choice(locations)["id"],
            "timestamp": rand_date(),
            "entities": [],
        })

    # --- Community-clustered communications/transactions so real network structure emerges
    # (fully-random uniform pairing would make almost every phone reachable from every other
    # phone within 1-2 hops, drowning out the engineered hidden-link signal). Phones are split
    # into 4 friend-groups; most contact stays within-group, a small number of cross-group edges
    # exist (these become the discoverable bridges).
    phone_ids = [p["id"] for p in phones]
    random.shuffle(phone_ids)
    group_size = max(1, len(phone_ids) // 4)
    groups = [phone_ids[i:i+group_size] for i in range(0, len(phone_ids), group_size)]

    communications = []
    cdr_i = 0
    for g in groups:
        if len(g) < 2:
            continue
        # dense-ish within-group chatter
        for _ in range(min(14, len(g) * 3)):
            p1, p2 = random.sample(g, 2)
            cdr_i += 1
            communications.append({
                "id": f"CDR{cdr_i:03d}", "type": "COMMUNICATION",
                "from_phone": p1, "to_phone": p2,
                "mode": random.choice(["CALL", "SMS"]),
                "duration_sec": random.randint(5, 900),
                "timestamp": rand_date(),
            })
    # a handful of sparse cross-group edges (structural bridges, not a fully connected mesh)
    for _ in range(6):
        ga, gb = random.sample(groups, 2)
        if not ga or not gb:
            continue
        p1, p2 = random.choice(ga), random.choice(gb)
        cdr_i += 1
        communications.append({
            "id": f"CDR{cdr_i:03d}", "type": "COMMUNICATION",
            "from_phone": p1, "to_phone": p2,
            "mode": random.choice(["CALL", "SMS"]),
            "duration_sec": random.randint(5, 900),
            "timestamp": rand_date(),
        })

    account_ids = [a["id"] for a in accounts]
    random.shuffle(account_ids)
    agroup_size = max(1, len(account_ids) // 4)
    agroups = [account_ids[i:i+agroup_size] for i in range(0, len(account_ids), agroup_size)]
    transactions = []
    txn_i = 0
    for g in agroups:
        if len(g) < 2:
            continue
        for _ in range(min(9, len(g) * 2)):
            a1, a2 = random.sample(g, 2)
            txn_i += 1
            transactions.append({
                "id": f"TXN{txn_i:03d}", "type": "TRANSACTION",
                "from_account": a1, "to_account": a2,
                "amount": random.choice([2500,4800,9999,15000,22000,45000,88000]),
                "timestamp": rand_date(),
            })
    for _ in range(4):
        ga, gb = random.sample(agroups, 2)
        if not ga or not gb:
            continue
        a1, a2 = random.choice(ga), random.choice(gb)
        txn_i += 1
        transactions.append({
            "id": f"TXN{txn_i:03d}", "type": "TRANSACTION",
            "from_account": a1, "to_account": a2,
            "amount": random.choice([2500,4800,9999,15000,22000,45000,88000,150000]),
            "timestamp": rand_date(),
        })

    # Build the indirect chain: A owns phone -> calls B's phone -> B sends funds to Account X -> X links to C -> C at Location L -> D also at Location L
    a_phone = next(p for p in phones if p["owner_id"] == A["id"])
    b_phone = next(p for p in phones if p["owner_id"] == B["id"])
    communications.append({"id": "CDR900", "type": "COMMUNICATION", "from_phone": a_phone["id"], "to_phone": b_phone["id"],
                            "mode": "CALL", "duration_sec": 340, "timestamp": "2026-02-10T21:15:00"})
    communications.append({"id": "CDR901", "type": "COMMUNICATION", "from_phone": a_phone["id"], "to_phone": b_phone["id"],
                            "mode": "CALL", "duration_sec": 512, "timestamp": "2026-02-14T20:55:00"})

    b_acct = next(a for a in accounts if a["holder_id"] == B["id"])
    c_acct = next(a for a in accounts if a["holder_id"] == C["id"])
    transactions.append({"id": "TXN900", "type": "TRANSACTION", "from_account": b_acct["id"], "to_account": c_acct["id"],
                          "amount": 65000, "timestamp": "2026-02-16T11:00:00"})

    bridge_location = locations[7]
    events.append({"id": "E900", "type": "EVENT", "description": "CCTV flag", "location_id": bridge_location["id"],
                    "timestamp": "2026-03-01T19:40:00", "entities": [C["id"]]})
    events.append({"id": "E901", "type": "EVENT", "description": "Surveillance sighting", "location_id": bridge_location["id"],
                    "timestamp": "2026-03-03T19:55:00", "entities": [C["id"]]})
    events.append({"id": "E902", "type": "EVENT", "description": "Surveillance sighting", "location_id": bridge_location["id"],
                    "timestamp": "2026-03-04T20:10:00", "entities": [Dp["id"]]})
    events.append({"id": "E903", "type": "EVENT", "description": "Routine patrol stop", "location_id": bridge_location["id"],
                    "timestamp": "2026-03-08T18:50:00", "entities": [Dp["id"]]})
    # correlated transaction windows near the same dates (financial correlation signal)
    d_acct = next(a for a in accounts if a["holder_id"] == Dp["id"])
    transactions.append({"id": "TXN901", "type": "TRANSACTION", "from_account": c_acct["id"], "to_account": d_acct["id"] if False else accounts[3]["id"],
                          "amount": 40000, "timestamp": "2026-03-02T09:30:00"})
    transactions.append({"id": "TXN902", "type": "TRANSACTION", "from_account": accounts[3]["id"], "to_account": d_acct["id"],
                          "amount": 38500, "timestamp": "2026-03-05T09:45:00"})

    # C becomes a bridge between two otherwise weakly-connected communities in mid-March (temporal event)
    cluster_alpha_phone = next(p for p in phones if p["owner_id"] == people[10]["id"])
    cluster_beta_phone = next(p for p in phones if p["owner_id"] == people[15]["id"])
    c_phone = next(p for p in phones if p["owner_id"] == C["id"])
    communications.append({"id": "CDR902", "type": "COMMUNICATION", "from_phone": c_phone["id"], "to_phone": cluster_alpha_phone["id"],
                            "mode": "CALL", "duration_sec": 220, "timestamp": "2026-03-14T10:00:00"})
    communications.append({"id": "CDR903", "type": "COMMUNICATION", "from_phone": c_phone["id"], "to_phone": cluster_beta_phone["id"],
                            "mode": "CALL", "duration_sec": 180, "timestamp": "2026-03-14T10:20:00"})

    # A second hidden-link example: Person P015 <-> Person P022 via shared vehicle + shared account
    shared_vehicle = vehicles[4]
    shared_vehicle["owner_id"] = people[14]["id"]
    events.append({"id": "E904", "type": "EVENT", "description": "CCTV flag", "location_id": locations[9]["id"],
                    "timestamp": "2026-02-20T08:00:00", "entities": [people[14]["id"], people[21]["id"]],
                    "note": "Both entities recorded near vehicle " + shared_vehicle["plate"]})

    # --- Engineered contradiction: Person B (Sanjay Iyer) at two places at overlapping times ---
    contradiction_events = [
        {"id": "E905", "type": "EVENT", "description": "Surveillance sighting", "location_id": locations[0]["id"],
         "timestamp": "2026-03-20T20:30:00", "entities": [B["id"]], "note": "Sighting: Chennai"},
        {"id": "E906", "type": "EVENT", "description": "Informant tip", "location_id": locations[1]["id"],
         "timestamp": "2026-03-20T20:45:00", "entities": [B["id"]], "note": "Sighting: Bengaluru"},
    ]
    events += contradiction_events

    reports = []
    fir_titles = ["Suspicious financial transfer reported","Unidentified vehicle near checkpoint",
                  "Informant tip on courier network","CDR analysis request","Surveillance follow-up report",
                  "Cyber-tip: coordinated messaging pattern","Cross-border logistics inquiry",
                  "Anonymous complaint regarding shell accounts","Repeat sighting at Sector-8",
                  "Vehicle plate match flagged","Financial anomaly - structuring pattern",
                  "Digital footprint correlation report","Community liaison report","Border security log excerpt",
                  "Case review - Operation Silent Web"]
    for i in range(15):
        reports.append({
            "id": f"FIR-{i+1:03d}", "type": "REPORT", "category": random.choice(
                ["FIR","CDR","Financial Transactions","Surveillance Report","Case History","Intelligence Report","Vehicle Records"]),
            "title": fir_titles[i],
            "date": rand_date(),
            "summary": f"Synthetic demo report referencing entities and events for investigative training purposes.",
            "linked_entities": [],
        })
    reports[0]["linked_entities"] = [A["id"], a_phone["id"]]
    reports[1]["linked_entities"] = [B["id"], b_phone["id"]]
    reports[13]["linked_entities"] = [C["id"], Dp["id"], bridge_location["id"]]

    dataset = {
        "meta": {"generated": datetime.now().isoformat(), "seed": 42, "disclaimer": "100% synthetic fictional data"},
        "people": people,
        "phones": phones,
        "vehicles": vehicles,
        "accounts": accounts,
        "locations": locations,
        "organizations": organizations,
        "events": events,
        "communications": communications,
        "transactions": transactions,
        "reports": reports,
        "scenario_key_entities": {
            "A_arjun_mehta": A["id"], "B_sanjay_iyer": B["id"], "C_priya_chatterjee_bridge": C["id"],
            "D_vikram_rao": Dp["id"], "F_rohan_bose_emerges_on_removal": Fp["id"],
            "duplicate_pair": ["P010", "P031", "P032"],
            "contradiction_entity": B["id"],
            "bridge_location": bridge_location["id"],
        },
        "cases": [
            {"id": "NX-2026-041", "title": "Operation Silent Web", "status": "ACTIVE", "priority": "CRITICAL",
             "created": "2026-01-05", "assigned_investigator": "Insp. A. Fernandes",
             "description": "Multi-entity financial-communication network under investigation for suspected coordinated illicit activity. Synthetic demo case.",
             "risk_level": "HIGH"},
            {"id": "NX-2026-052", "title": "Project Nightfall", "status": "ACTIVE", "priority": "MEDIUM",
             "created": "2026-02-11", "assigned_investigator": "Insp. R. Nataraj",
             "description": "Logistics-linked network showing anomalous cross-city movement patterns. Synthetic demo case.",
             "risk_level": "MEDIUM"},
            {"id": "NX-2026-063", "title": "Operation Crosslink", "status": "UNDER_REVIEW", "priority": "LOW",
             "created": "2026-03-02", "assigned_investigator": "Insp. K. Suresh",
             "description": "Early-stage intelligence review of a small regional cluster. Synthetic demo case.",
             "risk_level": "LOW"},
        ]
    }
    return dataset

if __name__ == "__main__":
    ds = gen()
    with open(OUT_PATH, "w") as f:
        json.dump(ds, f, indent=2)
    print(f"Wrote {OUT_PATH} with {len(ds['people'])} people, {len(ds['communications'])} comms, "
          f"{len(ds['transactions'])} txns, {len(ds['events'])} events, {len(ds['reports'])} reports.")
