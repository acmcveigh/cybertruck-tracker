# ⚡ Cybertruck Market Tracker

A daily deal-finder for **used Tesla Cybertrucks priced at or under $70,000**, in
**mostly undamaged / clean-title condition**. It pulls live dealer inventory from
a used-car listings API, filters and ranks the best deals, tracks the market over
time (price history, new listings, price drops), and emails the top picks to
**tommcveigh@yahoo.com every day at 8:00 AM Pacific** — each with a **link to the
seller** and the **distance from Vida, OR**.

It runs free on **GitHub Actions** (a cloud cron), so your computer doesn't need
to be on.

---

## How it works

```
Marketcheck API ──▶ filter (≤ $70k, clean title, no salvage/damage keywords)
                       │
                       ▼
                 rank by price + mileage + distance (+ CPO / 1-owner bonus)
                       │
       ┌───────────────┼─────────────────────────────┐
       ▼               ▼                             ▼
 daily snapshot   price-history store          HTML email to Tom
 (data/*.json)    (data/history.json)          (top picks + new + drops)
```

- **Distance from Vida, OR (97488)** comes straight from the API (`dist`), measured
  from `44.1460, -122.5698`.
- **"Undamaged / better condition"** is approximated by: requiring a clean title,
  excluding salvage/rebuilt/flood/branded/wrecked listings (keyword scan), and
  rewarding certified pre-owned and single-owner cars in the ranking.
- The **market tracker** keeps a per-VIN history committed back to the repo, so you
  accumulate price trends and get "🆕 new since yesterday" + "📉 price drops" each day.

---

## One-time setup (~15 minutes)

### 1. Get a Marketcheck API key (free tier)
1. Go to <https://www.marketcheck.com/apis> and sign up for a developer account.
2. Create an app / project and copy your **API key**.
3. Docs for reference: <https://docs.marketcheck.com/docs/api/cars/inventory/inventory-search>

> Free tiers are call-limited. This tool makes ~10–20 calls per day, which is well
> within typical limits. If you ever hit a 429, lower `SEARCH_RADIUS_MILES` or
> `MAX_LISTINGS`. (Auto.dev is wired up as an alternative — set `PROVIDER=autodev`
> and add `AUTODEV_API_KEY` — but Marketcheck is recommended.)

### 2. Create a Gmail App Password
The email is sent **from your Gmail** (`acmcveigh@gmail.com`) to Tom's Yahoo address.
1. Enable **2-Step Verification**: <https://myaccount.google.com/security>
2. Open **App passwords**: <https://myaccount.google.com/apppasswords>
3. Create one named "Cybertruck Tracker" and copy the **16-character password**
   (spaces don't matter — the code strips them).

### 3. Put this folder in a private GitHub repo
From `C:\Users\acmcv\cybertruck-tracker` (PowerShell):
```powershell
git init
git add .
git commit -m "Initial Cybertruck tracker"
gh repo create cybertruck-tracker --private --source . --push
```
(Or create the repo on github.com and `git remote add origin ... ; git push -u origin main`.)

### 4. Add your secrets to the repo
Repo → **Settings → Secrets and variables → Actions**.

**Secrets** (encrypted):

| Name                  | Value                                  |
|-----------------------|----------------------------------------|
| `MARKETCHECK_API_KEY` | your Marketcheck key                   |
| `GMAIL_USER`          | `acmcveigh@gmail.com`                   |
| `GMAIL_APP_PASSWORD`  | the 16-char app password from step 2   |

**Variables** (optional — sensible defaults are built in):

| Name                  | Default              |
|-----------------------|----------------------|
| `EMAIL_TO`            | `tommcveigh@yahoo.com` |
| `PRICE_MAX`           | `70000`              |
| `SEARCH_RADIUS_MILES` | `3000`               |
| `MAX_MILES`           | (none)               |

### 5. Test it now (no waiting until 8 AM)
Repo → **Actions** tab → **Cybertruck Daily Tracker** → **Run workflow**.
Leave **force = true** to bypass the 8 AM guard. Check Tom's inbox.
Tick **dry_run** if you just want to test the pull without sending an email — the
report HTML is saved to `data/last_report.html` and committed so you can open it.

That's it. From then on it emails automatically every morning at **8:00 AM Pacific**.

---

## The 8 AM schedule (and why there are two crons)

GitHub's cron runs in **UTC and ignores daylight saving**. To hit 8 AM Pacific all
year, the workflow fires at **15:00 and 16:00 UTC**, and `run.py --require-hour 8`
makes only the correct one proceed (the other exits immediately):

- Summer (PDT, UTC−7): 15:00 UTC = 8 AM ✅, 16:00 UTC = 9 AM ⏭️
- Winter (PST, UTC−8): 15:00 UTC = 7 AM ⏭️, 16:00 UTC = 8 AM ✅

---

## Configuration

All knobs are environment variables (repo Variables in CI, or a local `.env`).
See [`.env.example`](.env.example) and [`config.py`](config.py). Highlights:

| Variable               | Default | Meaning                                         |
|------------------------|---------|-------------------------------------------------|
| `PRICE_MAX`            | 70000   | Hard price ceiling                              |
| `MAX_MILES`            | (off)   | Optional mileage cap, e.g. `60000`              |
| `REQUIRE_CLEAN_TITLE`  | true    | Drop non-clean-title cars                       |
| `SEARCH_RADIUS_MILES`  | 3000    | Search radius from Vida (covers continental US) |
| `TOP_N_EMAIL`          | 12      | How many top picks in the email                 |
| `WEIGHT_PRICE/MILES/DISTANCE` | 1.0 / 0.7 / 0.6 | Ranking weights                  |

---

## Running locally (optional)

You don't need this — GitHub Actions does everything — but to test on your PC:
1. Install Python 3.11+ from <https://www.python.org/downloads/> (tick "Add to PATH").
2. In this folder:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   copy .env.example .env      # then edit .env with your keys
   python run.py --dry-run     # builds data/last_report.html, no email
   python run.py               # actually sends the email
   ```

---

## Layout

```
cybertruck-tracker/
├── run.py                     # entrypoint: fetch → filter → rank → track → email
├── config.py                  # all settings (from env / .env)
├── requirements.txt
├── .env.example               # copy to .env for local runs
├── tracker/
│   ├── models.py              # normalized Listing
│   ├── filters.py             # price/title/condition filter + ranking score
│   ├── store.py               # daily snapshots + rolling price history + diffs
│   ├── emailer.py             # HTML/text report + Gmail SMTP send
│   ├── geo.py                 # distance-from-Vida helpers
│   ├── util.py                # defensive JSON parsing helpers
│   └── sources/
│       ├── marketcheck.py     # primary data source
│       └── autodev.py         # optional alternative
├── data/                      # snapshots/ + history.json (committed by the Action)
└── .github/workflows/daily.yml
```

---

## Honest limitations

- **Coverage is dealer inventory** (what Marketcheck aggregates). Private-party
  cars on Facebook Marketplace / Craigslist aren't included — those sites block
  automation and forbid it in their ToS. Marketcheck has a separate *private party*
  endpoint you can add later if you want that.
- **Condition is approximate.** APIs expose title status and carfax flags, not a
  full inspection. The filters catch salvage/branded/obvious-damage listings, but
  always read the actual listing and verify before buying.
- **API field names can vary by plan.** Parsing is defensive, but if something
  looks off, run `--dry-run` and open `data/last_report.html` to sanity-check.
