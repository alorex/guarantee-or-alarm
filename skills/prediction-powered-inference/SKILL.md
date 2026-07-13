---
name: prediction-powered-inference
description: >
  Valid statistical inference when most labels are model-imputed (Jordan school): the
  PPI rectifier (small gold-standard set corrects an ML-imputed estimate; CIs cover the
  population estimand regardless of model quality), PPI++ power-tuning (asymptotically
  never worse than classical), cross-prediction when no pretrained model exists, and
  active label allocation under a budget. Use whenever a CI, p-value, or regression is
  about to be computed partly from model predictions — "we only have confirmed labels
  for a fraction", "can we use the LLM's labels", "survey plus model imputation",
  "attrition confirmed months later", "annotate a sample and extrapolate" — and as the
  audit that blocks naive-imputation inference (treating predictions as data), which
  silently undercovers. Owns INFERENCE-WITH-PREDICTED-LABELS only: NOT per-prediction
  coverage (conformal-uq), NOT selection error control (selective-inference), NOT the
  labeling model itself.
compatibility: "Bundled scripts/ppi.py (stdlib): mean-case PPI/PPI++ with coverage
  verification (naive imputation collapses to ~0 coverage; PPI nominal; lambda-tuning
  never-lose property). Production: ppi-py (Python) / ipd (R). Requires the labeled
  subset to be a random or known-probability sample. Imports statistical-grounding
  rules 1-2. Author: Alvaro. v1.0. Provenance: auto-research run research-jordan
  2026-07-05 ([src:J-PPI01..06])."
metadata:
  version: "1.0"
---

# Prediction-Powered Inference

The estimator everyone wants to use — run the model on everything, compute statistics on
its outputs — is invalid: prediction bias transmits directly into the estimate and CIs
can undercover toward zero as N grows. PPI keeps the convenience and restores validity
with one move: a **rectifier** estimated on a small trusted sample. Source of truth:
run wiki `research-jordan`, [[prediction-powered-inference]].

## The estimator

θ̂_PP = (imputed estimate on N unlabeled) − (1/n)Σ[f(Xᵢ) − Yᵢ] on the n labeled.
The rectifier is unbiased for the imputation error, so the CI covers the population
estimand for ANY f — model quality buys width, never validity (the conformal-uq
philosophy applied to estimation). **PPI++**: scale the prediction term by λ̂ chosen to
minimize variance; λ̂→0 recovers the classical labeled-only estimator, so tuned PPI
asymptotically never loses. **Cross-prediction**: no pretrained model — cross-fit the
predictor on the labeled data itself. **Active inference**: spend the label budget where
the model is unsure.

## Hard requirements (the guarantee's fine print)

1. The labeled subset is a **random (or known-probability) sample** of the population
   the unlabeled set represents. Convenience-labeled or MNAR subsets break the
   rectifier — this is the requirement practitioners violate first.
2. Same distribution across labeled/unlabeled (or model the shift with weights).
3. n large enough that rectifier variance doesn't dominate (check the CI decomposition;
   if the rectifier term dominates, PPI ≈ classical and the imputation bought nothing).

## Daily-work map (workforce / training / education analytics)

Attrition (confirmed months later), performance labels (sparse, expensive), engagement
constructs, item-response coding, LLM-assisted text annotation at scale: impute on the
full population, confirm a RANDOM subset, run PPI — and refuse any deliverable whose
CI was computed on predictions-as-data. LLM-labeler pipelines get a bonus: the labeled
subset doubles as the labeler's calibration data (conformal-uq gates), but keep the
leakage rule — samples used to tune the labeler can't also be the rectifier sample.

## Verification

`python scripts/ppi.py verify --json` (exit-code gated): naive-imputation coverage
collapses (≈0 at the test settings), PPI hits nominal, PPI beats classical width with an
informative predictor, λ̂ tuning is sane (≈0.9 informative / ≈0 noise, never-lose width
ratio ≈1). Run any local variant against this pattern before production
(numerical-vv ethos).

## How it composes

statistical-grounding rules 1–2 route here whenever predicted labels feed an interval;
conformal-uq covers the per-prediction question ("is THIS prediction right"), this skill
the population question ("what's the true rate, given imperfect predictions");
selective-inference takes over when the PPI output feeds a screened selection;
learning-design analytics (mastery rates from model-scored work) are a native consumer.
