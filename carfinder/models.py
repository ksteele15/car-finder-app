from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict


@dataclass
class Listing:
    source: str
    title: str
    url: str
    price: int | None = None
    location: str = ""
    year: int | None = None
    mileage: int | None = None
    color: str | None = None
    is_new: bool = False
    extra: dict = field(default_factory=dict)

    @property
    def key(self) -> str:
        m = re.search(r"/(\d{6,})(?:\.html)?(?:[/?]|$)", self.url)
        return f"{self.source}:{m.group(1) if m else self.url}"

    def to_dict(self) -> dict:
        return asdict(self)


_YEAR = re.compile(r"\b(19[89]\d|20[0-3]\d)\b")
_MILES = re.compile(r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(k)?\s*(?:miles|mile|mi)\b", re.I)
COLORS = ["black", "blue", "brown", "green", "grey", "gray", "orange", "purple",
          "red", "silver", "white", "yellow"]


def parse_year(text: str) -> int | None:
    m = _YEAR.search(text)
    return int(m.group(1)) if m else None


def parse_mileage(text: str) -> int | None:
    m = _MILES.search(text)
    if not m:
        return None
    n = float(m.group(1).replace(",", ""))
    if m.group(2):
        n *= 1000
    elif n < 1000:  # "85 miles" is almost certainly a typo/odd; "85k" handled above
        return None
    return int(n)


def parse_color(text: str) -> str | None:
    low = text.lower()
    for c in COLORS:
        if re.search(rf"\b{c}\b", low):
            return "grey" if c == "gray" else c
    return None


def parse_price(text: str) -> int | None:
    m = re.search(r"\$\s*([\d,]+)", text)
    return int(m.group(1).replace(",", "")) if m else None
