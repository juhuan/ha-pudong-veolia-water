#!/usr/bin/env python3
"""燃气 JSON（gas_export.py 输出）→ 幂等 SQL 到 stdout。"""
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


def d(v):
    """'2026-11-26 00:00:00' → '2026-11-26'（date 类型）。"""
    if not v:
        return "NULL"
    return s(str(v).strip()[:10])


def main():
    data = json.load(sys.stdin)
    fetched = data.get("fetched_at")
    lines = ["BEGIN;"]
    added_accounts = set()
    bill_count = 0

    for acct in data.get("accounts", []):
        cid = acct.get("customerId") or acct.get("customer_id")
        if not cid or cid in added_accounts:
            continue
        lines.append(
            "INSERT INTO gas_accounts (customer_id, account_id, record_id, company_code, account_code, "
            "customer_name, customer_address, book_code, customer_class, dept, gas_class, meter_flux, "
            "ladder_first, ladder_second, fetched_at) "
            f"VALUES ({s(cid)}, {s(acct.get('accountId'))}, {s(acct.get('recordId'))}, "
            f"{s(acct.get('companyCode'))}, {s(acct.get('accountCode'))}, {s(acct.get('customerName'))}, "
            f"{s(acct.get('customerAddress'))}, {s(acct.get('bookCode'))}, {s(acct.get('customerClass'))}, "
            f"{s(acct.get('dept'))}, {s(acct.get('gasClass'))}, {s(acct.get('meterFlux'))}, "
            f"{n(acct.get('ladderFirst'))}, {n(acct.get('ladderSecond'))}, {s(fetched)}) "
            "ON CONFLICT (customer_id) DO UPDATE SET account_id=EXCLUDED.account_id, "
            "customer_name=EXCLUDED.customer_name, customer_address=EXCLUDED.customer_address, "
            "book_code=EXCLUDED.book_code, fetched_at=EXCLUDED.fetched_at;"
        )
        added_accounts.add(cid)

    for b in data.get("bills", []):
        cid = b.get("_customer_id") or b.get("customerId")
        ym = b.get("billYM")
        if not cid or not ym:
            continue
        bill_count += 1
        raw = json.dumps(b, ensure_ascii=False)
        lines.append(
            "INSERT INTO gas_bills (customer_id, bill_ym, money, overdue_fine, payment_status, "
            "billing_type, billing_date, read_date, next_read_date, last_reading, current_reading, "
            "consumption, year_consumption, price, last_payday, add_money, advance_charge, "
            "last_balance, current_balance, idle_money, read_status, first_gear, second_gear, "
            "year_count, first_count, second_count, third_count, first_use, second_use, "
            "first_money, second_money, third_money, raw, fetched_at) "
            f"VALUES ({s(cid)}, {s(ym)}, {n(b.get('money'))}, {n(b.get('overdueFine'))}, "
            f"{s(b.get('paymentStatus'))}, {s(b.get('billingType'))}, {s(b.get('billingDate'))}, "
            f"{s(b.get('readDate'))}, {d(b.get('nextReadDate'))}, {n(b.get('lastReading'))}, "
            f"{n(b.get('currentReading'))}, {n(b.get('consumption'))}, {n(b.get('yearConsumption'))}, "
            f"{n(b.get('price'))}, {s(b.get('lastPayday'))}, {n(b.get('addMoney'))}, "
            f"{n(b.get('advanceCharge'))}, {n(b.get('lastBalance'))}, {n(b.get('currentBalance'))}, "
            f"{n(b.get('idleMoney'))}, {s(b.get('readStatus'))}, {n(b.get('firstGear'))}, "
            f"{n(b.get('secondGear'))}, {n(b.get('yearCount'))}, {n(b.get('firstCount'))}, "
            f"{n(b.get('secondCount'))}, {n(b.get('thirdCount'))}, {n(b.get('firstUse'))}, "
            f"{n(b.get('secondUse'))}, {n(b.get('firstMoney'))}, {n(b.get('secondMoney'))}, "
            f"{n(b.get('thirdMoney'))}, {s(raw)}, {s(fetched)}) "
            "ON CONFLICT (customer_id, bill_ym) DO UPDATE SET "
            "money=EXCLUDED.money, overdue_fine=EXCLUDED.overdue_fine, "
            "payment_status=EXCLUDED.payment_status, current_reading=EXCLUDED.current_reading, "
            "consumption=EXCLUDED.consumption, year_consumption=EXCLUDED.year_consumption, "
            "last_balance=EXCLUDED.last_balance, current_balance=EXCLUDED.current_balance, "
            "read_date=EXCLUDED.read_date, raw=EXCLUDED.raw, fetched_at=EXCLUDED.fetched_at;"
        )

    lines.append("COMMIT;")
    print("\n".join(lines))
    print(f"-- accounts={len(added_accounts)} bills={bill_count}", file=sys.stderr)


if __name__ == "__main__":
    main()
