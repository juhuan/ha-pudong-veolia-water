#!/usr/bin/env python3
"""从威客服接口拉取水费账单，输出 JSON 到 stdout。

销根号来源（按优先级）：命令行参数 > 环境变量 PDWLY_IDS > 同目录 accounts.txt（每行一个）。
接口无鉴权；仅返回近 3 期，历史靠本同步脚本每日累积。
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

API = "https://mtu.pudongwater.com/wkf/WX/GetBill"
UA = ("Mozilla/5.0 (Linux; Android 5.0; SM-N9100 Build/LRX21V) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 "
      "Chrome/37.0.0.0 Mobile Safari/537.36 "
      "MicroMessenger/6.0.2.56 NetType/WIFI")


def load_accounts() -> list[str]:
    if len(sys.argv) > 1:
        ids = [a.strip() for a in sys.argv[1].split(",") if a.strip()]
    elif os.getenv("PDWLY_IDS"):
        ids = [a.strip() for a in os.environ["PDWLY_IDS"].split(",") if a.strip()]
    else:
        f = Path(__file__).with_name("accounts.txt")
        ids = [l.strip() for l in f.read_text().splitlines() if l.strip() and not l.startswith("#")] if f.exists() else []
    return ids


def fetch(account: str) -> list[dict]:
    now = datetime.now()
    params = {"cid": account, "kaishisj": f"{now.year - 1}-{now.month:02d}", "jieshusj": ""}
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        payload = json.loads(r.read().decode())
    if payload.get("code") != "1":
        raise RuntimeError(f"{account}: 接口异常 {payload.get('message')}")
    bills = json.loads(payload["data"])
    bills.sort(key=lambda b: (int(b.get("YEAR", 0)), int(b.get("MONTH", 0))), reverse=True)
    return bills


def main():
    accounts = load_accounts()
    if not accounts:
        print("no accounts", file=sys.stderr)
        sys.exit(2)
    out = {"fetched_at": datetime.now().astimezone().isoformat(), "accounts": []}
    for acct in accounts:
        try:
            out["accounts"].append({"account_id": acct, "bills": fetch(acct)})
        except Exception as e:
            print(f"WARN {acct}: {e}", file=sys.stderr)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
