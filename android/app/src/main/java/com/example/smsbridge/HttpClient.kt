package com.example.smsbridge

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * 通往電腦端本地服務器的 HTTP 客戶端。
 *
 * 所有方法非阻塞，通過回調返回結果。
 */
class SmsHttpClient(private val baseUrl: String = DEFAULT_URL) {

    private val client = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .writeTimeout(5, TimeUnit.SECONDS)
        .build()

    /** POST 短信數據，回調在 OkHttp 線程池。 */
    fun postSms(
        sms: SmsData,
        onSuccess: (ForwardResult) -> Unit,
        onError: (String) -> Unit,
    ) {
        val body = sms.toJson().toString().toRequestBody(JSON_MEDIA_TYPE)
        val request = Request.Builder()
            .url("$baseUrl/api/sms")
            .post(body)
            .build()

        client.newCall(request).enqueue(object : okhttp3.Callback {
            override fun onResponse(call: okhttp3.Call, response: okhttp3.Response) {
                response.use {
                    val json = JSONObject(it.body?.string() ?: "{}")
                    onSuccess(
                        ForwardResult(
                            ok = json.optBoolean("ok"),
                            status = json.optString("status", "unknown"),
                            error = json.optString("error").ifEmpty { null },
                        )
                    )
                }
            }

            override fun onFailure(call: okhttp3.Call, e: java.io.IOException) {
                onError(e.message ?: "network error")
            }
        })
    }

    /** 健康檢查（心跳），用於判斷電腦端是否在線。 */
    fun checkHealth(
        onAlive: () -> Unit,
        onDead: (String) -> Unit,
    ) {
        val request = Request.Builder()
            .url("$baseUrl/health")
            .get()
            .build()

        client.newCall(request).enqueue(object : okhttp3.Callback {
            override fun onResponse(call: okhttp3.Call, response: okhttp3.Response) {
                response.use {
                    if (it.isSuccessful) onAlive() else onDead("http ${it.code}")
                }
            }

            override fun onFailure(call: okhttp3.Call, e: java.io.IOException) {
                onDead(e.message ?: "network error")
            }
        })
    }

    companion object {
        private const val DEFAULT_URL = "http://127.0.0.1:8580"
        private val JSON_MEDIA_TYPE = "application/json; charset=utf-8".toMediaType()
    }
}

/** POST /api/sms 的響應。 */
data class ForwardResult(
    val ok: Boolean,
    val status: String,
    val error: String?,
)
