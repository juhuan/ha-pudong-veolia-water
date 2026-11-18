---
name: gas-bill-sync
description: 同步上海燃气（微客服）账单到 pfm PostgreSQL，gas_ 前缀表。触发词「同步燃气」「同步燃气账单」「燃气账单入库」。数据来自 web-api.shgas.com.cn，用 ddddocr 识别图形验证码 + PWD(MD5) 登录换 token，无需人工收短信。
---

# 上海燃气账单同步

## 触发

用户说「同步燃气」「同步燃气账单」「燃气账单入库」时执行。

## 架构

- 数据源：`web-api.shgas.com.cn`（上海燃气微客服 H5 同款接口）
- 认证：`ddddocr` 识别 4 位图形验证码 → `doLogin(method=PWD, pwd=MD5)` 换 JWT token → `queryAccountListByUserCode` → `queryBills`
- token 有效期约 12h，每次同步现取，不依赖浏览器、不需短信验证码
- 落库：pfm 库（容器 `pfm-db-1`），`gas_` 前缀表
- 幂等键：账户 `customer_id`；账单 `(customer_id, bill_ym)`

## 文件

`scripts/` 下：
- `gas_api.py` — 核心：登录 + 抓账户/账单（stdlib urllib，OCR 走 `/root/pfm/gas/.venv`）
- `gas_export.py` — 包装抓取输出标准 JSON
- `gas_load.py` — JSON → 幂等 SQL
- `gas_schema.sql` — 建表（gas_accounts / gas_bills / gas_v_bills / gas_v_yearly）
- `sync.sh` — 编排：建表 → 抓取 → 写库 → 记 sync_runs

部署位置：debian `/root/pfm/gas/`
- `credentials.json`（chmod 600）：phone / password_md5 / login_mode / company_code / customer_id / account_id
- `.venv/`：uv 建的 Python 3.11 环境，装 ddddocr 1.6.1 + onnxruntime

## 执行

```bash
ssh debian 'bash /root/pfm/gas/sync.sh'
```

cron：`30 7 * * *`（每日 07:30，错开水费 07:20 / 电费 07:40）。

## 表结构

- `gas_accounts`：账户（客户号、户号、册号、阶梯气量上限）
- `gas_bills`：双月账单，一期一行，含阶梯用量/金额、结余、滞纳金、表底数，`raw` jsonb 存全字段
- `gas_v_bills`：派生表底差、阶梯合计、纯气费
- `gas_v_yearly`：年度汇总

## 常用查询

```sql
select * from gas_v_bills order by bill_ym desc;
select * from gas_v_yearly order by year desc;
```

## 已知限制

- 接口每次只返回近 2 期账单，历史靠每日 cron 累积，漏跑超一个抄表周期会缺口
- `companyCode=PD` 硬编码浦东，浦西账户需改
- 登录靠 OCR 识别率（实测约 80%），脚本内置 6 次重试兜底
- 密码登录凭据：明文密码 + 其 MD5（credentials.json 中的 password_md5 为 MD5 值，doLogin 直接发送）
- 凭据只在本地：macOS 密码 App（服务器 www.shgas.com.cn / 账号为手机号）+ debian `/root/pfm/gas/credentials.json`（chmod 600），仓库不含任何真实凭据。
