"""Vignette 2: the always-on dashboard (anytime-valid inference).

A metric delta is observed daily for 365 days, increments iid N(mu, 1).
Naive practice: two-sided z-test at alpha=0.05 on the running mean, every
day; the team "acts" at the first significant day. Anytime-valid practice:
a Robbins normal-mixture confidence sequence (mixture N(0, 1/rho) over the
drift gives the supermartingale M_n = sqrt(rho/(n+rho)) exp(S_n^2/(2(n+rho)));
Ville's inequality turns it into a time-uniform boundary).

Part A (null, mu=0): probability of at least one false alarm in a year.
Part B (real effect, mu=0.25): median day at which the CS legitimately stops.
"""
import math
import random

SEED = 2026
ALPHA = 0.05
RHO = 10.0
DAYS = 365
R = 2000


def cs_boundary(n):
    return math.sqrt((n + RHO) * (math.log((n + RHO) / RHO)
                                  + 2.0 * math.log(1.0 / ALPHA)))


Z975 = 1.959963984540054


def run_path(rng, mu):
    """Return (day of first naive rejection, day of first CS crossing)."""
    s, naive_day, cs_day = 0.0, None, None
    for n in range(1, DAYS + 1):
        s += rng.gauss(mu, 1.0)
        if naive_day is None and abs(s) / math.sqrt(n) > Z975:
            naive_day = n
        if cs_day is None and abs(s) > cs_boundary(n):
            cs_day = n
        if naive_day and cs_day:
            break
    return naive_day, cs_day


def main():
    rng = random.Random(SEED)
    # Part A: null
    fa_naive = fa_cs = 0
    for _ in range(R):
        nd, cd = run_path(rng, 0.0)
        fa_naive += nd is not None
        fa_cs += cd is not None
    print(f"RESULT null: naive_false_alarm_rate={fa_naive / R:.3f} "
          f"cs_false_alarm_rate={fa_cs / R:.3f} (target {ALPHA})")
    # Part B: true drift
    stops = []
    detected = 0
    for _ in range(R):
        _, cd = run_path(rng, 0.25)
        if cd is not None:
            detected += 1
            stops.append(cd)
    stops.sort()
    med = stops[len(stops) // 2] if stops else None
    print(f"RESULT effect(mu=0.25): cs_detection_rate={detected / R:.3f} "
          f"median_stopping_day={med} (fixed-horizon design would wait {DAYS})")


if __name__ == "__main__":
    main()
