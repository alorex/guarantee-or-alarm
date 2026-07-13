---
name: model-hierarchy
description: >
  Multilevel orchestration of models with heterogeneous capability/cost: a capable
  root model plans, locks context, and arbitrates; mid-tier models verify and
  aggregate corrections; cheap leaf models do bulk generation. Structured as an
  MLMC-style telescoping workload with multigrid-style V-cycle traversal and
  a-posteriori-error-driven escalation. Use whenever a task decomposes into many
  parallelizable subtasks with cheap verification (harvesting, extraction, drafting,
  candidate generation, test execution), whenever the user mentions cost/latency
  budgets for agent runs, or says: "use the model tree", "cascade this", "orchestrate
  with cheaper models", "MLMC the workload", "multi-index the axes", "hierarchical
  dispatch", "Haiku workers".
  Do NOT use for holistic-judgment tasks where verification costs as much as
  generation — collapse to 1-2 levels there.
compatibility: "Full form requires an environment that can address multiple models:
  Claude Code subagents (model: field in agent frontmatter), Cowork orchestration, or
  API calls with per-role model strings. Degrades gracefully to role-separation on a
  single model in Chat. Depends on loop-harness for locks, verifier protocol, state,
  and escalation format. Author: Alvaro. v1.2.0"
metadata:
  version: "1.2.0"
---

# Model Hierarchy

Levels $\ell = 0, \dots, L$: $\ell = 0$ cheapest (leaf workers), $\ell = L$ most
capable (root). Per-call cost $C_\ell$, level-$\ell$ output quality with error
$e_\ell$; $C_0 \ll C_L$. The design target is **expected cost near $C_0$ per unit of
work with quality anchored near $e_L$**, achieved by never letting expensive levels
redo cheap work — they compute *corrections*.

## The three load-bearing ideas

**1. Telescoping workload (MLMC; Giles 2008, 2015).** The deliverable is assembled as

$$\text{result} \;=\; \underbrace{\text{bulk work at } \ell=0}_{\text{many cheap calls}} \;+\; \sum_{\ell=1}^{L} \underbrace{\Delta_\ell}_{\text{corrections: few, small-variance}}$$

A mid-tier node receives leaf outputs and emits **deltas** — verdicts, corrections,
aggregations — never regenerated-from-scratch versions. The root receives only
mid-tier deltas and unresolved residuals. Budget allocation follows the MLMC rule
$N_\ell \propto \sqrt{V_\ell / C_\ell}$, with the empirical variance proxy $V_\ell$
= disagreement rate among independent level-$\ell$ samples on probe tasks, measured
in-flight (self-consistency voting is exactly variance reduction by cheap
replication). Operational allocation recipe: `references/allocation.md`.

**2. V-cycle traversal (multigrid; Brandt 1977).** Capable models see *global*
structure — plan coherence, cross-component consistency — that cheap models cannot
see from inside a local subtask; cheap models are excellent smoothers of *local*
error. One work unit is a V-cycle:

```
root:   plan / coarse solve  ──────────────►  arbitrate residuals, correct plan
              │  prolong (decompose)                ▲  restrict (residuals only,
              ▼                                     │   never full outputs)
mid:    contextualize subtasks, verify, delta ──────┤
              │                                     │
              ▼                                     │
leaf:   generate / smooth (best-of-n)  ─────────────┘
```

**3. Escalation = a-posteriori error estimation.** As in adaptive quadrature /
$h$-adaptive FEM: refine only where the local error indicator is large. A leaf
output passing its **deterministic check** (schema, unit test, citation resolution —
loop-harness scripts) and its **mid-tier verification** is accepted and never seen
by anything more expensive. Failure escalates exactly one tier. The root sees only
what survived two filters. Predicates and handoff schemas:
`references/tier-contracts.md`.

## Tier contracts (summary — full schemas in references)

