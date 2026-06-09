"""Continuous wallet scorer.

Loop:
  every SCORER_REFRESH_MINUTES:
    for each seed wallet:
      fetch fills (lookback window)
      compute metrics
    rank by composite_score
    write data/wallet_scores.json
    promote top N to data/active_wallets.json (consumed by paper trader)
    post a leaderboard summary to Discord
"""
from __future__ import annotations
import asyncio
import time
from datetime import datetime, timezone
from loguru import logger

from common.config import SETTINGS
from common.logging_setup import setup
from common.hl_client import HLClient, now_ms
from common.discord import send as discord_send, embed, COLOR_BLUE, COLOR_YELLOW
from common import wallet_store
from .metrics import compute, WalletMetrics


TOP_N_ACTIVE = 10  # how many wallets to promote into the paper-trade watchlist


async def score_once(client: HLClient) -> list[WalletMetrics]:
    seed = wallet_store.load_seed()
    if not seed:
        logger.warning("No seed wallets in data/seed_wallets.json — nothing to score")
        return []
    start_ms = now_ms() - SETTINGS.scorer_lookback_days * 86400 * 1000
    end_ms = now_ms()

    results: list[WalletMetrics] = []
    for w in seed:
        addr = w["address"]
        alias = w.get("alias")
        try:
            fills = await client.user_fills_by_time(addr, start_ms, end_ms)
        except Exception as e:
            logger.warning(f"fetch fills failed for {addr}: {e}")
            continue
        m = compute(addr, alias, fills, SETTINGS.scorer_lookback_days)
        results.append(m)
        logger.info(
            f"{alias or addr[:10]}: pnl=${m.net_pnl_usd:,.0f} "
            f"sharpe={m.sharpe_annualized:.2f} dd={m.max_drawdown_pct:.1f}% "
            f"trades={m.n_closing_fills} score={m.composite_score:.1f}"
        )

    # Filter wallets with too few trades to score reliably
    eligible = [m for m in results if m.n_closing_fills >= SETTINGS.scorer_min_trades]
    eligible.sort(key=lambda x: x.composite_score, reverse=True)

    wallet_store.save_scores([m.to_row() for m in results])
    active = [m.address for m in eligible[:TOP_N_ACTIVE]]
    wallet_store.save_active(active)
    return eligible


def _leaderboard_embed(ranked: list[WalletMetrics]) -> dict:
    if not ranked:
        return embed("Wallet Scorer", "No eligible wallets after filtering.",
                     color=COLOR_YELLOW)
    lines = ["```",
             f"{'#':>2}  {'alias':<14}  {'score':>5}  {'pnl$':>10}  {'sharpe':>6}  {'dd%':>5}  {'trades':>6}"]
    for i, m in enumerate(ranked[:15], 1):
        alias = (m.alias or m.address[:10])[:14]
        lines.append(
            f"{i:>2}  {alias:<14}  {m.composite_score:>5.1f}  "
            f"{m.net_pnl_usd:>10,.0f}  {m.sharpe_annualized:>6.2f}  "
            f"{m.max_drawdown_pct:>5.1f}  {m.n_closing_fills:>6}"
        )
    lines.append("```")
    return embed(
        f"Wallet leaderboard — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%MZ')}",
        "\n".join(lines),
        color=COLOR_BLUE,
        fields=[{"name": "Active (paper-trade watchlist)",
                 "value": str(len(ranked[:TOP_N_ACTIVE])),
                 "inline": True},
                {"name": "Lookback",
                 "value": f"{SETTINGS.scorer_lookback_days}d",
                 "inline": True}],
    )


async def main() -> None:
    setup("scorer")
    logger.info(f"Scorer starting — refresh every {SETTINGS.scorer_refresh_minutes}min")
    client = HLClient()
    try:
        while True:
            t0 = time.time()
            try:
                ranked = await score_once(client)
                await discord_send(embeds=[_leaderboard_embed(ranked)])
            except Exception as e:
                logger.exception(f"score_once failed: {e}")
            elapsed = time.time() - t0
            sleep_s = max(60, SETTINGS.scorer_refresh_minutes * 60 - int(elapsed))
            logger.info(f"sleeping {sleep_s}s")
            await asyncio.sleep(sleep_s)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
