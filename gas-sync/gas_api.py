#!/usr/bin/env python3
"""上海燃气（微客服）数据抓取：ddddocr 识图 + PWD 登录换 token + queryBills。

无第三方网络依赖（用 stdlib urllib），OCR 用同目录 .venv 的 ddddocr。
账号密码从 credentials.json 读取（MD5 密码，PWD 登录直接用）。
"""
import base64
import json
import os
import sys
import time
import urllib.request

BASE = "https://web-api.shgas.com.cn"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Origin": "https://www.shgas.com.cn",
    "Referer": "https://www.shgas.com.cn/",
    "Content-Type": "application/json;charset=UTF-8",
    "Accept": "application/json, text/plain, */*",
}

HERE = os.path.dirname(os.path.abspath(__file__))
CRED_PATH = os.environ.get("GAS_CRED", os.path.join(HERE, "credentials.json"))
# ddddocr 装在 gas/.venv，脚本可能在 scripts/ 或上级
VENV_PY = os.environ.get("GAS_VENV_PY", "/root/pfm/gas/.venv/bin/python")


def load_cred():
    with open(CRED_PATH, encoding="utf-8") as f:
        return json.load(f)


def get(url, extra=None):
    h = dict(HEADERS)
    if extra:
        h.update(extra)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))


def post(path, body, token=None):
    h = dict(HEADERS)
    if token:
        h["token"] = token
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=h,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))


def ocr_captcha(image_bytes):
    """调用独立 venv 的 ddddocr 识别验证码，返回 4 位字符串。"""
    import subprocess
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
        tf.write(image_bytes)
        path = tf.name
    try:
        code = (
            "import sys,ddddocr;"
            "o=ddddocr.DdddOcr(show_ad=False);"
            "print(o.classification(open(sys.argv[1],'rb').read()).strip().splitlines()[-1])"
        )
        out = subprocess.check_output(
            [VENV_PY, "-c", code, path], timeout=60, stderr=subprocess.DEVNULL
        ).decode().strip()
        return out
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def login(cred, max_retries=6):
    """图形验证码 OCR + PWD 登录，重试直到拿到 token。"""
    mobile = cred["phone"]
    pwd = cred["password_md5"]
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            ts = int(time.time())
            img = get(f"{BASE}/v1/thirdparty/common/img/getImgAuthCode?timestamp={ts}")
            if img.get("resultCode") != "0000":
                last_err = f"取验证码失败: {img.get('resultInfo')}"
                time.sleep(2)
                continue
            code = ocr_captcha(base64.b64decode(img["base64Image"]))
            if len(code) != 4 or not code.isalnum():
                last_err = f"验证码格式异常: {code!r}"
                time.sleep(1)
                continue
            body = {
                "imgAuthCode": code,
                "imgid": img["imgid"],
                "method": "PWD",
                "mobile": mobile,
                "origin": "PC",
                "pwd": pwd,
                "qrCode": "",
                "smsAuthCode": "",
                "timestamp": int(time.time() * 1000),
            }
            rsp = post("/v1/user/common/doLogin", body)
            if rsp.get("resultCode") == "0000" and rsp.get("token"):
                return rsp["token"]
            last_err = f"登录失败 attempt {attempt}: {rsp.get('resultCode')} {rsp.get('resultInfo')}"
            time.sleep(2)
        except Exception as e:  # noqa: BLE001
            last_err = f"attempt {attempt} 异常: {e}"
            time.sleep(2)
    raise RuntimeError(f"登录失败（{max_retries} 次）: {last_err}")


def query_accounts(token):
    return post("/v1/user/queryAccountListByUserCode",
                {"timestamp": int(time.time() * 1000)}, token=token)


def query_bills(token, customer_id, company_code="PD"):
    return post("/v1/accountingService/queryBills",
                {"customerId": customer_id, "companyCode": company_code,
                 "origin": "PC", "timestamp": int(time.time() * 1000)},
                token=token)


def fetch_all(cred=None):
    """返回 {accounts: [...], bills: [...]}，bills 带 customer_id。"""
    cred = cred or load_cred()
    token = login(cred)
    acc_rsp = query_accounts(token)
    if acc_rsp.get("resultCode") != "0000":
        raise RuntimeError(f"查账户失败: {acc_rsp.get('resultCode')} {acc_rsp.get('resultInfo')}")
    accounts = acc_rsp["accountList"]
    bills = []
    for a in accounts:
        cid = a.get("customerId") or a.get("accountId")
        rsp = query_bills(token, cid, cred.get("company_code", "PD"))
        if rsp.get("resultCode") != "0000":
            print(f"[gas] 账户 {cid} 账单查询失败: {rsp.get('resultInfo')}", file=sys.stderr)
            continue
        for b in rsp.get("bills", []):
            b = dict(b)
            b["_customer_id"] = cid
            bills.append(b)
    return {"accounts": accounts, "bills": bills, "token": token}


if __name__ == "__main__":
    data = fetch_all()
    # 打印脱敏摘要 + 完整字段样本（供建表）
    print(json.dumps({
        "account_count": len(data["accounts"]),
        "bill_count": len(data["bills"]),
        "sample_account_keys": list(data["accounts"][0].keys()) if data["accounts"] else [],
        "sample_bill": data["bills"][0] if data["bills"] else {},
    }, ensure_ascii=False, indent=2))
