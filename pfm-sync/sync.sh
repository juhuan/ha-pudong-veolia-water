#!/usr/bin/env bash
# 浦东威立雅水费 → pfm 库同步（debian 上运行）
# 用法: bash sync.sh [销根号,销根号2...]   不传则读 accounts.txt
set -uo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
export PATH=/usr/local/bin:/usr/bin:/bin
START_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
ARGS="${1:-}"

psql_q() { docker exec -i pfm-db-1 psql -U pfm -d pfm -v ON_ERROR_STOP=1 -q "$@"; }
psql_t() { docker exec pfm-db-1 psql -U pfm -d pfm -tAc "$1"; }

fail() {
    echo "[water] FAILED: $*" >&2
    local sid
    sid=$(psql_t "select id from sources where code='water'" || true)
    if [ -n "${sid:-}" ]; then
        psql_t "insert into sync_runs (source_id, started_at, status, added, updated, error)
                values ($sid, '$START_TS', 'error', 0, 0, '$*')" >/dev/null 2>&1 || true
    fi
    exit 1
}

docker ps --format '{{.Names}}' | grep -q '^pfm-db-1$' || fail "pfm-db-1 容器未运行"

# 首次运行自动建表
if [ "$(psql_t "select count(*) from information_schema.tables where table_name='water_bills'")" != "1" ]; then
    echo "[water] 初始化表结构"
    psql_q < "$HERE/water_schema.sql" || fail "建表失败"
fi

BEFORE=$(psql_t "select count(*) from water_bills")

echo "[water] 拉取账单"
if [ -n "$ARGS" ]; then
    python3 "$HERE/water_export.py" "$ARGS" > /tmp/water_export.json 2>/tmp/water_export.err
else
    python3 "$HERE/water_export.py" > /tmp/water_export.json 2>/tmp/water_export.err
fi
grep -q '"accounts"' /tmp/water_export.json || { cat /tmp/water_export.err >&2; fail "导出结果为空"; }

python3 "$HERE/water_load.py" < /tmp/water_export.json > /tmp/water_load.sql 2>/tmp/water_load.err \
    || { cat /tmp/water_load.err >&2; fail "生成 SQL 失败"; }

psql_q < /tmp/water_load.sql || fail "写库失败"

AFTER=$(psql_t "select count(*) from water_bills")
ADDED=$(( AFTER - BEFORE ))

SID=$(psql_t "select id from sources where code='water'")
psql_t "insert into sync_runs (source_id, started_at, finished_at, status, added, updated)
        values ($SID, '$START_TS', now(), 'success', $ADDED, 0)" >/dev/null

echo "[water] OK 账单=$AFTER(+$ADDED)"
cat /tmp/water_export.err 2>/dev/null | sed 's/^/[water] /'
