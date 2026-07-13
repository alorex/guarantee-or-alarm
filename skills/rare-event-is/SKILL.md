---
name: rare-event-is
description: >
  Rare-event probability and tail-expectation estimation, all three attack routes:
  control-based IS (variance minimization as stochastic optimal control; Markovian
  projection or policy learning supplies the near-zero-variance tilt), heavy-tailed IS
  (state-dependent mixtures where exponential tilting provably fails — single big
  jump), and multilevel splitting/RESTART (no change of measure at all) — plus
  efficiency-criteria gates (log-efficiency, bounded relative error) and
  multilevel/multi-index wrapping. Use whenever crude Monte Carlo needs infeasible
  sample sizes — "estimate P(failure) ~ 1e-6", "tail probability", "huge relative
  error", "IS keeps blowing up", "exceedance", "heavy-tailed losses" — including
  reliability, outage, and extreme-load questions. Owns RARE-EVENT ESTIMATOR DESIGN
  only: NOT MLMC verification (numerical-vv), NOT posterior fitting
  (bayesian-workflow), NOT experiment informativeness (bayesian-optimal-design), NOT
  output CIs (simulation-output-analysis).
compatibility: "Bundled scripts/is_demo.py (stdlib): Gaussian mean-shift IS with
  closed-form benchmark; verifies unbiasedness, variance reduction, and the
  control-error-costs-variance-not-bias invariant. Imports numerical-vv gates (incl.
  kurtosis telemetry); composes with model-hierarchy/MIMC for multilevel IS. Author:
  Alvaro. v1.1.0. Provenance: research-tempone (T-SOC*) + research-stochsim (S-RE*,
  S-SG*) wikis, 2026-07-05."
metadata:
  version: "1.1.0"
---

# Rare-Event Importance Sampling

Crude MC needs N ≈ 1/(p·RE²) samples for a rare probability p at relative error RE —
hopeless below p ~ 1e-4. The Tempone-school pipeline replaces sample count with a
**designed change of measure**: the estimator's variance-minimization problem is itself a
stochastic optimal control problem, and its value function characterizes the
zero-variance tilt. Source of truth: run wiki `research-tempone`,
[[control-based-importance-sampling]].

## The teachable invariant

**Approximation error in the control costs variance, never bias.** Any Girsanov/
exponential-tilt IS estimator with a *computable* likelihood ratio is exactly unbiased
regardless of how crude the control is; suboptimality only inflates variance. This is
what makes the pipeline practitioner-grade: cheap value-function surrogates are safe,
and the failure mode is detectable (variance/kurtosis telemetry), not silent.
`scripts/is_demo.py` demonstrates it: a deliberately 30%-wrong control stays unbiased
at measurably higher variance.

## The pipeline

1. **Write the target as an expectation** of a path/terminal functional under the
   nominal dynamics; identify the rarity parameter (threshold, noise scale, horizon).
2. **Pose the control problem**: minimize estimator variance over drift controls
   (equivalently, the log-transformed value function solves an HJB/backward recursion).
   Do NOT solve it exactly — that's the curse of dimensionality returning.
3. **Approximate the value function**, in order of preference:
   a. **Analytic/asymptotic** tilt (mean shift to the boundary; large-deviations rate
      function) — often enough, and the demo case;
   b. **Markovian projection**: project the high-dimensional dynamics onto the 1-3
      dimensional observable that defines the event, solve the low-dim control, lift
      the control back (Ben Hammouda et al. 2023);
   c. **Parameterized policy learning** within a control class (learning-based IS,
      Ben Hammouda et al. 2023).
   For McKean–Vlasov/mean-field: decouple first (freeze the law), then control the
   resulting SDE; wrap in double-loop estimators (Ben Rached et al. 2024).
4. **Tilt and weight**: simulate under the controlled measure, multiply by the exact
   likelihood ratio. The ratio must be computed from the *implemented* control, not the
   intended one — that discipline is what preserves unbiasedness.
