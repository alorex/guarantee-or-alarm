"""Run every demonstration and collect RESULT lines.

  python run_all.py           # run all, write results.txt, print summary
  python run_all.py --check   # additionally diff against expected_results.txt
                              # (exit 1 on mismatch)

Pure-stdlib, fixed seeds; output is deterministic across platforms, so the
check is an exact comparison.
"""
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
SCRIPTS = [
    "ex1_conformal_gate.py", "ex1b_gate_monitor.py", "ex2_anytime_valid.py",
    "ex3_ppi.py", "ex4_boed.py", "ex5_rare_event.py", "ex5b_nested_risk.py",
    "ex6_selective.py", "ex7_causal_ml.py", "ex8_queue_output.py",
    "ex9_hierarchy.py", "ex10_composition.py",
]


def main() -> int:
    lines = []
    for script in SCRIPTS:
        print(f"== {script}", flush=True)
        proc = subprocess.run([sys.executable, script], cwd=HERE,
                              capture_output=True, text=True, timeout=1800)
        if proc.returncode != 0:
            print(proc.stderr, file=sys.stderr)
            print(f"FAIL {script} (exit {proc.returncode})")
            return 1
        for line in proc.stdout.splitlines():
            if line.startswith("RESULT"):
                lines.append(f"{script}: {line}")
                print("  " + line)
    out = HERE / "results.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n{len(lines)} RESULT lines -> {out.name}")
    if "--check" in sys.argv:
        expected = (HERE / "expected_results.txt").read_text(encoding="utf-8")
        if expected != out.read_text(encoding="utf-8"):
            print("CHECK FAILED: results.txt differs from expected_results.txt")
            return 1
        print("CHECK PASSED: all RESULT lines match expected_results.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
