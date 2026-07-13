#!/usr/bin/env python3
"""leaf_dispatch.py — dispatch subtask cards to OpenRouter :free leaf models.

Part of the model-hierarchy skill (tier-0 external leaf binding). See
references/openrouter-leaves.md for the normative documentation.

Guarantees (enforced here, at script level, per the loop-harness enforcement
hierarchy — these are not negotiable by prompt):
  G1  data_class governance: cards marked `proprietary` (or missing data_class)
      are NEVER dispatched. No override flag exists for proprietary.
  G2  Throttle: never more than `rpm` (default 18) requests in any rolling
      60-second window.
  G3  Quota preflight: refuses (exit 2) to start a fan-out whose worst-case call
      count exceeds today's remaining daily quota.
  G4  Append-only JSONL log of every call, refusal, rotation, and stop.
  G5  Best-of-m replication is spread across distinct model FAMILIES first.
  G6  Batching packs K cards per call but acceptance stays per-card; two
      replicates of the same card never share a batch.

Exit codes: 0 = completed; 2 = invariant refusal / violation (harness convention).

Usage:
  python leaf_dispatch.py --cards cards.jsonl --config dispatch.json [--env .env]
                          [--allow-internal] [--skip-refused] [--dry-run]

Cards: JSONL, one card per line, schema per references/tier-contracts.md
(JSON rendering of the YAML card; `data_class` REQUIRED).
"""

import argparse
import datetime as dt
import json
import os
import random
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
DISPATCHABLE = {"public", "synthetic"}          # always eligible
GATED = {"internal"}                            # eligible only with --allow-internal
FORBIDDEN = {"proprietary"}                     # never eligible, no override
DEFAULTS = {
    "rpm": 18,
    "daily_cap": 50,
    "retry_headroom": 1.25,
    "batch_k": 1,
    "replication_m": 1,
    "max_tokens": 1024,
    "temperature": 0.7,
    "quota_file": ".harness/openrouter-quota.json",
    "log_file": ".harness/leaf-dispatch-log.jsonl",
    "request_timeout_s": 120,
    "max_429_per_unit": 4,
}


