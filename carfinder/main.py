from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

from . import report
from .config import load
from .filters import matches
from .sources.craigslist import Craigslist
from .sources.facebook import Facebook

log = logging.getLogger("carfinder")


def build_sources(cfg):
    srcs = []
    c = cfg.sources.get("craigslist", {})
    if c.get("enabled", True):
        srcs.append(Craigslist(c.get("sites", "all"), c.get("delay_seconds", 2.0)))
    f = cfg.sources.get("facebook", {})
    if f.get("enabled", False):
        srcs.append(Facebook(f.get("locations", []), f.get("storage_state")))
    return srcs


def dedupe(listings):
    """Same car cross-posted on several CL sites: collapse on title+price."""
    seen, out = set(), []
    for l in listings:
        k = (l.source, l.title.lower(), l.price)
        if k not in seen:
            seen.add(k)
            out.append(l)
    return out


def run(config_path: str, email: bool) -> int:
    cfg = load(config_path)
    state_file = Path(cfg.output["state_file"])
    seen = set(json.loads(state_file.read_text())) if state_file.exists() else set()

    found = []
    for src in build_sources(cfg):
        try:
            got = src.fetch(cfg.search)
        except Exception:  # noqa: BLE001
            log.exception("source %s crashed; continuing", src.name)
            continue
        kept = [l for l in got if matches(l, cfg.search)]
        log.info("%s: %d fetched, %d match", src.name, len(got), len(kept))
        found += kept

    found = dedupe(found)
    for l in found:
        l.is_new = l.key not in seen
    found = report.sort_listings(found)

    path = report.write_reports(found, cfg.output["dir"])
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(sorted(seen | {l.key for l in found})))
    print(f"{len(found)} listings ({sum(l.is_new for l in found)} new) -> {path}")

    if email and all(os.environ.get(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "EMAIL_TO")):
        sent = report.send_email(found, os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", 587)),
                                 os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"], os.environ["EMAIL_TO"])
        print("email sent" if sent else "no new listings; email skipped")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Daily WRX listing finder")
    ap.add_argument("-c", "--config", default="config.yaml")
    ap.add_argument("--email", action="store_true", help="email new listings (needs SMTP_* env vars)")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    raise SystemExit(run(a.config, a.email))


if __name__ == "__main__":
    main()
