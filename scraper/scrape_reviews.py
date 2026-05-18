from playwright.sync_api import sync_playwright
from pathlib import Path
from datetime import datetime, timedelta
import csv
import time
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).parent.parent
OUTPUT_FILE = BASE_DIR / "output" / "raw_reviews.csv"
CHROME_PROFILE = Path("C:/Users/shant/AppData/Local/Google/Chrome/User Data")

SEARCH_URL = "https://www.google.com/maps/search/Rinata+Restaurant+Minneapolis/"


def parse_relative_date(text):
    today = datetime.today()
    text = text.lower().strip()

    if not text or "just now" in text or "minute" in text or "hour" in text:
        return today

    n_match = re.search(r"(\d+)\s*(day|week|month|year)", text)
    a_match = re.search(r"\ba\s+(day|week|month|year)", text)

    if n_match:
        n, unit = int(n_match.group(1)), n_match.group(2)
    elif a_match:
        n, unit = 1, a_match.group(1)
    else:
        return today

    if unit == "day":
        return today - timedelta(days=n)
    elif unit == "week":
        return today - timedelta(weeks=n)
    elif unit == "month":
        return today - timedelta(days=n * 30)
    elif unit == "year":
        return today - timedelta(days=n * 365)
    return today


def extract_text(card, selectors, timeout=1000):
    for sel in selectors:
        try:
            el = card.locator(sel).first
            if el.count() > 0:
                t = el.inner_text(timeout=timeout).strip()
                if t:
                    return t
        except Exception:
            pass
    return ""


def extract_rating(card):
    for selector in ['span[aria-label*="star"]', 'span[role="img"][aria-label*="star"]']:
        try:
            el = card.locator(selector).first
            if el.count() > 0:
                label = el.get_attribute("aria-label") or ""
                m = re.search(r"(\d)", label)
                if m:
                    return int(m.group(1))
        except Exception:
            pass
    return 0



def wait_for_login(page):
    """Navigate to Google, pause for manual login, then confirm."""
    print("\n" + "="*60, flush=True)
    print("ACTION: Please log into Google in the browser window.", flush=True)
    print("="*60, flush=True)
    page.goto("https://accounts.google.com", wait_until="domcontentloaded", timeout=30000)
    print("\nA browser window has opened at accounts.google.com.", flush=True)
    print("Log in with your Google account, then come back here", flush=True)
    print("and press ENTER to continue...", flush=True)
    input()
    print("Continuing...\n", flush=True)


def scroll_and_load(page, panel_sel):
    last_count = 0
    stale = 0

    for attempt in range(100):
        count = page.locator("div.jftiEf").count()

        if count != last_count:
            print(f"  Reviews loaded: {count}", flush=True)
            stale = 0
            last_count = count
        else:
            stale += 1
            if stale >= 5:
                print(f"  Done scrolling — {count} reviews loaded.", flush=True)
                break

        try:
            panel = page.locator(panel_sel).first
            if panel.count() > 0:
                panel.evaluate("el => el.scrollTo(0, el.scrollHeight)")
            else:
                page.mouse.move(120, 500)
                page.mouse.wheel(0, 600)
        except Exception:
            page.mouse.wheel(0, 600)

        time.sleep(2)

    return last_count


def scrape_reviews():
    reviews = []

    with sync_playwright() as p:
        print("Launching browser...", flush=True)
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )

        try:
            page = context.new_page()
            wait_for_login(page)

            print(f"Navigating to Google Maps...", flush=True)
            page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=30000)
            time.sleep(5)

            # Print tabs to debug
            buttons = page.locator("button").all()
            tab_labels = []
            for btn in buttons:
                try:
                    label = btn.get_attribute("aria-label") or btn.inner_text(timeout=200).strip()
                    if label:
                        tab_labels.append(label[:40])
                except Exception:
                    pass
            print(f"Buttons found: {tab_labels[:15]}", flush=True)

            # Click Reviews tab — try multiple selectors
            print("Looking for Reviews tab...", flush=True)
            clicked = False
            for sel in [
                'button[aria-label*="Reviews"]',
                'button:has-text("Reviews")',
                'button.hh2c6:has-text("Reviews")',
            ]:
                try:
                    btn = page.locator(sel).first
                    if btn.count() > 0 and btn.is_visible(timeout=3000):
                        btn.click()
                        time.sleep(3)
                        clicked = True
                        print(f"  Clicked Reviews tab via: {sel}", flush=True)
                        break
                except Exception:
                    pass

            if not clicked:
                print("  Reviews tab not found — capturing screenshot for inspection.", flush=True)
                page.screenshot(path=str(BASE_DIR / "scraper/debug_logged_in.png"))

            # Sort by Newest
            try:
                sort_btn = page.locator('button[aria-label*="Sort"], button.g88MCb').first
                if sort_btn.is_visible(timeout=5000):
                    sort_btn.click()
                    time.sleep(1)
                    newest = page.locator('div[data-index="1"], li:has-text("Newest")').first
                    if newest.is_visible(timeout=3000):
                        newest.click()
                        time.sleep(2)
                        print("  Sorted by Newest.", flush=True)
            except Exception as e:
                print(f"  Sort skipped: {e}", flush=True)

            panel_sel = 'div.m6QErb[aria-label*="Reviews"], div.m6QErb.DxyBCb, div[role="feed"]'
            print("Scrolling to load all reviews...", flush=True)
            scroll_and_load(page, panel_sel)

            cards = page.locator("div.jftiEf").all()
            print(f"\nExtracting {len(cards)} reviews...", flush=True)

            for i, card in enumerate(cards):
                try:
                    rating = extract_rating(card)
                    date_raw = extract_text(card, [".rsqaWe", ".xRkPPb", ".dehysf"])
                    review_text = extract_text(card, [".wiI7pd", ".MyEned"])
                    has_response = card.locator(".CDe7pd").count() > 0
                    review_date = parse_relative_date(date_raw)

                    reviews.append({
                        "reviewer_id": f"Reviewer_{i + 1:03d}",
                        "rating": rating,
                        "date_raw": date_raw,
                        "date_approx": review_date.strftime("%Y-%m-%d"),
                        "day_of_week": review_date.strftime("%A"),
                        "review_text": review_text,
                        "has_owner_response": has_response,
                        "owner_response": "",
                    })

                    if (i + 1) % 25 == 0:
                        print(f"  Extracted {i+1}/{len(cards)}...", flush=True)

                except Exception as e:
                    print(f"  [!] Error on review {i+1}: {e}", flush=True)

        finally:
            browser.close()

    return reviews


def save_to_csv(reviews):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["reviewer_id", "rating", "date_raw", "date_approx",
                  "day_of_week", "review_text", "has_owner_response", "owner_response"]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(reviews)
    print(f"\nSaved {len(reviews)} reviews → {OUTPUT_FILE}", flush=True)


if __name__ == "__main__":
    print("=== Rinata Google Reviews Scraper ===", flush=True)
    reviews = scrape_reviews()
    if reviews:
        save_to_csv(reviews)
        print(f"\nDone! {len(reviews)} reviews collected.")
    else:
        print("\nNo reviews collected — check debug screenshots in scraper/ folder.")
