from playwright.sync_api import sync_playwright
import time, sys
sys.stdout.reconfigure(encoding="utf-8")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={"width": 1280, "height": 900},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

    print("Loading Maps search URL...")
    page.goto("https://www.google.com/maps/search/Rinata+Restaurant+Minneapolis/", wait_until="domcontentloaded", timeout=30000)
    time.sleep(8)  # Wait longer

    # Print all buttons
    print("Buttons:")
    for btn in page.locator("button").all():
        try:
            label = btn.get_attribute("aria-label") or ""
            text = btn.inner_text(timeout=200).strip()[:40]
            if "overview" in label.lower() or "review" in label.lower() or "menu" in label.lower() or "about" in label.lower():
                print(f"  TAB: text='{text}' aria='{label}'")
        except: pass

    # Check for review selectors
    for sel in ["div.jftiEf", ".wiI7pd", 'div[role="feed"]']:
        print(f"  '{sel}': {page.locator(sel).count()}")

    page.screenshot(path="C:/Users/shant/projects/Rinata/scraper/debug_fresh.png")
    print("Screenshot saved.")
    time.sleep(10)
    browser.close()