# ----------------------------------------------------------------------------- util
def die(msg: str, code: int = 2) -> None:
    print(f"leaf_dispatch: {msg}", file=sys.stderr)
    sys.exit(code)


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def read_env_key(env_path: str) -> str:
    """Read OPENROUTER_API_KEY from a .env file. Never from argv or environment
    of record — the .env file is the single sanctioned source."""
    if not os.path.exists(env_path):
        die(f".env file not found at {env_path!r}; cannot authenticate")
    key = None
    with open(env_path, "r", encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            if k.strip() == "OPENROUTER_API_KEY":
                key = v.strip().strip('"').strip("'")
    if not key:
        die(f"OPENROUTER_API_KEY not present in {env_path!r}")
    return key


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8-sig") as fh:
        cfg = json.load(fh)
    merged = dict(DEFAULTS)
    merged.update(cfg)
    roster = merged.get("roster") or []
    if not roster:
        die("config has an empty roster")
    for entry in roster:
        entry.setdefault("family", entry["model"].split("/")[0])
    return merged


def load_cards(path: str) -> list:
    cards = []
    with open(path, "r", encoding="utf-8-sig") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                card = json.loads(line)
            except json.JSONDecodeError as e:
                die(f"cards file line {i}: invalid JSON ({e})")
            if "card_id" not in card or "task" not in card:
                die(f"cards file line {i}: card missing card_id/task")
            cards.append(card)
    if not cards:
        die("no cards to dispatch")
    return cards


# ------------------------------------------------------------------- append-only log
class AppendLog:
    """Append-only JSONL log (loop-harness §3). Opened in 'a' mode only; every
    record is one line, flushed immediately, never rewritten."""

    def __init__(self, path: str, defaults: dict = None):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._fh = open(path, "a", encoding="utf-8")
        self._defaults = defaults or {}

    def write(self, event: str, **fields) -> None:
        rec = {"ts": utcnow().isoformat(), "event": event}
        rec.update(self._defaults)
        rec.update(fields)
        self._fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._fh.flush()
        os.fsync(self._fh.fileno())

    def close(self) -> None:
        self._fh.close()


# ------------------------------------------------------------------------ quota state
class Quota:
    """Daily-quota ledger. Malformed state is a hard stop (never silently reset:
    a zeroed counter under-reports usage, the unsafe direction)."""

    def __init__(self, path: str, daily_cap: int):
        self.path = path
        self.daily_cap = daily_cap
        today = utcnow().date().isoformat()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8-sig") as fh:
                    st = json.load(fh)
                assert isinstance(st["used"], int) and st["used"] >= 0
                assert isinstance(st["date"], str)
            except Exception as e:
                die(f"quota state file {path!r} is malformed ({e}); refusing to "
                    f"guess remaining quota — repair or delete it deliberately")
            self.used = st["used"] if st["date"] == today else 0
        else:
            self.used = 0
        self.date = today
        self._persist()

    def _persist(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump({"date": self.date, "used": self.used,
                       "daily_cap": self.daily_cap}, fh)
        os.replace(tmp, self.path)

    @property
    def remaining(self) -> int:
        return self.daily_cap - self.used

    def consume(self, n: int = 1) -> None:
        self.used += n
        self._persist()


# --------------------------------------------------------------------------- throttle
class Throttle:
    """Rolling 60 s window limiter (G2)."""

    def __init__(self, rpm: int):
        self.rpm = rpm
        self.stamps: list = []

    def wait(self) -> None:
        now = time.monotonic()
        self.stamps = [t for t in self.stamps if now - t < 60.0]
        if len(self.stamps) >= self.rpm:
            sleep_for = 60.0 - (now - self.stamps[0]) + 0.05
            time.sleep(max(sleep_for, 0.0))
        self.stamps.append(time.monotonic())


# ---------------------------------------------------------------------- data_class gate
def governance_gate(cards, allow_internal, skip_refused, log):
    """G1. Returns the dispatchable subset or exits 2. Fail-closed on missing/
    unknown data_class; `proprietary` has no override path by construction."""
    clean, refused = [], []
    for c in cards:
        dc = c.get("data_class")
        if dc in DISPATCHABLE or (dc in GATED and allow_internal):
            clean.append(c)
        else:
            reason = ("proprietary — external dispatch forbidden" if dc in FORBIDDEN
                      else "internal without --allow-internal" if dc in GATED
                      else f"missing/unknown data_class {dc!r} — fail-closed")
            refused.append((c["card_id"], reason))
    for cid, reason in refused:
        log.write("refused", card_id=cid, detail=reason)
    if refused and not skip_refused:
        ids = ", ".join(cid for cid, _ in refused)
        die(f"{len(refused)} card(s) refused by data_class gate ({ids}); "
            f"nothing dispatched. Reclassify, remove, or pass --skip-refused "
            f"to dispatch only the clean subset.")
    if not clean:
        die("no dispatchable cards after data_class gate")
    return clean


# --------------------------------------------------------------- batching / replication
def plan_units(cards, batch_k, m, roster):
    """Build dispatch units honoring G5/G6.

    A unit = (replicate_index, [cards], model). Replicates of one card go to
    distinct families first; a card appears at most once per batch."""
    families = []
    for e in roster:
        if e["family"] not in families:
            families.append(e["family"])
    by_family = {f: [e for e in roster if e["family"] == f] for f in families}
    units = []
    for rep in range(m):
        fam = families[rep % len(families)]
        model = random.choice(by_family[fam])["model"]
        for i in range(0, len(cards), batch_k):
            units.append({"rep": rep, "cards": cards[i:i + batch_k],
                          "model": model, "family": fam})
    return units


def worst_case_calls(n_cards, batch_k, m, headroom) -> int:
    import math
    return math.ceil(math.ceil(n_cards / batch_k) * m * headroom)


# ------------------------------------------------------------------------ HTTP + parse
def build_prompt(cards) -> str:
    if len(cards) == 1:
        c = cards[0]
        return (f"{c['task']}\n\nInputs:\n{json.dumps(c.get('inputs', []))}\n\n"
                f"Constraints:\n{json.dumps(c.get('constraints', []))}\n\n"
                f"Respond with the output only.")
    parts = ["You will complete several independent subtasks. Respond ONLY with a "
             "JSON array of objects {\"card_id\": ..., \"output\": ...}, one per "
             "subtask, no prose outside the JSON."]
    for c in cards:
        parts.append(f"--- card_id: {c['card_id']} ---\nTask: {c['task']}\n"
                     f"Inputs: {json.dumps(c.get('inputs', []))}\n"
                     f"Constraints: {json.dumps(c.get('constraints', []))}")
    return "\n\n".join(parts)


def call_openrouter(key, model, prompt, cfg, dry_run):
    """Returns (status, body_text, usage, latency_ms)."""
    t0 = time.monotonic()
    if dry_run:
        time.sleep(0.01)
        return 200, "DRY-RUN OUTPUT", {"prompt_tokens": 0, "completion_tokens": 0}, \
            int((time.monotonic() - t0) * 1000)
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": cfg["max_tokens"],
            "temperature": cfg["temperature"],
        }).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg["request_timeout_s"]) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            text = body["choices"][0]["message"]["content"]
            usage = body.get("usage", {})
            return 200, text, usage, int((time.monotonic() - t0) * 1000)
    except urllib.error.HTTPError as e:
        retry_after = e.headers.get("Retry-After")
        return e.code, retry_after or "", {}, int((time.monotonic() - t0) * 1000)
    except Exception:
        return 599, "", {}, int((time.monotonic() - t0) * 1000)  # timeout/transport


