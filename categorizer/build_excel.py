"""
Stage 5 — Excel Workbook Builder
Produces Rinata_Review_Analysis.xlsx with 4 sheets:
  1. Summary Dashboard
  2. Categorized Reviews
  3. Day-of-Week Analysis
  4. Raw Data
"""

import pandas as pd
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side, GradientFill
)
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.series import DataPoint
from openpyxl.utils import get_column_letter
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.formatting.rule import ColorScaleRule
from collections import Counter

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT     = Path(__file__).parent.parent
CAT_CSV  = ROOT / "output" / "categorized_reviews.csv"
RAW_CSV  = ROOT / "output" / "raw_reviews.csv"
OUTPUT   = ROOT / "output" / "Rinata_Review_Analysis.xlsx"

# ── Load data ─────────────────────────────────────────────────────────────────
print("=== Rinata Excel Builder ===\n", flush=True)
cat  = pd.read_csv(CAT_CSV, encoding="utf-8")
raw  = pd.read_csv(RAW_CSV, encoding="utf-8")
print(f"Categorized reviews: {len(cat)}", flush=True)
print(f"Raw reviews:         {len(raw)}\n", flush=True)

# ── Style constants ───────────────────────────────────────────────────────────
NAVY        = "0F3460"
RED         = "E94560"
WHITE       = "FFFFFF"
LIGHT_GRAY  = "F5F5F5"
MID_GRAY    = "DDDDDD"
GREEN       = "2ECC71"
AMBER       = "F39C12"
ROSE        = "E74C3C"
PURPLE      = "9B59B6"
DARK_TEXT   = "1A1A2E"

def header_font(size=11, bold=True, color=WHITE):
    return Font(name="Calibri", size=size, bold=bold, color=color)

def body_font(size=10, bold=False, color=DARK_TEXT):
    return Font(name="Calibri", size=size, bold=bold, color=color)

def fill(hex_color):
    return PatternFill("solid", fgColor=hex_color)

def border(style="thin"):
    s = Side(style=style, color=MID_GRAY)
    return Border(left=s, right=s, top=s, bottom=s)

def center():
    return Alignment(horizontal="center", vertical="center", wrap_text=True)

def left():
    return Alignment(horizontal="left", vertical="center", wrap_text=True)

def style_header_row(ws, row, col_start, col_end, bg=NAVY, fg=WHITE, height=28):
    ws.row_dimensions[row].height = height
    for col in range(col_start, col_end + 1):
        cell = ws.cell(row=row, column=col)
        cell.font      = header_font(color=fg)
        cell.fill      = fill(bg)
        cell.alignment = center()
        cell.border    = border()

def style_data_row(ws, row, col_start, col_end, bg=WHITE, height=18):
    ws.row_dimensions[row].height = height
    for col in range(col_start, col_end + 1):
        cell = ws.cell(row=row, column=col)
        cell.font      = body_font()
        cell.fill      = fill(bg)
        cell.alignment = left()
        cell.border    = border()

def write_cell(ws, row, col, value, bold=False, bg=WHITE, fg=DARK_TEXT,
               align="left", size=10, wrap=True):
    cell           = ws.cell(row=row, column=col, value=value)
    cell.font      = Font(name="Calibri", size=size, bold=bold, color=fg)
    cell.fill      = fill(bg)
    cell.alignment = Alignment(
        horizontal=align, vertical="center", wrap_text=wrap
    )
    cell.border    = border()
    return cell

# ── Aggregations ──────────────────────────────────────────────────────────────
DAY_ORDER  = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
CATEGORIES = ["Food Quality","Service/Staff","Atmosphere","Wait Time",
               "Price/Value","Order Accuracy","Miscellaneous"]

cat["rating"]     = pd.to_numeric(cat["rating"], errors="coerce")
raw["rating"]     = pd.to_numeric(raw["rating"], errors="coerce")

avg_rating        = raw["rating"].mean()
total_reviews     = len(raw)
reviews_with_text = len(cat)
pct_positive      = (cat["sentiment"] == "positive").sum() / len(cat) * 100
high_urgency      = cat[cat["urgency"] == "high"]
category_counts   = cat["primary_category"].value_counts()
sentiment_counts  = cat["sentiment"].value_counts()
urgency_counts    = cat["urgency"].value_counts()

# Day-of-week from raw (all 597 reviews for rating averages)
day_avg_rating = (
    raw.groupby("day_of_week")["rating"]
    .agg(["mean","count"])
    .reindex(DAY_ORDER)
    .reset_index()
)
day_avg_rating.columns = ["day_of_week","avg_rating","review_count"]

