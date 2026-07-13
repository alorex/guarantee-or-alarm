"""Vignette 1: calibrated LLM-verifier gate (conformal-uq / RCPS-style).

Artifacts are good or defective (25% defect rate). A judge emits a score
(higher = more confident the artifact is good): good ~ N(1.5,1),
defective ~ N(-0.7,1). Naive gate: accept if score > 0 ("judge says pass").
Calibrated gate: on n_cal labeled points, pick the most permissive threshold
whose Clopper-Pearson 90% upper bound on the defect rate among accepted
items is <= 5% (risk-controlling prediction set with a binomial tail bound).

We repeat calibration + evaluation R times and report: realized defect rate
among accepted items (naive vs gate), how often each stays under the 5%
target, and the acceptance fraction (the price paid).
"""
import math
import random

SEED = 2026
DEFECT_RATE = 0.25
TARGET = 0.05     # tolerated defect rate among accepted
DELTA = 0.10      # 1 - confidence of the bound
N_CAL, N_TEST, R = 500, 5000, 300


def draw(rng):
    bad = rng.random() < DEFECT_RATE
    s = rng.gauss(-0.7 if bad else 1.5, 1.0)
    return s, bad


def log_binom_pmf(k, m, p):
    if p <= 0.0:
        return 0.0 if k == 0 else -math.inf
    if p >= 1.0:
        return 0.0 if k == m else -math.inf
    return (math.lgamma(m + 1) - math.lgamma(k + 1) - math.lgamma(m - k + 1)
            + k * math.log(p) + (m - k) * math.log1p(-p))


def binom_cdf(k, m, p):
    return sum(math.exp(log_binom_pmf(i, m, p)) for i in range(k + 1))


def cp_upper(k, m, delta):
    """Clopper-Pearson upper confidence bound for a binomial proportion."""
    if k >= m:
        return 1.0
    lo, hi = k / m, 1.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if binom_cdf(k, m, mid) > delta:
            lo = mid
        else:
            hi = mid
    return hi


def calibrate(cal):
    """Scan thresholds from strict to permissive; stop before first violation.

    The CP upper bound is decreasing in m at fixed k, so a violation can only
    newly occur when a defective item enters the accepted set -- checking at
    those points only is exact and much faster.
    """
    cal = sorted(cal, reverse=True)          # by score, descending
    best_t, bad_seen = math.inf, 0
    for m, (s, bad) in enumerate(cal, start=1):
        if bad:
            bad_seen += 1
            if cp_upper(bad_seen, m, DELTA) > TARGET:
                break
        best_t = s
    return best_t


def draw_drifted(rng):
    """Perturbation: a new defect type the judge scores higher (post-
    calibration drift; exchangeability between calibration and deployment
    broken)."""
    bad = rng.random() < DEFECT_RATE
    s = rng.gauss(0.4 if bad else 1.5, 1.0)
    return s, bad


def main():
    rng = random.Random(SEED)
    res = {"naive": [], "gate": [], "gate-drift": []}
    acc = {"naive": [], "gate": [], "gate-drift": []}
    for _ in range(R):
        cal = [draw(rng) for _ in range(N_CAL)]
        t_hat = calibrate(cal)
        test = [draw(rng) for _ in range(N_TEST)]
        drift = [draw_drifted(rng) for _ in range(N_TEST)]
        for name, t, data in (("naive", 0.0, test), ("gate", t_hat, test),
                              ("gate-drift", t_hat, drift)):
            accepted = [bad for s, bad in data if s >= t]
            if accepted:
                res[name].append(sum(accepted) / len(accepted))
                acc[name].append(len(accepted) / N_TEST)
    for name in ("naive", "gate", "gate-drift"):
        r = res[name]
        mean_def = sum(r) / len(r)
        viol = sum(x > TARGET for x in r) / len(r)
        mean_acc = sum(acc[name]) / len(acc[name])
        print(f"RESULT {name}: defect_rate_among_accepted={mean_def:.4f} "
              f"share_of_runs_over_{TARGET:.0%}_target={viol:.3f} "
              f"acceptance_fraction={mean_acc:.3f}")


if __name__ == "__main__":
    main()
