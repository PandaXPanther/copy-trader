"""Discord webhook notifier. Non-fatal on failure."""
from __future__ import annotations
import httpx
from loguru import logger
from .config import SETTINGS


COLOR_GREEN = 0x2ECC71
COLOR_RED = 0xE74C3C
COLOR_BLUE = 0x3498DB
COLOR_YELLOW = 0xF1C40F


async def send(content: str = "", *, embeds: list[dict] | None = None) -> None:
    if not SETTINGS.discord_webhook or "REPLACE_ME" in SETTINGS.discord_webhook:
        logger.debug("Discord webhook not configured; skipping notify")
        return
    payload: dict = {}
    if content:
        payload["content"] = content
    if embeds:
        payload["embeds"] = embeds
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.post(SETTINGS.discord_webhook, json=payload)
            if r.status_code >= 400:
                logger.warning(f"Discord webhook {r.status_code}: {r.text[:200]}")
    except Exception as e:
        logger.warning(f"Discord send failed: {e}")


def embed(title: str, description: str = "", *, color: int = COLOR_BLUE,
          fields: list[dict] | None = None) -> dict:
    e = {"title": title[:256], "description": description[:4000], "color": color}
    if fields:
        e["fields"] = fields[:25]
    return e
