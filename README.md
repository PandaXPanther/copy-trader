<div align="center">

# copy-trader

**A research-grade Hyperliquid copy-trading pipeline — on-chain wallet scoring, composite ranking, and risk-filtered paper execution.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Hyperliquid](https://img.shields.io/badge/Hyperliquid-On--chain-50D2C8?style=for-the-badge)](https://hyperliquid.xyz)
[![pandas](https://img.shields.io/badge/pandas-2.2-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org)
[![License](https://img.shields.io/badge/License-Source--Available-red?style=for-the-badge)](#license)

</div>

---

## About

copy-trader is a two-stage research stack that identifies skilled perpetual-futures traders on Hyperliquid by analyzing their on-chain fill history, ranks them with a composite risk-adjusted score, then mirrors the top performers' trades into a fully risk-filtered paper-trading book.

Live execution is **intentionally not included**. The system is read-only against Hyperliquid's public endpoints — no private keys, no signing — and exists to validate wallet-selection methodology over a paper-trading horizon before any real capital is committed.

---

## What this project demonstrates

For reviewers evaluating quantitative and engineering judgment:

- **Quantitative research** — per-wallet metric computation: Sharpe ratio, max drawdown, win rate, profit factor, and a composite score over a 90-day lookback, with a minimum-trades floor to avoid statistically thin profiles.
- **Data engineering** — an async REST + WebSocket client for Hyperliquid public endpoints, streaming live fills into an in-memory portfolio persisted to disk.
- **Risk modeling** — pre-trade risk checks and position sizing: per-position cap, per-wallet cap, leverage cap, daily-loss circuit breaker, and a funding-rate filter that skips copies when annualized funding exceeds a threshold.
- **Discipline** — a deliberate "research first" posture: paper trading, conservative assumptions (4.5 bps taker fees both ways, immediate PnL realization), and an explicit roadmap for adding slippage and latency models only after the selection methodology proves out.

---

## How it works

1. **`scorer/`** — every 6 hours, pulls 90 days of fills for each seed wallet, computes Sharpe / drawdown / win-rate / profit-factor / composite score, and promotes the top N to an "active" watchlist. Posts a leaderboard to Discord on every refresh.
2. **`paper/`** — subscribes to the active wallets over Hyperliquid's WebSocket and mirrors their fills into an in-memory paper book with full risk filters. Every paper fill posts to Discord.

```
       ┌────────────────────┐
       │ data/seed_wallets  │  ← curated from on-chain research
       └─────────┬──────────┘
                 │ scorer/run.py (every 6h)
                 ▼
       ┌────────────────────┐
       │ wallet_scores.json │  ← ranked, with Sharpe / DD / score
       │ active_wallets.json│  ← top N promoted
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

If a source wallet puts 8% of their equity into ETH, the paper book puts ~8% of paper equity into ETH (capped at `PAPER_MAX_POSITION_PCT`). Dollar sizes are **not** mirrored 1:1 — that would be undercapitalized for whales and overcapitalized for small wallets. Leverage is mirrored up to `PAPER_MAX_LEVERAGE`.

Closes realize PnL immediately at the source fill price, assuming a 4.5 bps taker fee both ways. This is intentionally conservative; real fills incur slippage and reaction-time delay, which a later iteration adds as a configurable model once paper data justifies it.

---

## Configuration reference (`.env`)

| Var | Default | Meaning |
|---|---|---|
| `DISCORD_WEBHOOK_URL` | — | Channel for alerts |
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

## What's deliberately not here

- **Live execution / signing** — add only after paper proves the wallet selection.
- **Database** — Discord + JSON logs only, per the project spec.
- **Web dashboard** — use the `scripts/show_*` CLIs.
- **Other venues** — Hyperliquid-only for v1.

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

> **Note:** the committed `data/seed_wallets.json` is a sample. The production wallet set is a research output maintained separately and is not required to review the methodology.

---

## Disclaimer

This is research / educational infrastructure. Hyperliquid perps are highly leveraged and can liquidate. Copy trading is not a license to print money — past performance of any wallet does not guarantee future returns. Do not deploy real capital based on paper results alone.

---

## License

This project is **source-available for portfolio and educational review only** — it is not open source. No rights are granted to copy, redistribute, deploy, run, or commercially exploit this software. The production wallet-selection research and live execution layer are intentionally not included, so the code as published will not run as-is. See [`LICENSE`](LICENSE) for the full terms.
