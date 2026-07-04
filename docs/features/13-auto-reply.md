# 13. 短信自動回覆引擎

> 收到特定短信時，自動回覆預設內容或轉發到第三方 Webhook。

---

## 動機

收到「驗證碼」短信時自動轉發給家裏人？收到「門禁來訪」時自動回覆「請進」？自動回覆引擎讓短信不僅被讀取，還能產生行動。

## 架構

```
POST /api/sms ──→ 過濾 ──→ 聚合 ──→ 轉發 Telegram
                     │
                     ▼
              規則匹配引擎
                ├── 命中 → 執行 action
                │           ├── reply_sms: Android 端發送短信回覆
                │           ├── webhook:  POST 到外部 URL
                │           └── forward:  轉發到指定 Telegram 用戶
                └── 未命中 → 繼續正常流程
```

## 規則設計

```yaml
rules:
  - match:
      keyword: "驗證碼"
    action:
      type: forward
      to_chat: 987654321          # 轉發到另一個 Telegram 用戶

  - match:
      keyword: "門禁"
    action:
      type: reply_sms
      content: "請進"              # 自動回復「請進」

  - match:
      regex: "\\b(OK|確認|同意)\\b"
    action:
      type: webhook
      url: "https://hooks.example.com/sms"
```

## 實現

### 13.1 規則引擎

`server/reply_engine.py`：

```python
from dataclasses import dataclass
from enum import Enum

class ActionType(Enum):
    REPLY_SMS = "reply_sms"
    WEBHOOK = "webhook"
    FORWARD = "forward"

@dataclass
class Rule:
    keyword: str | None = None
    regex: str | None = None
    action_type: ActionType = ActionType.WEBHOOK
    action_target: str = ""    # phone number / URL / chat_id
    action_content: str = ""   # 回覆內容

class ReplyEngine:
    def __init__(self, rules: list[Rule]):
        self._rules = rules

    async def evaluate(self, sms: IncomingSMS) -> list[ActionResult]:
        results = []
        for rule in self._rules:
            if rule.keyword and rule.keyword in sms.body:
                results.append(await self._execute(rule, sms))
            elif rule.regex and re.search(rule.regex, sms.body):
                results.append(await self._execute(rule, sms))
        return results
```

### 13.2 Android 端發送短信

`ForwardService.kt` 新增處理 `reply_sms` action：

```kotlin
// 收到 action: reply_sms → 調用 SmsManager
private fun sendSmsReply(number: String, content: String) {
    val sms = SmsManager.getDefault()
    val parts = sms.divideMessage(content)
    sms.sendMultipartTextMessage(number, null, parts, null, null)
}
```

需要 `SEND_SMS` 權限（高敏感，可能被 Google Play 限制）。

## 檔案變更

| 文件 | 變更 |
|------|------|
| `server/reply_engine.py` | **新檔** — 規則匹配 + 執行 |
| `server/main.py` | POST /api/sms 中調用 evaluate |
| `server/config.py` | `reply_rules` 配置 |
| `android/.../ForwardService.kt` | 新增 `reply_sms` Action 處理 |
| `android/.../AndroidManifest.xml` | 新增 `SEND_SMS` 權限 |

## 依賴

- 無新增 Python 依賴
- Android 需 `SEND_SMS` 權限（敏感權限，可能被 Play Store 限制）

## 風險

- `SEND_SMS` 在 Android 上是非常敏感的權限，需顯式引導用戶
- 部分運營商可能阻擋自動發送的短信（高頻發送觸發風控）
- 回覆內容需完全由用戶預配置，不可開放任意回覆

## 驗收標準

- 收到含「門禁」的短信 → Android 自動回覆「請進」
- 收到含「驗證碼」的短信 → 轉發到指定 Telegram 用戶
- 規則可通過配置文件管理
- 空規則時不影響正常轉發流程