# Day-of-week category breakdown from categorized reviews
day_cat = pd.crosstab(cat["day_of_week"], cat["primary_category"])
day_cat = day_cat.reindex(DAY_ORDER).fillna(0).astype(int)

# ─────────────────────────────────────────────────────────────────────────────
wb = Workbook()
wb.remove(wb.active)   # remove default blank sheet

# =============================================================================
# SHEET 1 — SUMMARY DASHBOARD
# =============================================================================
print("Building Sheet 1: Summary Dashboard...", flush=True)
ws1 = wb.create_sheet("Summary Dashboard")
ws1.sheet_view.showGridLines = False
ws1.column_dimensions["A"].width = 3   # left margin

# ── Title banner ─────────────────────────────────────────────────────────────
ws1.row_dimensions[1].height = 8
ws1.merge_cells("B2:K2")
ws1.row_dimensions[2].height = 50
title_cell = ws1["B2"]
title_cell.value     = "Rinata Restaurant  —  Review Intelligence Dashboard"
title_cell.font      = Font(name="Calibri", size=22, bold=True, color=WHITE)
title_cell.fill      = fill(NAVY)
title_cell.alignment = Alignment(horizontal="center", vertical="center")
for col in range(2, 12):
    ws1.cell(row=2, column=col).fill = fill(NAVY)

ws1.merge_cells("B3:K3")
sub_cell = ws1["B3"]
sub_cell.value     = f"Based on {total_reviews} Google Reviews  |  {reviews_with_text} analyzed by AI  |  May 2026"
sub_cell.font      = Font(name="Calibri", size=11, color="AAAAAA")
sub_cell.fill      = fill("16213E")
sub_cell.alignment = Alignment(horizontal="center", vertical="center")
for col in range(2, 12):
    ws1.cell(row=3, column=col).fill = fill("16213E")
ws1.row_dimensions[3].height = 22

ws1.row_dimensions[4].height = 14

# ── KPI cards (row 5-9) ──────────────────────────────────────────────────────
kpis = [
    ("Total Reviews",    str(total_reviews),   NAVY),
    ("Avg Star Rating",  f"{avg_rating:.2f} / 5.00", GREEN),
    ("Positive Reviews", f"{pct_positive:.0f}%", GREEN),
    ("High Urgency",     str(len(high_urgency)), ROSE),
    ("Top Category",     category_counts.index[0], PURPLE),
]

kpi_cols = [2, 4, 6, 8, 10]
for (label, value, color), col in zip(kpis, kpi_cols):
    ws1.merge_cells(start_row=5, start_column=col,
                    end_row=5,   end_column=col+1)
    ws1.merge_cells(start_row=6, start_column=col,
                    end_row=8,   end_column=col+1)
    ws1.merge_cells(start_row=9, start_column=col,
                    end_row=9,   end_column=col+1)

    label_cell = ws1.cell(row=5, column=col, value=label.upper())
    label_cell.font      = Font(name="Calibri", size=8, bold=True, color="888888")
    label_cell.alignment = Alignment(horizontal="center", vertical="center")

    val_cell = ws1.cell(row=6, column=col, value=value)
    val_cell.font      = Font(name="Calibri", size=18, bold=True, color=color)
    val_cell.alignment = Alignment(horizontal="center", vertical="center")
    for r in range(6, 9):
        ws1.cell(row=r, column=col).fill = fill("FAFAFA")

ws1.row_dimensions[5].height = 16
ws1.row_dimensions[6].height = 30
ws1.row_dimensions[7].height = 10
ws1.row_dimensions[8].height = 10
ws1.row_dimensions[9].height = 10
ws1.row_dimensions[10].height = 14

# ── Section: Category Breakdown (rows 11+) ───────────────────────────────────
ws1.merge_cells("B11:F11")
ws1["B11"].value     = "Reviews by Category"
ws1["B11"].font      = Font(name="Calibri", size=13, bold=True, color=NAVY)
ws1["B11"].alignment = Alignment(horizontal="left", vertical="center")
ws1.row_dimensions[11].height = 24

# Headers
for col, hdr in zip([2,3,4,5,6], ["Category","Reviews","% of Total","Sentiment (Top)","Urgency Flags"]):
    write_cell(ws1, 12, col, hdr, bold=True, bg=NAVY, fg=WHITE, align="center")
