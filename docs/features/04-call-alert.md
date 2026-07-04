# 4. 來電提醒

> 手機接到來電時，SMSBridge 推送一條 Telegram 通知。

---

## 動機

Scam 來電、快遞、外賣——有時比短信更需要知道。雙卡用戶尤其需要區分哪個號碼來電。

## 數據模型

與短信共用同一個 POST 端點，透過 `body` 區分：

```json
{
  "sender": "快遞小哥",
  "number": "+861390000000",
  "body": "[電話]",
  "received_at": "2026-07-04T14:30:00",
  "sim_slot": 0,
  "device_id": "mi8"
}
```

服務器端自動將 `[電話]` 格式化為 📞 前綴。

## Android 端實現

### 4.1 監聽 `PHONE_STATE`

`CallReceiver.kt`（或併入 `SmsReceiver.kt`）：

```kotlin
class CallReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != TelephonyManager.ACTION_PHONE_STATE_CHANGED) return

        val state = intent.getStringExtra(TelephonyManager.EXTRA_STATE)
        if (state != TelephonyManager.EXTRA_STATE_RINGING) return  // 僅來電時觸發

        val number = intent.getStringExtra(TelephonyManager.EXTRA_INCOMING_NUMBER) ?: ""
        val simSlot = intent.getIntExtra("subscription", -1)

        val sms = SmsData(
            sender = "",
            number = number,
            body = "[電話]",
            receivedAt = ISO_FORMAT.format(Date()),
            simSlot = if (simSlot >= 0) simSlot % 2 else 0,
            deviceId = ForwardService.getOrCreateDeviceId(context),
        )

        val serviceIntent = Intent(context, ForwardService::class.java).apply {
            putExtra(SmsReceiver.EXTRA_SMS_JSON, sms.toJson().toString())
        }
        context.startForegroundService(serviceIntent)
    }
}
```

### 4.2 Manifest 添加

```xml
<uses-permission android:name="android.permission.READ_PHONE_STATE" />  <!-- 已有 -->

<receiver
    android:name=".CallReceiver"
    android:exported="true">
    <intent-filter>
        <action android:name="android.intent.action.PHONE_STATE" />
    </intent-filter>
</receiver>
```

權限 `READ_PHONE_STATE` 已在 Phase 2 申請，無需額外權限處理。

## 服務器端變化

格式化 `send_sms` 時檢測 `body == "[電話]"` 改用 📞 模板：

```python
def format_call(sms: IncomingSMS) -> str:
    sim = f"SIM{sms.sim_slot}" if sms.sim_slot else "SIM?"
    who = sms.sender or sms.number
    ts = sms.received_at.strftime("%Y-%m-%d %H:%M:%S")
    return (
        f"📞 <b>來電</b>  <i>{sim}</i>\n"
        f"<b>{escape(who)}</b>  <code>{escape(sms.number)}</code>\n"
        f"<i>{escape(ts)}</i>"
    )
```

## 可選增強

- 僅轉發非通訊錄來電（過濾已知聯繫人）
- 僅在 `forward_calls=true` 時轉發（配置開關）
- 通話結束後推送通話時長（需監聽 `IDLE` 狀態）

## 檔案變更

| 文件 | 變更 |
|------|------|
| `android/.../CallReceiver.kt` | **新檔** — PHONE_STATE 監聽 |
| `android/.../AndroidManifest.xml` | 註冊 CallReceiver |
| `server/telegram.py` | `format_sms` 中檢測 `[電話]` 改用 📞 |
| `.env.example` | 新增 `FORWARD_CALLS=true` |

## 驗收標準

- Mi8 收到來電 → 5 秒內 Telegram 收到 📞 通知
- Telegram 消息包含號碼 + SIM 槽
- 掛斷後不再發送（僅 RINGING 狀態觸發）
