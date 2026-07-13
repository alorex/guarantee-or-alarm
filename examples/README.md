# Numerical demonstrations — one per use case ("The toolkit in action")

Validation layer (Layer 2) of the article's V&V framework, executed. Each
script is dependency-free (Python ≥ 3.9 standard library only), uses a fixed
seed (2026), simulates a dataset with **known ground truth**, and runs the
naive and the V&V-informed analysis side by side. Each runs in seconds to
~1 minute on a laptop:

```
python ex1_conformal_gate.py    # calibrated LLM-verifier gate (conformal-uq), incl. drift perturbation
python ex1b_gate_monitor.py     # the gate's companion drift alarm (conformal-uq + anytime-valid)
python ex2_anytime_valid.py     # dashboard peeking (anytime-valid)
python ex3_ppi.py               # measurement with model labels (prediction-powered-inference)
python ex4_boed.py              # experiment design by EIG (bayesian-optimal-design)
python ex5_rare_event.py        # tail probability by IS (rare-event-is)
python ex5b_nested_risk.py      # nested-simulation bias (risk-measure-estimation)
python ex6_selective.py         # winner's curse + BH (selective-inference)
python ex7_causal_ml.py         # confounding, DML, policy value (causal-ml)
python ex8_queue_output.py      # M/M/1 output analysis (simulation-output-analysis)
python ex9_hierarchy.py         # cascade economics (model-hierarchy)
python ex10_composition.py      # three-skill chain: PPI + anytime-valid monitor under labeler drift
python run_all.py --check       # run everything, verify against expected_results.txt
```

`ex7` includes a hidden-confounder perturbation (identification failure);
`ex1` includes a post-calibration drift perturbation whose alarm `ex1b`
ships.

Output lines starting with `RESULT` are the numbers quoted in the article
(Table "Numerical demonstrations" and the toolkit vignettes).
