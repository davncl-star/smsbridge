package com.example.smsbridge

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.provider.Telephony
import android.telephony.SmsMessage

/**
 * 監聽系統 SMS_RECEIVED 廣播，解析短信並交由 ForwardService 轉發。
 *
 * Android 14+ 注意：
 * - 動態註冊不支持 SMS_RECEIVED（必須靜態註冊）
 * - 部分廠商 ROM 可能需要引導用戶加入"自啟動"白名單
 */
class SmsReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) return

        val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
        if (messages.isEmpty()) return

        // 獲取 SIM 卡槽信息（subscription ID）
        val subId = intent.extras?.getInt(SUBSCRIPTION_KEY, -1) ?: -1

        // 本機設備 ID（略，由 ForwardService 統一管理）
        val sms = SmsData.fromSmsMessages(
            messages = messages,
            format = intent.extras?.getString("format"),
            subId = subId,
            deviceId = null, // ForwardService 注入
        )

        // 啟動 / 通知 ForwardService 處理
        val serviceIntent = Intent(context, ForwardService::class.java).apply {
            putExtra(EXTRA_SMS_JSON, sms.toJson().toString())
        }
        context.startForegroundService(serviceIntent)
    }

    companion object {
        /** API 26+ 的 subscription extra key。 */
        private const val SUBSCRIPTION_KEY = "subscription"
        const val EXTRA_SMS_JSON = "sms_json"
    }
}
