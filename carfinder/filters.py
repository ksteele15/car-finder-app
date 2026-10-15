from __future__ import annotations

from .config import Search
from .models import Listing, parse_color, parse_mileage, parse_year


def matches(l: Listing, s: Search) -> bool:
    title = l.title.lower()
    if s.model and s.model.lower() not in title:
        return False
    if any(w.lower() in title for w in s.exclude_words):
        return False

    def bad(value, lo=None, hi=None) -> bool:
        if value is None:
            return s.strict  # unknown: drop only in strict mode
        return (lo is not None and value < lo) or (hi is not None and value > hi)

    year = l.year or parse_year(l.title)
    miles = l.mileage or parse_mileage(l.title)
    if bad(year, s.year_min, s.year_max):
        return False
    if bad(l.price, None, s.max_price):
        return False
    if bad(miles, None, s.max_mileage):
        return False
    if s.colors:
        color = l.color or parse_color(l.title)
        if color is None:
            if s.strict:
                return False
        elif color not in s.colors:
            return False
    return True
