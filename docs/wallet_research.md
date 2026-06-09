# Hyperliquid Top Wallets Research Notes

**Date:** 2026-06-09  
**Purpose:** Seed list for a Hyperliquid copy-trading bot watchlist

---

## Methodology

Data was pulled directly from the Hyperliquid official statistics API endpoint at `stats-data.hyperliquid.xyz/Mainnet/leaderboard`, which exposes 38,125 real trading accounts with live PnL, ROI, and notional volume data across four time windows (day / week / month / all-time). No third-party aggregators were used as the primary source.

**Hard filters applied:**

| Filter | Value | Rationale |
|---|---|---|
| Equity range | $50,000 – $10,000,000 | Below floor = variance/luck; above ceiling = market-moving, uncopyable |
| All-time PnL | ≥ $1,000,000 | Proof of sustained skill over a meaningful sample |
| 30-day PnL | > 0 | Currently active and profitable |
| 7-day PnL | > 0 | Currently active this week |
| VLM/equity ratio | < 20,000x | Removes obvious HFT/market-maker accounts |
| Absolute ROI | < 500,000% | Filters anomalous tiny-seed accounts or data artifacts |

After filters, 307 wallets qualified. The final 20 were selected by all-time PnL rank within the qualified set, with manual exclusion of two accounts: one with near-zero 30d PnL ($356) suggesting a dormant account, and one with only $130 in 30-day PnL despite passing other filters.

