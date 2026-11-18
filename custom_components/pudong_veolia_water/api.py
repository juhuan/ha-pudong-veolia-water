"""Async client for the Pudong Veolia bill endpoint."""

from __future__ import annotations

import json
from datetime import datetime

from aiohttp import ClientSession, ClientError

from .const import API_URL, API_USER_AGENT


class PudongVeoliaApiError(Exception):
    """Raised when the upstream endpoint fails or returns bad data."""


async def async_fetch_bills(session: ClientSession, account_id: str) -> list[dict]:
    """Fetch bills for one 销根号 (customer account id).

    The endpoint returns at most the latest 3 billing periods. It is a
    non-official endpoint used by the 威客服 mini program; no auth required.
    """
    now = datetime.now()
    start_time = f"{now.year - 1}-{now.month:02d}"

    try:
        async with session.get(
            API_URL,
            params={"cid": account_id, "kaishisj": start_time, "jieshusj": ""},
            headers={"User-Agent": API_USER_AGENT},
            timeout=20,
        ) as response:
            response.raise_for_status()
            payload = await response.json(content_type=None)
    except (ClientError, TimeoutError, ValueError) as err:
        raise PudongVeoliaApiError(f"请求失败: {err}") from err

    if payload.get("code") != "1":
        raise PudongVeoliaApiError(f"接口返回异常: {payload.get('message', payload)}")

    try:
        bills = json.loads(payload["data"])
    except (KeyError, TypeError, ValueError) as err:
        raise PudongVeoliaApiError(f"账单解析失败: {err}") from err

    if not isinstance(bills, list) or not bills:
        raise PudongVeoliaApiError("未查询到账单，请检查销根号")

    # 接口按账期倒序返回（新→旧），保险起见显式排序
    bills.sort(key=lambda b: (int(b.get("YEAR", 0)), int(b.get("MONTH", 0))), reverse=True)
    return bills
