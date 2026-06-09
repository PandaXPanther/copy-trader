# copy-trader — Hyperliquid wallet scorer + paper trader

A two-stage Hyperliquid copy-trading research stack:

1. **`scorer/`** — every 6h, pulls 90 days of fills for each seed wallet, computes Sharpe / drawdown / win-rate / profit-factor / composite score, and promotes the top N to an "active" watchlist. Posts a leaderboard to Discord on every refresh.
2. **`paper/`** — subscribes to the active wallets over Hyperliquid's WebSocket and mirrors their fills into an in-memory paper book with full risk filters (per-position cap, per-wallet cap, leverage cap, daily-loss circuit breaker, funding-rate filter). Every paper fill posts to Discord.

**No live trading code. No private keys. Read-only.**
Step 3 (live execution) is intentionally not included until paper trading proves out the wallet selection over 4–8 weeks.

---

## Architecture

```
       ┌────────────────────┐
       │ data/seed_wallets  │  ← from deep research (15-30 wallets)
       └─────────┬──────────┘
                 │ scorer/run.py (every 6h)
                 ▼
       ┌────────────────────┐
       │ wallet_scores.json │  ← ranked, with Sharpe/DD/score
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

## Components

| Path | What it does |
|---|---|
| `common/hl_client.py` | Async REST + WS client for Hyperliquid public endpoints |
| `common/discord.py` | Webhook notifier |
| `common/wallet_store.py` | Read/write seed/scores/active wallet files |
| `scorer/metrics.py` | Per-wallet metric computation (Sharpe, drawdown, PF, composite) |
| `scorer/run.py` | Long-running scorer loop |
| `paper/book.py` | In-memory portfolio, persisted to JSON |
| `paper/risk.py` | Pre-trade risk checks + sizing |
| `paper/run.py` | WS subscriber that mirrors fills into the book |
| `paper/summary.py` | Daily Discord summary |
| `scripts/deploy.sh` | One-shot VPS installer (systemd) |
| `scripts/import_seed.py` | Validate + load a research seed file |
| `scripts/show_scores.py` | CLI: pretty-print latest scores |
| `scripts/show_book.py` | CLI: pretty-print current paper book |

---

## Quick start (any machine)

```bash
git clone git@github.com:PandaXPanther/copy-trader.git
cd copy-trader
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit DISCORD_WEBHOOK_URL etc.

# Seed wallets from deep research (one-time):
python -m scripts.import_seed path/to/seed_wallets.json

# Run scorer (long-running, refreshes every SCORER_REFRESH_MINUTES):
python -m scorer.run

# In another shell, once scorer has produced data/active_wallets.json:
python -m paper.run

# Anytime:
python -m scripts.show_scores
python -m scripts.show_book
python -m paper.summary
```

---

## Deploying to your VPS via OpenClaw

These are the exact steps an OpenClaw agent (or you) should run on the VPS. They assume the VPS is Ubuntu/Debian, you have sudo, and SSH access is already configured.

### Step 1 — Clone the private repo

The repo is private. The cleanest, most repeatable auth for a headless server is a **GitHub deploy key** (read-only, repo-scoped, no PAT rotation hassle).

```bash
# On the VPS — generate a key for this server (one time):
ssh-keygen -t ed25519 -C "vps-copy-trader" -f ~/.ssh/copy_trader_deploy -N ""
cat ~/.ssh/copy_trader_deploy.pub
```

Then in GitHub: **PandaXPanther/copy-trader → Settings → Deploy keys → Add deploy key** → paste the `.pub` content. Leave "Allow write access" UNCHECKED.

Configure SSH to use that key for this repo:

```bash
cat >> ~/.ssh/config <<'EOF'
Host github-copytrader
  HostName github.com
  User git
  IdentityFile ~/.ssh/copy_trader_deploy
  IdentitiesOnly yes
