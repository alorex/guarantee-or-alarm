"""Vignette 7: targeting instead of averaging (causal-ml).

Part A, confounding: covariate x ~ N(0,1); treatment T ~ Bern(sigmoid(1.5x))
(sicker/more-active units get treated more); outcome Y = 2*T + 4*x + N(0,1).
True ATE = 2. Naive difference in means is badly inflated; a cross-fitted
AIPW/DML estimator with simple linear/logistic nuisances recovers the truth.

Part B, heterogeneity: effect tau(x) = 3 if x > 0 else 0 (ATE 1.5), treatment
cost 1 per unit. Policy values per capita: treat-nobody, treat-everybody,
and treat-where-the-estimated-subgroup-effect-exceeds-cost.
"""
import math
import random

SEED = 2026
N, REPS = 4000, 200


def sigmoid(t):
    return 1.0 / (1.0 + math.exp(-t))


def gen_confounded(rng):
    data = []
    for _ in range(N):
        x = rng.gauss(0, 1)
        t = 1 if rng.random() < sigmoid(1.5 * x) else 0
        y = 2.0 * t + 4.0 * x + rng.gauss(0, 1)
        data.append((x, t, y))
    return data


def ols1(pairs):
    """y ~ a + b*x by least squares."""
    n = len(pairs)
    mx = sum(x for x, _ in pairs) / n
    my = sum(y for _, y in pairs) / n
    sxx = sum((x - mx) ** 2 for x, _ in pairs)
    b = sum((x - mx) * (y - my) for x, y in pairs) / sxx if sxx > 0 else 0.0
    return my - b * mx, b


def logistic1(pairs, iters=25):
    """t ~ sigmoid(a + b*x) by Newton-Raphson."""
    a = b = 0.0
    for _ in range(iters):
        g0 = g1 = h00 = h01 = h11 = 0.0
        for x, t in pairs:
            p = sigmoid(a + b * x)
            w = p * (1 - p)
            g0 += t - p
            g1 += (t - p) * x
            h00 += w
            h01 += w * x
            h11 += w * x * x
        det = h00 * h11 - h01 * h01
        if det <= 1e-12:
            break
        a += (h11 * g0 - h01 * g1) / det
        b += (h00 * g1 - h01 * g0) / det
    return a, b


def aipw(data):
    """Two-fold cross-fitted AIPW for the ATE."""
    half = len(data) // 2
    folds = (data[:half], data[half:])
    psis = []
    for k in (0, 1):
        train, est = folds[1 - k], folds[k]
        a1, b1 = ols1([(x, y) for x, t, y in train if t == 1])
        a0, b0 = ols1([(x, y) for x, t, y in train if t == 0])
        ae, be = logistic1([(x, t) for x, t, _ in train])
        for x, t, y in est:
            e = min(0.95, max(0.05, sigmoid(ae + be * x)))
            m1, m0 = a1 + b1 * x, a0 + b0 * x
            psis.append(m1 - m0 + t * (y - m1) / e
                        - (1 - t) * (y - m0) / (1 - e))
    n = len(psis)
    est = sum(psis) / n
    se = math.sqrt(sum((p - est) ** 2 for p in psis) / (n - 1) / n)
    return est, se


def gen_hidden_confounder(rng):
    """Perturbation: a second confounder u that the analyst does NOT
    observe. Ignorability given x is violated; no estimator that adjusts
    only for x can be unbiased."""
    data = []
    for _ in range(N):
        x = rng.gauss(0, 1)
        u = rng.gauss(0, 1)
        t = 1 if rng.random() < sigmoid(1.0 * x + 1.0 * u) else 0
        y = 2.0 * t + 4.0 * x + 3.0 * u + rng.gauss(0, 1)
        data.append((x, t, y))
    return data


def main():
    rng = random.Random(SEED)
    naive, dml, dml_hidden = [], [], []
    for _ in range(REPS):
        data = gen_confounded(rng)
        y1 = [y for _, t, y in data if t == 1]
        y0 = [y for _, t, y in data if t == 0]
        naive.append(sum(y1) / len(y1) - sum(y0) / len(y0))
        est, _ = aipw(data)
        dml.append(est)
        est, _ = aipw(gen_hidden_confounder(rng))
        dml_hidden.append(est)
    avg = lambda xs: sum(xs) / len(xs)
    sd = lambda xs: math.sqrt(sum((x - avg(xs)) ** 2 for x in xs)
                              / (len(xs) - 1))
    print(f"RESULT naive_diff_means: mean={avg(naive):.2f} sd={sd(naive):.2f} "
          f"(truth 2.00)")
    print(f"RESULT dml_aipw:        mean={avg(dml):.2f} sd={sd(dml):.2f} "
          f"(truth 2.00)")
    print(f"RESULT dml_hidden_confounder: mean={avg(dml_hidden):.2f} "
          f"sd={sd(dml_hidden):.2f} (truth 2.00 -- identification, not "
          f"machinery, is what fails; sensitivity analysis or escalation "
          f"required)")

    # Part B: heterogeneous effect, randomized trial, cost = 1
    cost, vals = 1.0, {"treat-none": [], "treat-all": [], "targeted": []}
    for _ in range(REPS):
        data = []
        for _ in range(N):
            x = rng.gauss(0, 1)
            t = 1 if rng.random() < 0.5 else 0
            tau = 3.0 if x > 0 else 0.0
            y = tau * t + 1.0 * x + rng.gauss(0, 1)
            data.append((x, t, y, tau))
        # estimate subgroup effects on one half, evaluate policy on the other
        half = len(data) // 2
        train, test = data[:half], data[half:]
        tau_hat = {}
        for grp, cond in (("pos", lambda x: x > 0), ("neg", lambda x: x <= 0)):
            y1 = [y for x, t, y, _ in train if cond(x) and t == 1]
            y0 = [y for x, t, y, _ in train if cond(x) and t == 0]
            tau_hat[grp] = sum(y1) / len(y1) - sum(y0) / len(y0)
        for name, rule in (
                ("treat-none", lambda x: False),
                ("treat-all", lambda x: True),
                ("targeted", lambda x: tau_hat["pos" if x > 0 else "neg"] > cost)):
            v = sum((tau - cost) if rule(x) else 0.0
                    for x, _, _, tau in test) / len(test)
            vals[name].append(v)
    for name, vs in vals.items():
        print(f"RESULT policy_{name}: value_per_unit={avg(vs):+.3f}")


if __name__ == "__main__":
    main()