def split_batch_output(cards, text):
    """Per-card outputs from a (possibly batched) response. Unparseable batch =
    every card fails this attempt (G6: acceptance is per-card)."""
    if len(cards) == 1:
        return {cards[0]["card_id"]: text}
    try:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned[cleaned.find("["):cleaned.rfind("]") + 1]
        arr = json.loads(cleaned)
        out = {str(o["card_id"]): o["output"] for o in arr}
        if set(out) != {str(c["card_id"]) for c in cards}:
            return None
        return out
    except Exception:
        return None


def run_det_checks(card, output, dry_run):
    """Run the card's deterministic checks (loop-harness scripts convention:
    exit 0 pass, else fail). '{output}' in a check command is substituted with
    a temp file holding the output. Returns 'pass'|'fail'|'n/a'."""
    checks = (card.get("output_contract") or {}).get("deterministic_checks") or []
    if not checks:
        return "n/a"
    if dry_run:
        return "pass"
    with tempfile.NamedTemporaryFile("w", suffix=".out", delete=False,
                                     encoding="utf-8") as tf:
        tf.write(output if isinstance(output, str) else json.dumps(output))
        opath = tf.name
    try:
        for cmd in checks:
            rc = subprocess.run(cmd.replace("{output}", opath), shell=True,
                                capture_output=True, timeout=120).returncode
            if rc != 0:
                return "fail"
        return "pass"
    finally:
        os.unlink(opath)


