"""
Stage 4 — AI Categorization
Sends each review to Claude and saves structured labels to categorized_reviews.csv.
"""

import json
import time
import sys
import pandas as pd
import anthropic
from pathlib import Path
from dotenv import dotenv_values

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).parent.parent
INPUT       = ROOT / "output" / "clean_reviews.csv"
OUTPUT      = ROOT / "output" / "categorized_reviews.csv"
PROMPT_FILE = ROOT / "prompts" / "classify_prompt.txt"

# ── Config ────────────────────────────────────────────────────────────────────
MODEL       = "claude-haiku-4-5-20251001"
MAX_TOKENS  = 300          # plenty for a short JSON response
BATCH_SIZE  = 10           # reviews per batch before pausing
BATCH_PAUSE = 2            # seconds between batches (rate limit buffer)
SAVE_EVERY  = 50           # save progress to CSV every N reviews

# ── Setup ─────────────────────────────────────────────────────────────────────
env    = dotenv_values(ROOT / ".env")
client = anthropic.Anthropic(api_key=env["ANTHROPIC_API_KEY"])
system_prompt = PROMPT_FILE.read_text(encoding="utf-8")

# ── Load data ─────────────────────────────────────────────────────────────────
print("=== Rinata AI Categorizer ===\n", flush=True)
df = pd.read_csv(INPUT, encoding="utf-8")

# Only categorize reviews that have text
to_categorize = df[df["has_text"] == True].copy()
total = len(to_categorize)
print(f"Loaded {len(df)} total reviews.", flush=True)
print(f"Reviews with text to categorize: {total}\n", flush=True)

# ── Categorization function ───────────────────────────────────────────────────
def categorize_review(text: str) -> dict:
    """Send one review to Claude and return parsed JSON labels."""
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": f"Review:\n{text}"}]
    )
    raw = message.content[0].text.strip()

    # Strip markdown code fences if Claude wraps in ```json ... ```
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)


# ── Defaults for failed parses ────────────────────────────────────────────────
FALLBACK = {
    "primary_category":   "Miscellaneous",
    "secondary_category": None,
    "sentiment":          "mixed",
    "urgency":            "low",
    "confidence":         "low",
    "key_facts":          [],
    "one_line_summary":   "Could not parse AI response",
}

# ── Main loop ─────────────────────────────────────────────────────────────────
results = []
errors  = 0

for i, (idx, row) in enumerate(to_categorize.iterrows(), start=1):
    try:
        labels = categorize_review(row["review_text"])

        result = {
            "reviewer_id":        row["reviewer_id"],
            "rating":             row["rating"],
            "date_approx":        row["date_approx"],
            "day_of_week":        row["day_of_week"],
            "year_month":         row["year_month"],
            "is_positive":        row["is_positive"],
            "is_negative":        row["is_negative"],
            "review_text":        row["review_text"],
            "word_count":         row["word_count"],
            "primary_category":   labels.get("primary_category",   FALLBACK["primary_category"]),
            "secondary_category": labels.get("secondary_category", FALLBACK["secondary_category"]),
            "sentiment":          labels.get("sentiment",           FALLBACK["sentiment"]),
            "urgency":            labels.get("urgency",             FALLBACK["urgency"]),
            "confidence":         labels.get("confidence",          FALLBACK["confidence"]),
            "key_facts":          "; ".join(labels.get("key_facts", [])),
            "one_line_summary":   labels.get("one_line_summary",    FALLBACK["one_line_summary"]),
        }
        results.append(result)

        cat  = result["primary_category"]
        sent = result["sentiment"]
        conf = result["confidence"]
        print(f"  [{i:>3}/{total}] {row['rating']}* | {cat:<22} | {sent:<8} | conf: {conf}", flush=True)

    except Exception as e:
        errors += 1
        fallback_result = {
            "reviewer_id":        row["reviewer_id"],
            "rating":             row["rating"],
            "date_approx":        row["date_approx"],
            "day_of_week":        row["day_of_week"],
            "year_month":         row["year_month"],
            "is_positive":        row["is_positive"],
            "is_negative":        row["is_negative"],
            "review_text":        row["review_text"],
            "word_count":         row["word_count"],
            **FALLBACK,
            "key_facts":          "",
        }
        results.append(fallback_result)
        print(f"  [{i:>3}/{total}] ERROR: {e}", flush=True)

    # Pause between batches
    if i % BATCH_SIZE == 0:
        time.sleep(BATCH_PAUSE)

    # Incremental save every SAVE_EVERY reviews
    if i % SAVE_EVERY == 0:
        pd.DataFrame(results).to_csv(OUTPUT, index=False, encoding="utf-8")
        print(f"\n  -- Progress saved ({i}/{total} reviews) --\n", flush=True)

# ── Final save ────────────────────────────────────────────────────────────────
out_df = pd.DataFrame(results)
out_df.to_csv(OUTPUT, index=False, encoding="utf-8")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "="*55, flush=True)
print("CATEGORIZATION SUMMARY", flush=True)
print("="*55, flush=True)
print(f"  Reviews processed:  {total}", flush=True)
print(f"  Errors/fallbacks:   {errors}", flush=True)
print(f"  Output:             {OUTPUT.name}", flush=True)
print(flush=True)

print("  Category breakdown:", flush=True)
for cat, count in out_df["primary_category"].value_counts().items():
    print(f"    {cat:<26} {count:>3}", flush=True)

print(flush=True)
print("  Sentiment breakdown:", flush=True)
for sent, count in out_df["sentiment"].value_counts().items():
    print(f"    {sent:<12} {count:>3}", flush=True)

print(flush=True)
print("  Urgency breakdown:", flush=True)
for urg, count in out_df["urgency"].value_counts().items():
    print(f"    {urg:<12} {count:>3}", flush=True)

print(flush=True)
print("  Done!", flush=True)
