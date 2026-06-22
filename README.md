# Finletter

A small Python program that emails a styled, factual weekly markets summary every
Friday after the US close. It reports how global markets moved during the week
across four lenses: region rotation, US sector rotation, US market-cap tiers, and
per-region stock winners & losers.

See [`convos/prompt.md`](convos/prompt.md) for the full specification.

## How it works

- **Region rotation** is computed in **local currency** by comparing each region's
  local index (S&P 500, STOXX 600, OMX Stockholm 30, Straits Times) — each index's
  weekly % return is already a local-currency return, so no FX conversion is needed.
- **Sector rotation** and **cap tiers** use US ETFs (all USD, directly comparable).
- **Winners & losers** inspect ~15 of the largest companies per region.
- Data comes from Yahoo Finance via `yfinance`. The email is plain factual templates
  plus tables and two inline bar charts — no LLM-generated prose.
- **Opening summary** ("This week in the global economy") is the one LLM-sourced
  part: `finletter/news.py` shells out to the [Claude Code CLI](https://docs.claude.com/claude-code)
  in print mode (`claude -p … --allowedTools WebSearch WebFetch`) to pull five
  balanced global finance/macro headlines for the week. It's best-effort — if the
  `claude` binary is missing or the call fails, the summary block is omitted and
  the rest of the letter sends as usual. Tune via `CLAUDE_BIN`, `NEWS_MODEL`, and
  `NEWS_TIMEOUT_SECONDS` (see `.env.example`).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env: Gmail address + App Password + recipient
```

Gmail requires an **App Password** (with 2FA enabled), not your normal password:
https://myaccount.google.com/apppasswords

## Usage

```bash
# Local preview — fetch data, render HTML to a file, do NOT send:
python -m finletter.main --no-send --out out.html
open out.html   # or xdg-open on the Pi

# Fetch and send the email:
python -m finletter.main
```

## Scheduling on the Raspberry Pi (cron)

Run every Friday at 4:30pm US Eastern (after the US close, by which point European
and Asian markets are also closed for the week). `CRON_TZ` pins the schedule to
Eastern regardless of the Pi's own timezone:

```cron
CRON_TZ=America/New_York
30 16 * * 5  cd /home/pi/finletter && /home/pi/finletter/.venv/bin/python -m finletter.main >> /home/pi/finletter/run.log 2>&1
```

Edit with `crontab -e`. Before relying on the Friday schedule, test with a temporary
near-future time (e.g. set it a few minutes ahead and confirm the email arrives).

## Notes & tuning

- **Constituent lists** (`finletter/config.py`) are starter universes of the largest
  names per region. Market caps shift slowly; review them every few months.
- **SE Asia** spans multiple currencies; the Straits Times Index (Singapore, SGD) is
  used as a single representative. Swap the ticker in `REGION_INDICES` if preferred.
- **Flaky tickers**: yfinance coverage of some European/Swedish names is occasionally
  unreliable. Missing data never fails the run — affected tickers are listed in a
  footnote. A Stooq fallback (`pandas-datareader`) is noted as a hook in `data.py`.

## Project layout

```
finletter/
  config.py    # tickers, region defs, settings
  data.py      # yfinance fetch + weekly-return computation
  analysis.py  # rotation rankings + winners/losers (pure)
  charts.py    # matplotlib bar charts -> PNG bytes
  render.py    # HTML + plain-text assembly
  emailer.py   # SMTP send with inline images
  main.py      # orchestration + CLI
```
