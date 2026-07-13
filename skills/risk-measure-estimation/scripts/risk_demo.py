#!/usr/bin/env python3
"""risk_demo.py -- verification anchor for the risk-measure-estimation skill.

Closed forms used (standard normal Z, N(mu, sigma^2) loss X):
  VaR_a  = mu + sigma * z_a,            z_a = Phi^{-1}(a)
  CVaR_a = mu + sigma * phi(z_a)/(1-a)
Rockafellar-Uryasev: CVaR_a = min_t { t + E[(X-t)+]/(1-a) }, argmin = VaR_a.

Nested bias law (Gordy-Juneja): with Y ~ N(0,1), X|Y ~ N(Y, s^2), the fixed-M
nested estimator of p = P(E[X|Y] > c) = Phibar(c) actually targets
  p_M = P(Y + (s/sqrt(M)) Z > c) = Phibar(c / sqrt(1 + s^2/M)),
so its bias Phibar(c/sqrt(1+s^2/M)) - Phibar(c) is known EXACTLY and decays as 1/M.
The script checks the simulation against this analytic value and the ~4x bias
reduction from M to 4M.

Usage:
  python risk_demo.py verify --json      # exit code 0 iff all checks pass
"""
import argparse, json, math, random, statistics, sys

ND = statistics.NormalDist()

def var_cvar_closed(mu, sigma, a):
    z = ND.inv_cdf(a)
    return mu + sigma * z, mu + sigma * ND.pdf(z) / (1.0 - a)

def empirical_var(xs_sorted, a):
    n = len(xs_sorted)
    k = min(n - 1, max(0, math.ceil(a * n) - 1))
    return xs_sorted[k]

def ru_objective(xs, t, a):
    return t + sum(max(x - t, 0.0) for x in xs) / (len(xs) * (1.0 - a))

def nested_estimate(rng, N, M, s, c):
    """Fixed-M nested estimator of P(E[X|Y] > c); inner mean simulated exactly
    as Y + (s/sqrt(M)) Z, which is distributionally identical to averaging M
    inner draws N(Y, s^2) -- same estimator, cheaper."""
    se = s / math.sqrt(M)
    hits = 0
    for _ in range(N):
        y = rng.gauss(0.0, 1.0)
        if y + rng.gauss(0.0, se) > c:
            hits += 1
    return hits / N

def phibar(x):
    return 1.0 - ND.cdf(x)

def run_checks(seed=20260707):
    rng = random.Random(seed)
    checks = []

    # --- Check 1: empirical VaR/CVaR recover Gaussian closed forms -----------
    mu, sigma, a, n = 1.0, 2.0, 0.99, 400_000
    xs = sorted(rng.gauss(mu, sigma) for _ in range(n))
    var_cf, cvar_cf = var_cvar_closed(mu, sigma, a)
    var_emp = empirical_var(xs, a)
    cvar_emp = ru_objective(xs, var_emp, a)
    checks.append({
        "name": "gaussian_var_recovery",
        "passed": abs(var_emp - var_cf) < 0.05,
        "detail": {"empirical": var_emp, "closed_form": var_cf, "tol": 0.05}})
    checks.append({
        "name": "gaussian_cvar_recovery",
        "passed": abs(cvar_emp - cvar_cf) < 0.08,
        "detail": {"empirical": cvar_emp, "closed_form": cvar_cf, "tol": 0.08}})

    # --- Check 2: RU identity -- minimizer sits at VaR, value at CVaR --------
    # convexity: objective at VaR is below objective at VaR +/- 0.5
    obj_at_var = ru_objective(xs, var_cf, a)
    obj_lo = ru_objective(xs, var_cf - 0.5, a)
    obj_hi = ru_objective(xs, var_cf + 0.5, a)
    checks.append({
        "name": "rockafellar_uryasev_identity",
        "passed": (obj_at_var < obj_lo and obj_at_var < obj_hi
                   and abs(obj_at_var - cvar_cf) < 0.08),
        "detail": {"obj_at_var": obj_at_var, "obj_var_minus": obj_lo,
                   "obj_var_plus": obj_hi, "cvar_closed_form": cvar_cf}})

    # --- Check 3: nested bias matches its analytic law and decays ~1/M -------
    s, c, N = 2.0, 1.5, 200_000
    p_true = phibar(c)
    results = {}
    for M in (4, 16):
        p_M_analytic = phibar(c / math.sqrt(1.0 + s * s / M))
        p_hat = nested_estimate(rng, N, M, s, c)
        se_mc = math.sqrt(p_M_analytic * (1 - p_M_analytic) / N)
        results[M] = {"p_hat": p_hat, "p_M_analytic": p_M_analytic,
                      "abs_dev": abs(p_hat - p_M_analytic), "mc_se": se_mc,
                      "bias_analytic": p_M_analytic - p_true}
        checks.append({
            "name": f"nested_matches_analytic_biased_value_M{M}",
            "passed": abs(p_hat - p_M_analytic) < 4.0 * se_mc,
            "detail": results[M]})
    ratio = results[4]["bias_analytic"] / results[16]["bias_analytic"]
    emp_ratio = ((results[4]["p_hat"] - p_true) /
                 (results[16]["p_hat"] - p_true))
    checks.append({
        "name": "nested_bias_decays_like_1_over_M",
        "passed": 2.5 < ratio < 5.0 and 2.0 < emp_ratio < 6.5,
        "detail": {"analytic_bias_ratio_M4_over_M16": ratio,
                   "empirical_bias_ratio": emp_ratio,
                   "asymptotic_value": 4.0, "p_true": p_true}})
    return checks

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["verify"])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--seed", type=int, default=20260707)
    args = ap.parse_args()
    checks = run_checks(args.seed)
    ok = all(c["passed"] for c in checks)
    out = {"skill": "risk-measure-estimation", "seed": args.seed,
           "all_passed": ok, "checks": checks}
    print(json.dumps(out, indent=2) if args.json else
          "\n".join(f"[{'PASS' if c['passed'] else 'FAIL'}] {c['name']}" for c in checks))
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
