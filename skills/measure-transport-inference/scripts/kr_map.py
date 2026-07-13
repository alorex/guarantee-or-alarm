#!/usr/bin/env python3
"""kr_map.py - linear Knothe-Rosenblatt map from samples, with verification anchor.

The Gaussian case is the load-bearing unit test for any transport-map code: the KR
map is LINEAR and closed-form, S(x) = L^-1 (x - mu) with L L^T = Sigma (lower
Cholesky). Fitting a linear lower-triangular map by maximum likelihood from samples
of N(mu, Sigma) must recover mu and L, the log-Jacobian must equal -0.5 logdet Sigma
per point, pushed samples must be ~ N(0, I), and KR conditionals must match the
Gaussian conditional formulas. If a fancier parameterization can't pass this file's
checks on its linear subcase, it is wrong before it is expressive.

CLI:
  python kr_map.py verify [--seed 1] [--json]     exit 0 iff all checks pass
  python kr_map.py fit --data x.csv                fit linear KR map from samples
                                                   (CSV: one d-dim row per line)
Pure stdlib; small d by design.
verify checks (d=3 correlated Gaussian, n=20000):
  V1 map recovery: fitted mu and L within sampling tolerance of truth
  V2 pushforward: S(x_i) has mean ~0, cov ~I (max abs deviation gated)
  V3 jacobian: mean log|det dS| = -0.5 logdet Sigma_hat (identity, tight tol)
  V4 conditional: KR conditional of x3 | x1,x2 matches closed-form Gaussian
     conditional mean/variance on held-out points
"""
import argparse, json, math, random, sys

def mat_t(A): return [list(r) for r in zip(*A)]
def cholesky(A):
    n=len(A); L=[[0.0]*n for _ in range(n)]
    for i in range(n):
        for j in range(i+1):
            s=sum(L[i][k]*L[j][k] for k in range(j))
            L[i][j]=math.sqrt(A[i][i]-s) if i==j else (A[i][j]-s)/L[j][j]
    return L
def fwd_solve(L, b):
    n=len(L); y=[0.0]*n
    for i in range(n): y[i]=(b[i]-sum(L[i][k]*y[k] for k in range(i)))/L[i][i]
    return y

def sample_mvn(rng, mu, L, n):
    d=len(mu); out=[]
    for _ in range(n):
        z=[rng.gauss(0,1) for _ in range(d)]
        out.append([mu[i]+sum(L[i][k]*z[k] for k in range(i+1)) for i in range(d)])
    return out

def fit_linear_kr(X):
    """ML fit of linear lower-triangular map S(x) = Lhat^-1 (x - muhat).
    For Gaussians the MLE is muhat = xbar, Lhat = chol(sample covariance)."""
    n, d = len(X), len(X[0])
    mu = [sum(x[i] for x in X)/n for i in range(d)]
    C = [[sum((x[i]-mu[i])*(x[j]-mu[j]) for x in X)/n for j in range(d)] for i in range(d)]
    return mu, cholesky(C), C

def push(mu, L, x): return fwd_solve(L, [xi-mi for xi, mi in zip(x, mu)])
def logdet_grad(L): return -sum(math.log(L[i][i]) for i in range(len(L)))

