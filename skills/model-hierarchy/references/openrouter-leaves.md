# OpenRouter Free-Tier Leaves — External Leaf Binding

Binds the hierarchy's tier-0 (leaf) role to OpenRouter's `:free` model pool via the
OpenAI-compatible endpoint, dispatched by `scripts/leaf_dispatch.py`. This is a
*leaf-only* binding: mid-tier verification and root arbitration stay in the Claude
ecosystem. Rationale: free-tier leaves have exactly the profile MLMC wants at
$\ell = 0$ — near-zero $C_0$, high and heterogeneous $V_0$ — and the heterogeneity
is a feature: cross-family replication buys the error decorrelation that same-family
best-of-$n$ cannot (SKILL.md, "Correlated errors").

## Contents
1. Endpoint & auth
2. Rate/quota model (and why the dispatcher throttles at 18 rpm)
3. Roster configuration & family taxonomy
4. Data governance — `data_class` (normative)
5. Batching & replication semantics
6. Logging & quota state (loop-harness bindings)
7. Failure taxonomy & rotation policy
8. Maintenance: refreshing the roster

## 1. Endpoint & auth

- Endpoint: `POST https://openrouter.ai/api/v1/chat/completions` (OpenAI schema:
  `model`, `messages`, `max_tokens`, `temperature`; response carries `usage` with
  prompt/completion token counts).
- Auth: `Authorization: Bearer $OPENROUTER_API_KEY`. The dispatcher reads the key
  **only** from a `.env` file (`OPENROUTER_API_KEY=...`), never from a card, never
  from CLI args (keys in argv leak into shell history and process tables). The
  `.env` path defaults to `./.env`, overridable with `--env`.
- Optional headers `HTTP-Referer` / `X-Title` identify the app; harmless, set from
  config if present.

## 2. Rate/quota model

OpenRouter free-tier limits (as configured; **verify against current docs before a
large run — these move**):

| Limit | Value | Dispatcher control |
|---|---|---|
| Requests/min on `:free` models | 20 | token-bucket throttle at **18 rpm** (10% headroom; a single clock-skewed retry must not 429 the whole run) |
| Requests/day, credit balance < $10 | 50 | `daily_cap: 50` (default) |
| Requests/day, lifetime credits ≥ $10 | 1000 | `daily_cap: 1000` (set explicitly) |

The daily cap is the binding constraint, which is why the dispatcher runs a
**preflight**: it computes the worst-case call count of the requested fan-out,
`ceil(n_cards / K) × m × retry_headroom` (headroom default 1.25), checks it against
`daily_cap − used_today` from the quota state file, and **refuses to start** (exit 2)
if the fan-out cannot finish. A half-completed fan-out is worse than none: the
telescoping sum in SKILL.md assumes complete level-0 coverage; partial coverage
silently converts a variance problem into a bias problem (missing strata).

## 3. Roster configuration & family taxonomy

`--config dispatch.json`:

```json
{
  "roster": [
    {"model": "meta-llama/llama-3.3-70b-instruct:free", "family": "llama"},
    {"model": "google/gemini-2.0-flash-exp:free",        "family": "gemini"},
    {"model": "deepseek/deepseek-chat:free",             "family": "deepseek"},
    {"model": "qwen/qwen-2.5-72b-instruct:free",         "family": "qwen"},
    {"model": "mistralai/mistral-7b-instruct:free",      "family": "mistral"}
  ],
  "rpm": 18,
  "daily_cap": 50,
  "retry_headroom": 1.25,
  "batch_k": 1,
  "replication_m": 1,
  "max_tokens": 1024,
  "temperature": 0.7,
  "quota_file": ".harness/openrouter-quota.json",
  "log_file": ".harness/leaf-dispatch-log.jsonl"
}
```

- `family` defaults to the provider prefix (text before `/`) but should be set
  explicitly: provider prefix ≠ training lineage (e.g. multiple hosts serving Llama
  derivatives are one family for decorrelation purposes).
- Roster order is the fallback rotation order (§7).
- The example models above are illustrative and **will go stale**; see §8.

## 4. Data governance — `data_class` (NORMATIVE)

Free-tier OpenRouter routes may be served by providers that **log and/or train on
prompts**. Treat every byte sent to a `:free` model as disclosed to a third party.
Hence the `data_class` field on every subtask card (`references/tier-contracts.md`):

