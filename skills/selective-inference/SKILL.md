---
name: selective-inference
description: >
  FDR-controlled selection and honest post-selection inference (Candès school):
  Benjamini–Hochberg on valid p-values, fixed-X and model-X knockoffs for variable
  selection without p-values, conformal p-values + BH for outlier/anomaly lists,
  e-value derandomization for reproducible selections, and the select-then-infer trap
  (winner's curse) with its remedies. Use whenever many hypotheses/features/units are
  screened and the SELECTED SET carries the claim — "which features matter with FDR
  control", "flag anomalous employees/items", "this dashboard tests 50 cuts", "are
  these selected effects real", "my top performers regressed to the mean" — and as the
  audit when someone reports CIs on things they selected by looking. Owns SELECTION
  error control only: NOT prediction coverage (conformal-uq), NOT single-test
  methodology (statistical-grounding rule 2), NOT causal identification (study-design),
  NOT streaming/online hypothesis arrival (anytime-valid owns online FDR).
compatibility: "Bundled scripts/fdr.py (stdlib): BH + conformal p-values with
  synthetic-null FDR verification and a quantified winner's-curse demonstration
  (naive CIs on selected nulls cover ~20% vs 90% nominal). Knockoffs encoded as
  method knowledge (use knockpy/knockoff R pkg in practice). Imports
  statistical-grounding rules 5-6; feeds dossier-style claim audits. Author: Alvaro.
  v1.0.1. Provenance: auto-research run research-candes 2026-07-05 ([src:C-KO01..05])."
metadata:
  version: "1.0.1"
---

# Selective Inference

Selection is a hypothesis-generating machine and an inference-destroying one: the same
data that chose the winners cannot honestly evaluate them. This skill owns both sides —
choosing sets with guaranteed false-discovery control, and refusing the naive inference
that usually follows. Source of truth: run wiki `research-candes`, [[fdr-selection]].

## Decision table

| Situation | Method |
|---|---|
| Valid per-hypothesis p-values, independent/PRDS | BH at level q |
| Valid p-values, arbitrary dependence | BY (log-factor price) |
| Regression feature screening, n ≥ p, linear-Gaussian defensible | fixed-X knockoffs (n≥2p for the augmented construction — verify, D-C001) |
| Feature screening, p ≫ n, covariate distribution estimable | model-X knockoffs (estimate P_X on held-out data; robustness degrades with its KL error) |
| Anomaly/novelty list vs a reference sample | conformal p-values (PRDS ⇒ BH valid) |
| Deliverable must be reproducible | e-value derandomized knockoffs (average e-values across draws, then e-BH) |

Knockoff mechanics worth keeping straight: knockoffs need swap-exchangeability (model-X)
or Gram-matrix matching (fixed-X); importance statistics must be antisymmetric under
X_j ↔ X̃_j; under the null the sign of W_j is a fair coin — that coin is the entire
guarantee.

## The trap this skill exists to catch

**Select-then-naive-infer is invalid.** Naive CIs on data-selected winners cover far
below nominal — `scripts/fdr.py verify` quantifies it (≈20% realized coverage on
selected nulls vs 90% nominal, V4). Workforce analytics hits this constantly: "top performers"
regress, "best training cohort" was noise, "significant" dashboard cells were selected
by scanning. Remedies, in order of practicality: data splitting (select on one half,
infer on the other); report the selection-set FDR guarantee and decline per-item effect
sizes; conditional/selective inference (Lee–Taylor) when the selection rule is clean.

## Verification protocol

`python scripts/fdr.py verify --json` — exit-code gated: BH holds its level under the
global null; the conformal-p + BH outlier pipeline controls realized FDR with high
power; conformal p-values are super-uniform; the winner's curse is reproduced. Run any
local variant against synthetic nulls (known signal set, realized FDR ≤ q over
replicates, power tracked) before production — the house numerical-vv ethos applied to
error control.

## How it composes

statistical-grounding rules 5 (multiplicity) and 6 (selection hazard) route here for
machinery; conformal-uq owns coverage of predictions (its conformal machinery, this
skill's p-values — same calibration idea, different guarantee); dossier-style claim
audits flag any selected-then-inferred number and demand one of the remedies;
people-analytics dashboards get a standing rule — every "top/bottom N" table is a
selection event and carries this skill's caveats.

## Change ledger

| Version | Change | Provenance |
|---|---|---|
| 1.0.1 | Reciprocal boundary: online/streaming FDR routed to anytime-valid | research-ramdas run, 2026-07-05 |
| 1.0 | Baseline | research-candes run |
