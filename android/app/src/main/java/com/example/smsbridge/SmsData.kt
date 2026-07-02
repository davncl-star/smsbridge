package com.example.smsbridge

import android.telephony.SmsMessage
import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * 短信數據模型 —— 與 server/models.py 的 IncomingSMS 一一對應。
 *
 * 使用 org.json 而非 Gson/Moshi，零額外依賴。
 */
data class SmsData(
    val sender: String,     // 發件人姓名（通訊錄匹配後），空字符串表示未知
    val number: String,     // 發件人手機號
    val body: String,       // 短信正文
    val receivedAt: String, // ISO 8601 時間戳，如 "2026-06-30T17:00:00"
    val simSlot: Int,       // SIM 卡槽位 (0/1)
    val deviceId: String?,  // 設備唯一標識（用於多手機場景）
) {
    fun toJson(): JSONObject = JSONObject().apply {
        put("sender", sender)
        put("number", number)
        put("body", body)
        put("received_at", receivedAt)
        put("sim_slot", simSlot)
        put("device_id", deviceId ?: JSONObject.NULL)
    }

    companion object {
        private val ISO_FORMAT = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US)

        /**
         * 從 Android SmsMessage 數組創建 SmsData。
         * @param messages  系統廣播傳來的 pdu 解析結果
         * @param format    短信格式 ("3gpp" / "3gpp2")
         * @param subId     subscription ID（區分 SIM 卡；-1 則為未知）
         * @param deviceId  本機設備 ID（由 ForwardService 注入）
         */
        fun fromSmsMessages(
            messages: Array<SmsMessage>,
            format: String?,
            subId: Int,
            deviceId: String?,
        ): SmsData {
            // 合併多段短信（長短信拆分）
            val body = messages.joinToString("") { it.displayMessageBody ?: "" }

            // 取第一條的發件人信息（長短信 sender 一致）
            val first = messages.first()
            val sender = first.displayOriginatingAddress ?: ""

            // 獲取號碼（與 sender 通常相同；部分運營商可能不同）
            val number = first.originatingAddress ?: sender

            return SmsData(
                sender = sender,
                number = number,
                body = body,
                receivedAt = ISO_FORMAT.format(Date()),
                simSlot = if (subId >= 0) subId % 2 else 0,
                deviceId = deviceId,
            )
        }
    }
}