| Tier | Does | Never does | Returns |
|---|---|---|---|
| Root ($L$) | plan, decompose, own the context lock, arbitrate contradictions, decide stop | touch raw material; generate bulk content | corrected plan; final assembly |
| Mid ($0<\ell<L$) | contextualize subtasks downward; verify against locked rubric; aggregate; compute deltas | regenerate leaf work from scratch; modify the lock | `{verdict, delta, residuals[]}` |
| Leaf ($0$) | bulk generation, extraction, drafting, best-of-$n$ candidates, running tests | self-accept; see global context beyond its subtask card | `{output, self_check, confidence}` |

Generator/verifier separation (loop-harness §2) maps onto tiers: the verifier of a
level-$\ell$ output lives at level $\ell{+}1$ (or is a sibling with no generation
context, when the tier gap is unaffordable).

## Where the numerical analogy holds — and the two places it breaks

**Holds:** cost–accuracy tradeoff per level; corrections having small variance;
optimal allocation $\propto \sqrt{V_\ell/C_\ell}$; adaptive refinement driven by
local error indicators; cheap replication as variance reduction. Token-level proof
of concept: speculative decoding (Leviathan, Kalman & Matias, ICML 2023) — draft
proposes, target verifies with exact accept/reject. System-level validation:
cascades with answer-adequacy scoring (FrugalGPT — Chen, Zaharia & Zou 2023,
arXiv:2305.05176; RouteLLM — Ong et al. 2024).

**Breaks (design around these, do not paper over them):**
- **No Richardson extrapolation.** LLM error has no asymptotic expansion in a mesh
  parameter; agreement between tiers $\ell$ and $\ell{+}1$ bounds nothing about tier
  $L$'s view. The root's arbitration is a genuine computation, never an
  extrapolated limit. Never mark work "root-approved" from tier-agreement alone.
- **Correlated errors.** Models trained on overlapping corpora share failure modes:
  $n$ leaf samples agree confidently on the same wrong answer more often than
  independence predicts, so the effective sample size of a leaf ensemble is below
  $n$. Buy diversity through *prompt* variation (and provider variation where
  available — cf. Mixture-of-Agents, Wang et al. 2024), and treat unanimous leaf
  agreement on a checkable claim as still requiring the deterministic check.

## The applicability gate (run this BEFORE building the tree)

The hierarchy pays for itself only where the **verification asymmetry** holds:
checking a leaf output must be materially cheaper than producing it. Audit each
subtask stream:

- Cheap verification (schema conformance, unit tests, citation resolution, recovery
  checks, exact-match extraction): full 3-tier hierarchy.
- Moderate (rubric-graded judgment with a locked rubric): 2 tiers — leaves + a
  capable verifier/orchestrator.
- Expensive/holistic (is this argument persuasive? is this composition good?):
  **collapse to a single capable model.** A mid-tier here adds latency and cost
  without filtering power. This is the analog of losing the smoothing property:
  without it, coarse-grid correction buys nothing.

## Multi-index levels (when "level" has more than one axis) — v1.2.0

The scalar level $\ell$ generalizes to a multi-index $\alpha$ over independent
refinement axes — **model capability × context/evidence size × reasoning effort ×
replication count** — via mixed differences (MIMC; Haji-Ali, Nobile & Tempone,
Numer. Math. 2016). Do not run the corner configuration (best model + max context +
max effort) repeatedly; measure how quality changes along each axis *and whether the
changes interact*.

- **Mixed-regularity probe (admission test).** On 5–10 probe tasks compute the second
  difference $Q(\text{hi},\text{hi}) - Q(\text{hi},\text{lo}) - Q(\text{lo},\text{hi}) + Q(\text{lo},\text{lo})$
  for each axis pair. Near zero ⇒ axes separable ("mixed-regular"): multi-index
  budgeting is justified. Large ⇒ upgrades pay only jointly: collapse that pair into
  one scalar level and stay MLMC-style. This is the skill's second applicability gate,
  run after the verification-asymmetry gate.
- **Profit knapsack (what does the next dollar buy).** Maintain a downward-closed set
  of tried configurations; for each admissible forward neighbor (one axis refined one
  step) estimate profit = marginal quality gain / marginal cost; expand the highest-
  profit neighbor (Gerstner–Griebel adaptivity; Robbe, Nuyens & Vandewalle 2018).
  Anisotropy is the default — the optimal set is a weighted simplex, so cheap axes
  (context, replication) refine deeper than expensive ones (model tier).
