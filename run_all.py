"""
Rinata Pipeline Orchestrator

Runs the full Build 1 + Build 2 pipeline in the correct order, with sanity
checks between steps, so it can be triggered unattended (e.g. by n8n).

Run order (this order matters — see note on build_excel below):
    [scrape] -> clean_data -> categorize -> build_excel
             -> generate_responses -> build_response_sheets

IMPORTANT: build_excel.py rebuilds the workbook from scratch, so it MUST run
before build_response_sheets.py. This orchestrator enforces that order — do
not run build_excel.py again afterward or sheets 5 & 6 are wiped.

Usage:
    python run_all.py                 # clean -> ... -> response sheets
    python run_all.py --with-scrape   # also run the (fragile) Google scraper first

Exit codes:
    0  = success
    1  = a step failed or a sanity check failed (n8n should alert on this)

The scraper is the brittle, ToS-risky link. It is OFF by default and, when on,
is guarded: if it produces too few reviews the whole run aborts with exit 1
rather than overwriting good data with garbage.
"""

import sys
import subprocess
from pathlib import Path

ROOT   = Path(__file__).parent
OUTPUT = ROOT / "output"
PY     = sys.executable

MIN_RAW_REVIEWS   = 20    # abort if the scraper returns fewer than this
MIN_CLEAN_REVIEWS = 20    # abort if cleaning yields fewer than this


def run_step(label: str, script: Path) -> None:
    print("\n" + "=" * 64, flush=True)
    print(f">> {label}", flush=True)
    print("=" * 64, flush=True)
    result = subprocess.run([PY, str(script)], cwd=str(ROOT))
    if result.returncode != 0:
        fail(f"Step failed: {label} (exit {result.returncode})")


def csv_rows(path: Path) -> int:
    if not path.exists():
        return -1
    # Count data rows (minus header), tolerant of encoding.
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        return max(sum(1 for _ in fh) - 1, 0)


def sanity(label: str, path: Path, minimum: int) -> None:
    n = csv_rows(path)
    if n < minimum:
        fail(f"Sanity check failed after {label}: {path.name} has {n} rows "
             f"(expected >= {minimum}). Aborting before bad data propagates.")
    print(f"   sanity ok: {path.name} = {n} rows", flush=True)


def fail(msg: str) -> None:
    print("\n" + "!" * 64, flush=True)
    print(f"PIPELINE ABORTED: {msg}", flush=True)
    print("!" * 64, flush=True)
    sys.exit(1)


def main() -> None:
    with_scrape = "--with-scrape" in sys.argv
    print("=== Rinata Pipeline Orchestrator ===", flush=True)
    print(f"Scraper: {'ON' if with_scrape else 'OFF (using existing raw_reviews.csv)'}",
          flush=True)

    if with_scrape:
        run_step("Scrape Google reviews", ROOT / "scraper" / "scrape_reviews.py")
        sanity("scrape", OUTPUT / "raw_reviews.csv", MIN_RAW_REVIEWS)
    elif not (OUTPUT / "raw_reviews.csv").exists():
        fail("raw_reviews.csv not found and --with-scrape not set. "
             "Nothing to process.")

    run_step("Clean data", ROOT / "categorizer" / "clean_data.py")
    sanity("clean", OUTPUT / "clean_reviews.csv", MIN_CLEAN_REVIEWS)

    run_step("Categorize reviews (Claude)", ROOT / "categorizer" / "categorize.py")
    sanity("categorize", OUTPUT / "categorized_reviews.csv", 1)

    run_step("Build analysis workbook", ROOT / "categorizer" / "build_excel.py")

    run_step("Generate response drafts (Claude)",
             ROOT / "responder" / "generate_responses.py")
    sanity("generate", OUTPUT / "response_drafts.csv", 0)

    run_step("Add response sheets to workbook",
             ROOT / "responder" / "build_response_sheets.py")

    print("\n" + "=" * 64, flush=True)
    print("PIPELINE COMPLETE — all steps succeeded.", flush=True)
    print(f"  Drafts:  {OUTPUT / 'response_drafts.csv'}", flush=True)
    print(f"  Urgent:  {OUTPUT / 'urgent_responses.csv'}", flush=True)
    print(f"  Workbook:{OUTPUT / 'Rinata_Review_Analysis.xlsx'}", flush=True)
    print("=" * 64, flush=True)
    sys.exit(0)


if __name__ == "__main__":
    main()
