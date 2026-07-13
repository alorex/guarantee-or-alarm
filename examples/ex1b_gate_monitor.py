"""Vignette 1b: closing the gate's drift gap (conformal-uq + anytime-valid).

The calibrated verifier gate of ex1 guarantees its accepted-defect bound
only under exchangeability of calibration and deployment; ex1's
perturbation shows post-calibration drift voiding the guarantee silently.
This companion ships the missing alarm: a daily gold audit of a=20
randomly chosen ACCEPTED artifacts feeds an anytime-valid monitor (Robbins
normal-mixture boundary in intrinsic time v = n + n^2/m, charging for the
baseline defect rate being estimated from the m accepted calibration
items). When the accepted-defect rate drifts off its calibration value,
the monitor fires at a controlled false-alarm rate and the gate escalates
to recalibration.

Deployment: 40 days x 500 artifacts/day; drift begins day 21 (a new defect
type the judge scores higher, as in ex1). Reported: detection rate, median
alarm day, and the monitor's false-alarm rate over a no-drift horizon.
"""
import math
import random

from ex1_conformal_gate import (DEFECT_RATE, N_CAL, calibrate, draw,
                                draw_drifted)

SEED = 2026
DAYS, DRIFT_DAY = 40, 21
N_DAY, N_AUDIT = 500, 20
ALPHA, RHO = 0.05, 10.0
R = 300


def cs_boundary(v):
    return math.sqrt((v + RHO) * (math.log((v + RHO) / RHO)
                                  + 2.0 * math.log(1.0 / ALPHA)))


def run(rng, with_drift):
    cal = [draw(rng) for _ in range(N_CAL)]
    t_hat = calibrate(cal)
    accepted_cal = [bad for s, bad in cal if s >= t_hat]
    m = max(2, len(accepted_cal))
    p0 = max(1e-3, sum(accepted_cal) / m)
    sd0 = math.sqrt(p0 * (1 - p0))
    s = n = 0
    for day in range(1, DAYS + 1):
        gen = draw_drifted if (with_drift and day >= DRIFT_DAY) else draw
        accepted = [bad for s_, bad in (gen(rng) for _ in range(N_DAY))
                    if s_ >= t_hat]
        audit = accepted[:N_AUDIT] if len(accepted) >= N_AUDIT else accepted
        for bad in audit:
            n += 1
            s += (bad - p0) / sd0
            v = n + n * n / m
            if abs(s) > cs_boundary(v):
                return day
    return None


def main():
    rng = random.Random(SEED)
    alarms, fa = [], 0
    for _ in range(R):
        a = run(rng, with_drift=True)
        if a is not None and a >= DRIFT_DAY:
            alarms.append(a)
        fa += run(rng, with_drift=False) is not None
    alarms.sort()
    print(f"RESULT monitored_gate: detection_rate={len(alarms) / R:.3f} "
          f"median_alarm_day={alarms[len(alarms) // 2] if alarms else None} "
          f"(drift at day {DRIFT_DAY}) "
          f"false_alarm_rate_no_drift={fa / R:.3f} (target {ALPHA})")


if __name__ == "__main__":
    main()
