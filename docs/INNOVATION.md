# NEXUS-X — Why This Is Not "Just Another Link-Analysis Dashboard"

A conventional criminal-network dashboard shows investigators the
relationships they already have on file: a graph rendering of known
entities and known links. That's useful for visualization, but it puts all
the analytical burden back on the human.

NEXUS-X is built around a different question: **what does the data suggest
might be missing, and how confident should we be?**

## 1. Evidence-backed hidden-link hypotheses, not just visualization
Most link-analysis tools stop at drawing the graph you already have.
NEXUS-X's hidden-link engine actively scans **non-adjacent** entity pairs
for structural, temporal, and financial correlation signals (common
neighbors / Adamic-Adar, shared locations within a time window, correlated
transaction windows) and surfaces candidate relationships that were never
explicitly recorded anywhere — each with a transparent, reproducible
confidence score, not a black-box output.

## 2. Temporal network reconstruction
A static graph hides *when* a relationship became relevant. NEXUS-X
reconstructs the network month-by-month and automatically flags structural
events (e.g. an entity's betweenness centrality jumping sharply), so
investigators can see *when* a person became a bridge — not just that they
currently are one.

## 3. Evidence challenge engine
Every hypothesis is paired with what contradicts it and what's missing —
not just what supports it. This reframes the AI's role from "telling you
the answer" to "telling you what to go verify next," phrased as an
investigative question rather than an operational instruction.

## 4. Contradiction detection
Real casework is full of inconsistent source records. NEXUS-X actively
looks for entities placed in two incompatible locations within a short time
window and surfaces this as a reviewable conflict with candidate
explanations (entity-resolution error, timestamp error, shared device),
rather than silently trusting whichever record loaded last.

## 5. Counterfactual network simulation
Instead of only ranking nodes by centrality, NEXUS-X lets an investigator
ask "what happens to this network's connectivity if this entity weren't
here?" — a temporary, non-destructive simulation that shows fragmentation,
alternative paths, and the entity that would become the new structural
bridge. This is often more persuasive than a raw centrality number, and it
never converts into an operational recommendation ("arrest X").

## 6. Human-in-the-loop by construction, not by policy
Every AI output in NEXUS-X — hypothesis, duplicate-entity match, extracted
entity, contradiction — is stored as its own reviewable object with an
explicit status (`INVESTIGATIVE_HYPOTHESIS`, `PENDING_REVIEW`,
`REVIEW_REQUIRED`, etc.) and requires an investigator action
(Confirm/Reject/Review/Merge/Keep Separate) before it can be treated as
established. Nothing silently promotes itself to "fact" status.

## Net effect
NEXUS-X's value isn't the graph rendering — it's the layer of explainable,
reviewable reasoning sitting on top of it: hypotheses with visible math
behind their confidence, contradictions that get surfaced instead of
buried, and simulations that answer "why does this entity matter?" instead
of just asserting that it does.
