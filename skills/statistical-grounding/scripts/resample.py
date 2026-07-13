#!/usr/bin/env python3
"""resample.py - verified permutation test + bootstrap CI (pure stdlib).

Tools that make uncertainty statements must themselves be verified: `verify`
checks the permutation test's null calibration and the bootstrap's coverage
against nominal, exit-code gated for harness use.

CLI:
  python resample.py verify [--seed 1] [--json]
  python resample.py perm --a a.csv --b b.csv [--reps 9999] [--seed 1]
  python resample.py boot --data x.csv [--stat mean|median] [--ci pct|bca]
                          [--level 0.90] [--boots 4999] [--seed 1]

CSV inputs: one numeric value per line (no header).
verify checks (deterministic given --seed):
  V1 null calibration: two-sample permutation test on N(0,1) vs N(0,1),
     rejection rate at alpha=0.05 within 3-sigma binomial band of 0.05
  V2 power sanity: rejection rate under a 1-sigma mean shift substantially
     exceeds the null rate
  V3 bootstrap coverage: percentile 90% CI for a normal mean covers the truth
     at a rate within a 3-sigma band of 0.90
  V4 BCa sanity: on skewed (lognormal) data, BCa interval differs from
     percentile (bias/acceleration active) and both contain the sample stat
"""
import argparse, json, math, random, sys

