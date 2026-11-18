# 浦东威立雅水费 Home Assistant 集成

把上海浦东威立雅（威客服）的水费账单接入 Home Assistant。基于威客服小程序使用的账单接口，无需登录、无需 token、无需浏览器。

> ⚠️ 该接口是威客服小程序使用的**非官方接口**，未获浦东威立雅官方授权，可能随时变更或失效。本项目仅供个人在家庭自动化中使用，请自行评估风险。

## 功能

- 通过 UI（设置 → 设备与服务 → 添加集成）配置销根号，支持多个户号
- 双月账单数据，每 6 小时刷新一次
- 提供 8 个传感器实体，账单原始字段放在实体属性中
- 实体带完整属性：户名、地址、账期、表读数、抄表/缴费日期、近 3 期历史

## 实体

以销根号 `123456789` 为例，创建设备「威立雅水费 123456789」，包含：

| 实体 | 说明 | 单位 |
|---|---|---|
| `sensor.威立雅水费_xxx_本期应付` | 本期实付金额（取自 `SUMPAY`） | CNY |
| `sensor.威立雅水费_xxx_本期用水量` | 生活用水量 `WATERNUM` | m³ |
| `sensor.威立雅水费_xxx_本期污水量` | 污水量 `DIRTYNUM` | m³ |
| `sensor.威立雅水费_xxx_本期水费` | 水费 `WATERFEE` | CNY |
| `sensor.威立雅水费_xxx_本期污水处理费` | 污水处理费 `DIRTYFEE` | CNY |
| `sensor.威立雅水费_xxx_账户结余` | 账户结余 `NOWLEFT` | CNY |
| `sensor.威立雅水费_xxx_水表读数` | 本期表底数，累计型 | m³ |
| `sensor.威立雅水费_xxx_缴费状态` | 已缴 / 未缴 | — |

每个实体的属性中包含：`account_id`、`customer`、`address`、`bill_period`、`prev_meter_reading`、`meter_reading`、`copy_date`、`pay_time`、`next_copy_date`、`water_price`、`sewage_price`、`history_periods`（近 3 期）。

## 字段口径

- **本期应付** 取 `SUMPAY`（实付），而非 `SUMFEE`（账面合计）。实测两者可能相差 0.05 元（上期结余结转）。
- **接口每次最多返回近 3 期账单**，`kaishisj` 向前调无效，无法取得更早历史。若需长期趋势，需要自行按周期落库累积。
- 账单为**双月出账**，非日级用量，不适合做实时漏水告警。

## 安装

### HACS（推荐）

1. HACS → 右上角菜单 → 自定义存储库
2. 类别选 `Integration`，URL 填 `https://github.com/juhuan/ha-pudong-veolia-water`
3. 搜索「浦东威立雅水费」并安装
4. 重启 Home Assistant
5. 设置 → 设备与服务 → 添加集成 → 搜索「浦东威立雅水费」

### 手动

将 `custom_components/pudong_veolia_water/` 复制到 HA 配置目录的 `custom_components/` 下，重启 HA，然后添加集成。

## 配置

添加集成时输入账单上的**销根号**（9 位，通常以 9 开头）。可在「威客服」小程序 → 账单查询页查看。

## 故障排查

- 集成加载失败且日志出现 `cannot_connect`：确认销根号正确，且 HA 服务器能访问 `mtu.pudongwater.com`。
- 手动触发刷新：开发者工具 → 动作 → `homeassistant.update_entity`，选择任一水费实体。

## 接口

```
GET https://mtu.pudongwater.com/wkf/WX/GetBill
    ?cid=<销根号>&kaishisj=<YYYY-MM>&jieshusj=
```

返回 `{"code":"1", "data": "<JSON 字符串>", "cid": "...", "dz": "..."}`，`data` 需二次 JSON 解析。接口按账期倒序返回。

## License

MIT
