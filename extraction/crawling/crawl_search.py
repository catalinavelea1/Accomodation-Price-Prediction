
import argparse
import json
import random
import time
from datetime import datetime

from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

import config
from parsers import parse_search_page


def sleep():
    time.sleep(random.uniform(*config.DELAY_RANGE))


def dismiss_popups(page):
    for sel in ["#onetrust-accept-btn-handler", 'button[aria-label="Dismiss sign-in info."]']:
        try:
            page.locator(sel).first.click(timeout=2000)
        except Exception:
            pass
    page.keyboard.press("Escape")


def load_all_results(page, max_results: int) -> int:
    cards = page.locator('[data-testid="property-card"]')
    last, stale = -1, 0
    while True:
        count = cards.count()
        if count >= max_results:
            break
        if count == last:
            stale += 1
            if stale >= 3:
                break
        else:
            stale = 0
        last = count
        page.mouse.wheel(0, 20000)
        page.wait_for_timeout(1500)
        btn = page.get_by_role("button", name="Load more results")
        try:
            if btn.is_visible():
                btn.click()
                page.wait_for_timeout(2500)
        except Exception:
            pass
        dismiss_popups(page)
    return cards.count()


def already_done(path) -> set[tuple[str, str]]:
    done = set()
    if path.exists():
        for line in path.open(encoding="utf-8"):
            r = json.loads(line)
            done.add((r["query_city"], r["property_type"]))
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true", help="doar primul oras si primul tip")
    ap.add_argument("--headful", action="store_true", help="arata browserul")
    args = ap.parse_args()

    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = config.SEARCH_RESULTS_FILE
    done = already_done(out_path)

    cities = config.CITIES[:1] if args.test else config.CITIES
    types = dict(list(config.PROPERTY_TYPES.items())[:1]) if args.test else config.PROPERTY_TYPES
    max_res = 50 if args.test else config.MAX_RESULTS_PER_QUERY

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headful)
        ctx = browser.new_context(user_agent=config.USER_AGENT, locale="en-GB",
                                  viewport={"width": 1366, "height": 900})
        page = ctx.new_page()

        for city in cities:
            for ptype, ht_id in types.items():
                if (city, ptype) in done and not args.test:
                    print(f"[skip] {city} / {ptype} (deja facut)")
                    continue
                url = config.search_url(city, ht_id)
                print(f"[search] {city} / {ptype}")
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_selector('[data-testid="property-card"]', timeout=20000)
                except PWTimeout:
                    sleep()
                    continue
                dismiss_popups(page)
                n = load_all_results(page, max_res)
                rows = parse_search_page(page.content())
                ts = datetime.now().isoformat(timespec="seconds")
                with out_path.open("a", encoding="utf-8") as f:
                    for r in rows:
                        r.update(query_city=city, property_type=ptype, scraped_at=ts,
                                 checkin=config.CHECKIN, adults=config.ADULTS)
                        f.write(json.dumps(r, ensure_ascii=False) + "\n")
                with_price = sum(r["price"] is not None for r in rows)
                print(f"   -> {n} carduri, {len(rows)} parsate, {with_price} cu pret")
                sleep()

        browser.close()

if __name__ == "__main__":
    main()
