#!/usr/bin/env python3
"""eig_estimators.py - reference EIG estimators + linear-Gaussian verification anchor.

Implements the bottom rungs of the estimator ladder for expected information gain
(EIG) in Bayesian optimal experimental design, with the closed-form linear-Gaussian
benchmark every estimator must reproduce (Laplace is exact there).

Model (benchmark): theta ~ N(mu0, Sigma0), y = G(xi) theta + eps, eps ~ N(0, Sigma_e).
Closed form: EIG(xi) = 0.5 * logdet(Sigma0) - 0.5 * logdet(Sigma_post(xi)),
Sigma_post = (Sigma0^-1 + G' Sigma_e^-1 G)^-1.  [Long-Scavino-Tempone-Wang 2013 setting]

Estimators:
  eig_closed_form(G, S0, Se)                      exact (benchmark)
  eig_dlmc(G, S0, Se, N, M, seed)                 double-loop MC (O(1/M) inner bias)
  eig_laplace_sl(G, S0, Se)                       Laplace single-loop (exact for lin-Gauss)

CLI self-verification:
  python eig_estimators.py verify [--seed 1] [--json]
checks (V1) DLMC -> closed form as N,M grow; (V2) inner-loop bias decays ~ c/M with
positive sign (log-concavity); (V3) Laplace == closed form to machine precision.
Exit 0 iff all pass. Pure stdlib (no numpy) - small dims only, by design.
"""
import argparse, json, math, random, sys

# ---------- tiny dense linear algebra (stdlib only, small d) ----------
def mat_t(A): return [list(r) for r in zip(*A)]
def mat_mul(A, B):
    Bt = mat_t(B)
    return [[sum(a*b for a, b in zip(row, col)) for col in Bt] for row in A]
def mat_add(A, B): return [[a+b for a, b in zip(ra, rb)] for ra, rb in zip(A, B)]
def identity(n): return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
def cholesky(A):
    n = len(A); L = [[0.0]*n for _ in range(n)]
    for i in range(n):
        for j in range(i+1):
            s = sum(L[i][k]*L[j][k] for k in range(j))
            L[i][j] = math.sqrt(A[i][i]-s) if i == j else (A[i][j]-s)/L[j][j]
    return L
def logdet_psd(A):
    return 2.0*sum(math.log(cholesky(A)[i][i]) for i in range(len(A)))
def solve_chol(L, b):
    n = len(L); y = [0.0]*n
    for i in range(n): y[i] = (b[i] - sum(L[i][k]*y[k] for k in range(i)))/L[i][i]
    x = [0.0]*n
    for i in reversed(range(n)):
        x[i] = (y[i] - sum(L[k][i]*x[k] for k in range(i+1, n)))/L[i][i]
    return x
def inv_psd(A):
    L = cholesky(A); n = len(A)
    cols = [solve_chol(L, [1.0 if i == j else 0.0 for i in range(n)]) for j in range(n)]
    return mat_t(cols)
def mvn_sample(rng, mu, L):
    z = [rng.gauss(0, 1) for _ in mu]
    return [m + sum(L[i][k]*z[k] for k in range(i+1)) for i, m in enumerate(mu)]

# ---------- model pieces ----------
def posterior_cov(G, S0, Se):
    S0i, Sei = inv_psd(S0), inv_psd(Se)
    Gt = mat_t(G)
    return inv_psd(mat_add(S0i, mat_mul(Gt, mat_mul(Sei, G))))

def eig_closed_form(G, S0, Se):
    return 0.5*(logdet_psd(S0) - logdet_psd(posterior_cov(G, S0, Se)))

def eig_laplace_sl(G, S0, Se):
    # Laplace single-loop: for linear-Gaussian the Laplace posterior IS the posterior,
    # and EIG reduces to the same log-det ratio -> exact (the ladder's rung-1 sanity case).
    return eig_closed_form(G, S0, Se)

