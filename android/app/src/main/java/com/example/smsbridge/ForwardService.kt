package com.example.smsbridge

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.provider.Settings
import org.json.JSONObject
import java.util.LinkedList
import java.util.UUID
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/**
 * 前台服務：管理 HTTP 轉發、心跳檢測、斷線重試。
 *
 * 通信方式：
 * - 收到短信 → 立即 POST
 * - POST 失敗 → 加入重試隊列（最多 3 次，保留 10 條）
 * - 每 15 秒心跳 → 更新連接狀態
 */
class ForwardService : Service() {

    private lateinit var httpClient: SmsHttpClient
    private lateinit var deviceId: String
    private val executor = Executors.newSingleThreadScheduledExecutor()

    /** 待重試隊列（線程安全由 executor 串行保證） */
    private val retryQueue = LinkedList<QueuedSms>()

    /** 心跳計數（僅日誌用） */
    private var heartbeatTick = 0L

    // ── 生命週期 ─────────────────────────────────────────────────────────

    override fun onCreate() {
        super.onCreate()
        httpClient = SmsHttpClient(getServerUrl(this))
        deviceId = getOrCreateDeviceId(this)
        createNotificationChannel()
        startHeartbeat()
        updateState(State.DISCONNECTED)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.hasExtra(SmsReceiver.EXTRA_SMS_JSON) == true) {
            val json = intent.getStringExtra(SmsReceiver.EXTRA_SMS_JSON) ?: return START_STICKY
            val sms = parseSmsJson(json)
            if (sms != null) {
                forwardSms(sms)
            }
        }

        // 啟動前台通知（必須在 onCreate 後 5 秒內調用）
        startForeground(NOTIFY_ID, buildServiceNotification())
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        executor.shutdownNow()
        updateState(State.DISCONNECTED)
        super.onDestroy()
    }

    // ── SMS 轉發 ──────────────────────────────────────────────────────────

    private fun forwardSms(sms: SmsData) {
        executor.execute {
            val enriched = if (sms.deviceId == null) sms.copy(deviceId = deviceId) else sms
            doForward(enriched)
        }
    }

    private fun doForward(sms: SmsData) {
        httpClient.postSms(
            sms = sms,
            onSuccess = { result ->
                if (result.ok) {
                    log("forwarded to ${sms.number}")
                } else {
                    log("forward rejected: ${result.error}")
                }
            },
            onError = { error ->
                log("forward failed: $error — queuing retry")
                enqueueRetry(sms)
            },
        )
    }

    // ── 重試隊列 ──────────────────────────────────────────────────────────

    private fun enqueueRetry(sms: SmsData) {
        val existing = retryQueue.firstOrNull { it.sms == sms }
        if (existing != null) {
            existing.retries++
            if (existing.retries > MAX_RETRIES) {
                retryQueue.remove(existing)
                log("dropped sms to ${sms.number} after $MAX_RETRIES retries")
            }
        } else if (retryQueue.size < MAX_QUEUE) {
            retryQueue.add(QueuedSms(sms))
        }
    }

    private fun processRetryQueue() {
        val batch = retryQueue.toList()
        retryQueue.clear()
        for (queued in batch) {
            if (queued.retries < MAX_RETRIES) {
                doForward(queued.sms)
            }
        }
    }

    // ── 心跳 ──────────────────────────────────────────────────────────────

    private fun startHeartbeat() {
        executor.scheduleWithFixedDelay({
            heartbeatTick++
            httpClient.checkHealth(
                deviceId = deviceId,
                onAlive = {
                    updateState(State.CONNECTED)
                    processRetryQueue()
                },
                onDead = { err ->
                    updateState(State.DISCONNECTED)
                    if ((heartbeatTick % 4) == 0L) {
                        log("heartbeat: $err")
                    }
                },
            )
        }, 1, 15, TimeUnit.SECONDS)
    }

    // ── 狀態管理 ──────────────────────────────────────────────────────────

    private fun updateState(state: State) {
        if (_currentState != state) {
            _currentState = state
            // 更新前台通知文字
            val nm = getSystemService(NotificationManager::class.java)
            nm.notify(NOTIFY_ID, buildServiceNotification())
            // 廣播給 Activity（含時間戳）
            val intent = Intent(ACTION_STATE_CHANGED).apply {
                putExtra(EXTRA_STATE, state.name)
                putExtra(EXTRA_TIMESTAMP, System.currentTimeMillis())
            }
            sendBroadcast(intent)
        }
    }

    // ── 前台通知 ──────────────────────────────────────────────────────────

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                getString(R.string.channel_service),
                NotificationManager.IMPORTANCE_LOW,
            ).apply {
                description = getString(R.string.channel_service_desc)
            }
            val nm = getSystemService(NotificationManager::class.java)
            nm.createNotificationChannel(channel)
        }
    }

    private fun buildServiceNotification(): Notification {
        val openIntent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP
        }
        val pendingOpen = PendingIntent.getActivity(
            this, 0, openIntent,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )

        val statusText = when (_currentState) {
            State.CONNECTED -> getString(R.string.status_connected)
            State.DISCONNECTED -> getString(R.string.status_disconnected)
            State.CHECKING -> getString(R.string.status_connecting)
        }

        return Notification.Builder(this, CHANNEL_ID)
            .setContentTitle("SMSBridge")
            .setContentText(statusText)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentIntent(pendingOpen)
            .setOngoing(true)
            .build()
    }

    // ── 工具 ──────────────────────────────────────────────────────────────

    private fun log(msg: String) {
        android.util.Log.i(TAG, msg)
    }

    companion object {
        const val TAG = "SMSBridge"

        const val CHANNEL_ID = "smsbridge_service"
        const val NOTIFY_ID = 1001
        const val MAX_RETRIES = 3
        const val MAX_QUEUE = 10

        const val ACTION_STATE_CHANGED = "com.example.smsbridge.STATE_CHANGED"
        const val EXTRA_STATE = "state"
        const val EXTRA_TIMESTAMP = "timestamp_ms"

        // 當前連接狀態（線程安全用於單線程 executor，讀取用 @Volatile）
        @Volatile
        private var _currentState = State.DISCONNECTED
        val currentState: State get() = _currentState

        fun getServerUrl(context: Context): String {
            // TODO: 從 SharedPreferences 讀取可配置 URL
            return "http://127.0.0.1:8580"
        }

        fun getOrCreateDeviceId(context: Context): String {
            val prefs = context.getSharedPreferences("smsbridge", Context.MODE_PRIVATE)
            var id = prefs.getString("device_id", null)
            if (id == null) {
                id = UUID.randomUUID().toString().take(8)
                prefs.edit().putString("device_id", id).apply()
            }
            return id
        }

        private fun parseSmsJson(json: String): SmsData? {
            return try {
                val obj = JSONObject(json)
                SmsData(
                    sender = obj.optString("sender", ""),
                    number = obj.optString("number", ""),
                    body = obj.optString("body", ""),
                    receivedAt = obj.optString("received_at", ""),
                    simSlot = obj.optInt("sim_slot", 0),
                    deviceId = obj.optString("device_id", "").ifEmpty { null },
                )
            } catch (e: Exception) {
                android.util.Log.w(TAG, "parseSmsJson failed", e)
                null
            }
        }
    }
}

/** 連接狀態枚舉。 */
enum class State { CONNECTED, DISCONNECTED, CHECKING }

/** 重試隊列條目。 */
private data class QueuedSms(
    val sms: SmsData,
    var retries: Int = 0,
)
