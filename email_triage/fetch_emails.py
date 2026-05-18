"""
Build 6 / Stage 1 — Gmail Fetcher

Pulls supplier emails from the restaurant Gmail account and saves them as
output/raw_emails.json for the categorizer to process.

What it fetches:
  - Emails from known supplier domains (suppliers.json)
  - Emails matching common supplier subject keywords (suppliers.json)
  - Date window: last N days (default 30, set fetch_days in suppliers.json)

Deduplication: emails already in raw_emails.json are skipped (by message ID),
so re-running only fetches new messages.

Usage:
    python email_triage/fetch_emails.py
    python email_triage/fetch_emails.py --days 7    # last 7 days only
"""

import sys
import json
import base64
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from email import message_from_bytes

sys.path.insert(0, str(Path(__file__).parent))
from gmail_auth import get_gmail_service

ROOT         = Path(__file__).parent.parent
SUPPLIERS    = ROOT / "email_triage" / "suppliers.json"
RAW_OUT      = ROOT / "output" / "raw_emails.json"

MAX_BODY_CHARS = 3000   # trim very long bodies before passing to Claude


def load_config() -> dict:
    return json.loads(SUPPLIERS.read_text(encoding="utf-8"))


def build_queries(config: dict, days: int) -> list[str]:
    """Build Gmail search queries covering known suppliers + keyword subjects."""
    after = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y/%m/%d")
    queries = []

    # One query per supplier domain
    for supplier in config.get("suppliers", []):
        for domain in supplier.get("domains", []):
            queries.append(f"from:@{domain} after:{after}")

    # One query per keyword subject
    for kw in config.get("keyword_subjects", []):
        queries.append(f'subject:"{kw}" after:{after}')

    return queries


def extract_body(payload: dict) -> str:
    """Recursively extract plain-text body from a Gmail message payload."""
    mime = payload.get("mimeType", "")

    if mime == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

    if mime.startswith("multipart/"):
        for part in payload.get("parts", []):
            text = extract_body(part)
            if text:
                return text

    return ""


def clean_body(raw: str) -> str:
    """Strip excessive whitespace and trim to MAX_BODY_CHARS."""
    cleaned = re.sub(r"\n{3,}", "\n\n", raw.strip())
    if len(cleaned) > MAX_BODY_CHARS:
        cleaned = cleaned[:MAX_BODY_CHARS] + "\n\n[... body truncated ...]"
    return cleaned


def get_header(headers: list, name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def fetch_message(service, msg_id: str) -> dict | None:
    """Fetch full message and extract fields we care about."""
    try:
        msg = service.users().messages().get(
            userId="me", id=msg_id, format="full"
        ).execute()
    except Exception as e:
        print(f"  Warning: could not fetch message {msg_id}: {e}", flush=True)
        return None

    headers  = msg.get("payload", {}).get("headers", [])
    sender   = get_header(headers, "From")
    subject  = get_header(headers, "Subject")
    date_raw = get_header(headers, "Date")
    body     = clean_body(extract_body(msg.get("payload", {})))

    # Friendly date — just keep YYYY-MM-DD
    date_str = date_raw[:16].strip() if date_raw else ""

    return {
        "message_id":  msg_id,
        "thread_id":   msg.get("threadId", ""),
        "sender":      sender,
        "subject":     subject,
        "date":        date_str,
        "body":        body,
        "snippet":     msg.get("snippet", ""),
        "label_ids":   msg.get("labelIds", []),
    }


def search_messages(service, query: str) -> list[str]:
    """Return all message IDs matching a Gmail search query."""
    ids   = []
    token = None
    while True:
        kwargs = {"userId": "me", "q": query, "maxResults": 100}
        if token:
            kwargs["pageToken"] = token
        resp  = service.users().messages().list(**kwargs).execute()
        msgs  = resp.get("messages", [])
        ids  += [m["id"] for m in msgs]
        token = resp.get("nextPageToken")
        if not token:
            break
    return ids


def main():
    # ── Parse args ────────────────────────────────────────────────────────────
    days = 30
    for arg in sys.argv[1:]:
        if arg.startswith("--days="):
            days = int(arg.split("=")[1])
        elif arg == "--days" and sys.argv.index(arg) + 1 < len(sys.argv):
            days = int(sys.argv[sys.argv.index(arg) + 1])

    config  = load_config()
    days    = days or config.get("fetch_days", 30)
    queries = build_queries(config, days)

    print("=== Rinata Email Fetcher ===\n", flush=True)
    print(f"Date window:  last {days} days", flush=True)
    print(f"Queries:      {len(queries)}", flush=True)

    # ── Load already-fetched IDs ───────────────────────────────────────────────
    existing: list[dict] = []
    if RAW_OUT.exists():
        try:
            existing = json.loads(RAW_OUT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = []
    existing_ids = {e["message_id"] for e in existing}
    print(f"Already saved: {len(existing_ids)} messages\n", flush=True)

    # ── Search & deduplicate ──────────────────────────────────────────────────
    service    = get_gmail_service()
    all_ids: set[str] = set()

    for i, q in enumerate(queries, 1):
        found = search_messages(service, q)
        new   = [mid for mid in found if mid not in existing_ids]
        all_ids.update(new)
        print(f"  [{i:>2}/{len(queries)}] {q[:60]:<60} → {len(found)} found, "
              f"{len(new)} new", flush=True)

    new_ids = list(all_ids - existing_ids)
    print(f"\nNew messages to fetch: {len(new_ids)}", flush=True)

    if not new_ids:
        print("Nothing new to fetch. output/raw_emails.json is up to date.", flush=True)
        return

    # ── Fetch full messages ────────────────────────────────────────────────────
    fetched = []
    for i, mid in enumerate(new_ids, 1):
        msg = fetch_message(service, mid)
        if msg:
            fetched.append(msg)
        if i % 20 == 0:
            print(f"  Fetched {i}/{len(new_ids)}...", flush=True)

    # ── Save ──────────────────────────────────────────────────────────────────
    all_emails = existing + fetched
    RAW_OUT.parent.mkdir(exist_ok=True)
    RAW_OUT.write_text(json.dumps(all_emails, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n✓ Saved {len(all_emails)} total emails → {RAW_OUT.name}", flush=True)
    print(f"  ({len(fetched)} newly fetched)", flush=True)


if __name__ == "__main__":
    main()
