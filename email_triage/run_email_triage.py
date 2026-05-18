"""
Build 6 — Supplier Email Triage Pipeline Orchestrator

Runs all three stages in order with sanity checks between each:
    fetch_emails -> categorize_emails -> build_triage_sheet

Usage:
    python email_triage/run_email_triage.py               # standard run
    python email_triage/run_email_triage.py --days 7      # last 7 days only
    python email_triage/run_email_triage.py --skip-fetch  # categorize only (no new fetch)

Exit codes:
    0 = success
    1 = a step failed or sanity check failed
"""

import sys
import subprocess
from pathlib import Path

ROOT   = Path(__file__).parent.parent
OUTPUT = ROOT / "output"
PY     = sys.executable
TRIAGE = ROOT / "email_triage"


def run_step(label: str, args: list[str]) -> None:
    print("\n" + "=" * 64, flush=True)
    print(f">> {label}", flush=True)
    print("=" * 64, flush=True)
    result = subprocess.run([PY] + args, cwd=str(ROOT))
    if result.returncode != 0:
        fail(f"Step failed: {label} (exit {result.returncode})")


def file_exists(path: Path, label: str) -> None:
    if not path.exists():
        fail(f"Sanity check: {label} not found at {path}")
    print(f"   sanity ok: {path.name} exists", flush=True)


def fail(msg: str) -> None:
    print("\n" + "!" * 64, flush=True)
    print(f"PIPELINE ABORTED: {msg}", flush=True)
    print("!" * 64, flush=True)
    sys.exit(1)


def main():
    skip_fetch = "--skip-fetch" in sys.argv
    days_arg   = []
    for i, arg in enumerate(sys.argv):
        if arg == "--days" and i + 1 < len(sys.argv):
            days_arg = ["--days", sys.argv[i + 1]]
        elif arg.startswith("--days="):
            days_arg = [arg]

    print("=== Rinata Email Triage Orchestrator ===", flush=True)
    print(f"Fetch: {'SKIP (--skip-fetch)' if skip_fetch else 'ON'}", flush=True)

    if not skip_fetch:
        run_step("Fetch emails from Gmail",
                 [str(TRIAGE / "fetch_emails.py")] + days_arg)
        file_exists(OUTPUT / "raw_emails.json", "raw_emails.json")

    run_step("Categorize emails (Claude)",
             [str(TRIAGE / "categorize_emails.py")])
    file_exists(OUTPUT / "email_categories.csv", "email_categories.csv")

    run_step("Build triage workbook",
             [str(TRIAGE / "build_triage_sheet.py")])
    file_exists(OUTPUT / "Rinata_Email_Triage.xlsx", "Rinata_Email_Triage.xlsx")

    print("\n" + "=" * 64, flush=True)
    print("PIPELINE COMPLETE — all steps succeeded.", flush=True)
    print(f"  Categories: {OUTPUT / 'email_categories.csv'}", flush=True)
    print(f"  Urgent:     {OUTPUT / 'urgent_emails.csv'}", flush=True)
    print(f"  Workbook:   {OUTPUT / 'Rinata_Email_Triage.xlsx'}", flush=True)
    print("=" * 64, flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