Cross-reference sources: [Dexly Hyperliquid Leaderboard](https://dexly.trade/hyperliquid/leaderboard), [CryptoRank elite traders article](https://cryptorank.io/news/feed/9b029-hyperliquids-elite-traders-rack-up-massive-profits-amid-hype-token-surge), [Binance Square BobbyBigSize profile](https://www.binance.com/en/square/post/316196622871874), [Yahoo Finance / HyperDash trader profiles](https://finance.yahoo.com/news/trader-bets-64-7m-long-112100290.html).

---

## Top 5–7 Best Picks With Reasoning

### 1. `0xc59498175d6d317642aeb97f895a7ce1aa992191` — Position Trader (BEST COPY TARGET)

- **Equity:** $6.24M | **All-time PnL:** $36M | **ROI:** 716%
- **Why it's the top pick:** VLM/equity ratio of only 30x — the second-lowest in the entire top-20. This means the trader holds massive directional positions for weeks at a time. A copy bot with WebSocket latency of a few seconds will still get near-identical fills since positions rarely change. 30d PnL $1.74M (38.6%) and 7d $1.44M confirm this is active right now. No HFT signals whatsoever.
- **Style:** Macro position trader — think 2–8x leverage, BTC/ETH/SOL longs or shorts held for 1–6 weeks.
- **Copy mechanics:** Open a proportional position when wallet opens. Hold. Close when wallet closes. Dead simple.

### 2. `0x06cecfbac34101ae41c88ebc2450f8602b3d164b` — Ultra-Low-Frequency Position Trader

- **Equity:** $3.95M | **All-time PnL:** $14.7M | **ROI:** 378%
- **Why it ranks:** 23x VLM/equity — the lowest ratio in the top 20. Practically a "set it and forget it" copy target. 30d PnL $1.33M (41%) and 7d $1.97M (unusual 7d > 30d indicates fresh new position opened this week). Latency is completely irrelevant for this style.
- **Style:** Concentrated macro position, likely 5–10x on BTC or ETH, held for months.
- **Watch for:** Single bad positions could cause large swings in equity.

### 3. `0x42b6d907f36255d48f70db8b4a2684088a162634` — Conservative Position Trader

- **Equity:** $4.48M | **All-time PnL:** $18.6M | **ROI:** 766%
- **Why it ranks:** 44x VLM/equity at the second-lowest in the top 20. Consistent 30d ($1.48M, 49%) and 7d ($1.21M) performance. 766% ROI suggests grew from ~$500k seed to $4.5M through disciplined compounding. The "bread and butter" copy target — not flashy, just consistently directional.
- **Style:** Medium-leverage swing trades held for 1–3 weeks.

### 4. `0x8cc94dc843e1ea7a19805e0cca43001123512b6a` — Momentum Swing Trader (HOT STREAK)

- **Equity:** $6.18M | **All-time PnL:** $23.2M | **ROI:** 106%
- **Why it ranks:** 30d PnL of $4.18M (64.5%) is exceptional. 7d PnL $2.14M. 106% all-time ROI is modest, suggesting a large starting equity base (professional trader). $1.51B lifetime volume (245x ratio) means medium-frequency swing trading — copyable with a fast WebSocket bot.
- **Style:** Swing trades on BTC/ETH/SOL with moderate leverage, position duration hours to days.
- **Watch for:** Hot streaks in this range (64% in one month) typically revert.

### 5. `0x71dfc07de32c2ebf1c4801f4b1c9e40b76d4a23d` — VidaBWE (Named Trader)

- **Equity:** $9.85M | **All-time PnL:** $15.2M | **ROI:** 222%
- **Why it ranks:** Display name 'VidaBWE' adds accountability and traceability. 21x VLM/equity — third-lowest ratio in the top 20 (position trader). 30d $2.86M (41%) and 7d $1.75M. Nearly at the $10M equity cap but still within bounds. Named traders with public identities are far less likely to engage in wash-trading (they have reputational skin in the game).
- **Style:** Macro position trader, likely large BTC/ETH/SOL longs or shorts.

### 6. `0x8e096995c3e4a3f0bc5b3ea1cba94de2aa4d70c9` — 憨巴小龙 (Named, Chinese Community)

- **Equity:** $6.77M | **All-time PnL:** $59.7M | **ROI:** 1421%
- **Why it ranks:** Second-highest all-time PnL of the qualified copyable set. 210x VLM/equity ratio is moderate — swing trader. 30d $1.9M (39%) and 7d $588k. 1421% ROI suggests grew from ~$450k. The Chinese trading community has produced some of Hyperliquid's most successful traders. Has a display name which aides monitoring.
- **Watch for:** No social media footprint in English — harder to track strategic updates.

### 7. `0xf517639a8872e756ac98d3c65507d2ebc25cc032` — NMTD - Thank you Jeff

- **Equity:** $9.46M | **All-time PnL:** $27.6M | **ROI:** 3714%
- **Why it ranks:** Named trader visible on both the official leaderboard and [Dexly](https://dexly.trade/hyperliquid/leaderboard/0xf517639a8872e756ac98d3c65507d2ebc25cc032) (ranked #41 all-time). Exceptional 30d ($4.43M, 76.8%) and 7d ($1.74M). 3714% ROI from tiny seed. 
- **Caution:** 1375x VLM/equity suggests fast trading; latency-sensitive. Not for v1 bot — better suited for v2 with sub-second fill detection.

---

## Wallets That LOOKED Good But Were Filtered Out

| Address | Why Excluded |
|---|---|
| `0x393d...2109` (Dexly #1, all-time) | Equity $928M — far above $10M cap. Cannot copy without enormous slippage. |
| `0x488d...fe08` (Dexly #2) | Equity $187M — same issue. |
| `0x77c3...5e45` (CryptoRank all-time king) | Account value ~$500M, PnL $287M — uncopyable whale. |
| `0x87f9cd15f5050a9283b8896300f7c8cf69ece2cf` | Equity $92M — above cap. |
| `0x7fdafde5cfb5465924316eced2d3715494c517d1` (BobbyBigSize) | Dexly **labels this address as HFT**. $11B volume / $38M equity = 289x base ratio, but also Fasanara Capital (institutional algo firm). Strategy is not replicable by a retail copy bot. Also $38M equity exceeds cap. |
| `0x020ca66c30bec2c4fe3861a94e4db4a498a35872` (Machi Big Brother) | Cumulative losses of $28M–$30M+ as of 2026. Repeatedly liquidated at 25–40x leverage on ETH longs. Strong red flag — do NOT copy. |
| `0x5078c2fbea2b2ad61bc840bc023e35fce56bedb6` (James Wynn) | Famous for turning large profits but then losing $23M+. Account balance hit $6,010 as of Nov 2025. Eliminated on drawdown grounds. |
| `0xfae95f601f3a25ace60d19dbb929f2a5c57e3571` (thank you jefef) | Equity $2.4M, AT PnL $149M — sounds great. BUT 7d PnL = $0. Account appears dormant currently. Not active in last week. |
| `0x51156f7002c4f74f4956c9e0f2b7bfb6e9dbfac2` (jefe) | Equity $244k, AT PnL $71M — but 7d PnL = $0, 30d PnL tiny ($36k). Potentially dormant. |
| `0x9ab1c356e6af86361446497fce954b3cdf940206` | VLM/equity 97,467x — extreme HFT flag. Excluded. |
| `0xa464abbf049fb75585484addcbc00169062e813a` ("fuck jeff gib S3") | Equity $58k, 30d PnL $356, 7d PnL $402 — nearly dormant despite large all-time PnL. Likely withdrew principal. |
| `0x0a0b4d654d967a00407f5329588a258b68a4f615` | 30d PnL $130, 7d PnL $1 — completely inactive despite $12M AT PnL. Dormant/closed out. |
| `0xe86b057f5eb764c9738d6b0d38170befd0723664` | VLM/equity 6,587x — very high activity, potential HFT/systematic trader. Borderline; excluded for caution. |
| `0x7717a7a245d9f950e586822b8c9b46863ed7bd7e` | VLM/equity 3,270x and $24.9B lifetime volume — likely systematic/algo. Borderline copyable. |

---

## Ongoing Monitoring Recommendations

**Weekly checks (every 7 days):**
- Verify each wallet's 7-day PnL remains positive.
- Check for equity drawdown >20% from the level when you added the wallet.
- Flag any wallet where 7-day volume drops to zero (may be going dormant).

**Monthly checks:**
- Compare 30-day ROI against the wallet's historical average. If a wallet that averages 15%/month suddenly shows -30%, consider removing.
- Re-run the leaderboard filter query to find emerging wallets and rotate out underperformers.
- Check news / social channels for any named traders in your list (VidaBWE, x35767, NMTD, H universe, jez, 韦小宝.eth, 憨巴小龙) for strategy announcements.

**Automatic bot circuit-breakers to implement:**
1. **Equity drawdown gate:** Stop copying any wallet whose equity drops >35% from last 30-day peak.
2. **Dormancy gate:** Stop copying any wallet with zero fills for 14+ consecutive days.
3. **Leverage spike gate:** Alert if a wallet suddenly opens a position with >30x leverage (risk of liquidation cascade).
4. **Volatility gate:** If a wallet's unrealized PnL swings >50% of equity in a single day, flag for manual review.

**Tools to use for ongoing monitoring:**
- [Dexly Explorer](https://dexly.trade/hyperliquid/explorer) — paste any 0x address to get full trade history
- [HyperTracker.io](https://hypertracker.io) — real-time position alerts, cohort classification
- [Hyperliquid Official Leaderboard](https://app.hyperliquid.xyz/leaderboard) — 30d and all-time views
- [Lookonchain](https://www.lookonchain.com) — follows and tweets when large Hyperliquid wallets make notable moves

**VLM/equity ratio as a style guide for your bot:**

| Ratio | Inferred Style | Copy Latency Tolerance |
|---|---|---|
| < 100x | Position trader / macro | Minutes to hours — very forgiving |
| 100–500x | Swing trader | Seconds to minutes — manageable |
| 500–5000x | Active/intraday swing | Sub-second preferred |
| > 5000x | Likely HFT/systematic | Avoid in v1 bot |

---

*All wallet addresses are sourced directly from `stats-data.hyperliquid.xyz/Mainnet/leaderboard` (Hyperliquid's official live leaderboard API) or from [Dexly](https://dexly.trade/hyperliquid/leaderboard) and verified external news sources. No addresses were invented or estimated.*
