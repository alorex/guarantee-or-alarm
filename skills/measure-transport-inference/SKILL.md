---
name: measure-transport-inference
description: >
  Measure transport for inference and simulation (Marzouk school): monotone triangular
  (Knothe–Rosenblatt) maps in two learning regimes — map-from-density (variational, KL
  against an unnormalized target; includes transport-preconditioned MCMC) and
  map-from-samples (maximum likelihood, per-component convex objectives, ATM greedy
  feature selection) — plus block-triangular conditional maps for likelihood-free /
  simulation-based inference and amortized posteriors. Use to sample an awkward
  density, estimate joint/conditional densities from samples, build a generative
  conditional ("sample θ given y without a likelihood"), precondition a badly mixing
  MCMC chain, or on "normalizing flow", "transport map", "push the prior to the
  posterior", "simulation-based inference". Owns COUPLING machinery only: NOT MCMC
  diagnostics/model checking (bayesian-workflow), NOT what to measure
  (bayesian-optimal-design), NOT rare-event tilting (rare-event-is).
compatibility: "Bundled scripts/kr_map.py (stdlib): linear KR map from samples with the
  Gaussian verification anchor (Cholesky recovery, pushforward, Jacobian identity, KR
  conditional = Gaussian conditional). Real work: Python + baptistar/ATM or MParT, or
  normalizing-flow libraries when structure is absent. Imports numerical-vv gates.
  Author: Alvaro. v1.0. Provenance: auto-research run research-marzouk 2026-07-05
  ([src:M-TM01..07])."
metadata:
  version: "1.0"
---

# Measure Transport Inference

One idea, two directions: a monotone triangular map S couples a factorized reference η
to the target π (π = S♯η). Triangular structure buys O(d) Jacobians, back-substitution
inversion, per-component objectives, and — the deep property — **map sparsity mirrors
the target's Markov structure**, so variable ordering is a modeling decision. Source of
truth: run wiki `research-marzouk`, [[triangular-transport]].

## Decision table (start here)

| You have | You want | Use |
|---|---|---|
| Unnormalized density + gradients | samples / moments | map-from-density: min KL(S♯η ‖ π) — normalizing constant drops |
| Unnormalized density, chain mixing badly | efficient MCMC | transport-preconditioned MCMC: learn S from chain history, propose in reference space (watch adaptive-ergodicity) |
| Only samples of π | density estimate / generative model | map-from-samples = ML of S; integrated-rectifier parameterization; ATM greedy + cross-validated stopping |
| Only joint samples (θ, y) | posterior sampler for any y* | block-triangular conditional map: fix observed block, push reference through the θ-block (amortized SBI) |
| No structure to exploit, max expressiveness | generative model | normalizing flow — and accept the loss of interpretability/theory |

## Working rules

1. **Monotonicity by construction, not by constraint.** Use rectified/integrated
   parameterizations (global ∂_{x_k}S_k > 0, convex per-component objectives); pointwise
   monotonicity constraints fail off the training set, restricted parameterizations cost
   expressiveness.
2. **Order variables along the conditional-independence graph.** KR sparsity follows the
   Markov structure; a good ordering yields low-dimensional components; for conditionals,
   the conditioned block must come FIRST.
3. **Regularize by structure, validate by held-out likelihood.** ATM's cross-validated
   greedy stopping is the default against overfitting finite samples.
4. **Diagnostics**: map-from-density — variance of importance weights w = π/(S♯η)
   (a good map has near-degenerate weights); map-from-samples — held-out per-component
   objective; transport-MCMC — ESS per density evaluation and adaptation stabilization.
5. **Verification anchor (run before any real target)**: on a Gaussian, the KR map is
   linear and closed-form — `python scripts/kr_map.py verify --json` checks Cholesky
   recovery, pushforward normality, the log-Jacobian identity, and KR-conditional =
   Gaussian-conditional. Any fancier parameterization must pass its linear subcase.

## How it composes

- **bayesian-workflow** owns model checking and HMC diagnostics; call this skill when
  the posterior geometry defeats the sampler (preconditioning) or the likelihood is
  implicit (SBI). Its high-dim module (v1.1.0) shares the spectral-preflight philosophy.
- **bayesian-optimal-design** consumes transport-based EIG estimators and belief-state
  representations for sequential design (v1.1.0 §sequential).
- **rare-event-is** is the boundary case: measure *change* with explicit weights
  (Girsanov), not couplings — reach for it when the target event is rare, not awkward.
- **learning-design / psychometrics**: conditional maps are a route to amortized ability
  posteriors P(θ | response pattern) when item-bank models outgrow conjugate updates.
