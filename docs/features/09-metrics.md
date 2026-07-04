# 9. 監控端點

> 暴露 `/metrics` 端點，記錄轉發/過濾/失敗數量，可供 Prometheus 抓取。

---

## 動機

想知道 SMSBridge 的運行健康狀況：每天轉發多少短信？過濾了多少垃圾？失敗率多少？

## 實現

### 方案 A：簡單 JSON 端點

```python
# server/metrics.py
from dataclasses import dataclass, field
import threading

@dataclass
class Metrics:
    forwarded: int = 0
    filtered: int = 0
    failed: int = 0
    queued: int = 0
    aggregated: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def incr(self, name: str):
        with self._lock:
            setattr(self, name, getattr(self, name, 0) + 1)

metrics = Metrics()
```

在 `main.py` 中引入並在各分支調用：

```python
from .metrics import metrics

# filter 攔截時
metrics.incr("filtered")
# 發送成功時
metrics.incr("forwarded")
# 發送失敗時
metrics.incr("failed")
```

暴露端點：

```python
@app.get("/metrics")
async def get_metrics():
    return {
        "forwarded": metrics.forwarded,
        "filtered": metrics.filtered,
        "failed": metrics.failed,
        "queued": metrics.queued,
        "aggregated": metrics.aggregated,
        "uptime_seconds": time.monotonic() - _start_time,
    }
```

### 方案 B：Prometheus 格式

適合已經有 Prometheus + Grafana 基礎設施的用戶：

```python
from prometheus_client import Counter, generate_latest, REGISTRY

forwarded = Counter("smsbridge_forwarded_total", "轉發成功數")
filtered = Counter("smsbridge_filtered_total", "過濾攔截數")
failed = Counter("smsbridge_failed_total", "轉發失敗數")

@app.get("/metrics")
async def prometheus_metrics():
    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain; version=0.0.4",
    )
```

## 檔案變更

| 文件 | 變更 |
|------|------|
| `server/metrics.py` | **新檔** — Metrics 數據結構 |
| `server/main.py` | 注入 metrics 到 filter/forward/fail 分支 |
| `server/filter_engine.py` | 傳入 metrics 回調 |

## 依賴

- 方案 A：無新增依賴
- 方案 B：`prometheus_client`

## 驗收標準

- `GET /metrics` → JSON 包含所有計數器
- 轉發一條短信 → `forwarded` +1
- 攔截一條短信 → `filtered` +1
- 服務器重啓後計數器重置（如需持久化可結合 #6 SQLite）
