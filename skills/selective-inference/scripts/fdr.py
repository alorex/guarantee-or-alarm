#!/usr/bin/env python3
"""fdr.py - BH + conformal p-values with synthetic-null FDR verification, plus a
demonstration of the select-then-naive-CI trap (winner's curse).

CLI:
  python fdr.py verify [--seed 1] [--json]      exit 0 iff all checks pass
  python fdr.py bh --pvals p.csv --q 0.1        BH rejections (indices, threshold)
  python fdr.py conformal-p --cal cal.csv --test test.csv
      -> conformal p-value per test point: p = (1 + #{cal >= s}) / (n_cal + 1)

verify (M replications, deterministic given --seed):
  V1 BH under the global null: realized FDR (mean FDP) <= q + MC tol
  V2 outlier pipeline (conformal p + BH): realized FDR <= q + tol AND power > 0.5
     (cal ~ N(0,1); test = 80% nulls, 20% outliers ~ N(4,1); score = x)
  V3 conformal p super-uniformity under null: P(p <= t) <= t + MC tol for t in
     {0.05, 0.1, 0.2}
  V4 winner's curse demonstrated: select coordinates with the largest sample means
     among pure nulls, naive 90% CIs on the selected cover the truth (0) at a rate
     far below nominal (< 0.7) while unselected-coordinate CIs cover ~0.9
Pure stdlib.
"""
import argparse, json, math, random, sys

def bh(pvals, q):
    n=len(pvals); order=sorted(range(n), key=lambda i:pvals[i])
    thresh_idx=-1
    for rank,i in enumerate(order,1):
        if pvals[i] <= q*rank/n: thresh_idx=rank
    return set(order[:thresh_idx]) if thresh_idx>0 else set()

def conformal_p(cal, s):
    return (1+sum(1 for c in cal if c>=s))/(len(cal)+1)

def verify(seed=1, json_out=False):
    rng=random.Random(seed); checks={}
    # V1: BH global null, m=50 uniform p-values, q=0.1, M=800
    q=0.1; M=800; fdps=[]
    for _ in range(M):
        p=[rng.random() for _ in range(50)]
        R=bh(p,q); fdps.append(1.0 if R else 0.0)   # all rejections false under global null
    fdr1=sum(fdps)/M
    checks["V1_bh_global_null"]={"realized_FDR":round(fdr1,4),"q":q,
        "pass": fdr1 <= q + 3*math.sqrt(q*(1-q)/M)}
    # V2: conformal p + BH outlier pipeline; q=0.2, M=300
    q2=0.2; M2=300; fdps2=[]; pows=[]
    for _ in range(M2):
        cal=[rng.gauss(0,1) for _ in range(200)]
        nulls=[rng.gauss(0,1) for _ in range(40)]
        outs=[rng.gauss(4,1) for _ in range(10)]
        test=nulls+outs; labels=[0]*40+[1]*10
        p=[conformal_p(cal,s) for s in test]
        R=bh(p,q2)
        fd=sum(1 for i in R if labels[i]==0); td=sum(1 for i in R if labels[i]==1)
        fdps2.append(fd/max(len(R),1)); pows.append(td/10)
    fdr2=sum(fdps2)/M2; pow2=sum(pows)/M2
    checks["V2_conformal_bh_outliers"]={"realized_FDR":round(fdr2,4),"q":q2,
        "power":round(pow2,3),
        "pass": fdr2 <= q2 + 3*math.sqrt(q2*(1-q2)/M2) and pow2 > 0.5}
    # V3: super-uniformity
    cal=[rng.gauss(0,1) for _ in range(500)]
    ps=[conformal_p(cal, rng.gauss(0,1)) for _ in range(4000)]
    v3={}; ok3=True
    for t in (0.05,0.1,0.2):
        emp=sum(1 for p in ps if p<=t)/len(ps)
        tol=3*math.sqrt(t*(1-t)/len(ps))+0.01   # +cal-set randomness slack
        v3[f"t={t}"]={"P(p<=t)":round(emp,4),"bound":t,"tol":round(tol,4)}
        ok3 = ok3 and emp <= t+tol
    v3["pass"]=ok3; checks["V3_super_uniformity"]=v3
    # V4: winner's curse — m=200 null coords, n=10 obs each, select top 10 means
    Mreps=300; sel_cov=0; unsel_cov=0; nsel=0; nunsel=0
    z=1.645
    for _ in range(Mreps):
        means=[]; ses=[]
        for j in range(200):
            xs=[rng.gauss(0,1) for _ in range(10)]
            m=sum(xs)/10; sd=math.sqrt(sum((x-m)**2 for x in xs)/9)
            means.append(m); ses.append(sd/math.sqrt(10))
        top=sorted(range(200), key=lambda j:-means[j])[:10]
        topset=set(top)
        for j in range(200):
            covered = abs(means[j]) <= z*ses[j]      # CI for true mean 0
            if j in topset: sel_cov+=covered; nsel+=1
            else: unsel_cov+=covered; nunsel+=1
    cs=sel_cov/nsel; cu=unsel_cov/nunsel
    checks["V4_winners_curse"]={"naive_CI_coverage_selected":round(cs,3),
        "coverage_unselected":round(cu,3),
        "pass": cs < 0.7 and abs(cu-0.90) < 0.03}
    ok=all(c["pass"] for c in checks.values())
    out={"checks":checks,"all_pass":ok}
    print(json.dumps(out,indent=2) if json_out else
          "\n".join(f"{k}: {'PASS' if v['pass'] else 'FAIL'}" for k,v in checks.items()))
    return 0 if ok else 1

def read1(p): return [float(l) for l in open(p) if l.strip()]

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    v=sub.add_parser("verify"); v.add_argument("--seed",type=int,default=1); v.add_argument("--json",action="store_true")
    b=sub.add_parser("bh"); b.add_argument("--pvals",required=True); b.add_argument("--q",type=float,default=0.1)
    c=sub.add_parser("conformal-p"); c.add_argument("--cal",required=True); c.add_argument("--test",required=True)
    a=ap.parse_args()
    if a.cmd=="verify": return verify(a.seed,a.json)
    if a.cmd=="bh":
        p=read1(a.pvals); R=sorted(bh(p,a.q))
        print(json.dumps({"rejections":R,"n_rejected":len(R),"q":a.q})); return 0
    cal=read1(a.cal)
    print(json.dumps({"p_values":[conformal_p(cal,s) for s in read1(a.test)]})); return 0

if __name__=="__main__": sys.exit(main())
