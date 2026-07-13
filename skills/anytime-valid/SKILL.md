---
name: anytime-valid
description: >
  Safe anytime-valid inference (Ramdas school): confidence sequences (time-uniform CIs
  via nonnegative supermartingales + Ville — betting/empirical-Bernstein constructions),
  e-values and e-processes (evidence that composes: multiply independent, average
  dependent, e-BH under arbitrary dependence, universal inference when regularity
  fails), online FDR for streaming hypotheses (LORD→SAFFRON→ADDIS alpha-wealth ladder),
  and deployment discipline for continuously monitored experiments. Use whenever
  results are seen before data collection ends — "the dashboard updates daily", "can
  we stop early", "stakeholders keep peeking", "tests accumulate", "combine evidence
  across sites" — and as the audit catching peeking at fixed-horizon CIs. Owns VALIDITY-UNDER-OPTIONAL-STOPPING only: NOT per-prediction
  coverage under drift (conformal-uq ACI), NOT batch selection (selective-inference),
  NOT sequential design choice (bayesian-optimal-design).
compatibility: "Bundled scripts/cs_demo.py (stdlib): hedged betting confidence sequence
  with verification — peeking at fixed-n CIs measured at ~99% cumulative miscoverage vs
  CS at nominal, honest width price quantified, Ville bound checked at adversarial
  stopping. Production: confseq / expfamily packages, onlineFDR (Bioconductor). Imports
  statistical-grounding rules 2/5/8. Author: Alvaro. v1.0. Provenance: auto-research
  run research-ramdas 2026-07-05 ([src:R-*])."
metadata:
  version: "1.0"
---

# Anytime-Valid Inference

One primitive: a nonnegative supermartingale with M₀ = 1 under the null, plus Ville's
inequality P(∃t: M_t ≥ 1/α) ≤ α — Markov, uniformized over time. Evidence is a bettor's
wealth against the null; anything built this way is valid at EVERY stopping time, so
peeking, early stopping, and optional continuation are free. Source of truth: run wiki
`research-ramdas`.

## The problem this solves

A dashboard that refreshes is a sequential test whether anyone admits it or not.
Checking fixed-horizon 95% CIs at every refresh drives cumulative type-I error toward
certainty (measured: ~99% by t=500 in `cs_demo.py`; ~40%+ reported in production A/B
platforms). The fix is not "don't peek" — it's intervals that survive peeking.

## Confidence sequences (estimation face)

P(∀t: θ ∈ CI_t) ≥ 1−α. For bounded metrics: **hedged betting CS** (capital process per
candidate mean, Kelly-style predictable bets — tightest known) or closed-form
predictable-plug-in empirical-Bernstein; mixtures/stitching give √(log log t / t)
width. **The honest price**: ~1.3–2× wider than the fixed-n CI at the same n
(construction-dependent — simulate per metric); wasteful for a single pre-registered
analysis, mandatory the moment anyone peeks. **Sanity anchor**: Hoeffding CS ⊇ EB CS ⊇
betting CS; a "CS" narrower than the fixed-n Hoeffding CI is a bug.

## E-values (testing face)

E ≥ 0, E_H0[E] ≤ 1; reject at E ≥ 1/α. Composition rules: **multiply** independent or
sequentially-built e-values (exact multi-site meta-analysis, safe under optional
continuation); **average** arbitrarily dependent ones; p→e calibration is lossy, e→p =
1/e is clean — never round-trip. **e-BH**: FDR under arbitrary dependence, no BY
factor. **Universal inference** (split-LRT): finite-sample valid tests with NO
regularity conditions — the escape hatch when Wilks fails (mixture components,
boundary nulls); price is conservativeness. Bayes factors under point nulls are
e-values — sequential Bayesian monitoring becomes safe by reading them as e-processes.

## Online FDR module (streaming multiplicity)

Hypotheses arrive over time, decisions irrevocable: alpha-wealth mechanics (spend per
test, earn per rejection); ladder LORD → SAFFRON (online Storey adaptivity) → ADDIS
(discard conservative nulls). FDR under independence; mFDR/e-value variants under
dependence. Online beats batch BH only when decisions can't wait for the stream to end
— an always-on experimentation program. Batch selection stays in selective-inference.

## Deployment discipline

Pre-register the tuning (mixture parameter / bet schedule) — post-hoc tuning to the
observed effect breaks validity. Display the RUNNING INTERSECTION interval, not the
instantaneous one. Never mix fixed-horizon power calculations with sequential stopping.
Stakeholder sentence: "wider by design — valid at every peek, and you may legitimately
stop the moment it excludes zero." For workforce metrics that confirm slowly (90-day
retention): the trickle-in regime is exactly the CS habitat; pair per-test CSs with
cross-test e-value multiplicity.

## Verification

`python scripts/cs_demo.py verify --json` (exit-code gated): peeking violation
reproduced (~99% cumulative miscoverage), CS time-uniform at nominal, honest width
price measured, Ville bound checked under stop-at-max adversarial stopping.

## How it composes

statistical-grounding rules 2/5/8 route here for anything monitored; conformal-uq's
ACI owns streaming per-prediction coverage (this skill owns streaming
parameters/effects); selective-inference owns batch selection (reciprocal boundary);
bayesian-optimal-design owns WHAT to run next (this skill owns when you may stop);
causal-ml's adaptive-experiment corrections and this skill's CSs meet in
learning-design's practice engines — log propensities AND use anytime intervals.
