"""
Build 2 / Stage 5 — Excel Integration

Adds two sheets to the EXISTING Rinata_Review_Analysis.xlsx:
  Sheet 5 — "Response Drafts"   (standard queue)
  Sheet 6 — "Urgent Responses"  (handle first, red header, 1-star first)

IMPORTANT — run order:
  categorize  ->  build_excel  ->  generate_responses  ->  build_response_sheets

build_excel.py rebuilds the workbook from scratch (it does NOT append). If you
re-run build_excel.py after this script, sheets 5 & 6 are wiped — just re-run
this script afterward. This script is idempotent: running it repeatedly always
leaves exactly the two sheets, freshly rebuilt.
"""

import pandas as pd
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent
DRAFTS_CSV = ROOT / "output" / "response_drafts.csv"
URGENT_CSV = ROOT / "output" / "urgent_responses.csv"
WORKBOOK   = ROOT / "output" / "Rinata_Review_Analysis.xlsx"

# ── Style (matches build_excel.py palette) ────────────────────────────────────
NAVY, RED, WHITE      = "0F3460", "E94560", "FFFFFF"
LIGHT_GRAY, MID_GRAY  = "F5F5F5", "DDDDDD"
ROSE_BG, AMBER_BG     = "FADBD8", "FEF9E7"
DARK_TEXT             = "1A1A2E"

_side = Side(style="thin", color=MID_GRAY)
_border = Border(left=_side, right=_side, top=_side, bottom=_side)

def write_cell(ws, row, col, value, bold=False, bg=WHITE, fg=DARK_TEXT,
               align="left", size=10):
    cell = ws.cell(row=row, column=col, value=value)
    cell.font = Font(name="Calibri", size=size, bold=bold, color=fg)
    cell.fill = PatternFill("solid", fgColor=bg)
    cell.alignment = Alignment(horizontal=align, vertical="center", wrap_text=True)
    cell.border = _border
    return cell

def write_sheet(wb, name, df, columns, header_bg, position):
    """(Re)create a sheet from a dataframe. Idempotent: removes any existing copy."""
    if name in wb.sheetnames:
        del wb[name]
    ws = wb.create_sheet(name, index=position)
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A2"

    widths = {
        "Reviewer ID": 12, "Rating": 8, "Date": 12, "Original Review": 60,
        "Category": 16, "Draft Response": 60, "Word Count": 11,
        "QC Flag": 16, "Status": 16, "Urgency Reason": 32,
    }
    for c, header in enumerate(columns, 1):
        write_cell(ws, 1, c, header, bold=True, bg=header_bg, fg=WHITE,
                   align="center")
        ws.column_dimensions[get_column_letter(c)].width = widths.get(header, 18)
    ws.row_dimensions[1].height = 28

    for r, (_, rec) in enumerate(df.iterrows(), 2):
        base_bg = LIGHT_GRAY if r % 2 == 0 else WHITE
        for c, header in enumerate(columns, 1):
            key = COL_MAP[header]
            val = rec.get(key, "")
            cell_bg = base_bg
            if header == "Word Count" and isinstance(val, (int, float)) and val > 150:
                cell_bg = ROSE_BG          # too long — needs trimming
            if header == "QC Flag" and str(val).strip():
                cell_bg = AMBER_BG         # has a quality warning
            write_cell(ws, r, c, val, bg=cell_bg,
                       align="center" if header in ("Rating", "Word Count") else "left")
        ws.row_dimensions[r].height = 42
    return ws

# CSV column  ->  source field
COL_MAP = {
    "Reviewer ID": "reviewer_id", "Rating": "rating", "Date": "date_approx",
    "Original Review": "review_text", "Category": "primary_category",
    "Draft Response": "draft_response", "Word Count": "word_count",
    "QC Flag": "qc_flag", "Status": "status", "Urgency Reason": "urgency_reason",
}

STD_COLUMNS = ["Reviewer ID", "Rating", "Date", "Original Review", "Category",
               "Draft Response", "Word Count", "QC Flag", "Status"]
URG_COLUMNS = STD_COLUMNS + ["Urgency Reason"]

# ── Build ─────────────────────────────────────────────────────────────────────
print("=== Rinata Response Sheets Builder ===\n", flush=True)

if not WORKBOOK.exists():
    raise SystemExit(
        f"ERROR: {WORKBOOK.name} not found. Run build_excel.py first.")

drafts = pd.read_csv(DRAFTS_CSV, encoding="utf-8-sig")
urgent = pd.read_csv(URGENT_CSV, encoding="utf-8-sig") if URGENT_CSV.exists() else pd.DataFrame()
print(f"Standard drafts: {len(drafts)}", flush=True)
print(f"Urgent drafts:   {len(urgent)}\n", flush=True)

wb = load_workbook(WORKBOOK)
existing = list(wb.sheetnames)
print(f"Existing sheets: {existing}", flush=True)

write_sheet(wb, "Response Drafts", drafts, STD_COLUMNS, NAVY, position=4)

if len(urgent):
    urgent = urgent.sort_values("rating", ascending=True)
write_sheet(wb, "Urgent Responses", urgent, URG_COLUMNS, RED, position=5)

wb.save(WORKBOOK)

print(f"\nFinal sheets:    {wb.sheetnames}", flush=True)
print(f"Saved: {WORKBOOK}", flush=True)
print("Done!", flush=True)
