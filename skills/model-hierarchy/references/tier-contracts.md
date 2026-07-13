# Tier Contracts — Subtask Cards, Handoff Schemas, Escalation Predicates

## Subtask card (root/mid → leaf)

A leaf receives a *card*, not the run's context. Minimal by design: leaves that see
global context drift toward re-planning, which is not their job.

```yaml
card_id: <stream>-<seq>
stream: <e.g. harvest.subq3, extract.tables, draft.section2>
task: <imperative, one paragraph max>
inputs: [<explicit artifacts/URLs/snippets — no pointers into global state>]
output_contract:
  format: <schema name or literal structure>
  deterministic_checks: [<script + args that will be run on the output>]
constraints: [<the 2-4 lines of locked context that actually bind this subtask>]
replication: m = <n>            # best-of-n / self-consistency count
data_class: public | synthetic | internal | proprietary   # REQUIRED, fail-closed
```

`data_class` governs *where* a card may run. In-tenant leaves (Claude subagents)
accept any class; external leaf bindings (e.g. `references/openrouter-leaves.md`)
hard-refuse `proprietary` with no override, gate `internal` behind an explicit
flag, and treat a missing value as a refusal — unclassified data is not public by
silence. Classification happens at card-construction time (root/mid), because only
the tier holding global context can judge lineage; the dispatcher merely enforces.

**Deterministic checks must be decision-grade.** A check that passes near-misses
is worse than no check: it launders wrong outputs with a PASS stamp, and the tier
above stops looking. Field-validated failure mode: a substring check
(`findstr /C:"0.6"`) certified a leaf's incorrect posterior mean of 0.625 because
containment is not equality. Rules of thumb: anchor numeric and token matches at
word boundaries (`findstr /R /C:"\<0\.60*\>"`; grep `-w` or `\b...\b`); for
structured outputs, validate the parsed value, not the surface string; and when a
check cannot be made specific, say so in the card — an honest `n/a` routes the
card to verifier judgment, while a leaky PASS routes it nowhere. The check's
specificity bounds the meaning of every PASS it emits.

## Leaf return

```yaml
card_id: ...
output: <the artifact>
self_check: <result of running its own deterministic checks, honestly reported>
confidence: <low|med|high + one-line basis>   # calibration input, never an acceptance criterion
notes: [<anything encountered that seems inconsistent with the card's constraints —
         flagged, not worked around>]
```

`confidence` is advisory only. Acceptance is decided by checks and the tier above,
never by the generator's self-report — the generator/verifier separation applies
within a tier exactly as across tiers.

## Mid-tier return (→ root)

```yaml
stream: ...
verdict: PASS | PARTIAL | FAIL          # against the locked rubric slice for this stream
delta: <the correction actually applied, as a diff — never a regenerated artifact>
aggregation: <merged/deduplicated stream output, if this node aggregates>
residuals:
  - card_id: ...
    failure_mode: <deterministic check name | rubric dimension | contradiction>
    attempts: <k>                        # escalate at k = 2, see predicates
    evidence: <minimal excerpt — the residual, not the full output>
cost_report: {calls: n, tokens: t}
```

**Restriction discipline:** residuals carry the *failure evidence*, not full
outputs. This is what keeps upper-tier context small — the restriction operator in
the V-cycle. A mid node that forwards whole artifacts upward has failed its
contract even if the verdicts are correct.

## Escalation predicates (evaluate in order; first match wins)

1. **Deterministic-check failure** at leaf, attempt 1 → retry once at the same tier
   with the failure diagnostic appended to the card (cheap; most failures are
   local).
2. **Deterministic-check failure, attempt 2** (same card) → escalate one tier with
   both failure diagnostics. Never retry a third time at the same tier — repeated
   identical failure is structure, not noise (the residual/repeat logic from
   auto-iterate's triggers, applied per-card).
3. **Verifier FAIL** at mid tier → return to leaf once with the specific rubric
   gap; second FAIL → escalate to root as a residual.
4. **Contradiction** (two accepted outputs, or an output vs. locked context,
   mutually inconsistent) → escalate directly to root; do not resolve at mid tier.
   Contradictions are global-structure events — coarse-grid territory by
   definition.
5. **Lock-touching request** (anything requiring a change to locked context/rubric)
   → root, always, via the loop-harness escalation format; root decides whether to
   surface to the user.

Strictly one tier per escalation except predicates 4–5. Tier-skipping destroys the
cost profile and, worse, deprives the mid tier of the pattern data it needs for the
in-flight allocation adaptation.

## hierarchy-plan.md (the run's tier state file; loop-harness state conventions apply)

```markdown
# Hierarchy Plan — <run name>
## Gate audit
| Stream | Verification cost vs. generation | Tiers |
|---|---|---|
## Tier assignments
| Tier | Model | Role | Streams |
|---|---|---|---|
## Pilot results
| Stream | C_0 | V_0 (disagreement) | delta rate | Allocation N_0:N_1:N_2 |
|---|---|---|---|---|
## Escalation log (append-only)
| ts | card_id | predicate | from→to | resolution |
|---|---|---|---|---|
## Cost accounting
| Tier | planned calls | actual | tokens | notes |
|---|---|---|---|---|
```

## Claude-ecosystem bindings

- **Claude Code**: one subagent definition per tier role, with `model:` set in the
  agent frontmatter (e.g. haiku for leaf workers, sonnet for verifiers, the most
  capable available model for the coordinator). Cards travel as the subagent task
  prompt; returns as the subagent's final message, schema-validated by
  `loop-harness/scripts/validate_state.py` conventions.
- **API (AI-powered artifact / Cowork)**: per-role model strings on
  `/v1/messages`; the orchestrating context holds `hierarchy-plan.md` and issues
  cards; deterministic checks run in the execution environment between calls.
- **Chat (degraded mode)**: single model, role separation by explicit prompt-level
  switches; the allocation logic reduces to "how many candidates to draft before
  verifying" — still worth running the gate audit, since best-of-n with a locked
  rubric is the two-tier special case.
