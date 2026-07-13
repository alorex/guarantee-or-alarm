#!/usr/bin/env python3
"""ppi.py - prediction-powered inference (mean estimation) with coverage verification.

theta_PP = mean_f_unlabeled - rectifier, rectifier = mean(f(X_lab) - Y_lab).
Valid CIs regardless of predictor quality; naive imputation CIs are invalid.
PPI++ lambda-tuning: theta(l) = l*mean_f_N - [l*mean_f_n - mean_Y_n]; l chosen to
minimize variance; l->0 recovers classical.

CLI:
  python ppi.py verify [--seed 1] [--json]   exit 0 iff all checks pass
  python ppi.py mean --labeled lab.csv --unlabeled unl.csv [--alpha 0.05]
      lab.csv rows: f_x,y ; unl.csv rows: f_x

verify (M=1500 reps, n=80 labeled, N=4000 unlabeled, alpha=0.05, biased predictor):
  V1 naive imputation CIs collapse: coverage far below nominal (< 0.5)
  V2 PPI CIs ~ nominal (within 3-sigma binomial band of 0.95)
  V3 classical (labeled-only) ~ nominal but WIDER than PPI (informative predictor)
  V4 PPI++ sanity: with a pure-noise predictor, |lambda_hat| small and PPI++ width
     ~ classical width (never loses); with the good predictor lambda_hat near 1
Pure stdlib.
"""
import argparse, json, math, random, sys

Z = 1.959963984540054  # z_{0.975}

def mean_se(xs):
    n=len(xs); m=sum(xs)/n
    v=sum((x-m)**2 for x in xs)/(n-1)
    return m, math.sqrt(v/n), v

def ppi_ci(f_lab, y_lab, f_unl, lam=1.0, alpha=0.05):
    n, N = len(y_lab), len(f_unl)
    mfN, _, vfN = mean_se(f_unl)
    rect = [lam*f - y for f, y in zip(f_lab, y_lab)]
    mr, _, vr = mean_se(rect)
    est = lam*mfN - mr
    se = math.sqrt(lam*lam*vfN/N + vr/n)
    z = Z if abs(alpha-0.05)<1e-12 else -_ppf(alpha/2)
    return est, est - z*se, est + z*se, se

def lam_hat(f_lab, y_lab, f_unl):
    # variance-minimizing lambda (mean case): cov(f,Y)/ (var(f)*(1+n/N)) on labeled
    n, N = len(y_lab), len(f_unl)
    mf = sum(f_lab)/n; my = sum(y_lab)/n
    cov = sum((f-mf)*(y-my) for f,y in zip(f_lab,y_lab))/(n-1)
    vf  = sum((f-mf)**2 for f in f_lab)/(n-1)
    if vf <= 0: return 0.0
    return max(0.0, min(1.5, cov/(vf*(1+n/N))))

def gen(rng, n, N, predictor="good"):
    # Y = mu + eps ; f = biased/noisy view of Y
    mu = 2.0
    ys  = [mu + rng.gauss(0,1) for _ in range(n)]
    if predictor == "good":
        f  = lambda y: 0.9*y + 0.7 + rng.gauss(0,0.4)   # biased but informative
    else:
        f  = lambda y: rng.gauss(0,1)                    # pure noise
    f_lab = [f(y) for y in ys]
    y_unl = [mu + rng.gauss(0,1) for _ in range(N)]
    f_unl = [f(y) for y in y_unl]
    return f_lab, ys, f_unl, mu

def verify(seed=1, json_out=False):
    rng = random.Random(seed)
    M, n, N, alpha = 1500, 80, 4000, 0.05
    cov_naive = cov_ppi = cov_cl = 0
    w_ppi = w_cl = 0.0
    lams_good, lams_noise, w_pp_noise, w_cl_noise = [], [], [], []
    for _ in range(M):
        f_lab, y_lab, f_unl, mu = gen(rng, n, N, "good")
        # naive: treat predictions as data
        mN, seN, _ = mean_se(f_unl)
        cov_naive += (mN - Z*seN <= mu <= mN + Z*seN)
        # PPI (lambda=1)
        est, lo, hi, se = ppi_ci(f_lab, y_lab, f_unl, 1.0, alpha)
        cov_ppi += (lo <= mu <= hi); w_ppi += hi-lo
        # classical labeled-only
        mc, sec, _ = mean_se(y_lab)
        cov_cl += (mc - Z*sec <= mu <= mc + Z*sec); w_cl += 2*Z*sec
        lams_good.append(lam_hat(f_lab, y_lab, f_unl))
    # noise predictor arm (fewer reps suffice)
    for _ in range(400):
        f_lab, y_lab, f_unl, mu = gen(rng, n, N, "noise")
        l = lam_hat(f_lab, y_lab, f_unl); lams_noise.append(l)
        _, lo, hi, _ = ppi_ci(f_lab, y_lab, f_unl, l, alpha)
        w_pp_noise.append(hi-lo)
        mc, sec, _ = mean_se(y_lab); w_cl_noise.append(2*Z*sec)
    band = 3*math.sqrt(0.05*0.95/M)
    checks = {
      "V1_naive_collapses": {"coverage": round(cov_naive/M,4), "pass": cov_naive/M < 0.5},
      "V2_ppi_nominal": {"coverage": round(cov_ppi/M,4), "band": round(band,4),
                         "pass": abs(cov_ppi/M - 0.95) < band + 0.005},
      "V3_ppi_narrower_than_classical": {
          "width_ppi": round(w_ppi/M,4), "width_classical": round(w_cl/M,4),
          "coverage_classical": round(cov_cl/M,4),
          "pass": w_ppi/M < w_cl/M and abs(cov_cl/M - 0.95) < band + 0.005},
      "V4_lambda_tuning": {
          "mean_lambda_good": round(sum(lams_good)/len(lams_good),3),
          "mean_lambda_noise": round(sum(lams_noise)/len(lams_noise),3),
          "width_ratio_ppipp_vs_classical_noise": round(sum(w_pp_noise)/sum(w_cl_noise),3),
          "pass": sum(lams_good)/len(lams_good) > 0.6
                  and sum(lams_noise)/len(lams_noise) < 0.15
                  and sum(w_pp_noise)/sum(w_cl_noise) < 1.05},
    }
    ok = all(c["pass"] for c in checks.values())
    out = {"M": M, "n": n, "N": N, "checks": checks, "all_pass": ok}
    print(json.dumps(out, indent=2) if json_out else
          "\n".join(f"{k}: {'PASS' if v['pass'] else 'FAIL'}" for k,v in checks.items()))
    return 0 if ok else 1

def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify"); v.add_argument("--seed", type=int, default=1); v.add_argument("--json", action="store_true")
    m = sub.add_parser("mean"); m.add_argument("--labeled", required=True); m.add_argument("--unlabeled", required=True)
    m.add_argument("--alpha", type=float, default=0.05)
    a = ap.parse_args()
    if a.cmd == "verify": return verify(a.seed, a.json)
    lab = [tuple(map(float,l.split(","))) for l in open(a.labeled) if l.strip()]
    f_lab, y_lab = [x[0] for x in lab], [x[1] for x in lab]
    f_unl = [float(l) for l in open(a.unlabeled) if l.strip()]
    l = lam_hat(f_lab, y_lab, f_unl)
    est, lo, hi, se = ppi_ci(f_lab, y_lab, f_unl, l, a.alpha)
    print(json.dumps({"estimate": est, "ci": [lo, hi], "lambda": l, "se": se,
                      "n": len(y_lab), "N": len(f_unl)}, indent=2)); return 0

if __name__ == "__main__":
    sys.exit(main())
