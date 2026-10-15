# WRX finder

Searches Craigslist (all US sites) and Facebook Marketplace (a list of metros) for the car you
want, filters by year / color / price / mileage, flags listings you haven't seen before, and
writes a report (and optionally emails it).

## Setup
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
playwright install chromium        # only for Facebook
```
Edit `config.yaml` (year range, colors, max price, max mileage, make/model, metros).

## Run
```bash
python -m carfinder -v             # reports/latest.html, reports/wrx-YYYY-MM-DD.{html,md,json}
python -m carfinder --email        # also emails NEW listings (set SMTP_HOST, SMTP_USER, SMTP_PASSWORD, EMAIL_TO)
python -m pytest                   # tests
```
First run marks everything "new"; after that only unseen listings are (state in `state/seen.json`).

## Every morning
Home machine / Raspberry Pi is the most reliable (Craigslist blocks cloud IPs):
```cron
0 6 * * *  cd /path/to/car-finder-app && .venv/bin/python -m carfinder --email >> run.log 2>&1
```
`.github/workflows/daily.yml` is a backup that runs it on GitHub Actions (add the `SMTP_*`/`EMAIL_TO` secrets).

## Facebook
Marketplace has no API and no nationwide search, so this visits each metro in `locations`.
Logged-out you hit a login wall. For better results run `python fb_login.py` once to save a session to
`fb_state.json`. **Use a secondary account**: Facebook's terms prohibit automated scraping and can restrict
accounts that do it. Facebook changes its markup often, so expect to patch `sources/facebook.py` occasionally.
A failure in one source never stops the others.

## Known limits
- Year/mileage/color are read from listing titles (Craigslist's static results don't include them). With
  `strict: false` listings where they can't be read are kept; Craigslist already filters server-side.
- Add more sources (Cars.com, Autotrader, Cars & Bids) by adding a class in `carfinder/sources/` with `fetch(search)`.