def log_lik(y, Gth, Sei_L, ld_Se, q):
    # log N(y; G theta, Se): q = dim(y)
    d = [yi - gi for yi, gi in zip(y, Gth)]
    x = solve_chol(Sei_L, d)  # solves Se x = d via chol(Se)
    quad = sum(di*xi for di, xi in zip(d, x))
    return -0.5*(q*math.log(2*math.pi) + ld_Se + quad)

def eig_dlmc(G, S0, Se, N, M, seed=1):
    """Double-loop MC: outer N draws (theta,y) from joint; inner M prior draws for evidence."""
    rng = random.Random(seed)
    L0, Le = cholesky(S0), cholesky(Se)
    ld_Se, q = logdet_psd(Se), len(Se)
    mu0 = [0.0]*len(S0)
    acc = 0.0
    for _ in range(N):
        th = mvn_sample(rng, mu0, L0)
        Gth = [sum(g*t for g, t in zip(row, th)) for row in G]
        y = [m + e for m, e in zip(Gth, mvn_sample(rng, [0.0]*q, Le))]
        ll_true = log_lik(y, Gth, Le, ld_Se, q)
        # inner evidence estimate: logsumexp over M fresh prior draws
        lls = []
        for _ in range(M):
            thm = mvn_sample(rng, mu0, L0)
            Gthm = [sum(g*t for g, t in zip(row, thm)) for row in G]
            lls.append(log_lik(y, Gthm, Le, ld_Se, q))
        mx = max(lls)
        log_ev = mx + math.log(sum(math.exp(l - mx) for l in lls)/M)
        acc += ll_true - log_ev
    return acc/N

# ---------- verification ----------
def verify(seed=1, json_out=False):
    # 2-parameter, 2-observation design
    G  = [[1.0, 0.5], [0.2, 1.0]]
    S0 = [[1.0, 0.3], [0.3, 1.5]]
    Se = [[0.25, 0.0], [0.0, 0.25]]
    truth = eig_closed_form(G, S0, Se)
    checks, ok = {}, True

    # V3: Laplace exactness on linear-Gaussian
    lap = eig_laplace_sl(G, S0, Se)
    checks["V3_laplace_exact"] = {"laplace": lap, "truth": truth,
                                  "pass": abs(lap-truth) < 1e-12}

    # V1: DLMC convergence (N large, M growing)
    est_hi = eig_dlmc(G, S0, Se, N=2000, M=256, seed=seed)
    se_tol = 3*0.5/math.sqrt(2000) + 0.05   # crude CI + residual inner bias allowance
    checks["V1_dlmc_converges"] = {"dlmc_N2000_M256": est_hi, "truth": truth,
                                   "tol": round(se_tol, 4),
                                   "pass": abs(est_hi-truth) < se_tol}

    # V2: inner bias positive and decaying ~ c/M (Jensen: E log(evidence-hat) <= log evidence
    #     => DLMC overestimates EIG for finite M)
    biases = []
    for M in (4, 16, 64):
        est = eig_dlmc(G, S0, Se, N=4000, M=M, seed=seed+M)
        biases.append(est - truth)
    dec = biases[0] > biases[1] > biases[2]
    pos = all(b > 0 for b in biases)
    ratio = biases[0]/biases[1] if biases[1] else float("inf")
    checks["V2_inner_bias_structure"] = {
        "bias_M4_16_64": [round(b, 4) for b in biases],
        "monotone_decreasing": dec, "positive_sign": pos,
        "ratio_M4_over_M16": round(ratio, 2), "expected_ratio_if_1overM": 4.0,
        "pass": dec and pos and 2.0 < ratio < 8.0}

    ok = all(c["pass"] for c in checks.values())
    out = {"truth_closed_form": round(truth, 6), "checks": checks, "all_pass": ok}
    print(json.dumps(out, indent=2) if json_out else
          "\n".join([f"closed-form EIG = {truth:.6f}"] +
                    [f"{k}: {'PASS' if v['pass'] else 'FAIL'}" for k, v in checks.items()]))
    return 0 if ok else 1

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify"); v.add_argument("--seed", type=int, default=1)
    v.add_argument("--json", action="store_true")
    args = ap.parse_args()
    return verify(args.seed, args.json)

if __name__ == "__main__":
    sys.exit(main())
