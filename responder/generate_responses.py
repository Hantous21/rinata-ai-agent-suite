"""
Build 2 / Stage 3-4-6 — Response Generation, Urgency Routing, Quality Checks

Reads Build 1 output, drafts an owner response for every review that lacks an
owner reply, runs deterministic urgency routing and quality checks, and writes:

  output/response_drafts.csv     — standard (non-urgent) drafts
  output/urgent_responses.csv    — high-priority drafts (handle first)

Nothing is auto-posted. Drafts are for a human to review, edit, and post.

Run order:  categorize  ->  build_excel  ->  generate_responses  ->  build_response_sheets
"""

import re
import sys
import time
import pandas as pd
import anthropic
from pathlib import Path
from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).parent))
from voice_guidelines import VOICE, render_voice_block

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT          = Path(__file__).parent.parent
CAT_CSV       = ROOT / "output" / "categorized_reviews.csv"
CLEAN_CSV     = ROOT / "output" / "clean_reviews.csv"
DRAFTS_OUT    = ROOT / "output" / "response_drafts.csv"
URGENT_OUT    = ROOT / "output" / "urgent_responses.csv"
APPROVED_CSV  = ROOT / "output" / "approved_responses.csv"
REJECTED_CSV  = ROOT / "output" / "rejected_responses.csv"
PROMPT_DIR    = ROOT / "prompts"

# ── Config ────────────────────────────────────────────────────────────────────
MODEL       = "claude-haiku-4-5-20251001"
MAX_TOKENS  = 400          # ~120 words + headroom
BATCH_SIZE  = 10           # reviews per batch before pausing
BATCH_PAUSE = 2            # seconds between batches (rate limit buffer)
SAVE_EVERY  = 50           # checkpoint to CSV every N reviews
MAX_RATING  = 3            # only draft replies for reviews <= this rating

URGENT_KEYWORDS = [
    "sick", "food poisoning", "raw", "hair", "foreign object", "roach",
    "bug", "health", "hospital", "rude", "aggressive", "unsafe",
]

OUTPUT_COLUMNS = [
    "reviewer_id", "rating", "date_approx", "sentiment", "urgency",
    "primary_category", "review_text", "key_facts", "draft_response",
    "word_count", "qc_flag", "status",
]

# Tokens that are fine to see capitalized in a draft (not a leaked staff name).
NAME_SAFE = {
    "Rinata", "Italian", "Minneapolis", "Family", "Team", "Restaurant",
    "Dear", "Guest", "Thank", "Thanks", "We", "Our", "I", "Im", "Its",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
}

# ── Setup ─────────────────────────────────────────────────────────────────────
env    = dotenv_values(ROOT / ".env")
client = anthropic.Anthropic(api_key=env["ANTHROPIC_API_KEY"])

VOICE_BLOCK = render_voice_block()

def load_system_prompt(sentiment: str) -> str:
    """Load the prompt template for a sentiment and inject the voice block."""
    fname = {
        "positive": "response_positive_v1.txt",
        "negative": "response_negative_v1.txt",
        "mixed":    "response_mixed_v1.txt",
    }.get(sentiment, "response_mixed_v1.txt")
    template = (PROMPT_DIR / fname).read_text(encoding="utf-8")
    return template.replace("[VOICE_GUIDELINES]", VOICE_BLOCK)

SYSTEM_PROMPTS = {s: load_system_prompt(s) for s in ("positive", "negative", "mixed")}

# ── Data ──────────────────────────────────────────────────────────────────────
print("=== Rinata Review Response Agent ===\n", flush=True)

cat   = pd.read_csv(CAT_CSV, encoding="utf-8")
clean = pd.read_csv(CLEAN_CSV, encoding="utf-8")

# has_owner_response lives in clean_reviews.csv, not categorized — join it in.
owner_map = clean.set_index("reviewer_id")["has_owner_response"]

def has_owner_reply(reviewer_id) -> bool:
    val = owner_map.get(reviewer_id, False)
    return str(val).strip().lower() in ("true", "1")

cat["has_owner_response"] = cat["reviewer_id"].map(has_owner_reply)
cat["rating_num"] = pd.to_numeric(cat["rating"], errors="coerce")

# Only draft replies for low-rated reviews (<= MAX_RATING). High-rated
# reviews are left alone — the owner only wants to respond to 3-star and below.
to_draft = cat[
    (~cat["has_owner_response"]) & (cat["rating_num"] <= MAX_RATING)
].copy()

# ── Idempotency ───────────────────────────────────────────────────────────────
# Don't redo work: skip reviews already approved or rejected, and preserve
# (don't rewrite) drafts that are still awaiting the owner's approval.
def ids_in(path: Path) -> set:
    if not path.exists():
        return set()
    try:
        return set(pd.read_csv(path, encoding="utf-8-sig")["reviewer_id"].astype(str))
    except (KeyError, pd.errors.EmptyDataError):
        return set()

