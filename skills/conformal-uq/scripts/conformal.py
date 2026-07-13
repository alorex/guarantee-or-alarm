#!/usr/bin/env python3
"""conformal.py - split conformal prediction with exact finite-sample verification.

The guarantee is exact and checkable: 1-a <= P(Y in C(X)) <= 1-a + 1/(n+1) under
exchangeability, for ANY model. `verify` proves the implementation earns it — and
demonstrates that the #1 implementation bug (naive quantile without the (n+1)
correction) measurably undercovers.

CLI:
  python conformal.py verify [--seed 1] [--json]     exit 0 iff all checks pass
  python conformal.py calibrate --scores s.csv --alpha 0.1
      -> prints q_hat (the ceil((n+1)(1-a))-th smallest score) and the Beta interval
         for realized coverage.

verify (deliberately imperfect model — linear fit on quadratic data; validity must
hold anyway; M=400 replications, n_cal=100, n_test=200, alpha=0.1):
  V1 exact band: mean coverage in [0.90, 0.90+1/101] +/- MC tolerance
  V2 off-by-one bug detected: naive n-quantile threshold covers strictly less than
     the corrected rule and its mean falls below 1-alpha
  V3 Beta spread: std of per-replication coverage within [0.5x, 2x] of the
     Beta(n+1-l, l) prediction
  V4 adaptive (CQR-style locally scaled) score still covers on heteroscedastic data
Pure stdlib.
"""
import argparse, json, math, random, sys

def kth_smallest(scores, k):
    return sorted(scores)[k-1]

def conformal_qhat(scores, alpha):
    n = len(scores)
    k = math.ceil((n+1)*(1-alpha))
    if k > n: return float("inf")
    return kth_smallest(scores, k)

def naive_qhat(scores, alpha):
    n = len(scores)
    k = math.ceil(n*(1-alpha))          # the classic off-by-one
    return kth_smallest(scores, k)

def fit_linear(xs, ys):
    n=len(xs); mx=sum(xs)/n; my=sum(ys)/n
    b = sum((x-mx)*(y-my) for x,y in zip(xs,ys)) / max(sum((x-mx)**2 for x in xs),1e-12)
    return (my - b*mx), b

def gen(rng, n, hetero=False):
    xs=[rng.uniform(-2,2) for _ in range(n)]
    ys=[]
    for x in xs:
        sd = 0.2+0.6*abs(x) if hetero else 0.5
        ys.append(1.0 + 0.5*x + 0.8*x*x + rng.gauss(0, sd))   # quadratic truth
    return xs, ys

def one_rep(rng, alpha, n_cal, n_test, hetero=False, adaptive=False):
    xt, yt = gen(rng, 200, hetero)
    a, b = fit_linear(xt, yt)                                  # misspecified on purpose
    if adaptive:
        # local scale estimate from training residuals in |x| bins (crude sigma-hat)
        res=[(abs(x), abs(y-(a+b*x))) for x,y in zip(xt,yt)]
        lo=[r for d,r in res if d<1]; hi=[r for d,r in res if d>=1]
        s_lo=sum(lo)/len(lo); s_hi=sum(hi)/len(hi)
        sig=lambda x: s_lo if abs(x)<1 else s_hi
    else:
        sig=lambda x: 1.0
    xc, yc = gen(rng, n_cal, hetero)
    scores=[abs(y-(a+b*x))/sig(x) for x,y in zip(xc,yc)]
    q  = conformal_qhat(scores, alpha)
    qn = naive_qhat(scores, alpha)
    xs, ys = gen(rng, n_test, hetero)
    cov  = sum(1 for x,y in zip(xs,ys) if abs(y-(a+b*x))/sig(x) <= q)/n_test
    covn = sum(1 for x,y in zip(xs,ys) if abs(y-(a+b*x))/sig(x) <= qn)/n_test
    return cov, covn

def verify(seed=1, json_out=False):
    rng=random.Random(seed); alpha=0.1; n_cal=100; n_test=200; M=400
    covs=[]; covns=[]
    for _ in range(M):
        c, cn = one_rep(rng, alpha, n_cal, n_test)
        covs.append(c); covns.append(cn)
    mean_c=sum(covs)/M; mean_n=sum(covns)/M
    band_lo, band_hi = 1-alpha, 1-alpha+1/(n_cal+1)
    mc_tol = 3*math.sqrt(0.09/(M*n_test)) + 0.004   # MC + between-rep slack
    checks={}
    checks["V1_exact_band"]={"mean_coverage":round(mean_c,4),
        "band":[band_lo, round(band_hi,4)], "tol":round(mc_tol,4),
        "pass": band_lo - mc_tol <= mean_c <= band_hi + mc_tol}
    checks["V2_off_by_one_detected"]={"naive_mean":round(mean_n,4),
        "corrected_mean":round(mean_c,4),
        "pass": mean_n < mean_c and mean_n < band_lo}
    l=math.floor((n_cal+1)*alpha)
    a_beta, b_beta = n_cal+1-l, l
    beta_sd=math.sqrt(a_beta*b_beta/((a_beta+b_beta)**2*(a_beta+b_beta+1)))
    emp_sd=math.sqrt(sum((c-mean_c)**2 for c in covs)/(M-1))
    # empirical per-rep coverage adds binomial noise from finite n_test on top of Beta
    pred_sd=math.sqrt(beta_sd**2 + 0.09/n_test)
    checks["V3_beta_spread"]={"emp_sd":round(emp_sd,4),"pred_sd":round(pred_sd,4),
        "pass": 0.5 < emp_sd/pred_sd < 2.0}
    covs_a=[one_rep(rng, alpha, n_cal, n_test, hetero=True, adaptive=True)[0] for _ in range(150)]
    mean_a=sum(covs_a)/150
    checks["V4_adaptive_score_covers"]={"mean_coverage":round(mean_a,4),
        "pass": abs(mean_a-(band_lo+band_hi)/2) < 0.02}
    ok=all(c["pass"] for c in checks.values())
    out={"alpha":alpha,"n_cal":n_cal,"M":M,"checks":checks,"all_pass":ok}
    print(json.dumps(out,indent=2) if json_out else
          "\n".join(f"{k}: {'PASS' if v['pass'] else 'FAIL'}" for k,v in checks.items()))
    return 0 if ok else 1

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    v=sub.add_parser("verify"); v.add_argument("--seed",type=int,default=1); v.add_argument("--json",action="store_true")
    c=sub.add_parser("calibrate"); c.add_argument("--scores",required=True); c.add_argument("--alpha",type=float,default=0.1)
    a=ap.parse_args()
    if a.cmd=="verify": return verify(a.seed,a.json)
    s=[float(l) for l in open(a.scores) if l.strip()]; n=len(s)
    q=conformal_qhat(s,a.alpha); l=math.floor((n+1)*a.alpha)
    print(json.dumps({"n":n,"q_hat":q,"k":math.ceil((n+1)*(1-a.alpha)),
        "coverage_beta":[n+1-l,l]},indent=2)); return 0

if __name__=="__main__": sys.exit(main())
