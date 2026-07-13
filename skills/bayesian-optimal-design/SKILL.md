---
name: bayesian-optimal-design
description: >
  Bayesian optimal experimental design via expected information gain (EIG): the estimator
  ladder (Laplace single-loop, double-loop MC, Laplace-based importance sampling,
  multilevel/multi-index and rQMC variants), nuisance-parameter collapse, stochastic-
  gradient design optimization, and closed-form linear-Gaussian verification anchors. Use
  whenever the user chooses WHAT to measure or WHERE to place experiments/sensors/items
  before data exists — "which design maximizes information", "optimal sensor placement",
  "estimate the EIG", "my nested MC estimate drifts with inner samples", "utility of this
  experiment", "D-optimal vs information gain" — and for adaptive-testing item selection
  as max-information design, including SEQUENTIAL design ("what should the next
  experiment be, given results so far"). Owns DESIGN-CRITERION machinery only: NOT randomization/
  power/estimands (study-design), NOT fitting the posterior afterward
  (bayesian-workflow), NOT item calibration (psychometric-calibration).
compatibility: "Bundled scripts/eig_estimators.py (stdlib): DLMC + Laplace estimators
  with a self-verifying linear-Gaussian benchmark (closed-form EIG; O(1/M) inner-bias
  check). Imports numerical-vv for convergence-rate gates; feeds study-design (design
  chosen here, inference planned there) and psychometric-calibration (adaptive testing =
  max-information OED). Author: Alvaro. v1.1.0. Provenance: research-tempone +
  research-marzouk runs 2026-07-05 ([src:T-OED01..08], [src:M-OED01..06])."
metadata:
  version: "1.1.0"
---

# Bayesian Optimal Design

Experimental design as decision theory: choose the design ξ maximizing expected
information gain EIG(ξ) = E_y[D_KL(posterior ‖ prior)] — a **nested expectation** whose
inner integral (the evidence) sits inside a log. Everything difficult about OED follows
from that log, and everything in this skill is machinery for handling it. Source of
truth: the run wiki `research-tempone` (pages [[eig-estimation]], sources T-OED01–08).

## The estimator ladder (choose by posterior concentration × accuracy need)

| Rung | Estimator | Cost/bias structure | Use when |
|---|---|---|---|
| 1 | Laplace single-loop | O(1/N) bias floor (N = repeated obs); cheapest | posterior concentrated + rough ranking of designs suffices |
| 1b | Manifold Laplace | Laplace normal to the concentration manifold | parameters unidentifiable (under-determined designs) |
| 2 | DLMC | consistent; O(ε⁻³): inner O(1/M) bias leaks through the log | small problems, sanity baselines |
| 3 | DLMC + Laplace-IS | consistent at near-Laplace cost; kills underflow | default workhorse |
| 4 | MLMC / MIMC / ML-rQMC | restores ~O(ε⁻²); MIMC when (inner samples × mesh) are both axes | tight tolerances, PDE forward models |

**Nuisance parameters:** never add a third MC loop — collapse the nuisance
marginalization analytically (small-noise/Laplace) so complexity stays two-loop.

## Failure diagnostics (encode as tests, not vibes)

- **Inner-bias drift**: EIG estimate falls systematically as M grows ⇒ you are on rung 2
  reading the bias, not the signal. The bias is *positive* (Jensen: the log of the inner
  average under-estimates the log-evidence, inflating EIG) and ~c/M — verify the ratio
  halves-per-doubling before trusting any DLMC number. `eig_estimators.py verify` does
  exactly this check (observed ratio ≈ 4 per 4× in M).
- **Underflow**: −inf/NaN in the inner log for concentrated likelihoods ⇒ move to
  Laplace-IS (rung 3); more outer samples cannot fix it.
- **Laplace invalidity**: multimodal or unidentifiable posterior ⇒ rung-1 numbers are
  fiction; use manifold Laplace or rungs 3–4.

## Design optimization

Never grid-evaluate EIG over designs. Stochastic gradient ascent with per-iteration
gradient estimates (Laplace gradient: cheap/pre-asymptotically biased; Laplace-IS
gradient: consistent), Nesterov acceleration **with restart** — restart is the specific
mechanism that keeps acceleration stable under gradient noise.

## Verification protocol (numerical-vv applies)

1. **Linear-Gaussian anchor**: EIG has closed form (½·[logdet Σ₀ − logdet Σ_post]);
   Laplace is exact there. Every estimator must reproduce it to statistical tolerance —
   run `python scripts/eig_estimators.py verify --json` (exit-code gated: V1 convergence,
   V2 inner-bias sign/rate, V3 Laplace exactness).
2. **Bias-decay study**: on a mildly nonlinear scalar model, confirm O(1/N) Laplace bias
   and O(1/M) DLMC inner bias before production runs.
3. **Cost-rate check**: observed cost-vs-tolerance slope ≈ −3 for DLMC, ≈ −2 for
   multilevel variants; deviations indicate implementation bugs.

## Sequential OED — design as a belief-MDP (v1.1.0, Marzouk school)

When experiments happen in stages with feedback, design is a finite-horizon dynamic
program: state = (belief/posterior, physical state), action = design, reward =
incremental or terminal information gain (Huan–Marzouk 2016). **Batch design is the
open-loop special case; greedy one-step design is the myopic special case** — locate
your current practice on that ladder before optimizing anything.

- **Myopic vs non-myopic decision rule:** default to greedy when stages are
  cost-decoupled and the horizon is short. Escalate to lookahead/RL policies only under
  stage-coupled costs (movement, shared budgets) or positioning effects (early
  experiments enable informative later ones). Demonstrated non-myopic gains are moderate
  and problem-dependent — not a free lunch.
- **Policy ladder:** (1) ADP — regression value-function approximation + one-step
  lookahead; implicit policy, expensive at decision time (Huan–Marzouk 2016);
  (2) policy-gradient / actor-critic with NN policy — amortized offline, cheap online
  (Shen–Huan 2023). Belief states represented with transport maps
  (measure-transport-inference) for fast approximate posterior updates inside the loops.
- **Static optimization (SA vs SAA):** stochastic approximation (Robbins–Monro/SPSA) is
  robust but tuning-sensitive; SAA (fix common random numbers, then BFGS) is fast but
  inherits the fixed-sample bias (Huan–Marzouk 2014). This complements the Nesterov-
  with-restart guidance above.
- **Discrete selection (sensors/items) — batch greedy with guarantees:** MI objectives
  are generally NOT submodular; guarantees come via submodularity/supermodularity ratios
  (γ, η), with (1−1/e)-type bounds recovered when γ=η=1 and spectral bounds available in
  linear-Gaussian problems (Jagalur-Mohan–Marzouk 2021). Adaptive testing's greedy
  max-information item selection sits exactly here.
- **Estimator ladder extension:** transport/density-approximation EIG estimators — fit
  marginal + conditional densities, average the log-ratio; better-than-nested-MC MSE
  under optimal sample allocation; works for implicit/likelihood-free models; supports
  MI-loss-bounded linear dimension reduction (Li–Baptista–Marzouk 2024). Add as rung 5.

## How it composes

- **study-design** owns randomization, estimands, power; this skill picks the design
  *criterion* and its estimator. Run this first, then hand the chosen design over.
- **psychometric-calibration**: adaptive testing's max-information item selection is
  one-step greedy OED; calibrated item parameters are this skill's inputs, and the
  learning-design adaptive policy is the consumer.
- **bayesian-workflow** fits the model after data arrive; prior predictive checks there
  double as sanity checks on the priors used here.
- **model-hierarchy / MIMC delta**: multilevel EIG estimation is a workload its
  allocation recipe already fits.

## Change ledger

| Version | Change | Provenance |
|---|---|---|
| 1.1.0 | Sequential OED section (belief-MDP, policy ladder, γ/η batch-greedy, transport EIG estimators); closes research-tempone D-001 cross-school | research-marzouk wiki (M-OED01..06) |
| 1.0 | Estimator ladder, diagnostics, SGD design optimization, linear-Gaussian anchor | research-tempone wiki (T-OED01..08) |
