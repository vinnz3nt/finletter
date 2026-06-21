"""Static configuration: tickers, region definitions, and run settings.

All ticker symbols use yfinance conventions (e.g. ``.ST`` for Stockholm,
``.PA`` for Paris, ``^`` prefix for indices).

The constituent lists below are *starter* universes of the largest companies
per region by market cap. Market caps shift slowly, so these should be reviewed
every few months — but a stale entry only affects which names show up in the
winners/losers tables, never the program's correctness.
"""

# Days of daily history to fetch. Needs to span the current week plus the
# previous week's final trading day, with slack for holidays.
WEEK_LOOKBACK_DAYS = 12

# --- Section 1: region-level rotation (LOCAL currency) ------------------------
# Each region is represented by an index quoted in its own local currency, so
# the index's weekly % return *is* the local-currency return — no FX needed.
#
# SE Asia spans several currencies; the Straits Times Index (Singapore, SGD) is
# used as a single representative. Swap freely if a better proxy is preferred.
REGION_INDICES = {
    "US": {"ticker": "^GSPC", "name": "S&P 500", "currency": "USD"},
    "Europe (ex-SE)": {"ticker": "^STOXX", "name": "STOXX 600", "currency": "EUR"},
    "Sweden": {"ticker": "^OMX", "name": "OMX Stockholm 30", "currency": "SEK"},
    "SE Asia": {"ticker": "^STI", "name": "Straits Times", "currency": "SGD"},
}

# --- Section 2: US sector rotation (SPDR sector ETFs, all USD) -----------------
SECTOR_ETFS = {
    "XLK": "Technology",
    "XLC": "Communications",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLE": "Energy",
    "XLF": "Financials",
    "XLV": "Health Care",
    "XLI": "Industrials",
    "XLB": "Materials",
    "XLRE": "Real Estate",
    "XLU": "Utilities",
}

# --- Section 3: US market-cap tiers (all USD, directly comparable) -------------
CAP_TIER_ETFS = {
    "OEF": "Large cap (S&P 100)",
    "IJH": "Mid cap (S&P 400)",
    "IJR": "Small cap (S&P 600)",
}

# --- Section 4: per-region top constituents for winners/losers ----------------
# yfinance symbols. Targeting ~15 of the largest names per region.
REGION_CONSTITUENTS = {
    "US": [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "BRK-B", "LLY",
        "AVGO", "TSLA", "JPM", "V", "XOM", "UNH", "MA",
    ],
    "Sweden": [
        "INVE-B.ST", "ATCO-A.ST", "VOLV-B.ST", "ASSA-B.ST", "ABB.ST",
        "ERIC-B.ST", "SEB-A.ST", "SHB-A.ST", "SWED-A.ST", "HEXA-B.ST",
        "EQT.ST", "SAND.ST", "ALFA.ST", "EVO.ST", "TELIA.ST",
    ],
    "Europe (ex-SE)": [
        "ASML.AS", "NESN.SW", "NOVO-B.CO", "MC.PA", "RO.SW", "SAP.DE",
        "OR.PA", "AZN.L", "SHEL.L", "NOVN.SW", "TTE.PA", "SIE.DE",
        "PRX.AS", "SAN.PA", "AIR.PA",
    ],
    "SE Asia": [
        "D05.SI", "O39.SI", "U11.SI", "Z74.SI", "C6L.SI", "C38U.SI",
        "9CI.SI", "S68.SI", "A17U.SI", "BN4.SI", "C09.SI", "Y92.SI",
        "G13.SI", "BS6.SI", "F34.SI",
    ],
}
