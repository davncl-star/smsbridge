# 14. Home Assistant 集成

> 短信內容觸發 Home Assistant 自動化——「門禁來訪」→ 開門、「警報短信」→ 觸發警報。

---

## 動機

Home Assistant 是智能家居中樞。SMSBridge 收到特定短信時通過 Webhook 觸發 HA 自動化，讓短信也能驅動智能家居。

## 架構

```
手機短信 ──→ SMSBridge ──→ 過濾 + 聚合 ──→ Telegram
                              │
                         規則匹配（#13）
                              │
                          Webhook
                              │
                              ▼
                   Home Assistant Webhook
                              │
                              ▼
                        自動化場景
```

## 實現

### 14.1 SMSBridge 端：Webhook 動作

復用 #13 的規則引擎，新增 `action_type: webhook`：

```yaml
rules:
  - match:
      keyword: "門禁"
    action:
      type: webhook
      url: "http://homeassistant.local:8123/api/webhook/smsbridge_door"

  - match:
      keyword: "警報"
    action:
      type: webhook
      url: "http://homeassistant.local:8123/api/webhook/smsbridge_alarm"
```

### 14.2 規則執行

在 `reply_engine.py` 中：

```python
async def _execute_webhook(self, url: str, sms: IncomingSMS):
    async with httpx.AsyncClient() as client:
        await client.post(url, json={
            "number": sms.number,
            "body": sms.body,
            "sim_slot": sms.sim_slot,
            "sender": sms.sender,
            "received_at": sms.received_at.isoformat(),
        })
```

### 14.3 Home Assistant 端

在 `configuration.yaml` 中創建 Webhook 觸發器：

```yaml
automation:
  - alias: "門禁短信 → 開門"
    trigger:
      platform: webhook
      webhook_id: smsbridge_door
    action:
      - service: lock.open
        target:
          entity_id: lock.front_door
```

HA 收到 Webhook 後的 action 完全由用戶自定義。

### 14.4 無需 #13 的簡化方案

如果不想引入 #13 的規則引擎，可直接在主流程中硬編碼 Webhook 轉發：

```python
# server/main.py
async def forward_webhooks(sms: IncomingSMS, settings):
    hooks = settings.webhook_urls  # 逗號分隔的 URL 列表
    async with httpx.AsyncClient() as client:
        for url in hooks:
            try:
                await client.post(url, json=webhook_payload(sms), timeout=5)
            except Exception:
                log.warning("webhook failed: %s", url)
```

## 配置

```dotenv
# 簡化方案：每個短信都轉發到這些 Webhook
WEBHOOK_URLS=http://ha.local:8123/api/webhook/smsbridge_all

# 或結合 #13 規則做條件轉發
```

## 檔案變更

| 文件 | 變更 |
|------|------|
| `server/webhook.py` | **新檔** — Webhook 發送器 |
| `server/main.py` | 調用 webhook 發送 |
| `server/config.py` | `webhook_urls: list[str]` |

## 依賴

- 無新增 Python 依賴（httpx 已有）
- Home Assistant 端需允許來自 SMSBridge IP 的 Webhook

## 風險

- HA Webhook 無認證——確保 SMSBridge 和 HA 在安全網絡中
- 若 HA 無法訪問（不在同一子網），Webhook 會超時
- 高頻短信可能觸發 HA 自動化风暴（建議配合 #6 聚合窗口）

## 驗收標準

- HA 創建 Webhook 自動化 → 手機收到「門禁」短信 → HA 觸發自動化
- HA 不可達時不影響 SMSBridge 正常轉發
- 可通過 `WEBHOOK_URLS` 開關控制
