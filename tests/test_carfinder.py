from carfinder.config import Search
from carfinder.filters import matches
from carfinder.models import Listing, parse_mileage, parse_year
from carfinder.sources.craigslist import build_url, parse_results
from carfinder.sources.facebook import parse_card

CL_HTML = """
<ol class="cl-static-search-results">
<li class="cl-static-search-result" title="x"><a href="https://denver.craigslist.org/cto/d/denver-2018-subaru-wrx/7712345678.html">
<div class="title">2018 Subaru WRX Blue 42k miles</div><div class="details"><div class="price">$24,500</div><div class="location">denver</div></div></a></li>
<li class="cl-static-search-result"><a href="https://denver.craigslist.org/cto/d/y/7712345999.html">
<div class="title">WRX parts only 2016</div><div class="details"><div class="price">$1</div></div></a></li>
</ol>"""

S = Search(year_min=2015, year_max=2021, colors=["blue"], max_price=30000, max_mileage=80000,
           exclude_words=["parts"])


def test_parse_helpers():
    assert parse_year("2018 Subaru WRX") == 2018
    assert parse_mileage("only 42k miles") == 42000
    assert parse_mileage("85,500 mi") == 85500


def test_craigslist_parse_and_filter():
    ls = parse_results(CL_HTML, "denver")
    assert len(ls) == 2
    assert ls[0].price == 24500 and ls[0].year == 2018 and ls[0].mileage == 42000
    assert ls[1].price is None  # "$1" placeholder
    assert [matches(l, S) for l in ls] == [True, False]


def test_filter_bounds():
    base = dict(source="craigslist", url="https://x/1234567.html")
    assert not matches(Listing(title="2012 Subaru WRX blue", **base), S)
    assert not matches(Listing(title="2018 Subaru WRX blue", price=35000, **base), S)
    assert not matches(Listing(title="2018 Subaru WRX red", **base), S)
    assert not matches(Listing(title="2018 Subaru WRX blue 120k miles", **base), S)
    assert matches(Listing(title="2018 Subaru WRX", **base), S)  # unknowns pass when not strict
    S.strict = True
    assert not matches(Listing(title="2018 Subaru WRX", **base), S)
    S.strict = False


def test_craigslist_url():
    u = build_url("seattle", S)
    assert u.startswith("https://seattle.craigslist.org/search/cta?")
    assert "min_auto_year=2015" in u and "auto_paint=2" in u and "max_auto_miles=80000" in u


def test_facebook_card():
    l = parse_card("/marketplace/item/998877665544/?ref=x", "$22,000\n2019 Subaru WRX Premium\nPortland, OR\n45K miles")
    assert l.price == 22000 and l.year == 2019 and l.url.endswith("/998877665544/")