EOF
chmod 600 ~/.ssh/config
```

Clone:

```bash
sudo mkdir -p /opt/copy-trader
sudo chown $USER:$USER /opt/copy-trader
git clone git@github-copytrader:PandaXPanther/copy-trader.git /opt/copy-trader
cd /opt/copy-trader
```

### Step 2 — Install & configure

```bash
sudo bash scripts/deploy.sh   # installs venv, deps, systemd units
nano .env                     # set DISCORD_WEBHOOK_URL and any overrides
```

### Step 3 — Load the wallet seed file

The seed file (`seed_wallets.json`) comes from the research run. Either:

**Option A — copy it directly:**
```bash
cp /path/to/seed_wallets.json /opt/copy-trader/data/seed_wallets.json
```

**Option B — pull from GitHub** (if you commit it to a private branch):
```bash
git fetch && git checkout origin/main -- data/seed_wallets.json
```

**Option C — let the scorer fail-soft and seed manually:**
```bash
.venv/bin/python -m scripts.import_seed /tmp/seed_wallets.json
```

### Step 4 — Start services

```bash
sudo systemctl enable --now copytrader-scorer
# Wait one cycle (a few minutes) so active_wallets.json is populated:
sudo journalctl -u copytrader-scorer -f
# Then:
sudo systemctl enable --now copytrader-paper
```

### Step 5 — Verify

```bash
sudo systemctl status copytrader-scorer copytrader-paper
sudo journalctl -u copytrader-paper -f --since "5 minutes ago"

# Inspect state:
cd /opt/copy-trader
.venv/bin/python -m scripts.show_scores
.venv/bin/python -m scripts.show_book
```

You should see a "Paper trader online" embed in your Discord channel within ~30 seconds.

### Updating later

```bash
cd /opt/copy-trader
git pull
.venv/bin/pip install -r requirements.txt   # if deps changed
sudo systemctl restart copytrader-scorer copytrader-paper
```

---

## OpenClaw automation hook

If your OpenClaw agent already has SSH access to the VPS, this is the minimal command sequence it can run end-to-end (after the one-time deploy-key setup above):

```bash
ssh vps-host '
  set -e
  cd /opt/copy-trader
  git pull --ff-only
  .venv/bin/pip install -q -r requirements.txt
  sudo systemctl restart copytrader-scorer copytrader-paper
  sudo journalctl -u copytrader-paper -n 20 --no-pager
'
```

For first-time deploy, OpenClaw can run `scripts/deploy.sh` after cloning. Recommended Discord webhook channel: a private channel only you can see, since fills reveal which wallets you copy.

---

## Configuration reference (.env)

| Var | Default | Meaning |
|---|---|---|
| `DISCORD_WEBHOOK_URL` | — | Channel for alerts |
| `PAPER_STARTING_EQUITY_USD` | 10000 | Simulated starting capital |
| `PAPER_MAX_POSITION_PCT` | 10 | Max % of equity in any one copy |
| `PAPER_DAILY_LOSS_LIMIT_PCT` | 5 | Halts copies for the day if breached |
| `PAPER_MAX_LEVERAGE` | 10 | Caps source leverage you'll replicate |
| `PAPER_MAX_FUNDING_APR_PCT` | 200 | Skip copies when funding > this APR % |
| `PAPER_PER_WALLET_CAP_PCT` | 25 | Max % of equity in positions from any single wallet |
| `SCORER_LOOKBACK_DAYS` | 90 | Fill history window |
| `SCORER_MIN_TRADES` | 20 | Min closing fills to rank a wallet |
| `SCORER_REFRESH_MINUTES` | 360 | Re-score cadence |

---

## How sizing works (paper)

For each `Open` fill from a source wallet:

```
pct_of_source_equity = source_notional / source_clearinghouse_equity
our_notional         = pct_of_source_equity * our_paper_equity
our_notional         = min(our_notional, MAX_POSITION_PCT * equity)
our_notional         = min(our_notional, per_wallet_capacity_remaining)
size_units           = our_notional / current_mark_price
```

This means: if the source wallet puts 8% of their equity into ETH, we put ~8% of our paper equity into ETH (capped at `PAPER_MAX_POSITION_PCT`). We do NOT 1:1 the dollar size — that would be undercapitalized for whales and overcapitalized for small wallets.

Leverage is mirrored up to `PAPER_MAX_LEVERAGE`.

## Closes

When the source closes (or reverses) on a coin we hold for that wallet, we close at their fill price. We assume taker fee of 4.5 bps both ways. PnL is realized immediately.

This is intentionally conservative — real fills will have slippage and reaction-time delay. Once you've run paper for 2–4 weeks, the next iteration adds a configurable slippage model and latency simulator.

## What's deliberately NOT here

- **Live execution / signing.** Add only after paper proves the wallet selection.
- **Database.** Discord + JSON logs only, per the project spec.
- **Web dashboard.** Use `scripts/show_*` CLIs.
- **GMX or other venues.** Hyperliquid-only for v1.

## Disclaimer

This is research / educational infrastructure. Hyperliquid perps are highly leveraged and can liquidate. Copy trading is not a license to print money — past performance of any wallet does not guarantee future returns. Do not deploy real capital based on paper results alone.
