"""Vignette 3: measurement with model-generated labels (PPI).

Estimate the prevalence (12%) of a property in N=50,000 documents. An LLM
labels all of them (sensitivity 0.95, specificity 0.98 -> biased naive
estimate ~13.2%); a human labels a small gold sample of n=300 from the same
population. Compare three 90% intervals over R repetitions:
  model-only  : mean of model labels on all N (ignores label error),
  gold-only   : classical interval from the 300 human labels,
  PPI         : mean_N(f) + mean_gold(Y - f), variances combined.
Report bias, interval width, and empirical coverage of the truth.

The bulk corpus is simulated by exact binomial counts (per-item simulation
is equivalent for these statistics); the gold sample is simulated per item.
"""
import math
import random

SEED = 2026
PI = 0.12
SENS, SPEC = 0.95, 0.98
N, N_GOLD, R = 50_000, 300, 1000
Z90 = 1.6448536269514722


def binom(rng, n, p):
    if hasattr(rng, "binomialvariate"):          # Python >= 3.12
        return rng.binomialvariate(n, p)
    return sum(rng.random() < p for _ in range(n))


def mean_var(xs):
    m = sum(xs) / len(xs)
    v = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return m, v


def main():
    rng = random.Random(SEED)
    stats = {k: {"cov": 0, "w": 0.0, "est": 0.0} for k in
             ("model-only", "gold-only", "ppi")}

    def record(name, est, half):
        s = stats[name]
        s["cov"] += (est - half <= PI <= est + half)
        s["w"] += 2 * half
        s["est"] += est

    for _ in range(R):
        # bulk corpus: exact binomial counts
        n_pos = binom(rng, N, PI)
        tp = binom(rng, n_pos, SENS)
        fp = binom(rng, N - n_pos, 1 - SPEC)
        mf = (tp + fp) / N
        record("model-only", mf, Z90 * math.sqrt(mf * (1 - mf) / N))
        # gold sample: per item, keeping (y, f) pairing
        gold = []
        for _ in range(N_GOLD):
            y = 1 if rng.random() < PI else 0
            f = ((1 if rng.random() < SENS else 0) if y
                 else (1 if rng.random() > SPEC else 0))
            gold.append((y, f))
        mg, vg = mean_var([y for y, _ in gold])
        record("gold-only", mg, Z90 * math.sqrt(vg / N_GOLD))
        mr, vr = mean_var([y - f for y, f in gold])
        record("ppi", mf + mr,
               Z90 * math.sqrt(mf * (1 - mf) / N + vr / N_GOLD))

    for name, s in stats.items():
        print(f"RESULT {name}: mean_estimate={s['est'] / R:.4f} (truth {PI}) "
              f"mean_CI_width={s['w'] / R:.4f} "
              f"coverage_90={s['cov'] / R:.3f}")
    w_gold = stats["gold-only"]["w"] / R
    w_ppi = stats["ppi"]["w"] / R
    print(f"RESULT ppi_vs_gold: width_ratio={w_ppi / w_gold:.3f} "
          f"effective_gold_multiplier={(w_gold / w_ppi) ** 2:.2f}")


if __name__ == "__main__":
    main()
