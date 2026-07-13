#!/usr/bin/env python3
"""dml_demo.py - double/debiased ML on synthetic confounded data, verified.

Partially linear model: Y = theta*D + g(X) + eps, D = m(X) + nu, nonlinear g, m.
Shows the two failure modes DML exists to fix and that DML fixes them:
  V1 naive OLS of Y on D (ignoring X): biased, truth far outside CI
  V2 regularization bias: single residualization (Y - oversmoothed ghat) on raw D
     is non-orthogonal in m -> nuisance error transmits FIRST-order, biased
  V3 DML: same 1-NN-family nuisance (k-NN, k=8) WITH K-fold cross-fitting +
     orthogonal (residual-on-residual) score: truth covered at ~nominal rate over reps
  V4 orthogonality signature: SYSTEMATIC nuisance tilt delta*x injected into BOTH
     residualizations -> bias grows ~quadratically in delta (second-order), the
     defining property of a Neyman-orthogonal score
CLI: python dml_demo.py verify [--seed 1] [--json]      exit 0 iff all pass
Pure stdlib; k-NN nuisances in 1-D X for speed.
"""
import argparse, json, math, random, sys

THETA = 1.5

def gen(rng, n):
    X = [rng.uniform(-2,2) for _ in range(n)]
    m = [math.sin(1.5*x) + 0.5*x for x in X]              # E[D|X]
    D = [mi + rng.gauss(0,0.7) for mi in m]
    g = [0.8*x*x + 1.5*x + 1.2*math.cos(x) for x in X]    # E[Y|X] part, cov(m,g)>0
    Y = [THETA*d + gi + rng.gauss(0,1) for d,gi in zip(D,g)]
    return X, D, Y

def knn_fit_predict(x_tr, y_tr, x_te, k=8):
    """predict E[y|x] at x_te by k nearest neighbors in 1-D (sorted two-pointer)."""
    order = sorted(range(len(x_tr)), key=lambda i: x_tr[i])
    xs = [x_tr[i] for i in order]; ys = [y_tr[i] for i in order]
    import bisect
    out=[]
    for x in x_te:
        j = bisect.bisect_left(xs, x)
        lo, hi = max(0,j-k), min(len(xs), j+k)
        cand = sorted(range(lo,hi), key=lambda i: abs(xs[i]-x))[:k]
        out.append(sum(ys[i] for i in cand)/len(cand))
    return out

def ols_slope_ci(d, y):
    n=len(d); md=sum(d)/n; my=sum(y)/n
    sdd=sum((x-md)**2 for x in d); 
    th=sum((x-md)*(v-my) for x,v in zip(d,y))/sdd
    res=[v-my-th*(x-md) for x,v in zip(d,y)]
    se=math.sqrt((sum(r*r for r in res)/(n-2))/sdd)
    return th, th-1.96*se, th+1.96*se

def dml_plr(X, D, Y, K=5, k=8, rng=None, tilt=0.0):
    n=len(X); idx=list(range(n))
    if rng: rng.shuffle(idx)
    folds=[idx[i::K] for i in range(K)]
    Dres=[0.0]*n; Yres=[0.0]*n
    for f in folds:
        tr=[i for i in idx if i not in set(f)]
        mhat=knn_fit_predict([X[i] for i in tr],[D[i] for i in tr],[X[i] for i in f],k)
        ghat=knn_fit_predict([X[i] for i in tr],[Y[i] for i in tr],[X[i] for i in f],k)
        for j,i in enumerate(f):
            Dres[i]=D[i]-(mhat[j]+tilt*X[i]); Yres[i]=Y[i]-(ghat[j]+tilt*X[i])
    return ols_slope_ci(Dres, Yres)

def single_resid_oversmoothed(X, D, Y, k=200):
    # non-orthogonal: partial X out of Y only (oversmoothed), regress on RAW D
    ghat=knn_fit_predict(X, Y, X, k)
    Yres=[y-g for y,g in zip(Y,ghat)]
    return ols_slope_ci(D, Yres)

def verify(seed=1, json_out=False):
    rng=random.Random(seed)
    n, M = 600, 120
    checks={}
    # V1 naive OLS (single large rep is enough to show gross bias + repeated cover check)
    cov1=0; ths=[]
    for _ in range(40):
        X,D,Y=gen(rng,n); th,lo,hi=ols_slope_ci(D,Y); ths.append(th); cov1+= (lo<=THETA<=hi)
    checks["V1_naive_ols_biased"]={"mean_theta":round(sum(ths)/len(ths),3),"truth":THETA,
        "coverage":cov1/40,"pass": abs(sum(ths)/len(ths)-THETA)>0.15 and cov1/40<0.3}
    # V2 non-orthogonal single residualization with oversmoothed nuisance
    ths2=[]; cov2=0
    for _ in range(40):
        X,D,Y=gen(rng,n); th,lo,hi=single_resid_oversmoothed(X,D,Y,200); ths2.append(th); cov2+=(lo<=THETA<=hi)
    m2=sum(ths2)/len(ths2)
    checks["V2_nonorthogonal_biased"]={"mean_theta":round(m2,3),"truth":THETA,
        "coverage":cov2/40,"pass": abs(m2-THETA)>0.15 and cov2/40<0.5}
    # V3 DML coverage over M reps
    cov3=0; ths3=[]
    for _ in range(M):
        X,D,Y=gen(rng,n); th,lo,hi=dml_plr(X,D,Y,5,8,rng); ths3.append(th); cov3+=(lo<=THETA<=hi)
    m3=sum(ths3)/M; band=3*math.sqrt(0.05*0.95/M)+0.02
    checks["V3_dml_covers"]={"mean_theta":round(m3,3),"truth":THETA,
        "coverage":round(cov3/M,3),"pass": abs(cov3/M-0.95)<band and abs(m3-THETA)<0.05}
    # V4 orthogonality signature: systematic tilt delta*x in both nuisances;
    # orthogonal score => bias ~ quadratic in delta (ratio ~ (0.4/0.2)^2 = 4)
    biases=[]
    for s in (0.2,0.4):
        tt=[]
        for _ in range(60):
            X,D,Y=gen(rng,n); th,_,_=dml_plr(X,D,Y,5,8,rng,tilt=s); tt.append(th)
        biases.append(abs(sum(tt)/len(tt)-THETA))
    ratio = biases[1]/max(biases[0],1e-9)
    checks["V4_orthogonality_quadratic_bias"]={"bias_d0.2":round(biases[0],4),
        "bias_d0.4":round(biases[1],4),"ratio":round(ratio,2),
        "pass": biases[0]<0.08 and 2.2<ratio<6.0}
    ok=all(c["pass"] for c in checks.values())
    out={"n":n,"checks":checks,"all_pass":ok}
    print(json.dumps(out,indent=2) if json_out else
          "\n".join(f"{k}: {'PASS' if v['pass'] else 'FAIL'}" for k,v in checks.items()))
    return 0 if ok else 1

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    v=sub.add_parser("verify"); v.add_argument("--seed",type=int,default=1); v.add_argument("--json",action="store_true")
    a=ap.parse_args(); return verify(a.seed,a.json)

if __name__=="__main__": sys.exit(main())
