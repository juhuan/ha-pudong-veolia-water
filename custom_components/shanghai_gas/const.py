"""Constants for the Shanghai Gas integration."""

DOMAIN = "shanghai_gas"
UPDATE_INTERVAL_HOURS = 6

# pfm PostgreSQL 连接（HA 用 host 网络，经宿主映射端口访问）
DEFAULT_PG_HOST = "192.168.1.105"
DEFAULT_PG_PORT = 5433
DEFAULT_PG_DB = "pfm"
DEFAULT_PG_USER = "pfm"
DEFAULT_PG_PASSWORD = "pfm_secret"

CONF_PG_HOST = "pg_host"
CONF_PG_PORT = "pg_port"
CONF_CUSTOMER_ID = "customer_id"
