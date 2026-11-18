#!/usr/bin/env python3
"""水费 JSON（water_export.py 输出）→ 幂等 SQL 到 stdout。"""
import json
import sys


def s(v):
    if v is None or v == "":
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"


def n(v):
    if v is None or v == "":
        return "NULL"
    try:
        return str(float(v))
    except (TypeError, ValueError):
        return "NULL"


def month(b):
    try:
        return f"{int(b['YEAR'])}-{int(b['MONTH']):02d}-01"
    except (KeyError, TypeError, ValueError):
        return None


def ts(v):
    """归一化 2026/10/11 0:00:00 / 2026-10-07 12:39:44 → ISO，空串转 NULL。"""
    if not v:
        return None
    v = str(v).replace("/", "-")
    return v


def main():
    data = json.load(sys.stdin)
    fetched = data.get("fetched_at")
    lines = ["BEGIN;"]
    added_accounts = set()
    bill_count = 0

    for acct in data.get("accounts", []):
        aid = acct["account_id"]
        bills = acct.get("bills", [])
        if not bills:
            continue
        first = bills[0]
        if aid not in added_accounts:
            lines.append(
                "INSERT INTO water_accounts (account_id, customer_name, address, book_id, water_type, meter_caliber, fetched_at) "
                f"VALUES ({s(aid)}, {s(first.get('CUSTRNAME'))}, {s(first.get('CUSTADDRESS'))}, "
                f"{s(first.get('BOOKID'))}, {s(first.get('WATERTYPE'))}, {s(first.get('WATERMETERCALIBER'))}, {s(fetched)}) "
                "ON CONFLICT (account_id) DO UPDATE SET customer_name=EXCLUDED.customer_name, "
                "address=EXCLUDED.address, fetched_at=EXCLUDED.fetched_at;"
            )
            added_accounts.add(aid)

        for b in bills:
            bm = month(b)
            if not bm:
                continue
            bill_count += 1
            raw = json.dumps(b, ensure_ascii=False)
            other = (n(b.get("OTHERFEE")) or "0") + " + " + "(COALESCE(" + n(b.get("MAINTAIN")) + ",0))"
            lines.append(
                "INSERT INTO water_bills (account_id, billing_month, water_usage, sewage_volume, "
                "water_fee, water_price, sewage_fee, sewage_price, garbage_fee, other_fee, sum_fee, "
                "late_fee, sum_pay, prev_meter, meter, prev_balance, now_balance, copy_status, "
                "bill_status, pay_type, copy_date, pay_time, next_date, raw, fetched_at) "
                f"VALUES ({s(aid)}, {s(bm)}, {n(b.get('WATERNUM'))}, {n(b.get('DIRTYNUM'))}, "
                f"{n(b.get('WATERFEE'))}, {n(b.get('WATERPRICE'))}, {n(b.get('DIRTYFEE'))}, {n(b.get('DIRTYPRICE'))}, "
                f"{n(b.get('GARBAGEFEE'))}, ({other}), {n(b.get('SUMFEE'))}, {n(b.get('LATEFEES'))}, "
                f"{n(b.get('SUMPAY'))}, {n(b.get('PREVMETERDATA'))}, {n(b.get('METERDATA'))}, "
                f"{n(b.get('PREVLEFT'))}, {n(b.get('NOWLEFT'))}, {s(b.get('COPYMETERSTATUS'))}, "
                f"{n(b.get('BILLSTATUS'))}, {s(b.get('PAYTYPE'))}, {s(ts(b.get('COPYMETERDATE')))}, "
                f"{s(ts(b.get('PAYTIME')))}, {s(b.get('NEXTDATE'))}, {s(raw)}, {s(fetched)}) "
                "ON CONFLICT (account_id, billing_month) DO UPDATE SET "
                "water_usage=EXCLUDED.water_usage, sewage_volume=EXCLUDED.sewage_volume, "
                "water_fee=EXCLUDED.water_fee, sewage_fee=EXCLUDED.sewage_fee, sum_fee=EXCLUDED.sum_fee, "
                "sum_pay=EXCLUDED.sum_pay, meter=EXCLUDED.meter, now_balance=EXCLUDED.now_balance, "
                "copy_status=EXCLUDED.copy_status, bill_status=EXCLUDED.bill_status, "
                "pay_time=EXCLUDED.pay_time, raw=EXCLUDED.raw, fetched_at=EXCLUDED.fetched_at;"
            )

    lines.append("COMMIT;")
    print("\n".join(lines))
    print(f"-- accounts={len(added_accounts)} bills={bill_count}", file=sys.stderr)


if __name__ == "__main__":
    main()
