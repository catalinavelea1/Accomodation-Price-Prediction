
import argparse
import json
import random
import time

from playwright.sync_api import sync_playwright

import config
from crawl_search import dismiss_popups


def html_path(property_id: str):
    return config.DETAILS_HTML_DIR / (property_id.replace("/", "__") + ".html")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--headful", action="store_true")
    args = ap.parse_args()

    config.DETAILS_HTML_DIR.mkdir(parents=True, exist_ok=True)

    urls = {}
    for line in config.SEARCH_RESULTS_FILE.open(encoding="utf-8"):
        r = json.loads(line)
        urls.setdefault(r["property_id"], r["url"])
    todo = [(pid, u) for pid, u in urls.items() if not html_path(pid).exists()]
    if args.limit:
        todo = todo[: args.limit]
    print(f"{len(urls)} proprietati unice, {len(todo)} de descarcat")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headful)
        ctx = browser.new_context(user_agent=config.USER_AGENT, locale="en-GB")
        page = ctx.new_page()
        for i, (pid, url) in enumerate(todo, 1):
            try:
                page.goto(config.detail_url(url), wait_until="domcontentloaded", timeout=60000)
                dismiss_popups(page)
                page.wait_for_timeout(2000)
                page.mouse.wheel(0, 6000)
                page.wait_for_timeout(1500)
                html_path(pid).write_text(page.content(), encoding="utf-8")
                print(f"[{i}/{len(todo)}] ok  {pid}")
            except Exception as e:
                print(f"[{i}/{len(todo)}] EROARE {pid}: {e}")
            time.sleep(random.uniform(*config.DELAY_RANGE))
        browser.close()


if __name__ == "__main__":
    main()
