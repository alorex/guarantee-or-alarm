"""Vignette 5a: certifying against rare failures (rare-event-is).

Estimate p = P(Z > 4.75), Z ~ N(0,1). Exact: p = erfc(4.75/sqrt(2))/2
~ 1.017e-6. Naive Monte Carlo with n = 10^6 samples expects ~1 hit.
Importance sampling: draw Z ~ N(4.75, 1), reweight by the likelihood ratio
exp(-4.75*z + 4.75^2/2). Report both estimates, relative standard errors,
the empirical variance-reduction factor, and the sample size each method
needs for 10% relative error.
"""
import math
import random

SEED = 2026
C = 4.75
N = 1_000_000
P_EXACT = 0.5 * math.erfc(C / math.sqrt(2))


def main():
    rng = random.Random(SEED)

    hits = sum(rng.gauss(0, 1) > C for _ in range(N))
    p_naive = hits / N
    var_naive = P_EXACT * (1 - P_EXACT)          # per-sample variance
    rse_naive = math.sqrt(var_naive / N) / P_EXACT

    s = s2 = 0.0
    for _ in range(N):
        z = rng.gauss(C, 1.0)
        w = math.exp(-C * z + 0.5 * C * C) if z > C else 0.0
        s += w
        s2 += w * w
    p_is = s / N
    var_is = s2 / N - p_is * p_is                # per-sample variance
    rse_is = math.sqrt(var_is / N) / P_EXACT

    vrf = var_naive / var_is
    n_for_10pct = lambda v: v / (0.1 * P_EXACT) ** 2
    print(f"RESULT exact: p={P_EXACT:.3e}")
    print(f"RESULT naive: hits={hits} estimate={p_naive:.3e} "
          f"rel_std_err={rse_naive:.1%}")
    print(f"RESULT is:    estimate={p_is:.3e} rel_std_err={rse_is:.2%}")
    print(f"RESULT variance_reduction_factor={vrf:.2e}")
    print(f"RESULT n_for_10pct_rel_err: naive={n_for_10pct(var_naive):.1e} "
          f"is={n_for_10pct(var_is):.1e}")


if __name__ == "__main__":
    main()
