# 5. Docker 部署

> 電腦端服務器一鍵 Docker 部署，適合 NAS / VPS / Docker Desktop 常駐運行。

---

## 架構

```
docker-compose.yml
├── smsbridge-server
│   ├── port 8580
│   ├── .env volume
│   ├── logs volume
│   └── restart: unless-stopped
```

不包含 Android 端（手機端仍需單獨安裝 APK）。

## Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY server/ server/
COPY scripts/ scripts/

RUN pip install uv && uv sync --no-dev --frozen

EXPOSE 8580
VOLUME ["/app/logs"]
ENTRYPOINT ["uv", "run", "smsbridge", "start"]
```

## docker-compose.yml

```yaml
version: "3.8"
services:
  smsbridge:
    build: .
    container_name: smsbridge
    ports:
      - "8580:8580"
    env_file: .env
    volumes:
      - ./logs:/app/logs
      - ./.env:/app/.env:ro
    restart: unless-stopped
    network_mode: host   # 如需 mDNS / 同網絡 ADB 發現
```

### 說明

- `network_mode: host` 在 Linux 上可直接用 `127.0.0.1` 訪問主機 ADB
- 若用橋接模式（bridge），需確保 ADB server 在 host 上監聽 `0.0.0.0`
- `restart: unless-stopped` 確保開機自啓

## 使用方式

```bash
cd smsbridge
docker compose up -d
docker compose logs -f    # 查看日誌
docker compose down       # 停止
```

## 靜態構建（無需本地 Docker）

也可提供 `docker pull` 方式。但 SMSBridge 的 server 依賴極少，自建不複雜，無需 CI/CD。

## 檔案變更

| 文件 | 變更 |
|------|------|
| `Dockerfile` | **新檔** |
| `docker-compose.yml` | **新檔** |
| `.dockerignore` | **新檔** — 排除 .venv / android / __pycache__ |

## 風險

- Windows Docker Desktop + ADB 配合較麻煩（adb 在 host 上跑，容器裏無法直接調用）
- ADB 容器化方案：傳遞 `//./pipe/adb`（Windows）或 `/dev/bus/usb`（Linux）
- 更簡單：ADB 在 host 上跑，smsbridge server 在容器中只收 HTTP

## 驗收標準

- `docker compose up -d` → 服務器啓動
- `curl localhost:8580/health` → 200
- `docker compose logs` → 日誌正常
