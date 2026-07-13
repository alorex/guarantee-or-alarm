"""Vignette 10: composition — a three-skill chain with assumption
propagation (prediction-powered-inference + anytime-valid + the gate
discipline of conformal-uq).

Pipeline: every day an LLM labels N=2,000 documents for a property with
true prevalence 10%; a human audits a random n=40 gold subsample.
  Link 1 (PPI): the day's prevalence estimate is PPI-corrected using that
    day's gold subsample -- valid per day REGARDLESS of labeler quality,
    because the rectifier is estimated on the same day's gold labels.
  Link 2 (anytime-valid monitor): a Robbins normal-mixture confidence
    sequence watches the running mean of the rectifier (Y - f), calibrated
    on a 10-day burn-in. If the labeler's error structure drifts, the
    rectifier mean shifts and the CS fires at a controlled false-alarm rate
    -- the Layer-3 alarm that tells the operator the upstream link changed.
Perturbation: at day 31 of 60 the labeler silently degrades (specificity
0.97 -> 0.85, a false-positive burst -- e.g. a model upgrade or a new
document domain). The monitor's boundary runs in intrinsic time
v_n = n + n^2/m, which charges the sequence for the uncertainty of the
burn-in baseline estimated from m gold labels.

What composition preserves and what it does not: the PPI interval stays
valid throughout (its guarantee needs only each day's gold pairing); the
model-only estimate degrades silently; the monitor converts the silent
upstream drift into an explicit alarm within days. Reported: PPI daily
coverage over the full horizon, model-only error before/after drift, alarm
day distribution, and the false-alarm rate of the monitor when no drift
occurs.
"""
import math
import random

SEED = 2026
PI = 0.10
N_BULK, N_GOLD = 2000, 40
DAYS, DRIFT_DAY, BURN = 60, 31, 10
SENS0, SPEC0 = 0.92, 0.97
SPEC1 = 0.85                      # after silent drift: false-positive burst
ALPHA, RHO = 0.05, 10.0
R = 200
Z90 = 1.6448536269514722


def label(rng, y, spec):
    return (1 if rng.random() < SENS0 else 0) if y else \
           (1 if rng.random() > spec else 0)


def day_batch(rng, spec):
    gold = []
    for _ in range(N_GOLD):
        y = 1 if rng.random() < PI else 0
        gold.append((y, label(rng, y, spec)))
    # bulk mean of f via a subsample proxy for the 2,000 bulk docs
    mf = 0.0
    for _ in range(200):
        y = 1 if rng.random() < PI else 0
        mf += label(rng, y, spec)
    return gold, mf / 200


def cs_boundary(v):
    """Robbins normal-mixture boundary in intrinsic time v."""
    return math.sqrt((v + RHO) * (math.log((v + RHO) / RHO)
                                  + 2.0 * math.log(1.0 / ALPHA)))


def run(rng, with_drift):
    alarm_day = None
    covered = total = 0
    # burn-in: estimate the rectifier's stable mean and sd from m gold labels
    burn = []
    for _ in range(BURN):
        gold, _ = day_batch(rng, SPEC0)
        burn += [y - f for y, f in gold]
    m = len(burn)
    mu0 = sum(burn) / m
    sd0 = max(1e-6, math.sqrt(sum((x - mu0) ** 2 for x in burn) / (m - 1)))
    s = n = 0
    model_err_pre, model_err_post = [], []
    for day in range(BURN + 1, DAYS + 1):
        spec = SPEC1 if (with_drift and day >= DRIFT_DAY) else SPEC0
        gold, mf = day_batch(rng, spec)
        # Link 1: PPI daily interval
        rect = [y - f for y, f in gold]
        mr = sum(rect) / len(rect)
        vr = sum((x - mr) ** 2 for x in rect) / (len(rect) - 1)
        est = mf + mr
        half = Z90 * math.sqrt(mf * (1 - mf) / 200 + vr / N_GOLD)
        covered += (est - half <= PI <= est + half)
        total += 1
        (model_err_post if (with_drift and day >= DRIFT_DAY)
         else model_err_pre).append(abs(mf - PI))
        # Link 2: anytime-valid monitor on standardized rectifier stream;
        # intrinsic time charges for the estimated baseline's uncertainty
        for x in rect:
            n += 1
            s += (x - mu0) / sd0
            v = n + n * n / m
            if alarm_day is None and abs(s) > cs_boundary(v):
                alarm_day = day
    return covered / total, alarm_day, model_err_pre, model_err_post


def main():
    rng = random.Random(SEED)
    cov, alarms, pre, post = [], [], [], []
    fa = 0
    for _ in range(R):
        c, a, p1, p2 = run(rng, with_drift=True)
        cov.append(c)
        if a is not None and a >= DRIFT_DAY:
            alarms.append(a)
        pre += p1
        post += p2
        _, a0, _, _ = run(rng, with_drift=False)
        fa += a0 is not None
    alarms.sort()
    avg = lambda xs: sum(xs) / len(xs)
    print(f"RESULT ppi_daily_coverage_full_horizon={avg(cov):.3f} "
          f"(nominal 0.90; valid through the drift)")
    print(f"RESULT model_only_abs_error: pre_drift={avg(pre):.4f} "
          f"post_drift={avg(post):.4f} (silent degradation)")
    print(f"RESULT monitor: detection_rate="
          f"{len(alarms) / R:.3f} median_alarm_day="
          f"{alarms[len(alarms) // 2] if alarms else None} "
          f"(drift at day {DRIFT_DAY}) "
          f"false_alarm_rate_no_drift={fa / R:.3f} (target {ALPHA})")


if __name__ == "__main__":
    main()
