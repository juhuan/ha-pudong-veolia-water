#!/usr/bin/env python3
"""调 gas_api 抓账户+账单，输出标准 JSON 到 stdout。"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gas_api  # noqa: E402


def main():
    data = gas_api.fetch_all()
    out = {
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "accounts": data["accounts"],
        "bills": data["bills"],
    }
    json.dump(out, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
