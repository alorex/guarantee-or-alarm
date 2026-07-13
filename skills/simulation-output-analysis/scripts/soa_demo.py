#!/usr/bin/env python3
"""soa_demo.py - simulation output analysis on a known-answer process, verified.

AR(1): X_t = mu + phi*(X_{t-1}-mu) + eps, eps~N(0,1), phi=0.9, mu=3.
Known: stationary var = 1/(1-phi^2); integrated autocorrelation time
tau_int = (1+phi)/(1-phi) = 19; Var(Xbar_n) ~ (marginal var/n)*tau_int.

verify checks (M reps, n=4000, alpha=0.05):
  V1 naive iid CI collapses: coverage far below 0.95 (theory: z-CI too narrow by
     sqrt(19) ~ 4.36 -> coverage ~ 35%)
  V2 batch means (sqrt-n rule: b=m=63) with t_{b-1} CI: coverage ~ 0.95
  V3 tau_int recovered: BM variance estimate / (marginal var/n) ~ 19 within tolerance
  V4 warm-up: start at X_0 = mu+15; no-deletion mean biased upward at n=800 (bias
     > 3x its SE); MSER-style deletion cuts |bias| by > 60%
  V5 batch-count robustness: coverage within band for b in {20, 63, 125}
CLI: python soa_demo.py verify [--seed 1] [--json]   exit 0 iff all pass. Stdlib.
"""
import argparse, json, math, random, sys

PHI, MU = 0.9, 3.0
TAU = (1+PHI)/(1-PHI)               # 19
MVAR = 1.0/(1-PHI*PHI)              # marginal variance

T975 = {19: 2.093, 62: 1.999, 124: 1.979}   # t quantiles for b-1 df used below

def ar1(rng, n, x0=None):
    x = MU + rng.gauss(0,1)*math.sqrt(MVAR) if x0 is None else x0
    out=[]
    for _ in range(n):
        x = MU + PHI*(x-MU) + rng.gauss(0,1)
        out.append(x)
    return out

def naive_ci(xs):
    n=len(xs); m=sum(xs)/n
    v=sum((x-m)**2 for x in xs)/(n-1)
    h=1.96*math.sqrt(v/n)
    return m, h, v

def bm_ci(xs, b):
    n=len(xs); m_=n//b
    means=[sum(xs[i*m_:(i+1)*m_])/m_ for i in range(b)]
    gm=sum(means)/b
    vb=sum((x-gm)**2 for x in means)/(b-1)
    t=T975.get(b-1, 2.0)
    h=t*math.sqrt(vb/b)
    return gm, h, vb*m_    # vb*m_ estimates the time-average variance constant

def verify(seed=1, json_out=False):
    rng=random.Random(seed)
    M, n = 400, 4000
    b_sqrt = 63
    cov_naive=cov_bm=0; tau_est=[]
    cov_b={20:0,63:0,125:0}
    for _ in range(M):
        xs=ar1(rng,n)
        m,h,v = naive_ci(xs)
        cov_naive += (abs(m-MU)<=h)
        gm,hb,tavc = bm_ci(xs,b_sqrt)
        cov_bm += (abs(gm-MU)<=hb)
        tau_est.append(tavc/v)
        for b in cov_b:
            g2,h2,_=bm_ci(xs,b); cov_b[b]+= (abs(g2-MU)<=h2)
    checks={}
    checks["V1_naive_collapses"]={"coverage":round(cov_naive/M,3),
        "theory_note":"z-CI too narrow by sqrt(tau)=4.36","pass": cov_naive/M<0.6}
    band=3*math.sqrt(0.05*0.95/M)+0.015
    checks["V2_batch_means_nominal"]={"coverage":round(cov_bm/M,3),
        "band":round(band,3),"pass": abs(cov_bm/M-0.95)<band}
    te=sum(tau_est)/M
    checks["V3_tau_recovered"]={"tau_hat":round(te,2),"tau_true":TAU,
        "pass": abs(te-TAU)/TAU < 0.25}
    # V4 warm-up
    nw=800; reps=300; bias_no=0.0; bias_del=0.0
    for _ in range(reps):
        xs=ar1(rng,nw,x0=MU+15.0)
        bias_no += sum(xs)/nw - MU
        d=nw//10   # simple 10% deletion (MSER-style stand-in, deterministic)
        bias_del += sum(xs[d:])/(nw-d) - MU
    bias_no/=reps; bias_del/=reps
    se_no = math.sqrt(MVAR*TAU/nw/reps)*3
    checks["V4_warmup_bias"]={"bias_no_deletion":round(bias_no,4),
        "bias_after_deletion":round(bias_del,4),
        "pass": abs(bias_no)>3*se_no/3 and abs(bias_del) < 0.4*abs(bias_no)}
    ok5=all(abs(cov_b[b]/M-0.95)<band+0.02 for b in cov_b)
    checks["V5_batch_count_robust"]={ {f"b={b}": round(c/M,3) for b,c in cov_b.items()}.__str__(): "", "pass": ok5} if False else {"coverages":{f"b={b}":round(c/M,3) for b,c in cov_b.items()},"pass":ok5}
    ok=all(c["pass"] for c in checks.values())
    out={"M":M,"n":n,"phi":PHI,"tau_int_true":TAU,"checks":checks,"all_pass":ok}
    print(json.dumps(out,indent=2) if json_out else
          "\n".join(f"{k}: {'PASS' if v['pass'] else 'FAIL'}" for k,v in checks.items()))
    return 0 if ok else 1

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    v=sub.add_parser("verify"); v.add_argument("--seed",type=int,default=1); v.add_argument("--json",action="store_true")
    a=ap.parse_args(); return verify(a.seed,a.json)

if __name__=="__main__": sys.exit(main())
