"""Thin wrapper around Hyperliquid public REST + WebSocket.

We deliberately avoid the official SDK's signing layer (we never trade live here);
all calls are read-only. See https://hyperliquid.gitbook.io/hyperliquid-docs.
"""
from __future__ import annotations
import asyncio
import json
import time
from typing import Any, AsyncIterator, Callable
import httpx
import websockets
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import SETTINGS


class HLClient:
    def __init__(self) -> None:
        self.base = SETTINGS.hl_api_base.rstrip("/")
        self.ws_url = SETTINGS.hl_ws_url
        self._http = httpx.AsyncClient(timeout=20.0)

    # ---- REST ----
    @retry(stop=stop_after_attempt(4), wait=wait_exponential(min=1, max=10))
    async def _info(self, payload: dict) -> Any:
        r = await self._http.post(f"{self.base}/info", json=payload)
        r.raise_for_status()
        return r.json()

    async def user_fills(self, address: str) -> list[dict]:
        """Most recent fills (up to 2000)."""
        return await self._info({"type": "userFills", "user": address})

    async def user_fills_by_time(self, address: str, start_ms: int, end_ms: int) -> list[dict]:
        return await self._info({
            "type": "userFillsByTime",
            "user": address,
            "startTime": start_ms,
            "endTime": end_ms,
        })

    async def user_state(self, address: str) -> dict:
        """Account margin summary + open positions."""
        return await self._info({"type": "clearinghouseState", "user": address})

    async def meta(self) -> dict:
        """Universe + asset metadata."""
        return await self._info({"type": "meta"})

    async def all_mids(self) -> dict[str, str]:
        return await self._info({"type": "allMids"})

    async def funding_history(self, coin: str, start_ms: int) -> list[dict]:
        return await self._info({"type": "fundingHistory", "coin": coin, "startTime": start_ms})

    async def close(self) -> None:
        await self._http.aclose()

    # ---- WebSocket ----
    async def subscribe_user_events(
        self,
        addresses: list[str],
        on_event: Callable[[str, dict], Any],
    ) -> None:
        """Subscribe to userEvents for each address; call on_event(address, event).

        Auto-reconnects with backoff. on_event may be sync or async.
        """
        backoff = 1.0
        while True:
            try:
                async with websockets.connect(self.ws_url, ping_interval=20) as ws:
                    for addr in addresses:
                        await ws.send(json.dumps({
                            "method": "subscribe",
                            "subscription": {"type": "userEvents", "user": addr},
                        }))
                        # Also subscribe to userFills for richer fill metadata.
                        await ws.send(json.dumps({
                            "method": "subscribe",
                            "subscription": {"type": "userFills", "user": addr},
                        }))
                    logger.info(f"WS subscribed to {len(addresses)} addresses")
                    backoff = 1.0
                    async for raw in ws:
                        try:
                            msg = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        addr = (msg.get("data") or {}).get("user")
                        ch = msg.get("channel")
                        if ch in ("userEvents", "userFills") and addr:
                            res = on_event(addr, msg)
                            if asyncio.iscoroutine(res):
                                await res
            except Exception as e:
                logger.warning(f"WS error: {e}; reconnecting in {backoff:.1f}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)


def now_ms() -> int:
    return int(time.time() * 1000)
