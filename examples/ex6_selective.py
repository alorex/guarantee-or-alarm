"""Vignette 6: reporting the winners (selective-inference).

Part A, winner's curse: m=2000 null effects z_j ~ N(0,1); report every
effect with |z| > 2.576 (a per-comparison 1% screen). Naive 90% CIs
z +/- 1.645 on the selected effects vs conditional (truncated-normal) CIs
that account for the selection event |Z| > c. Coverage of the truth (0).

Part B, honest shortlists: 1950 nulls + 50 signals (mu=3). Naive "top 20
by |z|" vs Benjamini-Hochberg at q=0.10: false discovery proportion and
number of true signals found.
"""
import math
import random

SEED = 2026
M, C, ALPHA = 2000, 2.576, 0.10
Z90 = 1.6448536269514722
REPS = 400


def phi(t):
    return 0.5 * (1.0 + math.erf(t / math.sqrt(2)))


def trunc_cdf(z, mu, c):
    """CDF at z of N(mu,1) truncated to (-inf,-c] U [c, inf), for |z|>=c."""
    lo = phi(-c - mu)
    hi = 1.0 - phi(c - mu)
    denom = lo + hi
    if z <= -c:
        num = phi(z - mu)
    else:
        num = lo + max(0.0, phi(z - mu) - phi(c - mu))
    return num / denom


def cond_ci(z, c, alpha=ALPHA):
    """Invert the truncated-normal CDF in mu (decreasing in mu)."""
    def solve(target):
        lo, hi = z - 12.0, z + 12.0
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if trunc_cdf(z, mid, c) > target:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)
    return solve(1 - alpha / 2), solve(alpha / 2)


def main():
    rng = random.Random(SEED)
    # Part A: all-null screen
    n_sel = cov_naive = cov_cond = 0
    for _ in range(REPS):
        for _ in range(M):
            z = rng.gauss(0, 1)
            if abs(z) > C:
                n_sel += 1
                cov_naive += (z - Z90 <= 0.0 <= z + Z90)
                lo, hi = cond_ci(z, C)
                cov_cond += (lo <= 0.0 <= hi)
    print(f"RESULT winners_curse: n_selected={n_sel} "
          f"naive_90CI_coverage={cov_naive / n_sel:.3f} "
          f"conditional_90CI_coverage={cov_cond / n_sel:.3f}")

    # Part B: BH vs naive top-k on a mixed panel
    fdp_naive, fdp_bh, hits_naive, hits_bh = [], [], [], []
    for _ in range(REPS):
        effects = [3.0] * 50 + [0.0] * (M - 50)
        zs = [(rng.gauss(mu, 1), mu != 0) for mu in effects]
        top = sorted(zs, key=lambda t: -abs(t[0]))[:20]
        fd = sum(1 for _, sig in top if not sig)
        fdp_naive.append(fd / 20)
        hits_naive.append(sum(1 for _, sig in top if sig))
        ps = sorted(((2 * (1 - phi(abs(z))), sig) for z, sig in zs),
                    key=lambda t: t[0])
        k_star = max((k + 1 for k, (p, _) in enumerate(ps)
                      if p <= (k + 1) / M * 0.10), default=0)
        rejected = ps[:k_star]
        fd = sum(1 for _, sig in rejected if not sig)
        fdp_bh.append(fd / max(1, k_star))
        hits_bh.append(sum(1 for _, sig in rejected if sig))
    avg = lambda xs: sum(xs) / len(xs)
    print(f"RESULT shortlist_naive_top20: FDP={avg(fdp_naive):.3f} "
          f"true_signals_found={avg(hits_naive):.1f}/50")
    print(f"RESULT shortlist_BH_q10: FDR={avg(fdp_bh):.3f} "
          f"true_signals_found={avg(hits_bh):.1f}/50")


if __name__ == "__main__":
    main()