ws1.row_dimensions[12].height = 22

row = 13
for cat_name in CATEGORIES:
    count = int(category_counts.get(cat_name, 0))
    pct   = count / len(cat) * 100 if count > 0 else 0
    subset = cat[cat["primary_category"] == cat_name]
    top_sent = subset["sentiment"].value_counts().index[0] if len(subset) > 0 else "-"
    urg_flags = int((subset["urgency"].isin(["high","medium"])).sum())
    bg = LIGHT_GRAY if row % 2 == 0 else WHITE
    write_cell(ws1, row, 2, cat_name,      bg=bg, align="left")
    write_cell(ws1, row, 3, count,         bg=bg, align="center")
    write_cell(ws1, row, 4, f"{pct:.1f}%", bg=bg, align="center")
    write_cell(ws1, row, 5, top_sent,      bg=bg, align="center")
    write_cell(ws1, row, 6, urg_flags,     bg=bg, align="center")
    ws1.row_dimensions[row].height = 18
    row += 1

# ── Section: Day of Week (same sheet, right side) ────────────────────────────
ws1.merge_cells("H11:K11")
ws1["H11"].value     = "Performance by Day of Week"
ws1["H11"].font      = Font(name="Calibri", size=13, bold=True, color=NAVY)
ws1["H11"].alignment = Alignment(horizontal="left", vertical="center")

for col, hdr in zip([8,9,10,11], ["Day","Total Reviews","Avg Rating","Complaint Reviews"]):
    write_cell(ws1, 12, col, hdr, bold=True, bg=NAVY, fg=WHITE, align="center")

row2 = 13
for _, day_row in day_avg_rating.iterrows():
    day      = day_row["day_of_week"]
    count    = int(day_row["review_count"])
    avg      = round(float(day_row["avg_rating"]), 2)
    neg_count = int(cat[(cat["day_of_week"] == day) & (cat["sentiment"] == "negative")].shape[0])
    bg = LIGHT_GRAY if row2 % 2 == 0 else WHITE
    write_cell(ws1, row2, 8,  day,   bg=bg, align="left")
    write_cell(ws1, row2, 9,  count, bg=bg, align="center")
    write_cell(ws1, row2, 10, avg,   bg=bg, align="center")
    write_cell(ws1, row2, 11, neg_count, bg=bg, align="center")
    ws1.row_dimensions[row2].height = 18
    row2 += 1

# ── Section: High Urgency Reviews ────────────────────────────────────────────
last_row = max(row, row2) + 1
ws1.merge_cells(f"B{last_row}:K{last_row}")
ws1[f"B{last_row}"].value     = "High-Urgency Reviews — Read First"
ws1[f"B{last_row}"].font      = Font(name="Calibri", size=13, bold=True, color=ROSE)
ws1[f"B{last_row}"].alignment = Alignment(horizontal="left", vertical="center")
ws1.row_dimensions[last_row].height = 24
last_row += 1

for col, hdr in zip(range(2,8), ["#","Rating","Day","Category","Summary","Review Text"]):
    write_cell(ws1, last_row, col, hdr, bold=True, bg=ROSE, fg=WHITE, align="center")
ws1.row_dimensions[last_row].height = 22
last_row += 1

for i, (_, hrow) in enumerate(high_urgency.iterrows(), 1):
    bg = "FFF0F0" if i % 2 == 0 else WHITE
    write_cell(ws1, last_row, 2, i,                              bg=bg, align="center")
    write_cell(ws1, last_row, 3, int(hrow["rating"]),            bg=bg, align="center")
    write_cell(ws1, last_row, 4, hrow["day_of_week"],            bg=bg)
    write_cell(ws1, last_row, 5, hrow["primary_category"],       bg=bg)
    write_cell(ws1, last_row, 6, hrow["one_line_summary"],       bg=bg)
    write_cell(ws1, last_row, 7, hrow["review_text"][:200],      bg=bg)
    ws1.row_dimensions[last_row].height = 45
    last_row += 1

# Column widths
for col, w in zip([2,3,4,5,6,7,8,9,10,11],
                  [22,10,12,14,14,14,18,16,12,18]):
    ws1.column_dimensions[get_column_letter(col)].width = w

# =============================================================================
# SHEET 2 — CATEGORIZED REVIEWS
# =============================================================================
print("Building Sheet 2: Categorized Reviews...", flush=True)
ws2 = wb.create_sheet("Categorized Reviews")
ws2.sheet_view.showGridLines = False
ws2.freeze_panes = "A2"

