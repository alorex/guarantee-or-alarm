---
name: causal-ml
description: >
  ML-powered causal estimation with honest inference (Athey–Imbens–Wager + Chernozhukov
  schools): heterogeneous treatment effects via honest causal forests/GRF and the
  R-learner with RATE/Qini evaluation; double/debiased ML (Neyman orthogonality +
  cross-fitting) with omitted-variable sensitivity bounds; policy learning from AIPW
  scores under budget constraints with off-policy evaluation and adaptive-experiment
  corrections; and panel methods (synthetic control, SDID, matrix completion,
  staggered-DiD traps). Use whenever a treatment/program/policy EFFECT is estimated
  with ML anywhere in the pipeline — "who benefits from training", "did the program
  work, observationally", "assign treatments under a budget", "one site got the policy",
  "staggered rollout", "our A/B was a bandit" — AFTER identification is settled. Owns
  ESTIMATION only: NOT identification/DAGs/estimands/randomization (study-design), NOT
  model fitting per se (bayesian-workflow), NOT sequential design (bayesian-optimal-design).
compatibility: "Bundled scripts/dml_demo.py (stdlib): confounded synthetic data where
  naive OLS and non-orthogonal residualization are provably biased, DML covers at
  nominal rate, and the orthogonality signature (quadratic bias in nuisance tilt) is
  reproduced. Production: grf (R), DoubleML (Py/R), synthdid, did. Imports
  statistical-grounding; hands identification to study-design. Author: Alvaro. v1.0.
  Provenance: auto-research run research-causal-ml 2026-07-05 ([src:CM-*])."
metadata:
  version: "1.0"
---

# Causal ML

One trick instantiated everywhere: **orthogonalize, then cross-fit** — make the target
first-order insensitive to nuisance error, and never let an observation score itself.
AIPW scores are the universal currency. This skill is the estimation counterpart to
study-design: it never rescues a bad adjustment set, and it starts only after the
identification story is written. Source of truth: run wiki `research-causal-ml`.

## Module 1 — Heterogeneous effects (who benefits?)

Honest forests (disjoint split/estimate subsamples ⇒ valid pointwise CIs) / GRF (forest
weights into a local moment equation) / R-learner (residual-on-residual, quasi-oracle
under o(n^-1/4) cross-fit nuisances). Report GATEs over interpretable segments, never
raw individual CATEs; heterogeneity claims require held-out evidence
(`test_calibration`, then RATE/Qini on data not used to fit the rule). **Null
discipline: on constant-effect data the pipeline must find nothing** — that check is
half the verification recipe and the half practitioners skip.

## Module 2 — DML (average effects, observationally)

Naive ML plug-in fails twice (regularization bias, own-observation bias); orthogonal
scores + K-fold cross-fitting (K=4–5, DML2) fix both with nuisances at n^-1/4 rates.
PLR when constant effect is defensible; AIPW/interactive score for ATE with binary
treatment. **Mandatory before causal wording: OVB sensitivity bounds** (bias bounded by
confounder→outcome × confounder→treatment strength, benchmarked against observed
covariates — dml.sensemakr). An observational workforce effect without a sensitivity bound
violates the statistical-grounding contract.

## Module 3 — Policy learning (assign under constraints)

Per-unit AIPW scores → maximize policy value over a CONSTRAINED class (budget,
interpretability, legality); regret ~ √(VC(Π)/n). Off-policy evaluation needs logged
propensities bounded away from 0/1. **Adaptive collection (bandits, adaptive practice
engines) biases naive means** — use variance-stabilizing adaptive reweighting of AIPW
terms; this is why statistical-grounding rule 8 mandates propensity logging, and why
learning-design engines must log at decision time.

## Module 4 — Panel methods (org-level rollouts)

One/few treated + long T → SC/SDID (SDID default: unit + time weights, robust between
DiD and SC); many treated/staggered → MC-NNM or Callaway–Sant'Anna. **Never naive TWFE
on staggered adoption** (forbidden comparisons, sign can flip — run the Goodman-Bacon
decomposition whenever TWFE is reported). One treated unit ⇒ permutation inference only
(min p = 1/(J+1)); placebo-in-space, placebo-in-time, leave-one-donor-out are the
verification battery.

## Verification

`python scripts/dml_demo.py verify --json` (exit-code gated): naive OLS biased by the
predicted confounding amount, non-orthogonal residualization badly biased, DML covers
at nominal rate, and bias grows quadratically (not linearly) under systematic nuisance
tilt — the defining signature of an orthogonal score, measured.

## How it composes

study-design owns the estimand, DAG, overlap argument, and pre-analysis plan — no
identification story, no causal-ml; bayesian-optimal-design owns what to measure next;
learning-design supplies the assignment engines whose logs Module 3 consumes;
trigger-arena boundary: "design a pilot" routes to study-design, "estimate the effect
from these logs" routes here.
