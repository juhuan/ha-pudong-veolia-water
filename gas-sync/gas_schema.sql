-- 上海燃气（微客服 web-api.shgas.com.cn）数据域
-- 设计原则：业务数据全部落 gas_* 新表；sources / sync_runs 仅作同步元数据复用。
-- 幂等键：账户=customer_id；账单=(customer_id, bill_ym)。
-- 登录：ddddocr 识图 + PWD(MD5) 换 token，每次同步现取 token（12h 过期）。
-- 接口只返回近 2 期账单，靠每日同步累积历史。

BEGIN;

CREATE TABLE IF NOT EXISTS gas_accounts (
    id               serial PRIMARY KEY,
    customer_id      varchar(32) NOT NULL UNIQUE,   -- 客户号（queryBills 的 customerId）
    account_id       varchar(32),                  -- 户号
    record_id        varchar(32),
    company_code     varchar(8),                   -- PD=浦东
    account_code     varchar(64),
    customer_name    text,                         -- 户名（接口已脱敏）
    customer_address text,
    book_code        varchar(32),                  -- 抄表册号 ND18
    customer_class   varchar(16),                  -- 居民
    dept             varchar(32),                  -- 三所
    gas_class        varchar(16),                  -- 天然气
    meter_flux       varchar(16),
    ladder_first     numeric(10,2),                -- 第一档气量上限
    ladder_second    numeric(10,2),                -- 第二档气量上限
    first_seen       timestamptz NOT NULL DEFAULT now(),
    fetched_at       timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE gas_accounts IS '上海燃气账户（客户号/户号）';

CREATE TABLE IF NOT EXISTS gas_bills (
    id               bigserial PRIMARY KEY,
    customer_id      varchar(32) NOT NULL REFERENCES gas_accounts(customer_id) ON DELETE CASCADE,
    bill_ym          varchar(7) NOT NULL,           -- 账期 YYYY-MM
    money            numeric(12,2),                -- 本期金额
    overdue_fine     numeric(12,2),                -- 滞纳金
    payment_status   varchar(16),                  -- 已付款/未付款
    billing_type     varchar(16),                  -- 正常
    billing_date     timestamptz,                  -- 出账时间
    read_date        timestamptz,                  -- 抄表时间
    next_read_date   date,                         -- 下次抄表日
    last_reading     numeric(12,3),                -- 上期表底
    current_reading  numeric(12,3),                -- 本期表底
    consumption      numeric(12,3),                -- 本期用量 m³
    year_consumption numeric(12,3),                -- 年度累计用量
    price            numeric(10,4),                -- 气价
    last_payday      timestamptz,                  -- 上次缴费时间
    add_money        numeric(12,2),                -- 加收
    advance_charge   numeric(12,2),                -- 预收冲抵
    last_balance     numeric(12,2),                -- 上期结余
    current_balance  numeric(12,2),                -- 本期结余
    idle_money       numeric(12,2),                -- 闲置金额
    read_status      varchar(16),                  -- 智能采集
    first_gear       numeric(10,2),                -- 第一档气量上限
    second_gear      numeric(10,2),                -- 第二档气量上限
    year_count       numeric(12,3),                -- 年度已用气量
    first_count      numeric(12,3),                -- 第一档用量
    second_count     numeric(12,3),                -- 第二档用量
    third_count      numeric(12,3),                -- 第三档用量
    first_use        numeric(12,3),
    second_use       numeric(12,3),
    first_money      numeric(12,2),                -- 第一档金额
    second_money     numeric(12,2),                -- 第二档金额
    third_money      numeric(12,2),                -- 第三档金额
    raw              jsonb NOT NULL DEFAULT '{}'::jsonb,  -- 原始账单全字段
    fetched_at       timestamptz NOT NULL DEFAULT now(),
    UNIQUE (customer_id, bill_ym)
);
COMMENT ON TABLE gas_bills IS '上海燃气双月账单（一期一行）';

CREATE INDEX IF NOT EXISTS gas_bills_ym_idx ON gas_bills (bill_ym);
CREATE INDEX IF NOT EXISTS gas_bills_customer_idx ON gas_bills (customer_id, bill_ym DESC);

INSERT INTO sources (code, name, created_at)
VALUES ('gas', '上海燃气 微客服', now())
ON CONFLICT (code) DO NOTHING;

-- 账单视图：派生表底差、阶梯合计、实付口径
CREATE OR REPLACE VIEW gas_v_bills AS
SELECT b.customer_id,
       a.customer_name,
       a.customer_address,
       b.bill_ym,
       b.money,
       b.overdue_fine,
       b.payment_status,
       b.billing_type,
       b.read_status,
       b.last_reading,
       b.current_reading,
       round(b.current_reading - b.last_reading, 3)  AS meter_delta,
       b.consumption,
       b.year_consumption,
       b.price,
       b.first_count,
       b.second_count,
       b.third_count,
       round(coalesce(b.first_count,0)+coalesce(b.second_count,0)+coalesce(b.third_count,0),3) AS ladder_total,
       b.first_money,
       b.second_money,
       b.third_money,
       round(b.money - coalesce(b.overdue_fine,0), 2) AS pure_fee,
       b.last_balance,
       b.current_balance,
       b.read_date,
       b.billing_date,
       b.next_read_date,
       b.last_payday,
       b.fetched_at
FROM gas_bills b
JOIN gas_accounts a ON a.customer_id = b.customer_id;

-- 年度汇总
CREATE OR REPLACE VIEW gas_v_yearly AS
SELECT customer_id,
       extract(year FROM (bill_ym || '-01')::date)::int AS year,
       count(*)                                    AS periods,
       round(sum(consumption), 3)                  AS consumption,
       round(sum(money), 2)                        AS money,
       round(sum(overdue_fine), 2)                 AS overdue_fine
FROM gas_bills
GROUP BY customer_id, extract(year FROM (bill_ym || '-01')::date);

COMMIT;