headers = [
    "Reviewer", "Rating", "Date", "Day of Week", "Category",
    "Secondary Category", "Sentiment", "Urgency", "Confidence",
    "Key Facts", "Summary", "Review Text"
]
col_widths = [12, 8, 12, 14, 18, 18, 12, 10, 12, 40, 40, 60]

for col, (hdr, w) in enumerate(zip(headers, col_widths), 1):
    write_cell(ws2, 1, col, hdr, bold=True, bg=NAVY, fg=WHITE, align="center")
    ws2.column_dimensions[get_column_letter(col)].width = w
ws2.row_dimensions[1].height = 28

SENT_COLORS = {"positive": "D5F5E3", "negative": "FADBD8", "mixed": "FEF9E7"}
URG_COLORS  = {"high": "FADBD8", "medium": "FEF9E7", "low": "FDFEFE"}

for i, (_, r) in enumerate(cat.iterrows(), 2):
    sent_bg = SENT_COLORS.get(str(r["sentiment"]).lower(), WHITE)
    urg_bg  = URG_COLORS.get(str(r["urgency"]).lower(), WHITE)
    base_bg = LIGHT_GRAY if i % 2 == 0 else WHITE

    values = [
        r["reviewer_id"], int(r["rating"]) if pd.notna(r["rating"]) else "",
        str(r["date_approx"])[:10], r["day_of_week"],
        r["primary_category"], str(r["secondary_category"]),
        r["sentiment"], r["urgency"], r["confidence"],
        str(r["key_facts"]), str(r["one_line_summary"]),
        str(r["review_text"])
    ]
    bgs = [base_bg,base_bg,base_bg,base_bg,base_bg,base_bg,
           sent_bg, urg_bg, base_bg, base_bg, base_bg, base_bg]

    for col, (val, bg) in enumerate(zip(values, bgs), 1):
        write_cell(ws2, i, col, val, bg=bg)
    ws2.row_dimensions[i].height = 30

# =============================================================================
# SHEET 3 — DAY-OF-WEEK ANALYSIS
# =============================================================================
print("Building Sheet 3: Day-of-Week Analysis...", flush=True)
ws3 = wb.create_sheet("Day-of-Week Analysis")
ws3.sheet_view.showGridLines = False
ws3.freeze_panes = "A2"

# Title
ws3.merge_cells("A1:J1")
ws3["A1"].value     = "Day-of-Week Analysis — Ratings & Category Patterns"
ws3["A1"].font      = Font(name="Calibri", size=14, bold=True, color=WHITE)
ws3["A1"].fill      = fill(NAVY)
ws3["A1"].alignment = Alignment(horizontal="center", vertical="center")
ws3.row_dimensions[1].height = 32

# Part A: Ratings by day
ws3["A3"].value = "Average Rating & Volume by Day"
ws3["A3"].font  = Font(name="Calibri", size=12, bold=True, color=NAVY)
ws3.row_dimensions[3].height = 22

for col, hdr in enumerate(["Day","Total Reviews","Avg Rating","Positive","Negative","Mixed"], 1):
    write_cell(ws3, 4, col, hdr, bold=True, bg=NAVY, fg=WHITE, align="center")
ws3.row_dimensions[4].height = 22

for i, day in enumerate(DAY_ORDER, 5):
    day_cat_df = cat[cat["day_of_week"] == day]
    day_raw_df = raw[raw["day_of_week"] == day]
    total      = len(day_raw_df)
    avg        = round(float(day_raw_df["rating"].mean()), 2) if total > 0 else 0
    pos        = int((day_cat_df["sentiment"] == "positive").sum())
    neg        = int((day_cat_df["sentiment"] == "negative").sum())
    mix        = int((day_cat_df["sentiment"] == "mixed").sum())
    bg         = LIGHT_GRAY if i % 2 == 0 else WHITE
    write_cell(ws3, i, 1, day,   bg=bg, align="left")
    write_cell(ws3, i, 2, total, bg=bg, align="center")
    write_cell(ws3, i, 3, avg,   bg=bg, align="center")
    write_cell(ws3, i, 4, pos,   bg="D5F5E3", align="center")
    write_cell(ws3, i, 5, neg,   bg="FADBD8", align="center")
    write_cell(ws3, i, 6, mix,   bg="FEF9E7", align="center")
    ws3.row_dimensions[i].height = 18

