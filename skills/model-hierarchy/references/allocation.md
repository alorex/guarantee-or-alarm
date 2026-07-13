# Allocation — Operationalizing $N_\ell \propto \sqrt{V_\ell / C_\ell}$

The MLMC sample-allocation rule minimizes total cost $\sum_\ell N_\ell C_\ell$
subject to a target variance $\sum_\ell V_\ell / N_\ell \le \varepsilon^2$; the
Lagrangian optimum is $N_\ell \propto \sqrt{V_\ell / C_\ell}$ (Giles 2008; the 2015
*Acta Numerica* survey, §2, for the constrained-optimization derivation). The LLM
translation requires empirical stand-ins for $V_\ell$ and $C_\ell$ and honesty about
where the i.i.d. assumptions bend.

## Measurable quantities

- **$C_\ell$**: realized cost per call at tier $\ell$ — token price × mean tokens
  per subtask, or wall-clock if latency is the binding constraint. Measure from the
  pilot, don't use list prices alone: tier-$0$ subtasks are usually shorter, which
  compounds the price ratio.
- **$V_\ell$ proxy**: disagreement rate among $m$ independent level-$\ell$ samples
  on the same probe subtask, averaged over ~10 probes per stream. For discrete
  outputs: $1 - \max_a \hat p(a)$ (one minus the modal agreement). For graded
  outputs: variance of the verifier score across the $m$ samples. This is the
  self-consistency statistic (Wang et al., ICLR 2023) repurposed as a variance
  estimator.
- **Correction variance $V_{\Delta_\ell}$**: at mid tiers, what matters is the
  variance of the *delta* — how often does tier-$\ell$ verification change the
  tier-$(\ell{-}1)$ answer? Small delta variance is precisely what justifies few
  calls at that tier. If deltas are large and frequent, the tier below is
  under-capable for that stream: shift the stream up one tier rather than
  compensating with more corrections.

## Pilot design

~10 probe subtasks per stream, $m = 3\text{–}5$ replicates at tier 0, one pass at
tier 1. Record: cost per call, disagreement rate, tier-1 delta rate, deterministic-
check failure rate. Then set, per stream:

```
N_0 : N_1 : N_2  ∝  sqrt(V_0/C_0) : sqrt(V_Δ1/C_1) : sqrt(V_Δ2/C_2)
```

rounded to the workload's natural granularity. In practice with current price ratios
(order 10–30× between adjacent tiers) this lands near: leaves touch everything with
2–3× replication on high-disagreement streams; mid tier touches everything once
(verification is the point, not sampling); root touches only residuals and the
final assembly.

## In-flight adaptation

Recompute the disagreement proxy on a rolling window (last ~20 subtasks per
stream). Triggers:
- Disagreement at tier 0 rising → increase leaf replication $m$ on that stream
  (variance reduction is cheap there) *before* considering tier promotion.
- Escalation rate from a stream persistently > ~25% → the verification-asymmetry
  gate is failing for that stream; promote the stream one tier wholesale. This is
  cheaper than paying escalation overhead per item — the discrete analog of
  re-meshing rather than refining cell-by-cell.
- Unanimous leaf agreement that later fails a deterministic check → correlated-
  error event; log it, and discount that stream's agreement statistic (shrink the
  effective $m$) for the rest of the run.

## Caveats, stated plainly

1. The rule optimizes a *variance* budget; LLM quality loss is not pure variance —
   there is a bias component (systematic tier-$0$ blind spots) that no amount of
   replication removes. The mid tier exists to catch bias, replication to reduce
   variance; do not substitute one for the other.
2. Samples are exchangeable only within a fixed prompt template; changing the
   template mid-run resets the rolling statistics.
3. Cost accounting must include orchestration overhead (subtask-card construction,
   context duplication into each leaf). At high fan-out this overhead is the
   dominant term for very short subtasks — batch small items into one leaf call
   when the card is longer than the work.
