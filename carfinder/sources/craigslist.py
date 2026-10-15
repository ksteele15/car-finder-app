from __future__ import annotations

import logging
import re
import time
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from ..config import Search
from ..models import Listing, parse_color, parse_mileage, parse_price, parse_year

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# Craigslist's own paint codes for the auto_paint filter
PAINT = {"black": 1, "blue": 2, "brown": 3, "green": 4, "grey": 5, "orange": 6,
         "purple": 7, "red": 8, "silver": 9, "white": 10, "yellow": 11}

# Major US metros (subdomains). Used if the live site index can't be fetched.
FALLBACK_SITES = """
albuquerque anchorage atlanta austin baltimore batonrouge birmingham boise boston buffalo
charleston charlotte chattanooga chicago cincinnati cleveland colorado columbus dallas denver
desmoines detroit elpaso fresno greensboro greenville hartford honolulu houston indianapolis
jacksonville kansascity lasvegas lexington littlerock losangeles louisville madison memphis miami
milwaukee minneapolis nashville neworleans newyork norfolk oklahomacity omaha orangecounty
orlando philadelphia phoenix pittsburgh portland providence raleigh reno richmond rochester
sacramento saltlakecity sanantonio sandiego sfbay seattle spokane stlouis syracuse tampa tucson
tulsa washingtondc wichita
""".split()


def all_sites(session: requests.Session) -> list[str]:
    try:
        r = session.get("https://www.craigslist.org/about/sites", timeout=20)
        r.raise_for_status()
        # US section comes first on that page, before "CA", "INTL" headings
        us = r.text.split('id="can"')[0] if 'id="can"' in r.text else r.text
        subs = sorted(set(re.findall(r"https?://([a-z0-9]+)\.craigslist\.org", us)) - {"www", "forums", "geo"})
        if len(subs) > 100:
            return subs
    except requests.RequestException as e:
        log.warning("couldn't fetch CL site index (%s); using bundled metro list", e)
    return FALLBACK_SITES


def build_url(site: str, s: Search) -> str:
    params = {"query": s.model, "auto_make_model": f"{s.make} {s.model}".strip(),
              "srchType": "T"}
    if s.year_min: params["min_auto_year"] = s.year_min
    if s.year_max: params["max_auto_year"] = s.year_max
    if s.max_price: params["max_price"] = s.max_price
    if s.max_mileage: params["max_auto_miles"] = s.max_mileage
    codes = [PAINT[c] for c in s.colors if c in PAINT]
    if codes:
        params["auto_paint"] = codes
    return f"https://{site}.craigslist.org/search/cta?" + urlencode(params, doseq=True)


def parse_results(html: str, site: str) -> list[Listing]:
    """Parse the no-JS static results list Craigslist serves."""
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for li in soup.select("li.cl-static-search-result"):
        a = li.find("a", href=True)
        if not a:
            continue
        title = (li.select_one(".title") or li).get_text(" ", strip=True)
        price = parse_price(li.select_one(".price").get_text()) if li.select_one(".price") else None
        if price is not None and price < 1500:  # "$1"/"$0" placeholder prices
            price = None
        loc = li.select_one(".location")
        out.append(Listing(
            source="craigslist", title=title, url=a["href"], price=price,
            location=(loc.get_text(strip=True) if loc else site),
            year=parse_year(title), mileage=parse_mileage(title), color=parse_color(title),
        ))
    return out


class Craigslist:
    name = "craigslist"

    def __init__(self, sites="all", delay_seconds: float = 2.0):
        self.sites, self.delay = sites, delay_seconds
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def fetch(self, search: Search) -> list[Listing]:
        sites = all_sites(self.session) if self.sites == "all" else list(self.sites)
        log.info("craigslist: searching %d sites", len(sites))
        seen, out, blocked = set(), [], 0
        for i, site in enumerate(sites):
            try:
                r = self.session.get(build_url(site, search), timeout=25)
                if r.status_code in (403, 429):
                    blocked += 1
                    log.warning("craigslist %s: HTTP %s (rate-limited/blocked)", site, r.status_code)
                    if blocked >= 5:
                        log.error("craigslist: too many blocks, stopping early. Try a home IP / slower delay.")
                        break
                    time.sleep(30)
                    continue
                r.raise_for_status()
                for l in parse_results(r.text, site):
                    if l.key not in seen:
                        seen.add(l.key)
                        out.append(l)
            except requests.RequestException as e:
                log.warning("craigslist %s failed: %s", site, e)
            if i < len(sites) - 1:
                time.sleep(self.delay)
        return out
