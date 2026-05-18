"""
Build 6 / Stage 2 — Email Categorizer (Claude)

Reads output/raw_emails.json, runs each email through Claude Haiku for
categorization, and writes:

  output/email_categories.csv   — all categorized emails
  output/urgent_emails.csv      — high-urgency subset (price changes, disputes, etc.)

Idempotency: emails already in email_categories.csv are skipped — re-running
only processes new messages.

Usage:
    python email_triage/categorize_emails.py
    python email_triage/categorize_emails.py 5    # smoke-test: only 5 emails
"""

import sys
import json
import time
import re
import pandas as pd
import anthropic
from pathlib import Path
from dotenv import dotenv_values

ROOT         = Path(__file__).parent.parent
RAW_EMAILS   = ROOT / "output" / "raw_emails.json"
CATEGORIES   = ROOT / "output" / "email_categories.csv"
URGENT_OUT   = ROOT / "output" / "urgent_emails.csv"
PROMPT_FILE  = ROOT / "prompts" / "email_triage_v1.txt"

MODEL       = "claude-haiku-4-5-20251001"
MAX_TOKENS  = 400
BATCH_SIZE  = 10
BATCH_PAUSE = 2
SAVE_EVERY  = 25

VALID_CATEGORIES = {"invoice", "delivery", "price_change", "order_confirm",
                    "promo", "dispute", "general"}
VALID_URGENCY    = {"high", "medium", "low"}

OUTPUT_COLUMNS = [
    "message_id", "thread_id", "sender", "subject", "date",
    "snippet", "category", "urgency", "summary",
    "action_needed", "key_facts", "supplier_name",
]

env    = dotenv_values(ROOT / ".env")
client = anthropic.Anthropic(api_key=env["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = PROMPT_FILE.read_text(encoding="utf-8").split("## EMAIL:")[0].strip()
USER_TEMPLATE = "## EMAIL:\nSender: {sender}\nSubject: {subject}\nDate: {date}\n\n{body}"


def ids_done(path: Path) -> set:
    if not path.exists():
        return set()
    try:
        return set(pd.read_csv(path, encoding="utf-8-sig")["message_id"].astype(str))
    except (KeyError, pd.errors.EmptyDataError):
        return set()


def parse_response(raw: str, email: dict) -> dict:
    """Parse Claude's JSON response, with fallback on bad output."""
    # Strip any markdown fences Claude might accidentally add
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw.strip())
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "category":      "general",
            "urgency":       "low",
            "summary":       "[parse error — review manually]",
            "action_needed": "Review email manually",
            "key_facts":     [],
            "supplier_name": "Unknown",
        }

    # Validate enum fields
    if data.get("category") not in VALID_CATEGORIES:
        data["category"] = "general"
    if data.get("urgency") not in VALID_URGENCY:
        data["urgency"] = "low"

    return data


def categorize(email: dict) -> dict:
    user_msg = USER_TEMPLATE.format(
        sender=email.get("sender", ""),
        subject=email.get("subject", ""),
        date=email.get("date", ""),
        body=email.get("body", email.get("snippet", "")),
    )

    for attempt in (1, 2):
        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": user_msg}],
            )
            return parse_response(resp.content[0].text, email)
        except Exception as e:
            if attempt == 2:
                print(f"  ERROR: {e}", flush=True)
                return {
                    "category":      "general",
                    "urgency":       "low",
                    "summary":       "[generation failed]",
                    "action_needed": "Review email manually",
                    "key_facts":     [],
                    "supplier_name": "Unknown",
                }
            time.sleep(3)


def main():
    print("=== Rinata Email Categorizer ===\n", flush=True)

    if not RAW_EMAILS.exists():
        print(f"ERROR: {RAW_EMAILS} not found. Run fetch_emails.py first.", flush=True)
        sys.exit(1)

    emails = json.loads(RAW_EMAILS.read_text(encoding="utf-8"))
    done   = ids_done(CATEGORIES)
    todo   = [e for e in emails if str(e["message_id"]) not in done]

    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        todo = todo[:int(sys.argv[1])]
        print(f"** SMOKE TEST: limited to {len(todo)} emails **\n", flush=True)

    print(f"Total emails in raw: {len(emails)}", flush=True)
    print(f"Already categorized: {len(done)}", flush=True)
    print(f"To categorize now:   {len(todo)}\n", flush=True)

    if not todo:
        print("Nothing to categorize. output/email_categories.csv is up to date.", flush=True)
        return

    # ── Load existing results to append to ────────────────────────────────────
    existing_rows: list[dict] = []
    if CATEGORIES.exists():
        try:
            existing_rows = pd.read_csv(CATEGORIES, encoding="utf-8-sig").to_dict("records")
        except pd.errors.EmptyDataError:
            pass

    results = []
    errors  = 0

    for i, email in enumerate(todo, 1):
        cat_data = categorize(email)
        key_facts_str = "; ".join(cat_data.get("key_facts", []))

        row = {
            "message_id":    email["message_id"],
            "thread_id":     email.get("thread_id", ""),
            "sender":        email.get("sender", ""),
            "subject":       email.get("subject", ""),
            "date":          email.get("date", ""),
            "snippet":       email.get("snippet", ""),
            "category":      cat_data["category"],
            "urgency":       cat_data["urgency"],
            "summary":       cat_data["summary"],
            "action_needed": cat_data["action_needed"],
            "key_facts":     key_facts_str,
            "supplier_name": cat_data["supplier_name"],
        }
        results.append(row)

        is_urgent = cat_data["urgency"] == "high"
        tag = "URGENT" if is_urgent else "ok    "
        print(f"  [{i:>3}/{len(todo)}] {tag} [{cat_data['category']:<14}] "
              f"{email.get('subject', '')[:55]}", flush=True)

        if "[generation failed]" in cat_data["summary"]:
            errors += 1

        if i % BATCH_SIZE == 0:
            time.sleep(BATCH_PAUSE)

        if i % SAVE_EVERY == 0:
            all_rows = existing_rows + results
            pd.DataFrame(all_rows, columns=OUTPUT_COLUMNS).to_csv(
                CATEGORIES, index=False, encoding="utf-8-sig")
            print(f"\n  -- Checkpoint ({i}/{len(todo)}) --\n", flush=True)

    # ── Final write ───────────────────────────────────────────────────────────
    all_rows = existing_rows + results
    df = pd.DataFrame(all_rows, columns=OUTPUT_COLUMNS)
    df.to_csv(CATEGORIES, index=False, encoding="utf-8-sig")

    urgent = df[df["urgency"] == "high"].sort_values(
        "category", key=lambda x: x.map({"price_change": 0, "dispute": 1}).fillna(2)
    )
    urgent.to_csv(URGENT_OUT, index=False, encoding="utf-8-sig")

    print(f"\n{'='*55}", flush=True)
    print("CATEGORIZATION SUMMARY", flush=True)
    print(f"{'='*55}", flush=True)
    print(f"  Newly categorized: {len(results)}", flush=True)
    print(f"  Total in CSV:      {len(df)}", flush=True)
    print(f"  Urgent (high):     {len(urgent)}", flush=True)
    print(f"  Errors:            {errors}", flush=True)
    print(f"\n  By category:", flush=True)
    for cat, count in df["category"].value_counts().items():
        print(f"    {cat:<16} {count}", flush=True)


if __name__ == "__main__":
    main()
