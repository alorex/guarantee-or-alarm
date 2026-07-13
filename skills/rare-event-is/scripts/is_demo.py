#!/usr/bin/env python3
"""is_demo.py - control-based importance sampling, verified on a closed-form case.

Target: p = P(X > K), X ~ N(0,1) (Brownian terminal value, standardized).
Closed form: p = 0.5 * erfc(K / sqrt(2)).

IS: mean-shift tilt (the asymptotically optimal constant-drift control for this
event is mu* = K). Sample X ~ N(mu, 1); weight w(x) = exp(-mu*x + mu^2/2).
Estimator: mean of 1{x > K} * w(x). Exactly unbiased for ANY mu (Girsanov with a
computable likelihood ratio) - control error costs variance, never bias.

CLI:
  python is_demo.py verify [--seed 1] [--json]   # exit 0 iff all checks pass
  python is_demo.py run --k 4.5 --mu 4.5 --n 20000 [--seed 1]

verify checks (K = 4.0, p ~ 3.17e-5):
  V1 unbiasedness: IS(mu=K) estimate within 4 SE of closed form
  V2 variance reduction: relative error (IS, mu=K) << relative error (crude MC), and
     measured var-reduction factor > 100 at equal N
  V3 invariant: deliberately suboptimal control mu = 0.7K stays within 4 SE of truth
     (unbiased) while its empirical variance exceeds the optimal tilt's variance
  V4 overshoot warning check: extreme tilt mu = 3K inflates weight degeneracy
     (max-weight share rises), demonstrating IS non-monotonicity diagnostics
Pure stdlib, deterministic given --seed.
"""
import argparse, json, math, random, sys

def p_closed(k):
    return 0.5 * math.erfc(k / math.sqrt(2.0))

def is_estimate(k, mu, n, rng):
    s = s2 = 0.0
    wmax = 0.0
    for _ in range(n):
        x = rng.gauss(mu, 1.0)
        w = math.exp(-mu * x + 0.5 * mu * mu) if x > k else 0.0
        s += w; s2 += w * w; wmax = max(wmax, w)
    mean = s / n
    var = max(s2 / n - mean * mean, 0.0)
    se = math.sqrt(var / n)
    wshare = (wmax / s) if s > 0 else 1.0
    return mean, se, var, wshare

def crude_estimate(k, n, rng):
    hits = sum(1 for _ in range(n) if rng.gauss(0, 1) > k)
    mean = hits / n
    var = mean * (1 - mean)
    return mean, math.sqrt(var / n), var

def verify(seed=1, json_out=False):
    K, N = 4.0, 20000
    truth = p_closed(K)
    rng = random.Random(seed)
    checks = {}

    m_opt, se_opt, v_opt, ws_opt = is_estimate(K, K, N, rng)
    checks["V1_unbiased_optimal_tilt"] = {
        "estimate": m_opt, "truth": truth, "se": se_opt,
        "pass": abs(m_opt - truth) < 4 * se_opt and se_opt > 0}

    m_cr, se_cr, v_cr = crude_estimate(K, N, rng)
    vr_factor = (v_cr / v_opt) if v_opt > 0 else float("inf")
    re_is = se_opt / truth
    re_cr_theoretical = math.sqrt((1 - truth) / (truth * N))
    checks["V2_variance_reduction"] = {
        "crude_hits_in_N": round(m_cr * N), "var_reduction_factor": round(vr_factor, 1),
        "rel_err_IS": round(re_is, 4), "rel_err_crude_theoretical": round(re_cr_theoretical, 4),
        "pass": vr_factor > 100 and re_is < 0.1 * re_cr_theoretical}

    m_sub, se_sub, v_sub, _ = is_estimate(K, 0.7 * K, N, rng)
    checks["V3_control_error_costs_variance_not_bias"] = {
        "estimate_mu_0.7K": m_sub, "truth": truth, "se": se_sub,
        "var_suboptimal_over_var_optimal": round(v_sub / v_opt, 2),
        "pass": abs(m_sub - truth) < 4 * se_sub and v_sub > v_opt}

    m_ov, se_ov, v_ov, ws_ov = is_estimate(K, 3.0 * K, N, rng)
    checks["V4_overshoot_degeneracy_detectable"] = {
        "max_weight_share_optimal": round(ws_opt, 4), "max_weight_share_overshoot": round(ws_ov, 4),
        "pass": ws_ov > 5 * ws_opt}

    ok = all(c["pass"] for c in checks.values())
    out = {"K": K, "truth": truth, "N": N, "checks": checks, "all_pass": ok}
    print(json.dumps(out, indent=2) if json_out else
          "\n".join([f"p_closed(K=4) = {truth:.3e}"] +
                    [f"{k}: {'PASS' if v['pass'] else 'FAIL'}" for k, v in checks.items()]))
    return 0 if ok else 1

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify"); v.add_argument("--seed", type=int, default=1)
    v.add_argument("--json", action="store_true")
    r = sub.add_parser("run"); r.add_argument("--k", type=float, required=True)
    r.add_argument("--mu", type=float, required=True); r.add_argument("--n", type=int, default=20000)
    r.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    if a.cmd == "verify":
        return verify(a.seed, a.json)
    m, se, var, ws = is_estimate(a.k, a.mu, a.n, random.Random(a.seed))
    print(json.dumps({"estimate": m, "se": se, "closed_form": p_closed(a.k),
                      "max_weight_share": round(ws, 4)}, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
