# 7. TLS 加密傳輸

> 手機端 ↔ 電腦端之間的 HTTP 通信升級為 HTTPS，防止本地網絡竊聽。

---

## 動機

默認情況下短信內容以明文 HTTP 傳輸。雖說是本地網絡，但在宿舍/咖啡廳/公司共用 WiFi 環境下仍有被嗅探的風險。

## 實現方式

### 方案 A：自簽名證書（推薦）

1. **生成證書**：

```bash
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes
```

2. **FastAPI 啓用 HTTPS**：

```python
uvicorn.run("server.main:app", host="0.0.0.0", port=8580,
            ssl_keyfile="key.pem", ssl_certfile="cert.pem")
```

3. **Android OkHttp 信任自簽名證書**：

```kotlin
// HttpClient.kt
private fun createUnsafeClient(): OkHttpClient {
    val trustAllCerts = arrayOf(object : X509TrustManager {
        override fun checkClientTrusted(...) {}
        override fun checkServerTrusted(...) {}
        override fun getAcceptedIssuers() = emptyArray()
    })

    return OkHttpClient.Builder()
        .sslSocketFactory(TrustAllSSLSocketFactory(), trustAllCerts[0])
        .hostnameVerifier { _, _ -> true }
        .build()
}
```

### 方案 B：mTLS（雙向認證）

手機端也持有客戶端證書，服務器驗證客戶端身份：

優點：防止未授權設備連接
缺點：配置複雜，非技術用戶難以部署

## 檔案變更

| 文件 | 變更 |
|------|------|
| `server/main.py` | `uvicorn.run()` 增加 `ssl_*` 參數 |
| `server/config.py` | 新增 `tls_enabled`, `tls_cert`, `tls_key` |
| `android/.../HttpClient.kt` | 新增 `createUnsafeClient()` 方法 |
| `android/.../ForwardService.kt` | URL 默認從 `http://` 改為 `https://` 當 TLS 啓用 |
| `.env.example` | 新增 `TLS_ENABLED=false` |

## 依賴

- 無新增依賴（SSL 是 Python 內置 + OkHttp 內置）
- 生成證書需要 `openssl`（系統工具，非 Python 包）

## 安全提醒

- 自簽名證書**不防止中間人攻擊**（MITM），只防止被動竊聽
- 若需要 MITM 防護，應使用 Let's Encrypt / 公共 CA 簽發的證書
- 家庭網絡使用自簽名已足夠

## 驗收標準

- HTTPS 啓動後 `/health` 可通過 `https://127.0.0.1:8580/health` 訪問
- Android App 切換到 HTTPS 後連接成功（🟢）
- 明文 HTTP 訪問返回拒絕連接