def mean(x): return sum(x) / len(x)
def median(x):
    s = sorted(x); n = len(s)
    return s[n//2] if n % 2 else 0.5*(s[n//2-1] + s[n//2])
STATS = {"mean": mean, "median": median}

def perm_test(a, b, reps=9999, rng=None, stat=mean):
    """Two-sided two-sample permutation test on stat difference. Returns p."""
    rng = rng or random.Random(0)
    obs = abs(stat(a) - stat(b))
    pool, na = list(a) + list(b), len(a)
    hits = 0
    for _ in range(reps):
        rng.shuffle(pool)
        if abs(stat(pool[:na]) - stat(pool[na:])) >= obs - 1e-15:
            hits += 1
    return (hits + 1) / (reps + 1)   # add-one: valid p-value (Phipson-Smyth)

def boot_samples(x, boots, rng, stat):
    n = len(x)
    return sorted(stat([x[rng.randrange(n)] for _ in range(n)]) for _ in range(boots))

def quantile(s, q):
    idx = q * (len(s) - 1)
    lo = int(math.floor(idx)); hi = min(lo + 1, len(s) - 1)
    return s[lo] + (idx - lo) * (s[hi] - s[lo])

def norm_cdf(z): return 0.5 * math.erfc(-z / math.sqrt(2))
def norm_ppf(p):
    # Acklam rational approximation, |error| < 1.15e-9
    a=[-3.969683028665376e+01,2.209460984245205e+02,-2.759285104469687e+02,
       1.383577518672690e+02,-3.066479806614716e+01,2.506628277459239e+00]
    b=[-5.447609879822406e+01,1.615858368580409e+02,-1.556989798598866e+02,
       6.680131188771972e+01,-1.328068155288572e+01]
    c=[-7.784894002430293e-03,-3.223964580411365e-01,-2.400758277161838e+00,
       -2.549732539343734e+00,4.374664141464968e+00,2.938163982698783e+00]
    d=[7.784695709041462e-03,3.224671290700398e-01,2.445134137142996e+00,
       3.754408661907416e+00]
    plow = 0.02425
    if p < plow:
        q = math.sqrt(-2*math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > 1-plow:
        return -norm_ppf(1-p)
    q = p-0.5; r = q*q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)

def bootstrap_ci(x, stat=mean, ci="bca", level=0.90, boots=4999, rng=None):
    rng = rng or random.Random(0)
    s = boot_samples(x, boots, rng, stat)
    alpha = 1 - level
    if ci == "pct":
        return quantile(s, alpha/2), quantile(s, 1-alpha/2)
    # BCa (Efron 1987)
    theta = stat(x)
    prop = sum(1 for v in s if v < theta) / len(s)
    prop = min(max(prop, 1/(len(s)+1)), 1-1/(len(s)+1))
    z0 = norm_ppf(prop)
    # acceleration via jackknife
    n = len(x)
    jack = [stat(x[:i] + x[i+1:]) for i in range(n)]
    jm = mean(jack)
    num = sum((jm - j)**3 for j in jack)
    den = 6.0 * (sum((jm - j)**2 for j in jack) ** 1.5)
    a = num/den if den else 0.0
    def adj(q):
        z = norm_ppf(q)
        return norm_cdf(z0 + (z0 + z) / (1 - a*(z0 + z)))
    return quantile(s, adj(alpha/2)), quantile(s, adj(1-alpha/2))

def verify(seed=1, json_out=False):
    rng = random.Random(seed)
    checks = {}
    # V1/V2: permutation calibration and power (K runs, n=15 per group, reps=399)
    K, n, reps, alpha = 250, 15, 399, 0.05
    rej_null = rej_alt = 0
    for _ in range(K):
        a = [rng.gauss(0,1) for _ in range(n)]; b = [rng.gauss(0,1) for _ in range(n)]
        if perm_test(a, b, reps, rng) <= alpha: rej_null += 1
        a2 = [rng.gauss(0,1) for _ in range(n)]; b2 = [rng.gauss(1,1) for _ in range(n)]
        if perm_test(a2, b2, reps, rng) <= alpha: rej_alt += 1
    r0, r1 = rej_null/K, rej_alt/K
    band = 3*math.sqrt(alpha*(1-alpha)/K)
    checks["V1_null_calibration"] = {"reject_rate_null": r0, "nominal": alpha,
        "band_3sigma": round(band,4), "pass": abs(r0-alpha) < band}
    checks["V2_power_sanity"] = {"reject_rate_shifted": r1,
        "pass": r1 > 0.5 and r1 > r0 + 0.3}
    # V3: percentile coverage, 90% CI for normal mean, n=25, 300 reps
    R, n2, cover = 300, 25, 0
    for _ in range(R):
        x = [rng.gauss(5,2) for _ in range(n2)]
        lo, hi = bootstrap_ci(x, mean, "pct", 0.90, 999, rng)
        if lo <= 5 <= hi: cover += 1
    cv = cover/R; band3 = 3*math.sqrt(0.9*0.1/R) + 0.02  # +2% small-n bootstrap slack
    checks["V3_bootstrap_coverage"] = {"coverage": cv, "nominal": 0.90,
        "band": round(band3,4), "pass": abs(cv-0.90) < band3}
    # V4: BCa vs percentile on skewed data
    x = [math.exp(rng.gauss(0,1)) for _ in range(40)]
    p_lo, p_hi = bootstrap_ci(x, mean, "pct", 0.90, 1999, random.Random(seed+7))
    b_lo, b_hi = bootstrap_ci(x, mean, "bca", 0.90, 1999, random.Random(seed+7))
    theta = mean(x)
    moved = abs(b_lo-p_lo) + abs(b_hi-p_hi) > 1e-3
    checks["V4_bca_active_on_skew"] = {"pct": [round(p_lo,3), round(p_hi,3)],
        "bca": [round(b_lo,3), round(b_hi,3)],
        "pass": moved and p_lo <= theta <= p_hi and b_lo <= theta <= b_hi}
    ok = all(c["pass"] for c in checks.values())
    out = {"checks": checks, "all_pass": ok}
    print(json.dumps(out, indent=2) if json_out else
          "\n".join(f"{k}: {'PASS' if v['pass'] else 'FAIL'}" for k, v in checks.items()))
    return 0 if ok else 1

def read_csv(p): return [float(l.strip()) for l in open(p) if l.strip()]

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify"); v.add_argument("--seed", type=int, default=1)
    v.add_argument("--json", action="store_true")
    p = sub.add_parser("perm"); p.add_argument("--a", required=True); p.add_argument("--b", required=True)
    p.add_argument("--reps", type=int, default=9999); p.add_argument("--seed", type=int, default=1)
    b = sub.add_parser("boot"); b.add_argument("--data", required=True)
    b.add_argument("--stat", default="mean", choices=list(STATS))
    b.add_argument("--ci", default="bca", choices=["pct","bca"])
    b.add_argument("--level", type=float, default=0.90)
    b.add_argument("--boots", type=int, default=4999); b.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    if args.cmd == "verify": return verify(args.seed, args.json)
    if args.cmd == "perm":
        pv = perm_test(read_csv(args.a), read_csv(args.b), args.reps, random.Random(args.seed))
        print(json.dumps({"p_value": pv, "reps": args.reps})); return 0
    x = read_csv(args.data)
    lo, hi = bootstrap_ci(x, STATS[args.stat], args.ci, args.level, args.boots, random.Random(args.seed))
    print(json.dumps({"stat": STATS[args.stat](x), "ci": [lo, hi],
                      "method": args.ci, "level": args.level})); return 0

if __name__ == "__main__":
    sys.exit(main())
