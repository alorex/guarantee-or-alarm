---
name: statistical-grounding
description: >
  BASE meta-skill: the statistical conscience of the library. Enforces decision-theoretic
  and UQ discipline across ALL work — no naked point estimates, comparisons name their
  null and error control, decisions name their loss, resampling (permutation/bootstrap)
  preferred when assumptions are doubtful, calibration and proper scoring for predictions
  feeding decisions, declared multiplicity control, selective-inference hazards flagged.
  Use whenever a deliverable reports numbers that inform a decision — people/workforce
  analytics, training analytics, psychometrics, ML model choices, dashboards, A/B
  readouts — "is this difference real", "how sure are we", "quantify the uncertainty" —
  and as the grounding audit before anything ships. Also owns the SCHOOL-MINING LOOP
  (expand the library by mining prolific authors; Tempone pattern). NOT fitting
  (bayesian-workflow), NOT design (study-design / bayesian-optimal-design), NOT code V&V
  (numerical-vv).
compatibility: "Bundled scripts/resample.py (stdlib): seeded permutation test +
  percentile/BCa bootstrap with self-verifying null-calibration and coverage checks.
  references/author-roster.md: prioritized school-mining queue. BASE skill imported by
  data:*, dossier-style, study-design, learning-design, model-hierarchy, trigger-arena.
  Portable across surfaces. Author: Alvaro. v1.1.0 (live roster externalized to
  project state; bundled copy = seed). Provenance: distilled 2026-07-05."
metadata:
  version: "1.1.0"
---

# Statistical Grounding

Decision theory is the unifying frame: every analysis in daily work — a training-program
readout, an attrition model, an item bank decision, a model-hierarchy budget — terminates
in a decision under uncertainty, and the quality of that decision is bounded by the
honesty of the uncertainty statement behind it (Berger, *Statistical Decision Theory and
Bayesian Analysis*; Savage 1954). This skill is the library's enforcement layer for that
fact, the way loop-harness is the enforcement layer for loops.

## The grounding contract (non-negotiables)

1. **No naked point estimates.** Any number informing a decision carries an interval
   (CI, credible interval, or posterior summary) and names its method. A dashboard cell
   without uncertainty is a defect, not a simplification.
2. **Comparisons name their null and their error control.** Default to resampling when
   parametric assumptions are doubtful: **permutation** for exchangeable-under-null
   comparisons (state the exchangeability argument — blocked/stratified permutation when
   units aren't freely exchangeable); **bootstrap** for standard errors and CIs (BCa
   default; know the failure modes: heavy tails, dependence → block bootstrap, tiny n,
   statistics on the boundary). Efron & Tibshirani (1993); Good (2005).
3. **Decisions name their loss.** Report the decision-relevant quantity: P(effect >
   practically-relevant threshold), expected utility under the stated loss, cost-weighted
   classification thresholds — not a p-value alone. Value-of-information closes the loop
   with bayesian-optimal-design: EIG is expected VoI under log loss.
4. **Predictions feeding decisions get calibration + proper scoring rules** (Brier/log
   score, reliability diagrams; Gneiting & Raftery 2007). When model-agnostic coverage
   is needed, use **conformal prediction** — distribution-free finite-sample intervals
   (Vovk; Angelopoulos & Bates 2023 tutorial).
5. **Multiplicity is declared.** FWER or FDR (Benjamini–Hochberg), chosen before
   looking. People-analytics dashboards are multiplicity machines: dozens of cuts ×
   metrics × periods silently multiply the error budget.
6. **Selection invalidates naive inference.** Choosing the model/subgroup/feature first
   and then computing its CI on the same data is the classic silent error (Efron,
   *Large-Scale Inference* 2010; Candès knockoffs for selection with FDR control).
   Split, adjust, or flag — never ignore.
7. **Entropy/information criteria used with their assumptions.** AIC/WAIC/LOO for
   predictive comparison (PSIS-LOO mechanics live in bayesian-workflow); mutual
   information estimated with stated estimator bias; MDL framing when compression is
   the honest objective.
8. **Sequential/adaptive decisions log for off-policy evaluation.** Any bandit-like
   allocation (adaptive training assignment, item selection) must log propensities so
   later analysis is possible — the RL-flavored corner of the contract.

## Daily-work decision map (workforce / training analytics)

- **Training evaluation**: Kirkpatrick levels are outcomes, not designs — causal claims
  route to study-design; this skill owns the uncertainty statement on whatever design
  emerges, and the loss function ("what decision does this evaluation feed?").
- **Selection/promotion analytics**: range restriction and selection-on-observables
  hazards flagged (corrections carry their own uncertainty); fairness metrics reported
  WITH intervals — a point-estimate fairness gap is contract violation #1.
- **Attrition/performance models**: calibration before discrimination; cost-sensitive
  thresholds from the stated loss matrix, never 0.5-by-default.
- **Psychometrics**: CSEM and classification-consistency statements are the grounding
  layer's outputs; the machinery lives in psychometric-calibration.

## Resampling toolkit

`python scripts/resample.py verify --json` — exit-code-gated self-check (null
calibration of the permutation test, bootstrap coverage vs nominal). Then:
`resample.py perm --a a.csv --b b.csv` / `resample.py boot --data x.csv --stat mean --ci bca`.
Use the script for real analyses; the point of bundling it is that the *tool that makes
the uncertainty statement is itself verified* (numerical-vv ethos applied to statistics).

## The school-mining loop (meta feature)

The library grows by mining methodological schools, not by browsing marketplaces.
Protocol (distilled from the research-tempone run, 2026-07-05):
1. Nominate a prolific author/school from the LIVE roster kept as git-tracked
   state in the operator's project archive (not distributed with this skill;
   the bundled `references/author-roster.md` is a SEED TEMPLATE only, frozen at
   install time — never treat it as current).
2. Run auto-research at Standard depth: 3-5 cluster sub-questions, parallel harvest,
   level-2 admission, verifier pass, persistent wiki.
3. novelty-gate each cluster against the library: ADOPT (build with verified script) /
   MERGE (delta + version bump + ledger) / DEFER (logged trigger condition).
4. trigger-arena regression after any description change.
Cadence: one school per session-block; update the LIVE roster's status column (state
lives in the project, not in this package — skills are logic, rosters are state, per
loop-harness §3); wikis accumulate in outputs/research-<author>/.

## Composition

BASE skill: data:analyze/statistical-analysis import the contract wholesale;
dossier-style's claim/evidence audit checks contract conformance; study-design and
bayesian-optimal-design own upstream design; bayesian-workflow owns fitting;
trigger-arena's precision/recall get binomial intervals per this contract (its own
battery is small-sample data); model-hierarchy's allocation estimates (V_ℓ proxies)
are statistics and inherit rule 1. When any skill and this contract conflict, the
contract wins — escalate rather than ship an ungrounded number.