5. **Wrap in hierarchy when a discretization axis exists**: multilevel IS (levels ×
   tilt) or multi-index IS (time × particles × tilt) — IS is what tames the level-
   difference kurtosis that rare events otherwise inflict on MLMC/MIMC allocations.

## Diagnostics (gate before trusting any estimate)

- **Relative error and its trend** in the rarity parameter: an efficient scheme has
  bounded (or logarithmically growing) RE as the event rarifies; exploding RE ⇒ wrong
  tilt family.
- **Weight degeneracy**: max-weight share and effective sample size; a handful of
  weights carrying the estimate ⇒ the tilt overshoots (variance may be *worse* than
  crude MC — IS is not monotone in aggressiveness).
- **Kurtosis telemetry** (numerical-vv non-negotiable #3 applies verbatim): heavy-tailed
  weights make the variance estimate itself unreliable; report per level when wrapped
  in MLMC/MIMC.
- **Closed-form anchor**: always validate the implementation on a Gaussian/linear case
  with known answer before pointing it at the real system —
  `python scripts/is_demo.py verify --json` is exit-code gated for harness use.

## How it composes

- **numerical-vv** supplies the verification gates (rate checks, kurtosis, CI policy);
  this skill supplies the estimator being verified.
- **model-hierarchy (v1.2.0 multi-index section)**: multilevel/multi-index IS is the
  numerical anchor for the "screen kurtosis before multi-index budgeting" caution.
- **bayesian-workflow**: if the rare event is defined under parameter uncertainty,
  nest this estimator inside the posterior loop, never the reverse.
- **study-design / industrial practice**: reliability and exceedance questions (equipment
  failure, extreme load) are the natural professional workload.

## Route selection (v1.1.0 — the three attack routes)

| Situation | Route |
|---|---|
| Light tails, tractable density, value-function structure | Control-based IS (this skill's core above) |
| Light tails, simple structure | Exponential tilting / large-deviations tilt |
| **Heavy tails** (no exponential moments) | **State-dependent mixture IS** — tilting provably fails: no asymptotically optimal state-INDEPENDENT change of measure exists; rare events happen by ONE BIG JUMP. Blanchet–Glynn: per-step mixture of tail-inflated and nominal proposals, weights state-dependent; certified by Lyapunov/subsolution inequalities. Simpler baseline: hazard-rate twisting. |
| No tractable measure at all (high-dim, non-Markovian), but a progress metric exists | **Multilevel splitting / RESTART** — nested level sets of an importance function γ; split trajectories on up-crossings under ORIGINAL dynamics; p = ∏ conditional level probabilities; fixed-effort variant preferred; RESTART kills retrials on down-crossing. The crux is γ (optimal = the committor); guideline: equalize per-level conditional probabilities. |

Dual failure modes: IS dies by likelihood-ratio blow-up under a mis-specified tilt;
splitting dies by a bad importance function. Both estimators are unbiased; both combine
with RQMC.

## Efficiency-criteria gates (v1.1.0 — verification upgrades)

Hierarchy (weakest→strongest): unbiasedness < logarithmic/asymptotic efficiency <
bounded relative error (BRE: sd/mean bounded as p→0 — fixed-precision cost O(1)) <
vanishing relative error; bounded normal approximation adds CI-coverage reliability.
**Empirical gate (add to the diagnostics section):** run a rarity ladder — estimate
relative error at increasing thresholds; flat ⇒ BRE, rising ⇒ log-efficient at best,
declining ⇒ VRE; monitor ESS/max-weight per rung. Report the achieved class with the
estimate; theorem-level constants for the heavy-tail constructions are flagged
[UNCERTAIN] in the wiki — verify against primaries before quoting.

## Change ledger

| Version | Change | Provenance |
|---|---|---|
| 1.1.0 | Heavy-tail route (Blanchet–Glynn mixtures), splitting/RESTART route + IS-vs-splitting table, efficiency-criteria gates | research-stochsim wiki (S-RE01..06, S-SG01..04) |
| 1.0 | Control-based IS core | research-tempone wiki (T-SOC01..04) |
