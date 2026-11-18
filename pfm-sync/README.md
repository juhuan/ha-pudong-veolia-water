---
name: water-bill-sync
description: 把上海浦东威立雅（威客服）水费账单同步到 pfm 库（Postgres，容器 pfm-db-1，库 pfm，表 water_*）。触发词：同步水费、拉水费、更新水费、water bill、威立雅水费入库。
---

# 浦东威立雅水费同步（water-bill-sync）

直接调用威客服小程序的账单接口（无鉴权、无需登录态），在 debian 上拉数据 →
生成幂等 SQL → 灌进 pfm。`sources.code='water'`，同步记录写入 `sync_runs`。

## 运行

```bash
ssh debian 'bash /root/pfm/water/sync.sh'                       # 用 accounts.txt 里的销根号
ssh debian 'bash /root/pfm/water/sync.sh 123456789'             # 临时指定销根号（逗号分隔可多户）
```

首次运行自动建表（`water_schema.sql`）。幂等键见下，重复执行不产生重复行。

## 表（全部 water_ 前缀）

| 表 | 幂等键 | 说明 |
|---|---|---|
| `water_accounts` | `account_id` | 销根号；含户名、地址、抄表册号、表径 |
| `water_bills` | `(account_id, billing_month)` | 双月账单头，一期一行；`sum_pay` 为实付，`raw` 存全字段 |

视图：`water_v_bills`（账单+派生用水合计/结余调整/缴费状态）、`water_v_yearly`（年度汇总）。

## 常用查询

```sql
-- 账单明细（派生字段）
select * from water_v_bills order by billing_month desc;

-- 年度汇总
select * from water_v_yearly order by year desc, account_id;

-- 用水与实付趋势
select billing_month, total_volume, sum_pay from water_v_bills
where account_id='123456789' order by billing_month;
```

## 接口与字段映射

- 接口：`GET https://mtu.pudongwater.com/wkf/WX/GetBill?cid=<销根号>&kaishisj=<YYYY-MM>&jieshusj=`，带微信 UA。
- 返回 `code=1` + `data`（JSON 字符串，需二次解析），按账期倒序，**最多近 3 期**。

| 原始字段 | 列 | 备注 |
|---|---|---|
| `WATERMETERID` | `account_id` | 销根号 |
| `YEAR`+`MONTH` | `billing_month` | 账期月首日 |
| `WATERNUM` / `DIRTYNUM` | `water_usage` / `sewage_volume` | 生活用水 / 污水，m³ |
| `WATERFEE` / `DIRTYFEE` | `water_fee` / `sewage_fee` | 水费 / 污水处理费 |
| `SUMFEE` / `SUMPAY` | `sum_fee` / `sum_pay` | 账面合计 / 实付（含结余调整）；**应付以 SUMPAY 为准** |
| `PREVMETERDATA` / `METERDATA` | `prev_meter` / `meter` | 上期 / 本期表底 |
| `PREVLEFT` / `NOWLEFT` | `prev_balance` / `now_balance` | 上期 / 本期结余 |
| `BILLSTATUS` | `bill_status` | 1=已缴 0=未缴 |
| `COPYMETERDATE` / `PAYTIME` / `NEXTDATE` | `copy_date` / `pay_time` / `next_date` | 日期已归一化 |

## 坑

1. **接口只给近 3 期**，`kaishisj` 向前调无效。历史靠本脚本每日累积；漏跑超过一个抄表周期（约 2 个月）会缺口。建议挂 cron 每日跑。
2. **账单是双月出账**，非日级数据，不能做实时漏水告警。
3. `SUMPAY` 与 `SUMFEE` 可能差几分（结余结转），展示"应付"用 `SUMPAY`。
4. 抄表状态 `COPYMETERSTATUS='不用'` 的零账单（未用水）也会入库，`bill_status=0`、`sum_pay=0`，属正常。
5. 姓名/地址属个人信息，本 skill 如实入库到 `water_accounts`，注意库访问权限。

## 关联

HA 侧原生集成见 `https://github.com/juhuan/ha-pudong-veolia-water`（实体用于实时展示，本 skill 用于历史落库，两者独立）。

## 部署

```bash
scp -r scripts debian:/root/pfm/water/
ssh debian 'chmod +x /root/pfm/water/sync.sh && echo 123456789 > /root/pfm/water/accounts.txt'
```
