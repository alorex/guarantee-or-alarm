"""Vignette 4: designing the expensive experiment (Bayesian optimal design).

Calibrate a quadratic response theta0 + theta1*x + theta2*x^2 with prior
theta ~ N(0, I3) and noise sigma=0.5, choosing measurement locations x from
21 candidates on [-1,1]. Linear-Gaussian, so posteriors and the expected
information gain EIG(x) = 0.5*log(1 + g(x)' Sigma g(x) / sigma^2) are exact.
Strategies: greedy max-EIG; uniform-random placement; naive "always measure
the center". Report experiments needed to reach posterior trace <= 0.1.
"""
import math
import random

SEED = 2026
SIGMA2 = 0.25
TARGET_TRACE = 0.10
MAX_N = 120
CANDS = [-1.0 + i / 10 for i in range(21)]


def g(x):
    return (1.0, x, x * x)


def mat_vec(a, v):
    return [sum(a[i][j] * v[j] for j in range(3)) for i in range(3)]


def posterior_update(sigma, x):
    """Rank-one Gaussian update: Sigma' = Sigma - (Sigma g g' Sigma)/(sigma2 + g'Sigma g)."""
    gv = g(x)
    sg = mat_vec(sigma, gv)
    denom = SIGMA2 + sum(gv[i] * sg[i] for i in range(3))
    return [[sigma[i][j] - sg[i] * sg[j] / denom for j in range(3)]
            for i in range(3)]


def trace(m):
    return m[0][0] + m[1][1] + m[2][2]


def eig(sigma, x):
    gv = g(x)
    sg = mat_vec(sigma, gv)
    return 0.5 * math.log(1.0 + sum(gv[i] * sg[i] for i in range(3)) / SIGMA2)


def run(strategy, rng=None):
    sigma = [[1.0 if i == j else 0.0 for j in range(3)] for i in range(3)]
    picks = []
    for n in range(1, MAX_N + 1):
        if strategy == "greedy-EIG":
            x = max(CANDS, key=lambda c: eig(sigma, c))
        elif strategy == "random":
            x = rng.choice(CANDS)
        else:                       # center-only
            x = 0.0
        picks.append(x)
        sigma = posterior_update(sigma, x)
        if trace(sigma) <= TARGET_TRACE:
            return n, picks, trace(sigma)
    return None, picks, trace(sigma)


def main():
    rng = random.Random(SEED)
    n, picks, _ = run("greedy-EIG")
    print(f"RESULT greedy-EIG: n_experiments_to_target={n} "
          f"first_picks={picks[:6]}")
    ns = []
    for _ in range(500):
        n, _, _ = run("random", rng)
        ns.append(n if n is not None else MAX_N + 1)
    ns.sort()
    print(f"RESULT random: median_n_to_target={ns[len(ns) // 2]} "
          f"iqr=({ns[len(ns) // 4]},{ns[3 * len(ns) // 4]})")
    n, _, tr = run("center-only")
    print(f"RESULT center-only: n_to_target={n} "
          f"trace_after_{MAX_N}={tr:.3f} (design singular: curvature and "
          f"slope never identified)")


if __name__ == "__main__":
    main()
