#!/usr/bin/env bash
# 上海燃气 → pfm 库同步（debian 上运行）
# 每次现取 token（ddddocr 识图 + PWD 登录），无人工介入。
set -uo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
START_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)

psql_q() { docker exec -i pfm-db-1 psql -U pfm -d pfm -v ON_ERROR_STOP=1 -q "$@"; }
psql_t() { docker exec pfm-db-1 psql -U pfm -d pfm -tAc "$1"; }

fail() {
    echo "[gas] FAILED: $*" >&2
    local sid
    sid=$(psql_t "select id from sources where code='gas'" || true)
    if [ -n "${sid:-}" ]; then
        psql_t "insert into sync_runs (source_id, started_at, status, added, updated, error)
                values ($sid, '$START_TS', 'error', 0, 0, '$*')" >/dev/null 2>&1 || true
    fi
    exit 1
}

docker ps --format '{{.Names}}' | grep -q '^pfm-db-1$' || fail "pfm-db-1 容器未运行"

# 首次运行自动建表
if [ "$(psql_t "select count(*) from information_schema.tables where table_name='gas_bills'")" != "1" ]; then
    echo "[gas] 初始化表结构"
    psql_q < "$HERE/gas_schema.sql" || fail "建表失败"
fi

BEFORE=$(psql_t "select count(*) from gas_bills")

echo "[gas] 登录并拉取账单（OCR+PWD，约 5-15s）"
python3 "$HERE/gas_export.py" > /tmp/gas_export.json 2>/tmp/gas_export.err \
    || { cat /tmp/gas_export.err >&2; fail "导出失败（登录或抓包）"; }
grep -q '"accounts"' /tmp/gas_export.json || { cat /tmp/gas_export.err >&2; fail "导出结果为空"; }

python3 "$HERE/gas_load.py" < /tmp/gas_export.json > /tmp/gas_load.sql 2>/tmp/gas_load.err \
    || { cat /tmp/gas_load.err >&2; fail "生成 SQL 失败"; }

psql_q < /tmp/gas_load.sql || fail "写库失败"

AFTER=$(psql_t "select count(*) from gas_bills")
ADDED=$(( AFTER - BEFORE ))

SID=$(psql_t "select id from sources where code='gas'")
psql_t "insert into sync_runs (source_id, started_at, finished_at, status, added, updated)
        values ($SID, '$START_TS', now(), 'success', $ADDED, 0)" >/dev/null

echo "[gas] OK 账单=$AFTER(+$ADDED)"
cat /tmp/gas_export.err 2>/dev/null | sed 's/^/[gas] /'
