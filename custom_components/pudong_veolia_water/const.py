"""Constants for the Pudong Veolia Water integration."""

DOMAIN = "pudong_veolia_water"

API_URL = "https://mtu.pudongwater.com/wkf/WX/GetBill"
API_USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 5.0; SM-N9100 Build/LRX21V) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 "
    "Chrome/37.0.0.0 Mobile Safari/537.36 "
    "MicroMessenger/6.0.2.56 NetType/WIFI"
)

# 双月出账，6 小时刷新一次足够；避免对非官方接口造成压力
UPDATE_INTERVAL_HOURS = 6
