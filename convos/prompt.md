# Finletter — Project Specification

## What it is

A Python program running on a Raspberry Pi 4 that sends a styled weekly email every Friday after US markets close (~4:30pm ET). The email summarizes how global markets behaved during the week across multiple lenses: region vs region, sector vs sector, cap tier vs cap tier, and individual stock winners/losers.

---

## Schedule

- **Frequency**: Weekly, Fridays only
- **Send time**: After US market close (~4:15–4:30pm ET), which also ensures all European and Asian markets are closed for the week

---

## Regions

Four regions, each treated as a separate unit of analysis:

| Region | Scope |
|---|---|
| US | Top 15 companies by market cap (S&P 500 universe) |
| Sweden | Top 15 companies by market cap (OMX-listed) |
| Europe (ex-Sweden) | Top 15 companies by market cap (Stoxx 600 universe, excluding Swedish listings) |
| SE Asia | Top 15 companies by market cap |

---

## Email content

### 1. Region-level rotation
How regions performed relative to each other this week.
Implemented via broad regional ETFs (USD-denominated, so directly comparable):
- US → SPY or QQQ
- Europe (ex-Sweden) → VGK or IEUR
- Sweden → EWD
- SE Asia → AAXJ or VPL

> **Open question**: USD comparison vs local currency? USD is simpler and consistent; local currency reflects what local investors actually experienced.

### 2. Sector-level rotation (US)
How sectors performed relative to each other this week.
Implemented via SPDR sector ETFs: XLK (tech), XLI (industrials), XLE (energy), XLF (financials), etc.
Presented as a ranked list: "Tech outperformed Industrials, which beat Energy…"

### 3. Market-cap tier comparison
How large caps, mid caps, and small caps performed relative to each other this week (at minimum for US; ideally for other regions too if data is available).

### 4. Regional winners & losers
For each region: inspect the top 15 companies by market cap, surface the 3 best and 3 worst performers of the week.
Total: 6 companies × 4 regions = 24 companies highlighted.

Duplicates across regions are acceptable — a Swedish company can appear in both the Sweden winners/losers list and the Europe winners/losers list.

> Note on API requests: fetching 15 tickers per region × 4 regions = 60 requests. This is well within free-tier limits for Yahoo Finance / yfinance and should be batched where possible.

---

## Format & delivery

- **Format**: Styled HTML email with tables; graphs included where appropriate (inline images or chart-as-image)
- **Tone**: Factual. No LLM-generated prose. Predefined string templates for all narrative elements (e.g. `f"US losers this week: {loser_1}, {loser_2}, {loser_3}"`)
- **Delivery**: SMTP (Gmail or similar)
- **Recipient**: Single recipient (just me) for now

---

## Stack & infrastructure

- **Language**: Python
- **Key libraries**: `yfinance` (data), `pandas` (processing), `schedule` or cron (scheduling), `smtplib` (email)
- **Infrastructure**: Raspberry Pi 4
- **Data sources**: Free APIs (Yahoo Finance via yfinance as primary); may need a fallback for European/Swedish tickers where yfinance is unreliable

---

## Out of scope

- Daily letters
- Anomaly detection (rapid rises/steep drops)
- Multi-subscriber support
- LLM-generated analysis
