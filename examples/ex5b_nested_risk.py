"""Vignette 5b: risk functionals need nested-simulation care
(risk-measure-estimation).

Probability of large conditional loss: eta = P(E[X|Z] > c) with Z ~ N(0,1),
X|Z ~ N(Z, 4). Since E[X|Z] = Z, truth is P(Z > c) exactly. A practitioner
who cannot see the inner structure estimates E[X|Z] by an inner Monte Carlo
mean of M samples; the indicator's smoothing bias near the threshold decays
like 1/M. Fixed total budget B = n_outer * M: naive M=1 spends everything on
outer samples and inherits maximal inner bias; a budget-aware allocation
accepts fewer outer samples to shrink the bias below the noise floor.
"""
import math
import random

SEED = 2026
C = 1.6448536269514722          # true eta = P(Z > c) = 0.05
SIG_IN = 2.0
BUDGET = 20_000
REPS = 100
ETA = 0.05


def estimate(rng, m):
    n_outer = BUDGET // m
    hits = 0
    for _ in range(n_outer):
        z = rng.gauss(0, 1)
        inner = sum(rng.gauss(z, SIG_IN) for _ in range(m)) / m
        hits += inner > C
    return hits / n_outer


def main():
    rng = random.Random(SEED)
    for m in (1, 10, 100):
        ests = [estimate(rng, m) for _ in range(REPS)]
        mean = sum(ests) / REPS
        rmse = math.sqrt(sum((e - ETA) ** 2 for e in ests) / REPS)
        print(f"RESULT M={m:>3}: mean_estimate={mean:.4f} (truth {ETA}) "
              f"bias={mean - ETA:+.4f} rmse={rmse:.4f} "
              f"n_outer={BUDGET // m}")


if __name__ == "__main__":
    main()