| `data_class` | Dispatched? | Meaning |
|---|---|---|
| `public` | yes | already-public material (published papers, public web) |
| `synthetic` | yes | generated data with no real-record lineage |
| `internal` | only with `--allow-internal` | non-public but non-sensitive; requires a deliberate, logged decision |
| `proprietary` | **never — hard refusal, no override flag exists** | trade-secret, personnel, assessment-item, or otherwise controlled content |
| *(missing/unknown)* | **never** | fail-closed: unclassified data is not public by silence |

Refusal semantics: any `proprietary` or unclassified card aborts the entire run
(exit 2, zero HTTP calls issued) unless `--skip-refused` is passed, in which case
the clean subset dispatches and every refusal is written to the append-only log
with `event: "refused"`. There is deliberately no `--allow-proprietary`: an
invariant with an override flag is a suggestion (loop-harness enforcement
hierarchy — this one lives at the script level precisely so it cannot be argued
with mid-run).

## 5. Batching & replication semantics

- **Batching (`batch_k`)**: K cards are packed into one call as delimited sections;
  the model is instructed to return a JSON array of `{card_id, output}`. The
  dispatcher parses, splits, and runs each card's `deterministic_checks`
  individually — batching changes the transport, never the acceptance unit. A batch
  whose response is unparseable or missing card_ids fails *all* its cards (attempt
  consumed; escalation predicates in `tier-contracts.md` apply per card). Batch only
  when the card text is long relative to the work (allocation.md caveat 3);
  batching correlates in-batch errors, so never place two replicates of the same
  card in one batch — the dispatcher enforces this.
- **Replication (`replication_m`)**: best-of-$m$ per card, assigned round-robin
  across **distinct families** first, recycling families only when $m$ exceeds the
  family count. This is Mixture-of-Agents-style provider diversity as variance
  reduction with reduced error correlation; the mid-tier verifier (not the
  dispatcher) adjudicates among the $m$ candidates — the dispatcher reports
  per-replicate deterministic-check results and stops there (generator/verifier
  separation, loop-harness §2).

## 6. Logging & quota state (loop-harness bindings)

- **Log** (`log_file`, JSONL, append-only — one JSON object per line, verified by
  `loop-harness/scripts/check_log_append.py`): every call and every refusal:
  `{ts, event, card_id, batch_id, model, family, attempt, http_status,
  prompt_tokens, completion_tokens, latency_ms, det_check: "pass"|"fail"|"n/a",
  detail}`. Events: `call`, `refused`, `preflight_refusal`, `rotation`, `quota_stop`.
- **Quota state** (`quota_file`, JSON): `{date: "YYYY-MM-DD", used: n,
  daily_cap: c}`; reset when the date rolls (UTC). Updated after every issued
  request, including 429s (a 429'd request still consumed a request). Validates
  against a fixed schema on every read — malformed quota state is a hard stop, not
  a reset to zero (loop-harness §3: silent state rot fails loudly).

## 7. Failure taxonomy & rotation policy

| Signal | Action |
|---|---|
| HTTP 429 | put model on cooldown (honor `Retry-After` if present, else exponential: 30 s × 2^strikes), **rotate** to next roster model of a *different family* when the card's diversity budget allows, same family otherwise; log `rotation`. Each unit carries a 429 budget (`max_429_per_unit`, default 4); on exhaustion the unit fails to the escalation path rather than draining the daily quota — run-level burn is bounded by units × budget |
| HTTP 5xx | one immediate retry on the next roster model; second 5xx → card fails attempt 1, per-card escalation predicates take over |
| HTTP 401/403 | abort run — credential problem, not a card problem |
| Timeout | treat as 5xx |
| Parse failure (batch or single) | deterministic-check `fail`, attempt consumed |
| All roster models on cooldown | sleep until earliest cooldown expiry; if projected finish would breach the rpm-window or daily cap → `quota_stop`, exit 2 with partial-completion report |

Rotation never retries a card more than twice at tier 0 (tier-contracts predicate 2:
repeated identical failure is structure, not noise — escalate).

## 8. Maintenance: refreshing the roster

The `:free` pool churns weekly. Before any run larger than a pilot:
`GET https://openrouter.ai/api/v1/models`, filter `pricing.prompt == "0"` and
`pricing.completion == "0"`, intersect with the configured roster, and drop or
replace stale entries. Keep ≥ 3 families in the roster; below that, best-of-$m$
family diversity degenerates and the correlated-error discount (allocation.md,
in-flight adaptation) should be applied to agreement statistics.
