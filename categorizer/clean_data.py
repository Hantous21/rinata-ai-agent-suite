"""
Stage 3 — Data Cleaning
Loads raw_reviews.csv, cleans and validates it, outputs clean_reviews.csv.
"""

import sys
import pandas as pd
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT   = Path(__file__).parent.parent
INPUT  = ROOT / "output" / "raw_reviews.csv"
OUTPUT = ROOT / "output" / "clean_reviews.csv"

# ── Load ─────────────────────────────────────────────────────────────────────
print("=== Rinata Data Cleaner ===\n")
print(f"Loading {INPUT.name}...", flush=True)

df = pd.read_csv(INPUT, encoding="utf-8")
original_count = len(df)
print(f"  Loaded {original_count} rows.\n")

# ── Step 1: Fix data types ────────────────────────────────────────────────────
print("Step 1: Fixing data types...")
df["rating"] = pd.to_numeric(df["rating"], errors="coerce").astype("Int64")
df["has_owner_response"] = df["has_owner_response"].map(
    {"True": True, "False": False, True: True, False: False}
)
print(f"  Ratings:  {df['rating'].dtype}")
print(f"  Response: {df['has_owner_response'].dtype}")

# ── Step 2: Normalize text ────────────────────────────────────────────────────
print("\nStep 2: Normalizing review text...")
df["review_text"] = (
    df["review_text"]
    .fillna("")
    .str.strip()
    .str.replace(r"\s+", " ", regex=True)   # collapse multiple spaces/newlines
)
df["owner_response"] = (
    df["owner_response"]
    .fillna("")
    .str.strip()
    .str.replace(r"\s+", " ", regex=True)
)
print("  Text whitespace normalized.")

# ── Step 3: Flag rating-only reviews (no text) ────────────────────────────────
print("\nStep 3: Flagging rating-only reviews...")
df["has_text"] = df["review_text"].str.len() > 0
rating_only = (~df["has_text"]).sum()
print(f"  Rating-only reviews (no text): {rating_only}")
print(f"  Reviews with text:             {df['has_text'].sum()}")

# ── Step 4: Find true duplicates (same text AND rating, text must be non-empty)
print("\nStep 4: Checking for true duplicates...")
text_reviews = df[df["has_text"]].copy()
dupes = text_reviews.duplicated(subset=["review_text", "rating"], keep="first")
true_dupes = dupes.sum()
print(f"  True duplicate reviews found: {true_dupes}")
if true_dupes > 0:
    df = df.drop(df[df["has_text"] & dupes].index)
    print(f"  Removed {true_dupes} duplicates.")
else:
    print("  No true duplicates — all reviews are unique.")

# ── Step 5: Add useful derived columns ────────────────────────────────────────
print("\nStep 5: Adding derived columns...")
df["text_length"]    = df["review_text"].str.len()
df["word_count"]     = df["review_text"].str.split().str.len().fillna(0).astype(int)
df["is_positive"]    = df["rating"] >= 4
df["is_negative"]    = df["rating"] <= 2
df["is_neutral"]     = df["rating"] == 3
df["date_approx"]    = pd.to_datetime(df["date_approx"], errors="coerce")
df["year_month"]     = df["date_approx"].dt.to_period("M").astype(str)
print("  Added: text_length, word_count, is_positive, is_negative, is_neutral, year_month")

# ── Step 6: Validate no broken rows ──────────────────────────────────────────
print("\nStep 6: Validating data...")
missing_rating = df["rating"].isna().sum()
missing_date   = df["date_approx"].isna().sum()
missing_day    = df["day_of_week"].isna().sum()
print(f"  Rows with missing rating:    {missing_rating}")
print(f"  Rows with missing date:      {missing_date}")
print(f"  Rows with missing day:       {missing_day}")

# ── Step 7: Save ──────────────────────────────────────────────────────────────
print(f"\nStep 7: Saving clean data...")
df.to_csv(OUTPUT, index=False, encoding="utf-8")
print(f"  Saved {len(df)} rows -> {OUTPUT.name}")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "="*50)
print("CLEANING SUMMARY")
print("="*50)
print(f"  Original rows:        {original_count}")
print(f"  Duplicates removed:   {true_dupes}")
print(f"  Final rows:           {len(df)}")
print(f"  Reviews with text:    {df['has_text'].sum()}")
print(f"  Rating-only:          {(~df['has_text']).sum()}")
print()
print("  Rating breakdown:")
for star in sorted(df["rating"].dropna().unique()):
    count = (df["rating"] == star).sum()
    print(f"    {int(star)} star:  {count:>3} reviews")
print()
print("  Day of week breakdown:")
day_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
for day in day_order:
    count = (df["day_of_week"] == day).sum()
    print(f"    {day:<12} {count:>3}")
print()
print(f"  Output: {OUTPUT}")
print("  Done!")
