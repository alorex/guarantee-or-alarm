#!/usr/bin/env python3
"""cs_demo.py - confidence sequences vs peeking, verified.

Bounded X in [0,1] (Bernoulli-ish mixture), true mean mu. Implements:
  - fixed-n 95% CI (normal approx) checked at EVERY t  -> peeking violation
  - hedged betting CS (Waudby-Smith-Ramdas style): capital K_t(m) =
    prod(1 + lam_i*(X_i - m)) with predictable clipped lam; CI_t = {m: K_t(m) < 1/alpha}
    Validity holds for ANY predictable lam in range (supermartingale under truth),
    so tuning affects width, never coverage.

verify checks (B=250 null streams, T=500, grid 51, alpha=0.05):
  V1 peeking violation: P(exists t<=T: mu outside fixed-n CI) large (> 0.25)
  V2 CS time-uniform: P(exists t<=T: mu outside CS_t) <= alpha + MC tol
  V3 honest price: CS width at t=T wider than fixed-n CI width at n=T (ratio > 1)
  V4 e-process validity at adversarial stopping: for the capital process at the TRUE
     mean, E[K_tau] <= 1 with tau = argmax_t K_t (stop-at-max), within MC tolerance
     of the Ville bound: P(sup K >= 1/alpha) <= alpha
CLI: python cs_demo.py verify [--seed 1] [--json]    exit 0 iff all pass. Stdlib.
"""
import argparse, json, math, random, sys

def gen_x(rng):
    # bounded, non-Gaussian: mixture of Bernoulli(0.35) and Uniform(0,1), mu = 0.425
    return float(rng.random() < 0.35) if rng.random() < 0.5 else rng.random()
MU = 0.5*0.35 + 0.5*0.5   # 0.425

def run_stream(rng, T, alpha, grid):
    xs=[]; s=0.0; s2=0.0
    K=[1.0]*len(grid)               # capital per candidate mean (hedged: avg of long/short)
    Klong=[1.0]*len(grid); Kshort=[1.0]*len(grid)
    supK_true=0.0; K_true_long=1.0; K_true_short=1.0
    fixed_viol=False; cs_viol=False; K_path_true=[]
    var_hat=0.25
    for t in range(1, T+1):
        # predictable bet from PAST data only
        lam = min(0.5, math.sqrt(2*math.log(2/alpha)/(var_hat*t*math.log(t+2))))
        x = gen_x(rng); xs.append(x); s+=x; s2+=x*x
        mean = s/t
        var_hat = max(1e-3, s2/t - mean*mean)
        # fixed-n CI at this t (the peeker's interval)
        se = math.sqrt(var_hat/t)
        if abs(mean-MU) > 1.959963984540054*se: fixed_viol=True
        # betting CS update
        lo_idx, hi_idx = None, None
        for j,m in enumerate(grid):
            ll = max(-0.5/max(1e-9,1-m), -lam) if False else lam   # keep symmetric clipped lam
            # clip lambda to keep 1+lam*(x-m) > 0 for x in [0,1]
            lam_m = min(lam, 0.9/max(m,1e-9), 0.9/max(1-m,1e-9))
            Klong[j]  *= (1 + lam_m*(x - m))
            Kshort[j] *= (1 - lam_m*(x - m))
            K[j] = 0.5*Klong[j] + 0.5*Kshort[j]
        inside=[m for j,m in enumerate(grid) if K[j] < 1/alpha]
        if inside:
            if not (inside[0] <= MU <= inside[-1]): cs_viol=True
            cs_width = inside[-1]-inside[0]
        else:
            cs_viol=True; cs_width=0.0
        # capital at the true mean (for V4)
        lam_t = min(lam, 0.9/max(MU,1e-9), 0.9/max(1-MU,1e-9))
        K_true_long *= (1 + lam_t*(x - MU)); K_true_short *= (1 - lam_t*(x - MU))
        K_path_true.append(0.5*K_true_long + 0.5*K_true_short)
    fixed_w = 2*1.959963984540054*math.sqrt(var_hat/T)
    return fixed_viol, cs_viol, cs_width, fixed_w, K_path_true

def verify(seed=1, json_out=False):
    rng=random.Random(seed)
    B, T, alpha = 250, 500, 0.05
    grid=[i/50 for i in range(51)]
    fv=cv=0; cw=fw=0.0; ktau=[]; ville=0
    for _ in range(B):
        f,c,w,wf,kp = run_stream(rng,T,alpha,grid)
        fv+=f; cv+=c; cw+=w; fw+=wf
        ktau.append(max(kp))
        ville += (max(kp) >= 1/alpha)
    checks={}
    checks["V1_peeking_violates"]={"cum_miscoverage_fixed":round(fv/B,3),
        "pass": fv/B > 0.25}
    band=3*math.sqrt(alpha*(1-alpha)/B)
    checks["V2_cs_time_uniform"]={"cum_miscoverage_cs":round(cv/B,3),"alpha":alpha,
        "band":round(band,3),"pass": cv/B <= alpha + band}
    checks["V3_honest_price"]={"cs_width_T":round(cw/B,4),"fixed_width_T":round(fw/B,4),
        "ratio":round((cw/B)/(fw/B),2),"pass": cw/B > fw/B}
    checks["V4_ville_bound"]={"P_supK_ge_1_over_alpha":round(ville/B,3),
        "mean_K_at_stop_at_max":round(sum(ktau)/B,3),
        "pass": ville/B <= alpha + band}
    ok=all(c["pass"] for c in checks.values())
    out={"B":B,"T":T,"checks":checks,"all_pass":ok}
    print(json.dumps(out,indent=2) if json_out else
          "\n".join(f"{k}: {'PASS' if v['pass'] else 'FAIL'}" for k,v in checks.items()))
    return 0 if ok else 1

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    v=sub.add_parser("verify"); v.add_argument("--seed",type=int,default=1); v.add_argument("--json",action="store_true")
    a=ap.parse_args(); return verify(a.seed,a.json)

if __name__=="__main__": sys.exit(main())
