-- 浦东威立雅（威客服）水费数据域
-- 设计原则：业务数据全部落 water_* 新表；sources / sync_runs 仅作为同步元数据复用。
-- 幂等键：账户=account_id（销根号）；账单=(account_id, billing_month)。
-- 接口只返回近 3 期，故账单表靠每日同步累积历史；漏跑超过一个抄表周期会缺口。

BEGIN;

CREATE TABLE IF NOT EXISTS water_accounts (
    id              serial PRIMARY KEY,
    account_id      varchar(32) NOT NULL UNIQUE,        -- 销根号（WATERMETERID）
    customer_name   text,                               -- CUSTRNAME（姓名脱敏存储由使用方负责）
    address         text,                               -- CUSTADDRESS
    book_id         varchar(32),                        -- BOOKID 抄表册号
    water_type      varchar(16),                        -- WATERTYPE
    meter_caliber   varchar(16),                        -- WATERMETERCALIBER 表径
    first_seen      timestamptz NOT NULL DEFAULT now(),
    fetched_at      timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE water_accounts IS '浦东威立雅水费户号（销根号）';

CREATE TABLE IF NOT EXISTS water_bills (
    id              bigserial PRIMARY KEY,
    account_id      varchar(32) NOT NULL REFERENCES water_accounts(account_id) ON DELETE CASCADE,
    billing_month   date NOT NULL,                      -- 账期月首日，来自 YEAR+MONTH
    water_usage     numeric(10,3),                      -- WATERNUM 生活用水量 m³
    sewage_volume   numeric(10,3),                      -- DIRTYNUM 污水量 m³
    water_fee       numeric(12,2),                      -- WATERFEE 水费
    water_price     numeric(10,4),                      -- WATERPRICE 水单价
    sewage_fee      numeric(12,2),                      -- DIRTYFEE 污水处理费
    sewage_price    numeric(10,4),                      -- DIRTYPRICE 污水单价
    garbage_fee     numeric(12,2),                      -- GARBAGEFEE
    other_fee       numeric(12,2),                      -- OTHERFEE + MAINTAIN
    sum_fee         numeric(12,2),                      -- SUMFEE 账面合计（未含结余调整）
    late_fee        numeric(12,2),                      -- LATEFEES 违约金
    sum_pay         numeric(12,2),                      -- SUMPAY 实付金额（含结余调整）
    prev_meter      numeric(12,3),                      -- PREVMETERDATA 上期表底
    meter           numeric(12,3),                      -- METERDATA 本期表底
    prev_balance    numeric(12,2),                      -- PREVLEFT 上期结余
    now_balance     numeric(12,2),                      -- NOWLEFT 本期结余
    copy_status     text,                               -- COPYMETERSTATUS 抄表状态（正常/不用）
    bill_status     smallint,                           -- BILLSTATUS 1=已缴 0=未缴
    pay_type        varchar(8),                         -- PAYTYPE
    copy_date       timestamptz,                        -- COPYMETERDATE 抄表时间
    pay_time        timestamptz,                        -- PAYTIME 缴费时间
    next_date       date,                               -- NEXTDATE 下次抄表日
    raw             jsonb NOT NULL DEFAULT '{}'::jsonb, -- 原始账单全字段
    fetched_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (account_id, billing_month)
);
COMMENT ON TABLE water_bills IS '双月结算账单（一期一行）';

CREATE INDEX IF NOT EXISTS water_bills_month_idx ON water_bills (billing_month);
CREATE INDEX IF NOT EXISTS water_bills_account_idx ON water_bills (account_id, billing_month DESC);

INSERT INTO sources (code, name, created_at)
VALUES ('water', '浦东威立雅 威客服水费', now())
ON CONFLICT (code) DO NOTHING;

-- 账单明细视图：派生用水合计、实付口径、缴费状态
CREATE OR REPLACE VIEW water_v_bills AS
SELECT b.account_id,
       a.customer_name,
       a.address,
       b.billing_month,
       b.water_usage,
       b.sewage_volume,
       round(b.water_usage + b.sewage_volume, 3)          AS total_volume,
       b.water_fee,
       b.sewage_fee,
       b.sum_fee,
       b.sum_pay,
       round(b.sum_fee - b.sum_pay, 2)                    AS balance_adjust,
       b.prev_meter,
       b.meter,
       round(b.meter - b.prev_meter, 3)                   AS meter_delta,
       b.copy_status,
       CASE WHEN b.bill_status = 1 THEN '已缴' ELSE '未缴' END AS bill_status,
       b.copy_date,
       b.pay_time,
       b.next_date,
       b.fetched_at
FROM water_bills b
JOIN water_accounts a ON a.account_id = b.account_id;

-- 年度汇总：按账单口径
CREATE OR REPLACE VIEW water_v_yearly AS
SELECT account_id,
       extract(year FROM billing_month)::int            AS year,
       count(*)                                          AS periods,
       round(sum(water_usage), 3)                        AS water_usage,
       round(sum(sewage_volume), 3)                      AS sewage_volume,
       round(sum(water_fee), 2)                          AS water_fee,
       round(sum(sewage_fee), 2)                         AS sewage_fee,
       round(sum(sum_fee), 2)                            AS sum_fee,
       round(sum(sum_pay), 2)                            AS sum_pay
FROM water_bills
GROUP BY account_id, extract(year FROM billing_month);

COMMIT;
