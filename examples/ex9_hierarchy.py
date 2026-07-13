"""Vignette 9: paying for intelligence correctly (model-hierarchy).

Bulk workload of 100,000 items. Cheap model: 88% correct, cost 1/item.
Frontier model: 97% correct, cost 25/item. Verifier: cost 2/item, flags an
incorrect cheap answer with probability 0.92 (recall) and a correct one
with probability 0.08 (false-alarm rate); flagged items are redone by the
frontier model. A wrong artifact shipped downstream costs 200.

Strategies compared on cost per item, residual defect rate, cost per
CORRECT artifact, and total cost including downstream damage.
"""
import random

SEED = 2026
N_ITEMS = 100_000
ACC_CHEAP, COST_CHEAP = 0.88, 1.0
ACC_FRONT, COST_FRONT = 0.97, 25.0
VER_RECALL, VER_FA, COST_VER = 0.92, 0.08, 2.0
DOWNSTREAM = 200.0


def run(strategy, rng):
    cost = defects = 0.0
    for _ in range(N_ITEMS):
        if strategy == "all-frontier":
            cost += COST_FRONT
            ok = rng.random() < ACC_FRONT
        elif strategy == "all-cheap":
            cost += COST_CHEAP
            ok = rng.random() < ACC_CHEAP
        else:                                   # cascade
            cost += COST_CHEAP + COST_VER
            ok = rng.random() < ACC_CHEAP
            flagged = rng.random() < (VER_RECALL if not ok else VER_FA)
            if flagged:
                cost += COST_FRONT
                ok = rng.random() < ACC_FRONT
        defects += not ok
    return cost / N_ITEMS, defects / N_ITEMS


def main():
    rng = random.Random(SEED)
    for strategy in ("all-cheap", "all-frontier", "cascade"):
        c, d = run(strategy, rng)
        per_correct = c / (1 - d)
        total = c + d * DOWNSTREAM
        print(f"RESULT {strategy:>12}: cost_per_item={c:6.2f} "
              f"defect_rate={d:.4f} cost_per_correct={per_correct:6.2f} "
              f"cost_incl_downstream={total:6.2f}")


if __name__ == "__main__":
    main()