# Color scale on avg rating column
ws3.conditional_formatting.add(
    f"C5:C{4+len(DAY_ORDER)}",
    ColorScaleRule(
        start_type="min", start_color="FADBD8",
        end_type="max",   end_color="D5F5E3"
    )
)

# Part B: Category heatmap by day
start_row = 5 + len(DAY_ORDER) + 2
ws3[f"A{start_row}"].value = "Complaint Category by Day (complaint volume)"
ws3[f"A{start_row}"].font  = Font(name="Calibri", size=12, bold=True, color=NAVY)
ws3.row_dimensions[start_row].height = 22
start_row += 1

cats_present = [c for c in CATEGORIES if c in day_cat.columns]
for col, hdr in enumerate(["Day"] + cats_present, 1):
    write_cell(ws3, start_row, col, hdr, bold=True, bg=NAVY, fg=WHITE, align="center")
ws3.row_dimensions[start_row].height = 22
start_row += 1

for i, day in enumerate(DAY_ORDER):
    bg = LIGHT_GRAY if i % 2 == 0 else WHITE
    write_cell(ws3, start_row + i, 1, day, bg=bg, align="left")
    for j, cat_name in enumerate(cats_present, 2):
        val = int(day_cat.loc[day, cat_name]) if day in day_cat.index and cat_name in day_cat.columns else 0
        write_cell(ws3, start_row + i, j, val, bg=bg, align="center")
    ws3.row_dimensions[start_row + i].height = 18

# Color scale on heatmap
end_heatmap = start_row + len(DAY_ORDER) - 1
last_col    = get_column_letter(1 + len(cats_present))
ws3.conditional_formatting.add(
    f"B{start_row}:{last_col}{end_heatmap}",
    ColorScaleRule(
        start_type="min", start_color="FFFFFF",
        end_type="max",   end_color=NAVY
    )
)

# Column widths
for col, w in enumerate([18,14,12,14,14,14,14,14,14,14], 1):
    ws3.column_dimensions[get_column_letter(col)].width = w

# Bar chart — avg rating by day
chart = BarChart()
chart.type    = "col"
chart.title   = "Average Rating by Day of Week"
chart.y_axis.title = "Avg Rating"
chart.x_axis.title = "Day"
chart.style   = 10
chart.height  = 10
chart.width   = 18
chart.y_axis.scaling.min = 4.0

data_ref = Reference(ws3, min_col=3, min_row=4, max_row=4+len(DAY_ORDER))
cats_ref = Reference(ws3, min_col=1, min_row=5, max_row=4+len(DAY_ORDER))
chart.add_data(data_ref, titles_from_data=True)
chart.set_categories(cats_ref)
ws3.add_chart(chart, f"H3")

# =============================================================================
# SHEET 4 — RAW DATA
# =============================================================================
print("Building Sheet 4: Raw Data...", flush=True)
ws4 = wb.create_sheet("Raw Data")
ws4.sheet_view.showGridLines = False
ws4.freeze_panes = "A2"

raw_headers = ["Reviewer","Rating","Date (Approx)","Date (Original)","Day of Week","Review Text","Owner Response"]
raw_widths   = [12, 8, 14, 18, 14, 80, 40]

for col, (hdr, w) in enumerate(zip(raw_headers, raw_widths), 1):
    write_cell(ws4, 1, col, hdr, bold=True, bg=NAVY, fg=WHITE, align="center")
    ws4.column_dimensions[get_column_letter(col)].width = w
ws4.row_dimensions[1].height = 28

for i, (_, r) in enumerate(raw.iterrows(), 2):
    bg = LIGHT_GRAY if i % 2 == 0 else WHITE
    values = [
        r["reviewer_id"],
        int(r["rating"]) if pd.notna(r["rating"]) else "",
        str(r["date_approx"])[:10],
        r["date_raw"],
        r["day_of_week"],
        str(r["review_text"]) if pd.notna(r["review_text"]) else "",
        str(r["owner_response"]) if pd.notna(r["owner_response"]) else "",
    ]
    for col, val in enumerate(values, 1):
        write_cell(ws4, i, col, val, bg=bg)
    ws4.row_dimensions[i].height = 30

# =============================================================================
# Sheet order: Dashboard first
# =============================================================================
wb._sheets = [ws1, ws2, ws3, ws4]

# ── Save ─────────────────────────────────────────────────────────────────────
wb.save(OUTPUT)
print(f"\nSaved: {OUTPUT}", flush=True)
print("Done!", flush=True)