- **Cautions.** (a) Coarse levels may need a *different procedure*, not a cheaper
  knob — cheap models often need different prompts/scaffolds to stay coupled to the
  fine estimator (the implicit-tau-leap lesson; Ben Hammouda, Moraes & Tempone 2017).
  (b) Heavy-tailed quality differences break mixed-difference budgeting — the kurtosis
  telemetry from numerical-vv applies per axis pair, not just per level; screen before
  trusting a multi-index allocation (Ben Rached et al. 2023).
- **Calibration anchor.** With two genuine axes (time steps × particles) MIMC beats
  MLMC by a full order (TOL⁻³ → TOL⁻² log²; Haji-Ali & Tempone 2018 — single-school
  result). The analogous win for agents is a hypothesis to measure in the pilot, not a
  theorem to assume.

## Integration with the sibling skills

- **auto-research**: Phase 1 harvesting + extraction = leaf work (claim-in-page is a
  cheap check); Phase 2 compilation = mid-tier; Phase 3 synthesis + Phase 4 verifier
  arbitration + all `INSTRUCTIONS.md` decisions = root. The existing parallel-
  harvest subagents become leaf workers by adding a `model:` field.
- **auto-iterate**: Phase 1 candidate generation = leaf best-of-$n$; Phase 2 rubric
  grading = mid-tier verifier; Phase 4 context assimilation and any rubric question
  = root, always.
- **sketch-to-build**: Leg 1 stays with the user + capable model (it is a
  human-in-the-loop confirmation step, not bulk work); Leg 2 orchestration = root;
  Leg 3 dispatched execution = leaf/mid depending on the checkability of the task.
- **loop-harness** supplies the locks, state spine, deterministic checks, and the
  escalation message format — the hierarchy adds only *who runs what*, orthogonally.

## Run protocol

```
Hierarchy run checklist:
- [ ] Gate: verification asymmetry audited per subtask stream; tier count chosen
- [ ] Contracts: tier assignments + handoff schemas written to hierarchy-plan.md
- [ ] Pilot: ~10 probe subtasks per stream → measure disagreement rate (V_ℓ proxy)
      and per-call cost → set N_ℓ ∝ sqrt(V_ℓ/C_ℓ), write allocation to plan
- [ ] Execute V-cycles; escalate strictly one tier per failure; log every
      escalation in the run log (append-only)
- [ ] Account: per-tier call counts and cost vs. plan in hierarchy-plan.md; if
      realized escalation rate from a stream exceeds ~25%, re-run the gate for
      that stream (its verification asymmetry assumption is failing)
- [ ] Close: root performs final assembly; deliver with the cost accounting
```

## External leaves (OpenRouter free tier)

Tier 0 can be bound to OpenRouter `:free` models via `scripts/leaf_dispatch.py` —
near-zero $C_0$ with genuine cross-family diversity for the correlated-error
problem above. The dispatcher enforces, at script level: the `data_class` card
field (hard refusal of `proprietary`, fail-closed on unclassified), an 18 rpm
throttle with 429-driven roster rotation, a daily-quota preflight that refuses
unfinishable fan-outs, K-card batching with per-card acceptance, best-of-$m$
spread across model families, and append-only call logging in loop-harness format.
Read `references/openrouter-leaves.md` before any external dispatch — the data-
governance section is normative.

## Reference files

| Condition | Load |
|---|---|
| Setting per-tier budgets, computing the allocation, or the pilot design | `references/allocation.md` |
| Writing subtask cards, handoff schemas, or escalation predicates | `references/tier-contracts.md` |
| Dispatching leaf work to OpenRouter `:free` models; anything touching `leaf_dispatch.py`, `data_class`, quotas, or roster maintenance | `references/openrouter-leaves.md` |

## Change ledger

| Version | Change | Provenance |
|---|---|---|
| 1.2.0 | Multi-index levels section: mixed-regularity probe, profit knapsack, coupling/kurtosis cautions | research-tempone wiki (T-MIMC01/04/05/06/08), 2026-07-05 |
| 1.1.4 | Baseline (external leaves, allocation recipe) | — |