def load_pending(path: Path) -> pd.DataFrame:
    """Existing rows still awaiting approval — kept verbatim, not regenerated."""
    if not path.exists():
        return pd.DataFrame()
    try:
        df_ = pd.read_csv(path, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        return pd.DataFrame()
    if "status" not in df_.columns:
        return pd.DataFrame()
    return df_[df_["status"].astype(str).str.strip() == "Pending Review"].copy()

handled_ids   = ids_in(APPROVED_CSV) | ids_in(REJECTED_CSV)
preserved     = pd.concat(
    [load_pending(DRAFTS_OUT), load_pending(URGENT_OUT)], ignore_index=True
)
if not preserved.empty:
    preserved = preserved.drop_duplicates(subset="reviewer_id", keep="first")
preserved_ids = set(preserved["reviewer_id"].astype(str)) if not preserved.empty else set()
skip_ids      = handled_ids | preserved_ids

to_draft = to_draft[~to_draft["reviewer_id"].astype(str).isin(skip_ids)].copy()

# Optional smoke-test cap: `python generate_responses.py 5` drafts only 5.
if len(sys.argv) > 1 and sys.argv[1].isdigit():
    to_draft = to_draft.head(int(sys.argv[1]))
    print(f"** SMOKE TEST: limited to {len(to_draft)} reviews **\n", flush=True)

total = len(to_draft)
print(f"Categorized reviews:               {len(cat)}", flush=True)
print(f"Already have an owner reply:       {int(cat['has_owner_response'].sum())}", flush=True)
print(f"Rating filter:                     <= {MAX_RATING} stars", flush=True)
print(f"Already approved/rejected (skip):  {len(handled_ids)}", flush=True)
print(f"Still pending, kept as-is:         {len(preserved_ids)}", flush=True)
print(f"NEW reviews to draft a reply for:  {total}\n", flush=True)


# ── Generation ────────────────────────────────────────────────────────────────
def build_user_message(row) -> str:
    return (
        f"Star rating: {row['rating']}/5\n\n"
        f"Review text:\n{row['review_text']}\n\n"
        f"Key facts (from analysis): {row.get('key_facts', '')}\n\n"
        f"One-line summary: {row.get('one_line_summary', '')}\n\n"
        f"Primary category: {row.get('primary_category', '')}\n\n"
        f"Write the owner response now."
    )

def generate_draft(sentiment: str, user_msg: str) -> str:
    """One Claude call. System prompt is marked cacheable (reused every call)."""
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPTS.get(sentiment, SYSTEM_PROMPTS["mixed"]),
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": user_msg}],
    )
    return message.content[0].text.strip().strip('"').strip()


# ── Quality checks (deterministic — Stage 6) ──────────────────────────────────
def qc_flags(draft: str, key_facts: str, review_text: str, word_count: int) -> str:
    flags = []
    low = draft.lower()

    # BANNED_PHRASE — any avoided phrase present
    if any(p in low for p in VOICE["avoid_phrases"]):
        flags.append("BANNED_PHRASE")

    # TOO_LONG — over the 150-word hard cap
    if word_count > 150:
        flags.append("TOO_LONG")

    # GENERIC — shares no meaningful word with the review's key facts
    fact_words = {w for w in re.findall(r"[a-z]{4,}", str(key_facts).lower())}
    draft_words = {w for w in re.findall(r"[a-z]{4,}", low)}
    stop = {"that", "this", "with", "your", "have", "thank", "back", "look",
            "forward", "again", "soon", "made", "make", "were", "será",
            "from", "very", "much", "rinata", "team", "family", "guest"}
    if fact_words and not (fact_words & draft_words) - stop:
        flags.append("GENERIC")

    # STAFF_NAME — a capitalized word that isn't in the review and isn't safe
    review_low = str(review_text).lower()
    for sentence in re.split(r"(?<=[.!?])\s+", draft):
        tokens = re.findall(r"\b[A-Z][a-zA-Z]{2,}\b", sentence)
        for j, tok in enumerate(tokens):
            if j == 0:                       # sentence-initial — ignore
                continue
            if tok in NAME_SAFE:
                continue
            if tok.lower() in review_low:    # the guest mentioned it
                continue
            flags.append("STAFF_NAME")
            break
        if "STAFF_NAME" in flags:
            break

    return "; ".join(dict.fromkeys(flags))


# ── Urgency routing (deterministic — Stage 4) ─────────────────────────────────
def urgency_reason(row) -> str:
    reasons = []
    try:
        if int(row["rating"]) in (1, 2):
            reasons.append(f"{int(row['rating'])}-star rating")
    except (ValueError, TypeError):
        pass
    if str(row.get("urgency", "")).strip().lower() == "high":
        reasons.append("urgency=high from analysis")
    text_low = str(row["review_text"]).lower()
    hits = [k for k in URGENT_KEYWORDS if k in text_low]
    if hits:
        reasons.append("keywords: " + ", ".join(hits))
    return " | ".join(reasons)


