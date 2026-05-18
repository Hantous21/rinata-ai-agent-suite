"""
Record an owner's approve/reject decision for one review.

Called by the n8n workflow after the human clicks Approve or Reject. Looks up
the full draft row, appends it (plus decision + timestamp) to the right ledger,
and marks it in the live draft queues so it drops out of the next digest.

Usage:
    python responder/record_decision.py --reviewer-id Reviewer_042 --decision approved
    python responder/record_decision.py --reviewer-id Reviewer_042 --decision rejected --reason "tone too formal"

Exit 0 on success, 1 if the reviewer_id isn't found in the pending queues.
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

ROOT         = Path(__file__).parent.parent
DRAFTS_CSV   = ROOT / "output" / "response_drafts.csv"
URGENT_CSV   = ROOT / "output" / "urgent_responses.csv"
APPROVED_CSV = ROOT / "output" / "approved_responses.csv"
REJECTED_CSV = ROOT / "output" / "rejected_responses.csv"


def read(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def append(path: Path, row: dict) -> None:
    df = read(path)
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reviewer-id", required=True)
    ap.add_argument("--decision", required=True, choices=["approved", "rejected"])
    ap.add_argument("--reason", default="")
    args = ap.parse_args()

    rid = str(args.reviewer_id).strip()
    found = None
    for path in (URGENT_CSV, DRAFTS_CSV):
        df = read(path)
        if df.empty or "reviewer_id" not in df.columns:
            continue
        match = df[df["reviewer_id"].astype(str) == rid]
        if not match.empty:
            found = match.iloc[0].to_dict()
            # Mark it decided in the live queue so it leaves the next digest.
            df.loc[df["reviewer_id"].astype(str) == rid, "status"] = args.decision.capitalize()
            df.to_csv(path, index=False, encoding="utf-8-sig")
            break

    if found is None:
        print(f"ERROR: {rid} not found in pending queues.", file=sys.stderr)
        sys.exit(1)

    found["decision"]    = args.decision
    found["decision_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    found["reason"]      = args.reason
    target = APPROVED_CSV if args.decision == "approved" else REJECTED_CSV
    append(target, found)

    print(f"{rid} -> {args.decision} (recorded in {target.name})")
    sys.exit(0)


if __name__ == "__main__":
    main()
