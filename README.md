# Guarantee or Alarm

**Statistical verification for LLM-assisted decision pipelines** — a library
of agent skills (markdown playbooks + dependency-free Python) implementing a
three-layer framework:

1. **Verification of tooling.** Every statistical procedure ships with an
   *exact anchor*: a closed-form or finite-sample ground truth the code must
   reproduce (the analogue of the method of exact solutions).
2. **Operating-characteristic verification.** Every procedure demonstrates
   its coverage / FDR / false-alarm behavior on synthetic ground truth, with
   the naive analysis run alongside as control, and with perturbation checks
   that violate its assumptions to show what breaks and which alarm fires.
3. **Runtime guarantee-or-alarm.** A number delivered to a decision carries
   a stated guarantee — of a stated kind, under stated assumptions, feeding
   a named loss — or a machine-readable alarm fires and the case escalates.

Companion repository for the paper *"Guarantee or Alarm: Statistical
Verification for LLM-Assisted Decision Pipelines"* (arXiv link upon
publication). Every number in the paper reproduces from `examples/`.

## Quickstart

Requires Python ≥ 3.9, standard library only. No pip installs.

```bash
cd examples
python run_all.py            # runs all demonstrations (~5 minutes)
python run_all.py --check    # verifies output against expected_results.txt
python ex1_conformal_gate.py # or run any single demonstration
```

## The skills

Each `skills/<name>/` package contains `SKILL.md` (the playbook: when the
method applies, decision points, failure modes, stopping rules) and
`scripts/` (verified reference implementations — agents invoke these, never
re-implement them).

| Skill | Owns | Guarantee class |
|---|---|---|
| `conformal-uq` | Prediction sets; calibrated LLM-verifier gates | exact finite-sample (exchangeability) |
| `anytime-valid` | Confidence sequences, e-values, online FDR | exact time-uniform (martingale) |
| `prediction-powered-inference` | Valid inference from model labels + gold subset | asymptotic |
| `selective-inference` | Multiplicity, winner's curse, post-selection CIs | exact conditional / FDR |
| `causal-ml` | DML/AIPW, heterogeneous effects, policy learning | asymptotic, conditional on identification |
| `bayesian-optimal-design` | Expected-information-gain design ladder | model-based finite-sample |
| `rare-event-is` | Importance sampling / splitting for tail probabilities | diagnostic-gated |
| `risk-measure-estimation` | VaR/CVaR, nested simulation | asymptotic + bias-aware allocation |
| `simulation-output-analysis` | Batch means, transient handling, unbiased MLMC | asymptotic + shipped diagnostics |
| `measure-transport-inference` | Triangular transport maps for Bayesian inference | anchor-verified, diagnostic-gated |
| `model-hierarchy` | Cost-tiered orchestration; cost per *verified* artifact | economic (measured) |
| `statistical-grounding` | The base contract (8 rules) binding the library | — |

## The demonstrations (`examples/`)

`ex1`–`ex10` map to the paper's use-case vignettes; `ex1b` (gate drift
monitor) and the perturbation modes of `ex1`/`ex7` are the assumption-
violation checks; `ex10` is the three-skill composition chain (PPI daily
intervals + anytime-valid drift monitor over a silently degrading labeler).
All seeds fixed (2026); pure-Python `random` is deterministic across
platforms, so `--check` compares exact output.

## Scope (read before deploying)

The anchors certify the **reference scripts**, not an agent's decision to
invoke them or the arguments it constructs; alarms are emitted as
machine-readable artifacts intended for a harness, not for the agent's
prose. Statistical validity does **not** compose automatically across
chained skills — see the composition demonstration and the paper's scope
section. Live-workload validation (gold-set audits) is prescribed by the
framework and is the adopter's obligation, not something this repository
can do for you.

## License

Code: MIT (see `LICENSE`). Paper text (`paper/`): CC BY 4.0.

## Citation

See `CITATION.cff`.
