from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Search:
    make: str = "Subaru"
    model: str = "WRX"
    year_min: int | None = None
    year_max: int | None = None
    colors: list[str] = field(default_factory=list)
    max_price: int | None = None
    max_mileage: int | None = None
    exclude_words: list[str] = field(default_factory=list)
    strict: bool = False


@dataclass
class Config:
    search: Search
    sources: dict
    output: dict


def load(path: str | Path) -> Config:
    raw = yaml.safe_load(Path(path).read_text()) or {}
    s = raw.get("search", {})
    s["colors"] = [c.lower().replace("gray", "grey") for c in s.get("colors") or []]
    return Config(
        search=Search(**s),
        sources=raw.get("sources", {}),
        output=raw.get("output", {"dir": "reports", "state_file": "state/seen.json"}),
    )
