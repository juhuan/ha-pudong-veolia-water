"""Data access for Shanghai Gas integration: read gas bills from pfm PostgreSQL."""

from __future__ import annotations

import datetime
from typing import Any

import psycopg2
import psycopg2.extras

from .const import (
    DEFAULT_PG_DB,
    DEFAULT_PG_HOST,
    DEFAULT_PG_PASSWORD,
    DEFAULT_PG_PORT,
    DEFAULT_PG_USER,
)


class ShanghaiGasApiError(Exception):
    """Raised when gas data cannot be read."""


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    return str(value)


def fetch_bills_sync(
    customer_id: str,
    pg_host: str = DEFAULT_PG_HOST,
    pg_port: int = DEFAULT_PG_PORT,
) -> list[dict[str, Any]]:
    """Read latest gas bills for a customer from pfm (synchronous).

    Caller must run this in an executor to avoid blocking the event loop.
    """
    try:
        conn = psycopg2.connect(
            host=pg_host,
            port=pg_port,
            dbname=DEFAULT_PG_DB,
            user=DEFAULT_PG_USER,
            password=DEFAULT_PG_PASSWORD,
            connect_timeout=10,
        )
    except Exception as err:  # noqa: BLE001
        raise ShanghaiGasApiError(f"无法连接 pfm 库: {err}") from err

    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT customer_id, customer_name, customer_address, bill_ym,
                       money, overdue_fine, payment_status, billing_type, read_status,
                       last_reading, current_reading, meter_delta, consumption,
                       year_consumption, price, first_count, second_count, third_count,
                       ladder_total, first_money, second_money, third_money, pure_fee,
                       last_balance, current_balance, read_date, billing_date,
                       next_read_date, last_payday, fetched_at
                FROM gas_v_bills
                WHERE customer_id = %s
                ORDER BY bill_ym DESC
                """,
                (customer_id,),
            )
            rows = cur.fetchall()
    except Exception as err:  # noqa: BLE001
        raise ShanghaiGasApiError(f"查询燃气账单失败: {err}") from err
    finally:
        conn.close()

    bills: list[dict[str, Any]] = []
    for row in rows:
        d = dict(row)
        for key in ("read_date", "billing_date", "last_payday", "fetched_at"):
            d[key] = _iso(d.get(key))
        for key in ("next_read_date",):
            d[key] = _iso(d.get(key))
        bills.append(d)
    return bills
