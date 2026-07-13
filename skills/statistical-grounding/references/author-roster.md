# author-roster.md — school-mining queue (SEED snapshot)
*This is the seed copy bundled with the statistical-grounding skill, frozen at
pin time for reproducibility. The live roster is project state maintained
outside this repository (skills are logic, rosters are state).*

*Consumed by the school-mining loop (SKILL.md §school-mining). One school per
session-block; verdicts via novelty-gate; wikis persist in outputs/research-<author>/.
Affiliations as of training knowledge — verify at mining time. Status column updated
after each run.*

| P | Author / school | Affiliation | Clusters to mine | Expected library impact | Status |
|---|---|---|---|---|---|
| 1 | **Youssef Marzouk** | MIT (UQ group) | Transport maps; LIS/certified dimension reduction; sequential OED; transport filtering | **MINED 2026-07-05** → measure-transport-inference (new), bayesian-optimal-design v1.1.0 (sequential OED, closes D-001 cross-school), bayesian-workflow v1.1.0 (high-dim module); filtering DEFER w/ triggers | done |
| 1 | **Emmanuel Candès** | Stanford | Conformal prediction; knockoffs; selective inference; LLM verifier gates | **MINED 2026-07-05** → conformal-uq (new, incl. calibrated verifier gates for the loop stack), selective-inference (new); 3 debates OPEN (D-C001..003) | done |
| 1 | **Michael I. Jordan** | UC Berkeley | Variational inference; probabilistic graphical models; decision-focused ML; bandits | **MINED 2026-07-05** → prediction-powered-inference (new), bayesian-workflow v1.2.0 (VI module); PGM reject-standalone (thin wedge, parked); bandits deferred to Lattimore-Szepesvári/Ramdas | done |
| 1 | **Causal-ML school: Athey–Imbens–Wager + Chernozhukov** | Stanford GSB / MIT | Causal forests, policy learning, adaptive experimentation, DML | **MINED 2026-07-05** → causal-ml (new: HTE/DML/policy/panel), study-design v1.1.0 (adaptive-experiment checklist + estimation boundary) | done |
| 1 | **Aaditya Ramdas** | CMU | Confidence sequences, e-processes, online FDR, sequential practice | **MINED 2026-07-05** → anytime-valid (new: CS + e-values + online FDR module + deployment), selective-inference v1.0.1 (boundary). P1 queue now EMPTY. | done |
| 2 | **James Heckman** | U. Chicago | Selection models, control functions, program evaluation | Workforce self-selection & range-restriction machinery; mine after causal-ML run | queued |
| 2 | **Peter Bühlmann** | ETH Zürich | Invariant causal prediction, graphical models, high-dim | Complements causal-ML run with DAG/invariance angle | queued |
| 2 | **Gerardo Rubino** | INRIA Rennes | Rare-event simulation by **splitting/RESTART**; Monte Carlo reliability; queueing/network performance; neural-based performance eval | MERGE into rare-event-is: the splitting family + an IS-vs-splitting decision table (when value-function tilts are unavailable, splitting wins) | queued |
| 2 | **Bradley Efron** | Stanford | Bootstrap refinements; **empirical Bayes**; large-scale simultaneous inference (local FDR) | Feeds statistical-grounding rules 2/5/6 directly; candidate `large-scale-inference` if the dashboard-multiplicity workload grows | queued |
| 3 | **Art Owen** | Stanford | (R)QMC; variance reduction; empirical likelihood | MERGE material for numerical-vv + model-hierarchy sampling notes; overlaps rQMC entries already in research-tempone | queued |
| 3 | **Pierre L'Ecuyer** | U. Montréal | RNG streams/testing; RQMC; simulation methodology | MERGE into numerical-vv (RNG-stream discipline for parallel loops) | queued |
| 3 | **Lattimore & Szepesvári** | DeepMind / Alberta | Bandits; off-policy evaluation; sequential decisions | Candidate `bandit-decisions` for adaptive experimentation in training analytics (grounding rule 8 consumer); pairs with learning-design adaptive policies | queued |
| — | Gelman / Vehtari | Columbia / Aalto | Bayesian workflow, PSIS-LOO | Already the backbone of bayesian-workflow — monitor for new methodology only | monitor |
| — | R. Tempone | KAUST/RWTH | MIMC, OED, control-IS, adaptivity | **MINED 2026-07-05** → bayesian-optimal-design, rare-event-is, model-hierarchy v1.2.0, numerical-vv v1.1.0 | done |

## Nomination criteria (for adding rows)
School-forming (students/collaborators propagate a coherent toolkit), method-first
(techniques transfer beyond the home domain), practitioner-reachable (papers state
algorithms, not just theorems), and gate-plausible (a cluster could plausibly score
ADOPT/MERGE against the current library — check INDEX.md first).
