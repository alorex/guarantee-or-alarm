---
name: risk-measure-estimation
description: >
  Estimation of risk functionals of a simulated loss distribution (Giles-Haji-Ali-
  Krumscheid school): nested expectation estimators for P(loss beyond threshold) with
  adaptive inner sampling, stochastic root-finding for quantiles/VaR, CVaR/expected
  shortfall via Rockafellar-Uryasev, and MLMC estimation of CDFs, central moments
  (h-statistics), and robustness indicators - one multilevel run yielding CDF + quantile
  + CVaR to tolerance (Krumscheid-Nobile). Use whenever a tail or risk quantity OF A
  DISTRIBUTION is the target - "estimate the 99% VaR", "expected shortfall",
  "probability of large portfolio loss with inner repricing", "nested simulation too
  expensive", "CDF via MLMC", "CVA risk", any nested expectation E[f(E[X|Y])]. Owns
  RISK-FUNCTIONAL estimation only: NOT rare-event tilt design (rare-event-is), NOT
  output CIs (simulation-output-analysis), NOT MLMC code verification (numerical-vv),
  NOT which loss matters (statistical-grounding rule 3 - this skill supplies the
  quantities that rule demands).
compatibility: "Bundled scripts/risk_demo.py (stdlib): Gaussian closed-form anchor (VaR/CVaR recovery, Rockafellar-Uryasev identity, nested-bias law vs analytic form). Imports numerical-vv gates for MLMC deployments; composes with rare-event-is when the tail event is rare. Author: Alvaro. v1.0. Provenance: Tempone coauthor exploration P1, novelty-gate SHARPEN-ADOPT 2026-07-07; primaries web-verified."
metadata:
  version: "1.0"
---

# Risk-Measure Estimation

rare-event-is answers "how likely is this fixed event"; this skill answers "what does
the tail of this distribution look like, and what does it cost me" — quantiles, VaR,
CVaR/expected shortfall, CDFs, and the nested expectations underneath portfolio-loss
probabilities. It is the loss side of statistical-grounding rule 3: decisions name
their loss, and these are the estimators that price it.

## The teachable invariant

**The indicator's discontinuity is the whole game.** In a nested estimator for
P(E[X|Y] > c), inner-sample noise only matters where the conditional mean sits near
the threshold c — everywhere else the indicator is insensitive to it. Uniform inner
sampling therefore wastes almost all of its budget; *adaptive* inner sampling
(more inner samples only for outer scenarios near the boundary) restores MLMC-grade
complexity: O(eps^-2 |log eps|^2) for probabilities, O(eps^-2) for VaR/CVaR via
root-finding (Giles & Haji-Ali, SIAM/ASA JUQ 7(2), 2019). The bias law that drives all
of this is closed-form-checkable: a plain M-inner-sample estimator has bias Theta(1/M)
(Gordy & Juneja, Mgmt Sci 2010) — `scripts/risk_demo.py` verifies it exactly.

## Decision table (start here)

| You have | You want | Use |
|---|---|---|
| iid samples of the loss | VaR_a, CVaR_a | empirical quantile + Rockafellar–Uryasev: CVaR_a = min_t { t + E[(X−t)+]/(1−a) }, minimizer = VaR_a — one convex problem gives both |
| Inner expectation inside the loss (portfolio repricing, CVA) | P(loss > c) | nested MLMC with adaptive inner sampling (Giles–Haji-Ali 2019); budget M ∝ 1/eps if forced to stay non-adaptive (Gordy–Juneja) |
| Same, plus a quantile target | VaR / CVaR | stochastic root-finding on the smoothed CDF wrapped around the nested estimator — O(eps^-2) |
| A simulable model with a discretization axis | CDF, quantile, CVaR simultaneously | Krumscheid–Nobile MLMC for distributions & robustness indicators (arXiv:2208.07252): one multilevel run, all three to tolerance |
| Central moments (variance, skewness of output) | unbiased moment estimates | MLMC h-statistics (Krumscheid–Nobile, JCP 2020) — never plug-in powers of means |
| The tail event is RARE (a beyond ~1−1e-4) | any of the above | compose: this skill's functional + rare-event-is's measure design |

