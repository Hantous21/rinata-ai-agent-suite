"""
Build 6 / Stage 3 — Triage Workbook Builder

Reads output/email_categories.csv and builds output/Rinata_Email_Triage.xlsx
with four sheets:

  Sheet 1 — All Emails      (full list, colour-coded by urgency)
  Sheet 2 — Urgent Queue    (high urgency: price changes, disputes, past-due)
  Sheet 3 — Invoices        (all invoice emails for payment tracking)
  Sheet 4 — Price Changes   (price change notices, sorted newest first)

Usage:
    python email_triage/build_triage_sheet.py
"""

import sys
import pandas as pd
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ROOT       = Path(__file__).parent.parent
CATS_CSV   = ROOT / "output" / "email_categories.csv"
WORKBOOK   = ROOT / "output" / "Rinata_Email_Triage.xlsx"

# ── Colours ────────────────────────────────────────────────────────────────────
RED    = PatternFill("solid", fgColor="FFD6D6")   # high urgency
AMBER  = PatternFill("solid", fgColor="FFF3CD")   # medium urgency
GREEN  = PatternFill("solid", fgColor="D6F0D6")   # low urgency
HEADER = PatternFill("solid", fgColor="2C3E50")   # dark header
WHITE  = PatternFill("solid", fgColor="FFFFFF")

URGENCY_FILL = {"high": RED, "medium": AMBER, "low": GREEN}

HEADER_FONT  = Font(bold=True, color="FFFFFF", size=10)
BODY_FONT    = Font(size=10)
THIN         = Side(style="thin", color="D0D0D0")
BORDER       = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP         = Alignment(wrap_text=True, vertical="top")
CENTER       = Alignment(horizontal="center", vertical="top")

# ── Column definitions ─────────────────────────────────────────────────────────
ALL_COLS = [
    ("Date",          "date",          12, False),
    ("Supplier",      "supplier_name", 18, False),
    ("Subject",       "subject",       35, False),
    ("Category",      "category",      14, True),
    ("Urgency",       "urgency",        9, True),
    ("Summary",       "summary",       45, True),
    ("Action Needed", "action_needed", 40, True),
    ("Key Facts",     "key_facts",     40, True),
    ("Sender",        "sender",        30, False),
]


def thin_border():
    return Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def write_sheet(ws, df: pd.DataFrame, cols: list, title: str) -> None:
    """Write a formatted sheet from a DataFrame."""
    ws.title = title

    # Header row
    for col_idx, (label, _, width, _) in enumerate(cols, 1):
        cell = ws.cell(row=1, column=col_idx, value=label)
        cell.fill   = HEADER
        cell.font   = HEADER_FONT
        cell.border = thin_border()
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    ws.row_dimensions[1].height = 20
    ws.freeze_panes = "A2"

    # Data rows
    for row_idx, (_, row) in enumerate(df.iterrows(), 2):
        urgency = str(row.get("urgency", "low")).strip().lower()
        fill    = URGENCY_FILL.get(urgency, WHITE)

        for col_idx, (_, field, _, wrap) in enumerate(cols, 1):
            val  = row.get(field, "")
            cell = ws.cell(row=row_idx, column=col_idx, value=str(val) if pd.notna(val) else "")
            cell.fill      = fill
            cell.font      = BODY_FONT
            cell.border    = thin_border()
            cell.alignment = WRAP if wrap else Alignment(vertical="top")

        ws.row_dimensions[row_idx].height = 45

    # Auto-filter
    ws.auto_filter.ref = ws.dimensions


def main():
    print("=== Rinata Email Triage Workbook ===\n", flush=True)

    if not CATS_CSV.exists():
        print(f"ERROR: {CATS_CSV} not found. Run categorize_emails.py first.", flush=True)
        sys.exit(1)

    df = pd.read_csv(CATS_CSV, encoding="utf-8-sig")
    if df.empty:
        print("No categorized emails found.", flush=True)
        sys.exit(0)

    # Sort: urgent first, then by date desc
    urgency_order = {"high": 0, "medium": 1, "low": 2}
    df["_urgency_sort"] = df["urgency"].map(urgency_order).fillna(3)
    df = df.sort_values(["_urgency_sort", "date"], ascending=[True, False])
    df = df.drop(columns=["_urgency_sort"])

    wb = Workbook()
    wb.remove(wb.active)    # remove default blank sheet

    # Sheet 1 — All Emails
    write_sheet(wb.create_sheet(), df, ALL_COLS, "All Emails")
    print(f"  Sheet 1: All Emails ({len(df)} rows)", flush=True)

    # Sheet 2 — Urgent Queue
    urgent = df[df["urgency"] == "high"]
    write_sheet(wb.create_sheet(), urgent, ALL_COLS, "Urgent Queue")
    print(f"  Sheet 2: Urgent Queue ({len(urgent)} rows)", flush=True)

    # Sheet 3 — Invoices
    invoices = df[df["category"] == "invoice"]
    write_sheet(wb.create_sheet(), invoices, ALL_COLS, "Invoices")
    print(f"  Sheet 3: Invoices ({len(invoices)} rows)", flush=True)

    # Sheet 4 — Price Changes
    price_changes = df[df["category"] == "price_change"]
    write_sheet(wb.create_sheet(), price_changes, ALL_COLS, "Price Changes")
    print(f"  Sheet 4: Price Changes ({len(price_changes)} rows)", flush=True)

    wb.save(WORKBOOK)
    print(f"\n✓ Saved → {WORKBOOK}", flush=True)


if __name__ == "__main__":
    main()