# Carry forward still-pending drafts verbatim (no new API call, no rewrite).
preserved_results = []
for _, pr in preserved.iterrows():
    reason = urgency_reason(pr)
    preserved_results.append({
        "reviewer_id":      pr["reviewer_id"],
        "rating":           pr["rating"],
        "date_approx":      str(pr.get("date_approx", ""))[:10],
        "sentiment":        pr.get("sentiment", "mixed"),
        "urgency":          pr.get("urgency", ""),
        "primary_category": pr.get("primary_category", ""),
        "review_text":      pr.get("review_text", ""),
        "key_facts":        pr.get("key_facts", ""),
        "draft_response":   pr.get("draft_response", ""),
        "word_count":       pr.get("word_count", 0),
        "qc_flag":          pr.get("qc_flag", "") if pd.notna(pr.get("qc_flag", "")) else "",
        "status":           "Pending Review",
        "_urgent":          bool(reason),
        "urgency_reason":   reason,
    })

# ── Main loop ─────────────────────────────────────────────────────────────────
results = []
errors  = 0

for i, (_, row) in enumerate(to_draft.iterrows(), start=1):
    sentiment = str(row.get("sentiment", "mixed")).strip().lower()
    if sentiment not in ("positive", "negative", "mixed"):
        sentiment = "mixed"

    user_msg = build_user_message(row)

    draft = None
    for attempt in (1, 2):                    # retry once
        try:
            draft = generate_draft(sentiment, user_msg)
            break
        except Exception as e:
            if attempt == 2:
                errors += 1
                draft = "[GENERATION FAILED — review manually]"
                print(f"  [{i:>3}/{total}] ERROR after retry: {e}", flush=True)
            else:
                time.sleep(3)

    word_count = len(draft.split())
    reason     = urgency_reason(row)
    is_urgent  = bool(reason)
    qc         = (
        "" if draft.startswith("[GENERATION FAILED")
        else qc_flags(draft, row.get("key_facts", ""), row["review_text"], word_count)
    )

    results.append({
        "reviewer_id":      row["reviewer_id"],
        "rating":           row["rating"],
        "date_approx":      str(row.get("date_approx", ""))[:10],
        "sentiment":        sentiment,
        "urgency":          row.get("urgency", ""),
        "primary_category": row.get("primary_category", ""),
        "review_text":      row["review_text"],
        "key_facts":        row.get("key_facts", ""),
        "draft_response":   draft,
        "word_count":       word_count,
        "qc_flag":          qc,
        "status":           "Pending Review",
        "_urgent":          is_urgent,
        "urgency_reason":   reason,
    })

    tag = "URGENT" if is_urgent else "ok    "
    qc_note = f" | QC: {qc}" if qc else ""
    print(f"  [{i:>3}/{total}] {row['rating']}* {sentiment:<8} {tag} "
          f"{word_count:>3}w{qc_note}", flush=True)

    if i % BATCH_SIZE == 0:
        time.sleep(BATCH_PAUSE)

    if i % SAVE_EVERY == 0:
        pd.DataFrame(preserved_results + results)[OUTPUT_COLUMNS].to_csv(
            DRAFTS_OUT, index=False, encoding="utf-8-sig")
        print(f"\n  -- Checkpoint saved ({i}/{total}) --\n", flush=True)

# ── Split & final write ───────────────────────────────────────────────────────
# Final queues = still-pending carried forward + newly generated.
all_results = preserved_results + results
df = pd.DataFrame(all_results, columns=OUTPUT_COLUMNS + ["_urgent", "urgency_reason"])

standard = df[~df["_urgent"].astype(bool)][OUTPUT_COLUMNS]
urgent   = df[df["_urgent"].astype(bool)][OUTPUT_COLUMNS + ["urgency_reason"]].copy()
if not urgent.empty:
    urgent = urgent.sort_values("rating", ascending=True)

standard.to_csv(DRAFTS_OUT, index=False, encoding="utf-8-sig")
urgent.to_csv(URGENT_OUT, index=False, encoding="utf-8-sig")

# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 55, flush=True)
print("RESPONSE GENERATION SUMMARY", flush=True)
print("=" * 55, flush=True)
print(f"  Newly generated:     {len(results)}", flush=True)
print(f"  Carried forward:     {len(preserved_results)}", flush=True)
print(f"  Total pending:       {len(df)}", flush=True)
print(f"  Standard queue:      {len(standard)}  -> {DRAFTS_OUT.name}", flush=True)
print(f"  Urgent queue:        {len(urgent)}  -> {URGENT_OUT.name}", flush=True)
print(f"  Generation errors:   {errors}", flush=True)
flagged = (df["qc_flag"] != "").sum()
print(f"  Drafts with QC flag: {flagged}", flush=True)
if flagged:
    print(flush=True)
    all_flags = "; ".join(df.loc[df["qc_flag"] != "", "qc_flag"]).split("; ")
    for f, c in pd.Series([x for x in all_flags if x]).value_counts().items():
        print(f"    {f:<14} {c:>3}", flush=True)
print("\n  Done!", flush=True)
