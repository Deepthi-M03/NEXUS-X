# NEXUS-X — Judges' Q&A Preparation

**1. Why AI, and not just a normal database query tool?**
Because the highest-value output — a relationship nobody explicitly
recorded — can't be found with a SELECT statement. It requires scoring
structural, temporal, and financial signals across the whole graph. That
said, we deliberately keep the "AI" fully explainable: every score is a
transparent weighted sum of named features, never a black-box model output.

**2. Why graph analytics specifically?**
Criminal network investigation is inherently relational — the object of
interest is "who connects to whom, how, and when," which is exactly the
graph data model. Centrality, community detection, and path-finding are
mature, well-understood graph algorithms, not experimental ML.

**3. How do you prevent false accusations?**
Every AI output is explicitly labeled CONFIRMED / INFERRED / HYPOTHESIS /
CONTRADICTED / UNVERIFIED and visually distinguished (solid vs dashed
edges, distinct colors). Hypotheses always show supporting AND
contradicting evidence plus what's missing. Nothing auto-promotes to fact
status; every hypothesis requires investigator review before any downstream
use. We use terminology like "entity," "person of interest," and
"analytical hypothesis" — never "criminal" or "suspect."

**4. How is confidence calculated?**
As a fixed-weight sum of six explainable features (common neighbors 25%,
temporal overlap 20%, shared locations 20%, communication correlation 15%,
financial correlation 10%, source reliability 10%). The exact per-feature
scores are visible via "View Score Breakdown" — nothing is randomly
generated.

**5. How do you handle incorrect or conflicting source data?**
The Contradiction Detection Engine actively scans for entities placed at
incompatible locations within a short time window and surfaces them for
review with candidate explanations, rather than silently trusting one
record.

**6. How does entity resolution work?**
A weighted combination of name similarity (fuzzy string matching), phone
number overlap, shared city/address, and consistent age — never a silent
merge. Every match requires an explicit investigator decision: Merge, Keep
Separate, or Review Later.

**7. How is this different from existing commercial link-analysis tools
(e.g. i2 Analyst's Notebook, Palantir)?**
Those tools are primarily visualization and query platforms over data you
already have. NEXUS-X's differentiators are the hidden-link hypothesis
engine (actively proposing unrecorded relationships with visible math),
the evidence challenge engine (what contradicts / what's missing), the
counterfactual simulator, and full human-in-the-loop status tracking on
every AI output — see `docs/INNOVATION.md`.

**8. Can it scale?**
The current prototype runs comfortably at 100–500 nodes / 500–2000 edges
in-process with NetworkX. The repository layer is architected so NetworkX
can be swapped for Neo4j + Graph Data Science at production scale without
changing the API contract (see `docs/architecture.md`).

**9. Can it integrate with NCRB systems (CCTNS, ICJS, etc.)?**
The ingestion layer is designed around category-tagged document uploads
(FIR, CDR, Financial Transactions, Surveillance Report, etc.) that map
directly onto typical NCRB record categories. A production integration
would replace the sample-document/manual-upload path with authenticated
API pulls from CCTNS/ICJS, feeding the same entity-extraction → investigator
review → graph-integration pipeline.

**10. What happens if the LLM hallucinates?**
By default, there is no LLM in the loop at all — the Copilot uses a
deterministic query parser exclusively, so there is nothing to hallucinate.
If an LLM API key is optionally configured, the LLM is only ever allowed to
select a query *intent* (e.g. "path-between" vs "why-important"); the
actual answer is still generated deterministically from the graph. The LLM
can never author graph facts or evidence citations.

**11. How is evidence protected / is data tamper-proof?**
This prototype uses an in-memory, append-only audit log (timestamp, action,
user, case, object) for every ingestion, review, merge, simulation, and
report-generation event. A production deployment would back this with a
write-once storage layer or hash-chained log; the blockchain theme in the
problem statement points naturally toward using a permissioned ledger for
audit-log integrity specifically (not for storing case data itself).

**12. Why is this better than manual investigation?**
It doesn't replace the investigator — it directs their attention. Instead
of manually cross-referencing hundreds of CDRs, transactions, and sighting
reports, the investigator gets a ranked, explainable shortlist of
hypotheses, contradictions, and structurally significant entities to check
first, with the underlying evidence one click away.

**13. Does it use facial recognition or biometric data?**
No. Explicitly excluded by design.

**14. Does it profile by religion, caste, or other protected
characteristics?**
No. NEXUS-X never ingests, infers, or displays such attributes. This is a
hard design constraint, not a configuration option.

**15. What's the accuracy of the hidden-link engine?**
Because this is a synthetic-data prototype, "accuracy" against real
ground truth can't be claimed. What's demonstrable is *reproducibility and
explainability*: identical inputs always yield identical, inspectable
scores — the honest claim is "explainable candidate generation," not "proven
accuracy," which is why every output remains a reviewable hypothesis.

**16. What if two people genuinely have no hidden connection but the
system flags one anyway?**
That's exactly why hypotheses always show contradicting and missing
evidence and require explicit investigator review before any action — the
system is tuned to surface candidates for verification, not to assert
truth.

**17. How do you avoid bias from incomplete or skewed source data?**
The system only reasons over what's explicitly ingested; it doesn't infer
demographic risk profiles. Entity resolution and hidden-link scoring rely
solely on communication, financial, and locational co-occurrence — never
demographic proxies.

**18. What's the biggest current limitation?**
The prototype's frontend is a dependency-free vanilla JS SPA rather than
the originally-scoped Next.js/TypeScript/shadcn stack, chosen deliberately
to guarantee zero-build-step demo reliability. See the README's
Limitations section for the full list.

**19. Could this be gamed by an adversary feeding false records?**
Any ingestion system can be poisoned by bad source data — this is a
general data-integrity problem for any downstream analytics layer, not
specific to NEXUS-X. Mitigations in scope: every extracted entity requires
investigator confirmation before graph integration, and the contradiction
engine is specifically designed to catch inconsistent/conflicting records.

**20. What's the future scope?**
Neo4j + Graph Data Science backend for real scale; authenticated ingestion
from live NCRB/CCTNS feeds; role-based access control and multi-investigator
collaboration; hash-chained/blockchain-backed audit logging; a proper
Next.js/TypeScript frontend rebuild; and richer temporal-community
detection (dynamic community tracking rather than month-snapshot
recomputation).
