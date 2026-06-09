"""Paper trader: subscribe to active wallets, mirror their fills into a paper book.

Notes on Hyperliquid fill semantics (from userFills WS channel):
  Each fill has: coin, px, sz, side (A=sell/B=buy), startPosition, dir, closedPnl, fee.
  We classify each fill as Open or Close by inspecting `dir`:
    "Open Long" / "Open Short" -> open
    "Close Long" / "Close Short" -> close
    "Long > Short" / "Short > Long" -> reverse (close + open)
"""
from __future__ import annotations
import asyncio
import time
from datetime import datetime, timezone
from loguru import logger

from common.config import SETTINGS
from common.logging_setup import setup
from common.hl_client import HLClient, now_ms
from common.discord import send as discord_send, embed, COLOR_GREEN, COLOR_RED, COLOR_YELLOW
from common import wallet_store
from .book import Book, Position, log_fill
from .risk import evaluate_open


# --- Hyperliquid taker fee assumption for paper: 0.045% (4.5 bps) ---
PAPER_TAKER_FEE_BPS = 4.5


class PaperEngine:
    def __init__(self) -> None:
        self.client = HLClient()
        self.book = Book.load_or_new()
        self.marks: dict[str, float] = {}
        self.funding_cache: dict[str, tuple[float, float]] = {}  # coin -> (apr_pct, ts)
        self.source_equity: dict[str, float] = {}  # wallet -> equity USD (from clearinghouseState)

    async def refresh_marks(self) -> None:
        try:
            mids = await self.client.all_mids()
            self.marks = {k: float(v) for k, v in mids.items()}
        except Exception as e:
            logger.warning(f"refresh_marks failed: {e}")

    async def refresh_source_equity(self, addresses: list[str]) -> None:
        for a in addresses:
            try:
                st = await self.client.user_state(a)
                ms = st.get("marginSummary", {})
                self.source_equity[a] = float(ms.get("accountValue", 0))
            except Exception as e:
                logger.warning(f"user_state failed for {a}: {e}")

    async def get_funding_apr(self, coin: str) -> float:
        now = time.time()
        cached = self.funding_cache.get(coin)
        if cached and now - cached[1] < 600:
            return cached[0]
        try:
            hist = await self.client.funding_history(coin, int((now - 3600) * 1000))
            if hist:
                latest = hist[-1]
                hr_rate = float(latest.get("fundingRate", 0))
                apr = hr_rate * 24 * 365 * 100  # HL funding is hourly
                self.funding_cache[coin] = (apr, now)
                return apr
        except Exception as e:
            logger.debug(f"funding_history({coin}) failed: {e}")
        return 0.0

    # -----------------------------------------------------------------
    async def handle_fill(self, source_wallet: str, fill: dict) -> None:
        coin = fill.get("coin")
        if not coin:
            return
        px = float(fill.get("px", 0))
        sz = float(fill.get("sz", 0))
        direction = (fill.get("dir") or "").lower()
        time_ms = int(fill.get("time", now_ms()))
        fill_iso = datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc).isoformat()

        key = f"{source_wallet}:{coin}"
        existing = self.book.positions.get(key)

        log_fill({
            "source_wallet": source_wallet, "coin": coin, "px": px, "sz": sz,
            "dir": direction, "time": fill_iso,
        })

        # --- CLOSE / REVERSE ---
        if existing and ("close" in direction or ">" in direction):
            # Close our paper position at the source's fill price (best-effort sim).
            pnl = existing.unrealized(px)
            fee = abs(existing.size) * px * PAPER_TAKER_FEE_BPS / 10000
            self.book.realized_pnl += pnl
            self.book.fees_paid += fee
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            self.book.daily_pnl[today] = self.book.daily_pnl.get(today, 0.0) + pnl - fee
            color = COLOR_GREEN if pnl > 0 else COLOR_RED
            await discord_send(embeds=[embed(
                f"📕 CLOSE {existing.side} {coin}  PnL ${pnl:+,.2f}",
                f"source: `{source_wallet[:10]}…`\nentry ${existing.entry_px:.4f} → exit ${px:.4f}\n"
                f"fee ${fee:.2f} | realized total ${self.book.realized_pnl:+,.2f}\n"
                f"equity ${self.book.equity:,.2f}",
                color=color,
            )])
            del self.book.positions[key]
            self.book.save()

            # If reversal, fall through to open the opposite side after close
            if ">" not in direction:
                return

        # --- OPEN ---
        if "open" in direction or ">" in direction or not existing:
            side = "LONG" if ("long" in direction or fill.get("side") == "B") else "SHORT"
            await self.refresh_marks()
            mark = self.marks.get(coin, px)
            funding = await self.get_funding_apr(coin)

            source_eq = self.source_equity.get(source_wallet, 0.0)
            source_notional = abs(sz) * px

            # For leverage, infer from source clearinghouseState if available — fallback 1.0
            try:
                st = await self.client.user_state(source_wallet)
                ap = next((p for p in st.get("assetPositions", [])
                           if p.get("position", {}).get("coin") == coin), None)
                if ap:
                    src_lev = float(ap.get("position", {}).get("leverage", {}).get("value", 1))
                else:
                    src_lev = 1.0
            except Exception:
                src_lev = 1.0

            decision = evaluate_open(
                self.book, coin=coin, source_wallet=source_wallet,
                source_notional_usd=source_notional,
                source_equity_usd=source_eq,
                source_leverage=src_lev,
                funding_apr_pct=abs(funding),
                marks=self.marks,
            )
            if not decision.allow:
                logger.info(f"SKIP open {coin} from {source_wallet[:10]}: {decision.reason}")
                await discord_send(embeds=[embed(
                    f"⏸️  SKIP {side} {coin}",
                    f"reason: `{decision.reason}`\nsource: `{source_wallet[:10]}…`",
                    color=COLOR_YELLOW,
                )])
                return

            our_size_units = decision.size_usd / mark
            fee = decision.size_usd * PAPER_TAKER_FEE_BPS / 10000
            self.book.fees_paid += fee
            self.book.positions[key] = Position(
                coin=coin, source_wallet=source_wallet, side=side,
                size=our_size_units, entry_px=mark, leverage=decision.leverage,
                opened_at=fill_iso, notional_usd=decision.size_usd,
            )
            self.book.save()
            await discord_send(embeds=[embed(
                f"📗 OPEN {side} {coin}  ${decision.size_usd:,.0f} @ ${mark:.4f}",
                f"source: `{source_wallet[:10]}…`\nleverage {decision.leverage:.1f}x | "
                f"funding {funding:+.1f}% APR\nequity ${self.book.equity:,.2f}",
                color=COLOR_GREEN if side == "LONG" else COLOR_RED,
            )])

    # -----------------------------------------------------------------
    async def run(self) -> None:
        addresses = wallet_store.load_active()
        if not addresses:
            logger.error("No active wallets — run the scorer first (data/active_wallets.json missing)")
            return
        logger.info(f"Subscribing to {len(addresses)} wallets")
        await self.refresh_marks()
        await self.refresh_source_equity(addresses)
        await discord_send(embeds=[embed(
            "🚀 Paper trader online",
            f"Tracking {len(addresses)} wallets\n"
            f"Equity: ${self.book.equity:,.2f}\n"
            f"Open positions: {len(self.book.positions)}",
        )])

        async def handler(addr: str, msg: dict) -> None:
            data = msg.get("data", {})
            fills = data.get("fills") or data.get("Fills") or []
            for f in fills:
                try:
                    await self.handle_fill(addr, f)
                except Exception as e:
                    logger.exception(f"handle_fill error: {e}")

        # Periodic refresh of marks + source equity
        async def refresher() -> None:
            while True:
                await asyncio.sleep(60)
                await self.refresh_marks()
                if int(time.time()) % 600 < 60:
                    await self.refresh_source_equity(addresses)

        ref_task = asyncio.create_task(refresher())
        try:
            await self.client.subscribe_user_events(addresses, handler)
        finally:
            ref_task.cancel()
            await self.client.close()


async def main() -> None:
    setup("paper")
    engine = PaperEngine()
    await engine.run()


if __name__ == "__main__":
    asyncio.run(main())
