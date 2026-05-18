"""
Emit the pending drafts (status == "Pending Review") as a JSON array on stdout.

Used by the n8n workflow: an Execute Command node runs this, n8n parses the
JSON, then loops one approval email per item. Keeping the parsing in Python
(not in n8n CSV nodes) makes the workflow version-stable and testable.

Output: JSON list of objects with the fields n8n needs for the approval email.
"""

import json
import sys
import pandas as pd
from pathlib import Path

# Force UTF-8 stdout so redirected output (n8n Execute Command) stays valid
# JSON on Windows instead of falling back to cp1252.
sys.stdout.reconfigure(encoding="utf-8")

ROOT       = Path(__file__).parent.parent
DRAFTS_CSV = ROOT / "output" / "response_drafts.csv"
URGENT_CSV = ROOT / "output" / "urgent_responses.csv"

FIELDS = ["reviewer_id", "rating", "date_approx", "primary_category",
          "review_text", "draft_response", "word_count", "qc_flag"]


def load(path: Path, queue: str) -> list:
    if not path.exists():
        return []
    try:
        df = pd.read_csv(path, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        return []
    if "status" not in df.columns:
        return []
    df = df[df["status"].astype(str).str.strip() == "Pending Review"]
    rows = []
    for _, r in df.iterrows():
        item = {f: ("" if pd.isna(r.get(f)) else r.get(f)) for f in FIELDS}
        item["queue"] = queue
        item["urgency_reason"] = (
            "" if pd.isna(r.get("urgency_reason", "")) else r.get("urgency_reason", "")
        )
        rows.append(item)
    return rows


def main() -> None:
    # Urgent first so the workflow can prioritize those approvals.
    items = load(URGENT_CSV, "urgent") + load(DRAFTS_CSV, "standard")
    json.dump(items, sys.stdout, ensure_ascii=False, default=str)


if __name__ == "__main__":
    main()
