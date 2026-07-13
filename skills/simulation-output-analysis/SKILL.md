---
name: simulation-output-analysis
description: >
  Statistical analysis of stochastic-simulation OUTPUT (Glynn school): batch-means and
  regenerative confidence intervals with the variance-inflation correction (naive iid
  SEs are wrong by the integrated autocorrelation time), warm-up/initial-transient
  deletion (MSER-family), valid sequential stopping, MCMC standard errors and ESS,
  unbiased estimation via randomized truncation (Rhee–Glynn; couplings), and
  Monte Carlo gradient estimation (IPA vs likelihood-ratio vs SPSA). Use whenever a
  simulation or MCMC run produces numbers someone will act on — "how long should this
  run", "CI for a steady-state metric", "is the warm-up over", "MCMC standard error",
  "stop when the CI is tight enough", "unbiased parallel replications", "gradient of a
  simulation output" — and as the audit catching iid standard errors on autocorrelated
  output. Owns OUTPUT statistics only: NOT code correctness (numerical-vv), NOT
  rare-event measure design (rare-event-is), NOT arbitrary-peeking validity
  (anytime-valid).
compatibility: "Bundled scripts/soa_demo.py (stdlib): AR(1) known-answer verification —
  naive-CI collapse by the predicted sqrt(tau) factor, batch-means coverage restored,
  tau recovered, warm-up bias eliminated, batch-count robustness. Production: mcmcse
  (R), arviz ESS. Feeds bayesian-workflow (MCMC SEs) and model-hierarchy (beta/gamma
  taxonomy for unbiasing). Author: Alvaro. v1.0. Provenance: auto-research run
  research-stochsim 2026-07-05 (Glynn+Rubino school, [src:S-*])."
metadata:
  version: "1.0"
---

# Simulation Output Analysis

numerical-vv certifies the simulator is *coded correctly*; this skill owns what its
outputs *mean*: the invariant object is the asymptotic (time-average) variance
constant, not the marginal variance, and every recipe here estimates or exploits it
honestly. Source of truth: run wiki `research-stochsim`.

## Core: CIs under autocorrelation

Var(X̄_n) ≈ (marginal σ²/n) · τ_int, τ_int = 1 + 2Σρ_k. The naive iid SE misses the
factor τ_int entirely — CIs too narrow by √τ_int (measured in `soa_demo.py`: φ=0.9
AR(1), τ=19, naive coverage 0.37 vs nominal 0.95). Recipes:

- **Batch means** (default): b batches of size m, t-CI with b−1 df; √n rule (b=m=√n)
  or MSE-optimal m ∝ n^{1/3}; consistency needs BOTH b→∞ and m→∞.
- **Regenerative** (when regeneration points are identifiable): iid cycles, steady-state
  mean = E[Y]/E[τ], delta-method CI — no batch tuning.
- **Always report ESS = n/τ̂** beside any simulation/MCMC estimate; MCMC standard
  errors are the same mathematics (mcmcse; feeds bayesian-workflow non-negotiable #3).

## Pipeline order

1. **Warm-up deletion first** (MSER-5 default; initialization bias does not average
   out — it decays, and slowly under high autocorrelation), 2. then variance
   estimation, 3. then (optionally) **sequential stopping**: "run until half-width ≤ ε"
   is valid iff an FCLT holds AND the variance estimator is strongly consistent
   (Glynn–Whitt) — never pair a stopping rule with a naive iid SE. Boundary:
   anytime-valid owns arbitrary-peeking dashboards; Glynn–Whitt licenses the classical
   fixed-precision rule for a simulation you control.

## Module: unbiased estimation (randomized truncation)

μ = ΣΔ_n; draw level N with tail p_n; Z = Σ_{n≤N} Δ_n/p_n is exactly unbiased — MLMC
with a randomized top level: iid replicates, embarrassing parallelism, no bias
budgeting. **Gate before use**: finite variance requires Σ E[Δ_n²]/p_n < ∞ and finite
cost Σ c_n p_n < ∞ — satisfiable together only when β > γ (variance decays faster than
cost grows); otherwise MLMC's controlled bias is safer. Couplings instantiate Δ_n for
Markov chains (unbiased MCMC, burn-in removed). Finite mean ≠ usable.

## Module: gradient estimation

IPA/pathwise (differentiate the path, seed fixed): unbiased iff the response is a.s.
continuous in θ; lowest variance. LR/score (differentiate the density): handles
discontinuous responses; variance grows with horizon. SPSA: derivative-free fallback,
two evaluations regardless of dimension. Decision rule: smooth response → IPA;
θ-in-distribution or discontinuous → LR; black box → SPSA. Boundary:
bayesian-optimal-design's SGD loop CONSUMES the estimator this module selects.

## Verification

`python scripts/soa_demo.py verify --json` (exit-code gated): naive collapse by the
known factor, batch-means coverage restored, τ_int recovered, warm-up bias
eliminated by deletion, batch-count robustness. Run any local variant against a
known-τ process before production.

## How it composes

bayesian-workflow (MCMC SEs and ESS are this skill's machinery); numerical-vv (code
correct → THEN this skill; its CI-gate policy applies to these CIs); rare-event-is
(rare-event outputs need this skill's SEs plus that skill's measure design);
model-hierarchy (β/γ taxonomy shared with the unbiasing module); anytime-valid
(reciprocal stopping-validity boundary); learning-design simulations (policy
simulators must report BM CIs, not iid SEs).
