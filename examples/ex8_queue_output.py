"""Vignette 8: trusting a simulation's summary (simulation-output-analysis).

M/M/1 queue, lambda=0.9, mu=1.0; stationary mean waiting time in queue is
Wq = lambda / (mu*(mu-lambda)) = 9 exactly. Each replication simulates
44,000 customers via the Lindley recursion, discards a 4,000-customer
warm-up, and builds a 90% CI for Wq two ways: naive (treat the 40,000
autocorrelated waits as iid) and batch means (20 batches of 2,000, t-CI;
batch length must dominate the relaxation time ~(1-rho)^-2 = 100 customers,
a check the skill makes explicit). Coverage and width over R replications.
"""
import math
import random

SEED = 2026
LAM, MU = 0.9, 1.0
WQ_TRUE = LAM / (MU * (MU - LAM))          # 9.0
WARM, KEEP = 4000, 40000
BATCHES = 20
R = 300
T90_19 = 1.7291                             # t_{0.95, 19}
Z90 = 1.6448536269514722


def simulate(rng):
    w, waits = 0.0, []
    for i in range(WARM + KEEP):
        a = rng.expovariate(LAM)            # interarrival
        s = rng.expovariate(MU)             # service
        w = max(0.0, w + s - a)
        if i >= WARM:
            waits.append(w)
    return waits


def main():
    rng = random.Random(SEED)
    cov = {"naive": 0, "batch": 0}
    widths = {"naive": [], "batch": []}
    for _ in range(R):
        waits = simulate(rng)
        n = len(waits)
        m = sum(waits) / n
        v = sum((x - m) ** 2 for x in waits) / (n - 1)
        half = Z90 * math.sqrt(v / n)
        cov["naive"] += (m - half <= WQ_TRUE <= m + half)
        widths["naive"].append(2 * half)
        bsize = n // BATCHES
        bm = [sum(waits[i * bsize:(i + 1) * bsize]) / bsize
              for i in range(BATCHES)]
        mb = sum(bm) / BATCHES
        vb = sum((x - mb) ** 2 for x in bm) / (BATCHES - 1)
        half = T90_19 * math.sqrt(vb / BATCHES)
        cov["batch"] += (mb - half <= WQ_TRUE <= mb + half)
        widths["batch"].append(2 * half)
    for name in ("naive", "batch"):
        print(f"RESULT {name}: coverage_90={cov[name] / R:.3f} "
              f"median_CI_width={sorted(widths[name])[R // 2]:.2f} "
              f"(truth Wq={WQ_TRUE})")


if __name__ == "__main__":
    main()