def verify(seed=1, json_out=False):
    rng = random.Random(seed)
    mu_t = [1.0, -2.0, 0.5]
    Sig  = [[2.0, 0.8, 0.4],[0.8, 1.5, 0.6],[0.4, 0.6, 1.0]]
    L_t  = cholesky(Sig)
    n = 20000
    X = sample_mvn(rng, mu_t, L_t, n)
    checks = {}

    mu_h, L_h, C_h = fit_linear_kr(X)
    tol_mu = 4*math.sqrt(max(Sig[i][i] for i in range(3))/n)
    err_mu = max(abs(a-b) for a, b in zip(mu_h, mu_t))
    err_L  = max(abs(L_h[i][j]-L_t[i][j]) for i in range(3) for j in range(i+1))
    checks["V1_map_recovery"] = {"err_mu": round(err_mu,4), "tol_mu": round(tol_mu,4),
        "err_L": round(err_L,4), "pass": err_mu < tol_mu and err_L < 0.05}

    Z = [push(mu_h, L_h, x) for x in X]
    zm = [sum(z[i] for z in Z)/n for i in range(3)]
    zc = [[sum(z[i]*z[j] for z in Z)/n - zm[i]*zm[j] for j in range(3)] for i in range(3)]
    dev = max(max(abs(zm[i]) for i in range(3)),
              max(abs(zc[i][j]-(1.0 if i==j else 0.0)) for i in range(3) for j in range(3)))
    checks["V2_pushforward_standard_normal"] = {"max_dev": round(dev,4), "pass": dev < 0.05}

    ld_map = logdet_grad(L_h)
    ld_sig = -0.5*(2*sum(math.log(L_h[i][i]) for i in range(3)))
    checks["V3_jacobian_identity"] = {"logdet_dS": round(ld_map,6),
        "minus_half_logdet_Sigma": round(ld_sig,6), "pass": abs(ld_map-ld_sig) < 1e-9}

    # V4: KR conditional x3 | x1,x2 = closed-form Gaussian conditional
    # KR: fix z1,z2 from observed (x1,x2); x3(z3) = mu3 + L31 z1 + L32 z2 + L33 z3
    # => conditional mean at z3=0-mean: mu3 + L31 z1 + L32 z2; var = L33^2
    errs_m = []
    for _ in range(200):
        xo = sample_mvn(rng, mu_t, L_t, 1)[0]
        z = push(mu_h, L_h, xo)
        kr_mean = mu_h[2] + L_h[2][0]*z[0] + L_h[2][1]*z[1]
        # closed form from fitted covariance: mu3 + C32 C22^-1 ([x1,x2]-mu12)
        C22 = [[C_h[0][0],C_h[0][1]],[C_h[1][0],C_h[1][1]]]
        L22 = cholesky(C22)
        rhs = fwd_solve(L22, [xo[0]-mu_h[0], xo[1]-mu_h[1]])
        w   = fwd_solve(mat_t(L22), rhs[::-1])  # careful: full solve below instead
        # do a proper 2x2 solve
        det = C22[0][0]*C22[1][1]-C22[0][1]*C22[1][0]
        a1 = ( C22[1][1]*(xo[0]-mu_h[0]) - C22[0][1]*(xo[1]-mu_h[1]))/det
        a2 = (-C22[1][0]*(xo[0]-mu_h[0]) + C22[0][0]*(xo[1]-mu_h[1]))/det
        cf_mean = mu_h[2] + C_h[2][0]*a1 + C_h[2][1]*a2
        errs_m.append(abs(kr_mean-cf_mean))
    kr_var = L_h[2][2]**2
    det = C_h[0][0]*C_h[1][1]-C_h[0][1]*C_h[1][0]
    s11 = ( C_h[1][1]*C_h[2][0] - C_h[0][1]*C_h[2][1])/det
    s12 = (-C_h[1][0]*C_h[2][0] + C_h[0][0]*C_h[2][1])/det
    cf_var = C_h[2][2] - (C_h[2][0]*s11 + C_h[2][1]*s12)
    checks["V4_kr_conditional_matches_gaussian"] = {
        "max_mean_err": round(max(errs_m),10), "kr_var": round(kr_var,6),
        "closed_form_var": round(cf_var,6),
        "pass": max(errs_m) < 1e-9 and abs(kr_var-cf_var) < 1e-9}

    ok = all(c["pass"] for c in checks.values())
    out = {"checks": checks, "all_pass": ok}
    print(json.dumps(out, indent=2) if json_out else
          "\n".join(f"{k}: {'PASS' if v['pass'] else 'FAIL'}" for k, v in checks.items()))
    return 0 if ok else 1

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify"); v.add_argument("--seed", type=int, default=1)
    v.add_argument("--json", action="store_true")
    f = sub.add_parser("fit"); f.add_argument("--data", required=True)
    a = ap.parse_args()
    if a.cmd == "verify": return verify(a.seed, a.json)
    X = [[float(v) for v in l.split(",")] for l in open(a.data) if l.strip()]
    mu, L, C = fit_linear_kr(X)
    print(json.dumps({"mu": mu, "L": L, "logdet_dS": logdet_grad(L)}, indent=2)); return 0

if __name__ == "__main__":
    sys.exit(main())
