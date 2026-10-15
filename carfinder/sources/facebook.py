"""Facebook Marketplace via a headless browser. Best-effort and fragile.

Marketplace has no public API or nationwide search, so we visit the vehicles
page for each metro in `locations`. Facebook changes its markup often and
discourages scraping (see README); logged-out sessions get a login wall and
partial results, so a saved session (`storage_state`) works much better.
"""
from __future__ import annotations

import logging
import random
import re
from pathlib import Path
from urllib.parse import urlencode

from ..config import Search
from ..models import Listing, parse_color, parse_mileage, parse_price, parse_year

log = logging.getLogger(__name__)


def build_url(city: str, s: Search) -> str:
    p = {"query": f"{s.make} {s.model}".strip(), "exact": "false", "sortBy": "creation_time_descend"}
    if s.year_min: p["minYear"] = s.year_min
    if s.year_max: p["maxYear"] = s.year_max
    if s.max_price: p["maxPrice"] = s.max_price
    if s.max_mileage: p["maxMileage"] = s.max_mileage
    return f"https://www.facebook.com/marketplace/{city}/vehicles?" + urlencode(p)


def parse_card(href: str, text: str) -> Listing | None:
    """`text` is the card's inner text: usually price / title / location lines."""
    lines = [x.strip() for x in text.split("\n") if x.strip()]
    if not lines:
        return None
    price = next((parse_price(x) for x in lines if x.startswith("$")), None)
    rest = [x for x in lines if not x.startswith("$")]
    title = next((x for x in rest if parse_year(x)), rest[0] if rest else "")
    mileage = next((parse_mileage(x) for x in rest if parse_mileage(x)), None)
    loc = rest[-1] if len(rest) > 1 and rest[-1] != title else ""
    m = re.search(r"/marketplace/item/(\d+)", href)
    if not m or not title:
        return None
    return Listing(
        source="facebook", title=title, price=price, location=loc,
        url=f"https://www.facebook.com/marketplace/item/{m.group(1)}/",
        year=parse_year(title), mileage=mileage, color=parse_color(title),
    )


class Facebook:
    name = "facebook"

    def __init__(self, locations: list[str], storage_state: str | None = None):
        self.locations, self.storage_state = locations, storage_state

    def fetch(self, search: Search) -> list[Listing]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            log.error("facebook: playwright not installed (pip install playwright && playwright install chromium)")
            return []
        out, seen = [], set()
        state = self.storage_state if self.storage_state and Path(self.storage_state).exists() else None
        if not state:
            log.warning("facebook: no saved login session; expect a login wall and thin results")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context(storage_state=state, viewport={"width": 1280, "height": 1800})
            page = ctx.new_page()
            for city in self.locations:
                try:
                    page.goto(build_url(city, search), wait_until="domcontentloaded", timeout=45000)
                    page.wait_for_timeout(3000)
                    # dismiss the logged-out login modal if present
                    for sel in ('div[aria-label="Close"]', 'div[role="dialog"] [aria-label="Close"]'):
                        if page.locator(sel).count():
                            page.locator(sel).first.click(timeout=2000)
                            break
                    for _ in range(3):  # scroll to lazy-load more cards
                        page.mouse.wheel(0, 2500)
                        page.wait_for_timeout(1200)
                    cards = page.eval_on_selector_all(
                        'a[href*="/marketplace/item/"]',
                        "els => els.map(e => [e.getAttribute('href'), e.innerText])")
                    n = 0
                    for href, text in cards:
                        l = parse_card(href, text)
                        if l and l.key not in seen:
                            seen.add(l.key)
                            l.extra["metro"] = city
                            out.append(l)
                            n += 1
                    log.info("facebook %s: %d cards", city, n)
                except Exception as e:  # noqa: BLE001 - one bad city shouldn't kill the run
                    log.warning("facebook %s failed: %s", city, e)
                page.wait_for_timeout(random.randint(2000, 5000))
            browser.close()
        return out
