from __future__ import annotations

import html
import json
import smtplib
from datetime import date
from email.message import EmailMessage
from pathlib import Path

from .models import Listing


def _fmt(l: Listing) -> dict:
    return {
        "price": f"${l.price:,}" if l.price else "?",
        "year": l.year or "?",
        "miles": f"{l.mileage:,}" if l.mileage else "?",
        "color": l.color or "?",
    }


def sort_listings(ls: list[Listing]) -> list[Listing]:
    return sorted(ls, key=lambda l: (not l.is_new, l.price or 10**9))


def to_markdown(ls: list[Listing]) -> str:
    out = [f"# WRX finder: {date.today()}  ({len(ls)} listings, {sum(l.is_new for l in ls)} new)\n",
           "| New | Price | Year | Miles | Color | Source | Location | Listing |",
           "|---|---|---|---|---|---|---|---|"]
    for l in ls:
        f = _fmt(l)
        out.append(f"| {'🆕' if l.is_new else ''} | {f['price']} | {f['year']} | {f['miles']} | "
                   f"{f['color']} | {l.source} | {l.location} | [{l.title[:70]}]({l.url}) |")
    return "\n".join(out) + "\n"


def to_html(ls: list[Listing]) -> str:
    rows = []
    for l in ls:
        f = _fmt(l)
        rows.append(
            f"<tr class='{'new' if l.is_new else ''}'><td>{'NEW' if l.is_new else ''}</td>"
            f"<td>{f['price']}</td><td>{f['year']}</td><td>{f['miles']}</td><td>{f['color']}</td>"
            f"<td>{l.source}</td><td>{html.escape(l.location)}</td>"
            f"<td><a href='{html.escape(l.url)}'>{html.escape(l.title[:80])}</a></td></tr>")
    return f"""<!doctype html><meta charset=utf-8><title>WRX finder</title>
<style>body{{font:14px system-ui;margin:1.5rem}}table{{border-collapse:collapse}}
td,th{{padding:6px 10px;border-bottom:1px solid #ddd;text-align:left}}tr.new{{background:#eefbe7}}</style>
<h2>WRX finder, {date.today()} ({len(ls)} listings, {sum(l.is_new for l in ls)} new)</h2>
<table><tr><th></th><th>Price</th><th>Year</th><th>Miles</th><th>Color</th><th>Source</th><th>Location</th><th>Listing</th></tr>
{''.join(rows)}</table>"""


def write_reports(ls: list[Listing], out_dir: str) -> Path:
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    stem = d / f"wrx-{date.today()}"
    stem.with_suffix(".html").write_text(to_html(ls))
    stem.with_suffix(".md").write_text(to_markdown(ls))
    stem.with_suffix(".json").write_text(json.dumps([l.to_dict() for l in ls], indent=2))
    (d / "latest.html").write_text(to_html(ls))
    return stem.with_suffix(".html")


def send_email(ls: list[Listing], host: str, port: int, user: str, password: str,
               to: str, only_new: bool = True) -> bool:
    items = [l for l in ls if l.is_new] if only_new else ls
    if not items:
        return False
    msg = EmailMessage()
    msg["Subject"] = f"WRX finder: {len(items)} {'new ' if only_new else ''}listings"
    msg["From"], msg["To"] = user, to
    msg.set_content(to_markdown(items))
    msg.add_alternative(to_html(items), subtype="html")
    with smtplib.SMTP(host, port) as s:
        s.starttls()
        s.login(user, password)
        s.send_message(msg)
    return True
