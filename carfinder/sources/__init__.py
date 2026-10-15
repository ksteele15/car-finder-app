from __future__ import annotations

from typing import Protocol

from ..config import Search
from ..models import Listing


class Source(Protocol):
    name: str

    def fetch(self, search: Search) -> list[Listing]: ...
