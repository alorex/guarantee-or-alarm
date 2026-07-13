---
name: conformal-uq
description: >
  Distribution-free uncertainty quantification via conformal prediction (Candès school):
  split conformal with the exact finite-sample guarantee, CQR for heteroscedastic
  regression, APS/RAPS prediction sets for classification, jackknife+/CV+, weighted
  conformal under covariate shift, adaptive/online conformal (ACI/dtACI) for streaming,
  conformal risk control for monotone losses, and calibrated acceptance gates for
  LLM/verifier pipelines (conformal alignment, abstention, trust-or-escalate). Use
  whenever a prediction feeds a decision and needs coverage a model can't fake —
  "prediction interval for this score", "how confident is the classifier", "guarantee
  the flagged list misses at most 10%", "calibrate the verifier threshold", "coverage
  under drift" — and for monitoring deployed models. Owns COVERAGE/RISK guarantees for
  predictions only: NOT FDR-controlled selection (selective-inference), NOT posterior
  inference (bayesian-workflow), NOT what the loss should be (statistical-grounding).
compatibility: "Bundled scripts/conformal.py (stdlib): split conformal with exact
  finite-sample verification — band check, off-by-one bug detection, Beta-spread
  validation, adaptive-score coverage. Calibration data must be untouched by training
  (leakage rule). Imports statistical-grounding rule 4; gates compose with
  trigger-arena labels and model-hierarchy escalation. Author: Alvaro. v1.0.
  Provenance: auto-research run research-candes 2026-07-05 ([src:C-CP/SH/LLM])."
metadata:
  version: "1.0"
---

# Conformal UQ

Exchangeability is the only assumption; everything else is bought with a held-out
calibration set: 1−α ≤ P(Y ∈ C(X)) ≤ 1−α + 1/(n+1), finite-sample, for ANY model —
quality buys narrow sets, never validity. Source of truth: run wiki `research-candes`,
[[conformal-core]] / [[shift-online]] / [[verifier-gates]].

## The recipe (always the same skeleton)

Fit on D_train → score D_cal → q̂ = the ⌈(n+1)(1−α)⌉-th smallest score → C(x) =
{y : s(x,y) ≤ q̂}. The (n+1) correction is load-bearing: a naive n-quantile undercovers
by ~1/(n+1) — `scripts/conformal.py verify` detects exactly this bug. Hard floor
n ≥ ⌈1/α⌉−1; n ≈ 1000 keeps realized coverage (∼Beta(n+1−l, l)) within ±1%.

## Score-selection table

| Task | Score | Notes |
|---|---|---|
| Regression, homoscedastic | \|y−μ̂(x)\| | constant width |
| Regression, real data | CQR: max{q̂_lo−y, y−q̂_hi} | heteroscedasticity-adaptive default |
| Classification, smallest sets | 1−π̂_y | worst conditional adaptivity |
| Classification, adaptive | APS (randomized cumulative mass) | exact coverage w/ randomization |
| Many classes | RAPS (APS + rank penalty) | tune λ, k_reg on a separate split |
| No split to spare | jackknife+ | ≥ 1−2α worst case; plain jackknife has NO guarantee |

## Non-exchangeable regimes

Known covariate shift + stable P(Y|X) → weighted conformal (check the effective sample
size of estimated weights). Slow unmodeled drift → fixed decaying weights, TV-bounded
degradation. Streaming with feedback → ACI: αₜ₊₁ = αₜ + γ(α − errₜ) — long-run coverage
under arbitrary shift, but as a TIME-AVERAGE (intervals oscillate; dtACI tunes γ).
KPI ≠ coverage → conformal risk control: calibrate λ̂ so E[monotone loss] ≤ α (e.g.,
"miss ≤10% of true leavers" on a flagged-employee list).

## Calibrated gates for agent/verifier pipelines

Any verifier score + labeled reference batch ⇒ conformal-alignment acceptance gate:
of everything auto-accepted, ≤ α is bad (FDR-style). Abstention variants bound error
among emitted answers; trust-or-escalate gives model-hierarchy a provable per-tier
accepted-but-wrong bound ("auto-accept leaf output only if the gate passes"). Existing
eval/battery labels are the calibration data — but ONLY labels never used to tune the
gated scorer (leakage rule). Guarantees are marginal, per-(task, model, scorer), and
die on model updates — recalibrate, and monitor rolling coverage (ACI when streaming).

## Hard rules

1. Calibration data untouched by fitting/tuning/score selection — leakage kills the
   guarantee silently.
2. Report the realized-coverage Beta interval, never just "guaranteed 1−α".
3. Marginal ≠ conditional: per-group validity needs per-group calibration; per-instance
   conditional coverage is impossible distribution-free. Say so in deliverables.
4. Run `python scripts/conformal.py verify --json` before trusting any local variant.

## How it composes

statistical-grounding rule 4 names this machinery — this skill is its implementation.
selective-inference owns FDR over SELECTIONS (conformal p-values live there);
bayesian-workflow owns posteriors (conformal wraps its point predictions when
distribution-free cover is needed); learning-design mastery decisions can carry
conformal risk control ("false-mastery ≤ α" as a monotone loss).
