# 10. 多通道推送

> 同時推送短信通知到多個平臺：Telegram、ServerChan、PushDeer、Bark、PushPlus。

---

## 動機

Telegram 在中國大陸需要 VPN；備用通道確保短信通知不丟失。Bark（iOS）和 ServerChan（微信）是國內用戶常用的備選。

## 架構

```
POST /api/sms ──→ forwarder dispatch
                    ├── telegram    (已實現)
                    ├── serverchan  (微信)
                    ├── pushdeer    (自建)
                    ├── bark        (iOS)
                    └── pushplus    (微信)
```

## 實現

### 10.1 推送通道接口

`server/channels/__init__.py`：

```python
from abc import ABC, abstractmethod

class PushChannel(ABC):
    @abstractmethod
    async def send(self, text: str, settings) -> tuple[bool, str | None]:
        """返回 (ok, error_message)"""
        pass
```

### 10.2 Telegram（已有）

```python
# server/channels/telegram.py
class TelegramChannel(PushChannel):
    async def send(self, text, settings):
        ok, _, err = await send_text(text, settings)
        return ok, err
```

### 10.3 ServerChan

```python
# server/channels/serverchan.py
class ServerChanChannel(PushChannel):
    async def send(self, text, settings):
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://sctapi.ftqq.com/{settings.serverchan_token}.send",
                data={"title": "SMSBridge", "desp": text},
            )
            return resp.is_success, resp.text
```

### 10.4 Bark（iOS）

```python
# server/channels/bark.py
class BarkChannel(PushChannel):
    async def send(self, text, settings):
        url = f"{settings.bark_server}/{settings.bark_key}/{text}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            return resp.is_success, resp.text
```

### 10.5 調度器

`server/forwarder.py`：

```python
_channels: dict[str, PushChannel] = {}

def register(name: str, channel: PushChannel):
    _channels[name] = channel

async def dispatch(sms: IncomingSMS, settings) -> list[ForwardResult]:
    text = format_sms(sms)
    results = []
    for name, ch in _channels.items():
        ok, err = await ch.send(text, settings)
        results.append(ForwardResult(ok=ok, error=err, status="delivered" if ok else "failed"))
    return results
```

## 配置

```dotenv
# 通道開關
CHANNELS=telegram,serverchan

# ServerChan
SERVERCHAN_TOKEN=sct12345...

# Bark
BARK_SERVER=https://api.day.app
BARK_KEY=xxxxxxxx

# PushDeer
PUSHDEER_KEY=pd123...
```

## 檔案變更

| 文件 | 變更 |
|------|------|
| `server/channels/__init__.py` | **新檔** — PushChannel 接口 |
| `server/channels/telegram.py` | **新檔** — Telegram 通道（包裝現有邏輯） |
| `server/channels/serverchan.py` | **新檔** |
| `server/channels/bark.py` | **新檔** |
| `server/channels/pushdeer.py` | **新檔** |
| `server/forwarder.py` | **新檔** — 通道調度器 |
| `server/main.py` | 改用 forwarder.dispatch |
| `server/config.py` | 新增 `channels` + 各通道 token |
| `pyproject.toml` | 無新增依賴（httpx 已有） |

## 風險

- ServerChan / PushDeer 等依賴外網，純 ADB + USB 場景不可用
- 各通道消息格式可能不同（Markdown / HTML / 純文本）
- 增加通道後請注意 API rate limit

## 驗收標準

- 配置 `CHANNELS=telegram` → 僅 Telegram 推送（向後兼容）
- 配置 `CHANNELS=telegram,serverchan` → 兩個通道都收到
- 某通道失敗（如 Bark 服務不可達）不影響其他通道