# -------------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--cards", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--env", default=".env")
    ap.add_argument("--allow-internal", action="store_true")
    ap.add_argument("--skip-refused", action="store_true")
    ap.add_argument("--dry-run", action="store_true",
                    help="no network; simulate 200s (for evals/pilots)")
    ap.add_argument("--out", default="leaf-returns.jsonl",
                    help="per-replicate leaf returns (JSONL)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    log = AppendLog(cfg["log_file"],
                    {"dry_run": True} if args.dry_run else None)
    cards = load_cards(args.cards)

    # G1 — governance gate runs BEFORE auth/quota: a proprietary card must be
    # refused even if everything else is misconfigured.
    cards = governance_gate(cards, args.allow_internal, args.skip_refused, log)

    key = "DRY" if args.dry_run else read_env_key(args.env)
    quota = Quota(cfg["quota_file"], cfg["daily_cap"])

    # G3 — preflight
    need = worst_case_calls(len(cards), cfg["batch_k"], cfg["replication_m"],
                            cfg["retry_headroom"])
    if need > quota.remaining:
        log.write("preflight_refusal", detail=f"need~{need}, "
                  f"remaining={quota.remaining}/{quota.daily_cap}")
        die(f"preflight: fan-out needs ~{need} calls (incl. retry headroom) but "
            f"only {quota.remaining}/{quota.daily_cap} remain today; refusing to "
            f"start an unfinishable fan-out. Shrink the fan-out or raise "
            f"daily_cap if your account tier allows.")

    units = plan_units(cards, cfg["batch_k"], cfg["replication_m"], cfg["roster"])
    throttle = Throttle(cfg["rpm"])
    cooldown: dict = {}          # model -> monotonic time when usable again
    roster_models = [e["model"] for e in cfg["roster"]]
    fam_of = {e["model"]: e["family"] for e in cfg["roster"]}
    returns = open(args.out, "a", encoding="utf-8")

    def pick_alternative(current):
        now = time.monotonic()
        # prefer a different family, then anything off cooldown
        for pool in ([m for m in roster_models if fam_of[m] != fam_of[current]],
                     roster_models):
            live = [m for m in pool if cooldown.get(m, 0) <= now]
            if live:
                return live[0]
        return None

    for u in units:
        model, attempt, done = u["model"], 0, False
        unit_429 = 0
        while not done and attempt < 2:
            attempt += 1
            if cooldown.get(model, 0) > time.monotonic():
                alt = pick_alternative(model)
                if alt is None:
                    wake = min(cooldown.values()) - time.monotonic()
                    if quota.remaining <= 0:
                        log.write("quota_stop", detail="all models cooling, quota 0")
                        die("quota exhausted mid-run; partial results in "
                            f"{args.out} — see log for completed cards")
                    time.sleep(max(wake, 0.5))
                else:
                    log.write("rotation", detail=f"{model}→{alt} (cooldown)")
                    model = alt
            if quota.remaining <= 0:
                log.write("quota_stop", detail="daily cap reached mid-run")
                die("daily cap reached mid-run; partial results preserved")
            throttle.wait()
            status, text, usage, ms = call_openrouter(key, model,
                                                      build_prompt(u["cards"]),
                                                      cfg, args.dry_run)
            quota.consume()
            if status == 200:
                per_card = split_batch_output(u["cards"], text)
                for c in u["cards"]:
                    cid = str(c["card_id"])
                    out = None if per_card is None else per_card.get(cid)
                    det = "fail" if out is None else run_det_checks(c, out,
                                                                    args.dry_run)
                    log.write("call", card_id=cid, batch_id=id(u) % 100000,
                              model=model, family=fam_of[model],
                              attempt=attempt, http_status=200,
                              prompt_tokens=usage.get("prompt_tokens"),
                              completion_tokens=usage.get("completion_tokens"),
                              latency_ms=ms, det_check=det,
                              detail="replicate %d" % u["rep"])
                    returns.write(json.dumps({
                        "card_id": cid, "rep": u["rep"], "model": model,
                        "dry_run": bool(args.dry_run),
                        "output": out, "self_check": det,
                        "confidence": "n/a (dispatcher does not self-assess)",
                    }) + "\n")
                done = True
            elif status == 429:
                unit_429 += 1
                ra = int(text) if text.strip().isdigit() else 30 * (2 ** attempt)
                cooldown[model] = time.monotonic() + ra
                log.write("call", model=model, family=fam_of[model],
                          attempt=attempt, http_status=429, latency_ms=ms,
                          det_check="n/a", detail=f"cooldown {ra}s "
                          f"(unit 429 budget {unit_429}/{cfg['max_429_per_unit']})")
                if unit_429 >= cfg["max_429_per_unit"]:
                    # Liveness guard: a saturated free tier must not drain the
                    # daily quota on one unit. Fail the unit -> escalation path.
                    log.write("unit_429_budget_exhausted",
                              detail=f"unit for cards "
                              f"{[str(c['card_id']) for c in u['cards']]} "
                              f"consumed {unit_429} rate-limited requests")
                    break
                alt = pick_alternative(model)
                if alt:
                    log.write("rotation", detail=f"{model}→{alt} (429)")
                    model = alt
                    attempt -= 1        # a 429 is not the card's failure
            else:  # 5xx / timeout / auth
                if status in (401, 403):
                    die(f"auth failure ({status}); aborting run")
                log.write("call", model=model, family=fam_of[model],
                          attempt=attempt, http_status=status, latency_ms=ms,
                          det_check="n/a", detail="transport/server error")
                alt = pick_alternative(model)
                model = alt or model
        if not done:
            for c in u["cards"]:
                log.write("call", card_id=str(c["card_id"]), model=model,
                          attempt=attempt, http_status=None, det_check="fail",
                          detail="attempts/429-budget exhausted at tier 0 — "
                                 "escalate (tier-contracts predicate 2)")
    returns.close()
    log.close()
    print(f"leaf_dispatch: done; used {quota.used}/{quota.daily_cap} today; "
          f"returns → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