## Pipeline

1. **Name the functional and its tolerance** (eps on VaR? on CVaR? relative or
   absolute?). CVaR error >= quantile error propagated through the tail — budget for it.
2. **Classify the nesting.** No inner expectation → plain empirical/RU route. Inner
   expectation → nested; decide adaptive vs fixed-M by whether you control the inner
   sampler.
3. **Smooth before you root-find.** Quantile estimation through an indicator is
   noisy; sigmoid/kernel smoothing of the CDF (bandwidth tied to level) is what makes
   the multilevel coupling variance decay — the same trick Krumscheid–Nobile use for
   distribution estimation.
4. **Wrap in MLMC when a level axis exists**, and hand the rate/kurtosis checks to
   numerical-vv non-negotiable #3 verbatim — level-difference kurtosis is *worse* for
   indicator functionals than for means; expect to need the smoothing of step 3.
5. **Report per statistical-grounding**: interval + method, and the decision quantity
   itself (P(loss beyond threshold), expected shortfall), not a p-value proxy.

## Diagnostics

- **Bias-law check**: for fixed-M nested estimators, the bias at M and at 4M should
  differ by ~4x (Theta(1/M)); if not, the inner sampler is correlated with the outer
  scenario — a modeling bug, not a variance problem.
- **Boundary concentration**: in adaptive schemes, log the fraction of inner budget
  spent within the smoothing bandwidth of the threshold; << 1 means the adaptation
  isn't engaging (threshold too far in the tail → compose with rare-event-is).
- **RU sanity**: the RU objective is convex in t; a minimizer far from the empirical
  quantile means the tail sample is too thin for the requested a.
- **Closed-form anchor first**: `python scripts/risk_demo.py verify --json`
  (exit-code gated) — Gaussian VaR/CVaR recovery, RU identity, and the nested bias
  law against its analytic value. Any production variant must pass its Gaussian case.

## How it composes

- **rare-event-is**: reciprocal boundary. Rare fixed event → tilt design there;
  distributional functional → here; deep-tail CVaR → both (their measure, this
  functional). *Proposed reciprocal clause for its description: "NOT risk functionals
  of a distribution — VaR/CVaR/nested expectations (risk-measure-estimation)."*
- **simulation-output-analysis**: owns the CI on whatever estimator this skill
  selects (batch means if the loss path is autocorrelated).
- **numerical-vv**: owns rate/telescoping/kurtosis verification of any MLMC deployment.
- **statistical-grounding**: rule 3 consumer — tail functionals are the loss-side
  quantities the contract demands.
- **conformal-uq**: conformal risk control bounds *prediction* risk; this skill
  estimates *simulation/portfolio* risk — don't cross-trigger.

## Literature

| Topic | Read |
|---|---|
| Nested MLMC for loss probabilities, adaptive inner sampling | Giles & Haji-Ali, SIAM/ASA JUQ 7(2):497–525 (2019); arXiv:1802.05016 |
| Nested-simulation bias/budget | Gordy & Juneja, Management Science 56(10) (2010) |
| CVaR as convex minimization | Rockafellar & Uryasev, J. Risk 2 (2000) |
| MLMC central moments (h-statistics) | Krumscheid, Nobile & Verani, JCP 414 (2020) |
| MLMC distributions & robustness indicators | Krumscheid & Nobile et al., arXiv:2208.07252 |
| CVA risk application | Giles & Haji-Ali, arXiv:2301.05886 |
| Multilevel stochastic approximation for VaR/ES | Crépey, Frikha et al., Finance & Stochastics (2025) |

## Change ledger

| Version | Change | Provenance |
|---|---|---|
| 1.0 | Initial: nested/quantile/CVaR ladder, RU route, MLMC distribution module, Gaussian anchor script | Coauthor-exploration P1, gate 2026-07-07 |
