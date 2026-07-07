<div align="center">

# copy-trader

**A Hyperliquid copy-trading research pipeline. It scores on-chain wallets by how good they actually are, ranks them, and paper-trades the top ones.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Hyperliquid](https://img.shields.io/badge/Hyperliquid-On--chain-50D2C8?style=for-the-badge)](https://hyperliquid.xyz)
[![pandas](https://img.shields.io/badge/pandas-2.2-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org)
[![License](https://img.shields.io/badge/License-Source--Available-red?style=for-the-badge)](#license)

</div>

---

## What it is

This is a two-stage pipeline I built to figure out whether copy-trading on Hyperliquid actually works before I put any real money into it.

Stage 1 is the scorer. Every 6 hours it pulls 90 days of fills for each wallet I'm tracking, computes Sharpe, max drawdown, win rate, profit factor, and a composite score, then promotes the top N to an "active" watchlist and posts a leaderboard to Discord.

Stage 2 is the paper trader. It subscribes to those active wallets over Hyperliquid's WebSocket and mirrors their fills into a fake paper portfolio with full risk filters. Every paper fill posts to Discord.

There's no live execution code in here and no private keys. The whole thing is read-only against Hyperliquid's public endpoints. I'm not adding live trading until the paper track record proves the wallet selection is actually good over 4 to 8 weeks.

---

## What I learned building it

- **Quantitative research.** I had to figure out how to actually measure if a trader is good. I compute Sharpe ratio, max drawdown, win rate, profit factor, and a composite score over a 90-day lookback, with a minimum-trades floor so I'm not ranking wallets on 3 lucky trades.
- **Data engineering.** Async REST and WebSocket client for Hyperliquid's public endpoints, streaming live fills into an in-memory portfolio that gets persisted to disk.
- **Risk modeling.** Pre-trade checks and position sizing: per-position cap, per-wallet cap, leverage cap, daily-loss circuit breaker, and a funding-rate filter that skips a copy when annualized funding gets too high.
- **Discipline.** This was the hard part. It's really tempting to skip paper trading and just go live when the leaderboard looks good, but I made myself wait. The model assumes 4.5 bps taker fees both ways and realizes PnL immediately, which is conservative. I'm only adding a slippage and latency model once the paper data justifies it.

---

## How it works

1. **`scorer/`** - every 6 hours, pulls 90 days of fills for each seed wallet, computes Sharpe / drawdown / win-rate / profit-factor / composite score, and promotes the top N to an "active" watchlist. Posts a leaderboard to Discord on every refresh.
2. **`paper/`** - subscribes to the active wallets over Hyperliquid's WebSocket and mirrors their fills into an in-memory paper book with full risk filters. Every paper fill posts to Discord.

```
       ┌────────────────────┐
       │ data/seed_wallets  │  <- curated from on-chain research
       └─────────┬──────────┘
                 │ scorer/run.py (every 6h)
                 ▼
       ┌────────────────────┐
       │ wallet_scores.json │  <- ranked, with Sharpe / DD / score
       │ active_wallets.json│  <- top N promoted
       └─────────┬──────────┘
                 │ paper/run.py (WebSocket)
                 ▼
   ┌──────────────────────────────┐
   │ paper_state.json (positions) │
   │ paper_fills.jsonl   (log)    │
   │ Discord webhook   (alerts)   │
   └──────────────────────────────┘
```

---

## Components

| Path | What it does |
|---|---|
| `common/hl_client.py` | Async REST + WS client for Hyperliquid public endpoints |
| `common/discord.py` | Webhook notifier |
| `common/wallet_store.py` | Read/write seed / scores / active wallet files |
| `scorer/metrics.py` | Per-wallet metric computation (Sharpe, drawdown, PF, composite) |
| `scorer/run.py` | Long-running scorer loop |
| `paper/book.py` | In-memory portfolio, persisted to JSON |
| `paper/risk.py` | Pre-trade risk checks + sizing |
| `paper/run.py` | WS subscriber that mirrors fills into the book |
| `paper/summary.py` | Daily Discord summary |
| `scripts/import_seed.py` | Validate + load a research seed file |
| `scripts/show_scores.py` | CLI: pretty-print latest scores |
| `scripts/show_book.py` | CLI: pretty-print current paper book |

---

## Sizing model

For each `Open` fill from a source wallet:

```
pct_of_source_equity = source_notional / source_clearinghouse_equity
our_notional         = pct_of_source_equity * our_paper_equity
our_notional         = min(our_notional, MAX_POSITION_PCT * equity)
our_notional         = min(our_notional, per_wallet_capacity_remaining)
size_units           = our_notional / current_mark_price
```

If a source wallet puts 8% of their equity into ETH, the paper book puts about 8% of paper equity into ETH, capped at `PAPER_MAX_POSITION_PCT`. I don't mirror the dollar size 1:1 because that's undercapitalized for whales and overcapitalized for small wallets. Leverage is mirrored up to `PAPER_MAX_LEVERAGE`.

When the source closes or reverses on a coin I hold for that wallet, I close at their fill price and realize PnL immediately, assuming a 4.5 bps taker fee both ways. This is conservative on purpose. Real fills have slippage and reaction-time delay, and I'll add a configurable model for that once there's enough paper data to tune it against.

---

## Configuration (`.env`)

| Var | Default | Meaning |
|---|---|---|
| `DISCORD_WEBHOOK_URL` | - | Channel for alerts |
| `PAPER_STARTING_EQUITY_USD` | 10000 | Simulated starting capital |
| `PAPER_MAX_POSITION_PCT` | 10 | Max % of equity in any one copy |
| `PAPER_DAILY_LOSS_LIMIT_PCT` | 5 | Halts copies for the day if breached |
| `PAPER_MAX_LEVERAGE` | 10 | Caps source leverage to replicate |
| `PAPER_MAX_FUNDING_APR_PCT` | 200 | Skip copies when funding > this APR % |
| `PAPER_PER_WALLET_CAP_PCT` | 25 | Max % of equity in positions from any single wallet |
| `SCORER_LOOKBACK_DAYS` | 90 | Fill-history window |
| `SCORER_MIN_TRADES` | 20 | Min closing fills to rank a wallet |
| `SCORER_REFRESH_MINUTES` | 360 | Re-score cadence |

---

## What's not in here

- **Live execution / signing.** Add only after paper proves the wallet selection.
- **Database.** Discord + JSON logs only, per the project spec.
- **Web dashboard.** Use the `scripts/show_*` CLIs.
- **Other venues.** Hyperliquid only for v1.

---

## Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.11+ |
| Exchange data | Hyperliquid Python SDK + public REST/WS |
| Data | pandas, numpy |
| Validation | pydantic |
| Logging | loguru |
| Resilience | tenacity |
| Alerts | Discord webhooks |
| Hosting | systemd on a VPS |

---

## Quick start

```bash
git clone https://github.com/PandaXPanther/copy-trader.git
cd copy-trader
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit DISCORD_WEBHOOK_URL etc.

# Seed wallets from on-chain research (one-time):
python -m scripts.import_seed path/to/seed_wallets.json

# Run scorer (long-running, refreshes every SCORER_REFRESH_MINUTES):
python -m scorer.run

# In another shell, once data/active_wallets.json exists:
python -m paper.run

# Anytime:
python -m scripts.show_scores
python -m scripts.show_book
python -m paper.summary
```

> The committed `data/seed_wallets.json` is a sample. The production wallet set is a research output I keep separately, and you don't need it to review the methodology.

---

## Disclaimer

This is research and educational infrastructure. Hyperliquid perps are highly leveraged and can liquidate you. Copy trading is not a license to print money, and past performance of any wallet doesn't guarantee future returns. Don't deploy real capital based on paper results alone.

---

## License

This code is **source-available for portfolio and educational review only**, not open source. You can read it to see what I built, but you can't copy, redistribute, deploy, run, or make money off it. The production wallet-selection research and the live execution layer aren't included, so the code as published won't run as-is. See [`LICENSE`](LICENSE) for the full terms.
