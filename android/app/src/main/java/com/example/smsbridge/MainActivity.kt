package com.example.smsbridge

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : ComponentActivity() {

    /** 權限請求啟動器 */
    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { /* 權限結果由 UI 層的狀態管理處理 */ }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    SmsBridgeApp(
                        onRequestPermissions = { requestMissingPermissions() },
                    )
                }
            }
        }
    }

    private fun requestMissingPermissions() {
        val needed = getMissingPermissions(this)
        if (needed.isNotEmpty()) {
            permissionLauncher.launch(needed.toTypedArray())
        }
    }

    companion object {
        fun getMissingPermissions(context: Context): List<String> {
            val perms = mutableListOf<String>()

            if (ContextCompat.checkSelfPermission(context, Manifest.permission.RECEIVE_SMS)
                != PackageManager.PERMISSION_GRANTED
            ) {
                perms.add(Manifest.permission.RECEIVE_SMS)
            }

            if (ContextCompat.checkSelfPermission(context, Manifest.permission.READ_PHONE_STATE)
                != PackageManager.PERMISSION_GRANTED
            ) {
                perms.add(Manifest.permission.READ_PHONE_STATE)
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                if (ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS)
                    != PackageManager.PERMISSION_GRANTED
                ) {
                    perms.add(Manifest.permission.POST_NOTIFICATIONS)
                }
            }

            return perms.toList()
        }

        fun allPermissionsGranted(context: Context): Boolean {
            return getMissingPermissions(context).isEmpty()
        }
    }
}

// ── Compose ────────────────────────────────────────────────────────────────

/** 時間戳格式化 */
private val TIMESTAMP_FMT = SimpleDateFormat("HH:mm:ss", Locale.getDefault())

/** 單條日誌條目 */
private data class LogEntry(
    val time: String,
    val fromState: String?,
    val toState: String,
)

@Composable
fun SmsBridgeApp(onRequestPermissions: () -> Unit) {
    val context = LocalContext.current

    var state by remember { mutableStateOf(ForwardService.currentState) }
    var serviceRunning by remember { mutableStateOf(false) }
    val logEntries = remember { mutableStateListOf<LogEntry>() }

    // 監聽 ForwardService 狀態廣播
    DisposableEffect(Unit) {
        val receiver = object : BroadcastReceiver() {
            override fun onReceive(context: Context, intent: Intent) {
                val newState = try {
                    State.valueOf(intent.getStringExtra(ForwardService.EXTRA_STATE) ?: "")
                } catch (_: IllegalArgumentException) {
                    ForwardService.currentState
                }
                val tsMs = intent.getLongExtra(ForwardService.EXTRA_TIMESTAMP, System.currentTimeMillis())
                val timeStr = TIMESTAMP_FMT.format(Date(tsMs))
                val oldLabel = when (state) {
                    State.CONNECTED -> "已連接"
                    State.DISCONNECTED -> "未連接"
                    State.CHECKING -> "檢測中"
                }
                val newLabel = when (newState) {
                    State.CONNECTED -> "已連接"
                    State.DISCONNECTED -> "未連接"
                    State.CHECKING -> "檢測中"
                }
                logEntries.add(0, LogEntry(time = timeStr, fromState = oldLabel, toState = newLabel))
                state = newState
            }
        }
        context.registerReceiver(receiver, IntentFilter(ForwardService.ACTION_STATE_CHANGED),
            Context.RECEIVER_EXPORTED
        )
        onDispose { context.unregisterReceiver(receiver) }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
    ) {
        // ── 頂部：標題 + 權限 + 連接狀態 ──
        Text(
            text = "SMSBridge",
            style = MaterialTheme.typography.headlineMedium,
        )

        Spacer(Modifier.height(12.dp))

        PermissionStatus()

        Spacer(Modifier.height(8.dp))

        ConnectionCard(state = state)

        Spacer(Modifier.height(12.dp))

        // ── 控制列 ──
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Button(
                onClick = {
                    if (serviceRunning) {
                        context.stopService(Intent(context, ForwardService::class.java))
                        serviceRunning = false
                    } else {
                        if (!MainActivity.allPermissionsGranted(context)) {
                            onRequestPermissions()
                            return@Button
                        }
                        context.startForegroundService(
                            Intent(context, ForwardService::class.java)
                        )
                        serviceRunning = true
                    }
                },
                modifier = Modifier.weight(1f),
            ) {
                Text(if (serviceRunning) "停止服務" else "啟動服務")
            }
            Button(
                onClick = { logEntries.clear() },
            ) {
                Text("清除日誌")
            }
        }

        Spacer(Modifier.height(8.dp))

        // ── 設備 ID ──
        val deviceId = remember {
            ForwardService.getOrCreateDeviceId(context)
        }
        Text(
            text = "設備 ID: $deviceId",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        Spacer(Modifier.height(12.dp))

        // ── Log Panel ──
        Text(
            text = "連接日誌",
            style = MaterialTheme.typography.titleSmall,
            fontWeight = FontWeight.Bold,
        )
        Spacer(Modifier.height(4.dp))

        val listState = rememberLazyListState()
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
                .background(
                    Color(0xFF1E1E1E),
                    RoundedCornerShape(8.dp),
                )
                .padding(8.dp),
        ) {
            if (logEntries.isEmpty()) {
                Text(
                    text = "（尚無日誌，啟動服務後將自動記錄斷線/重連事件）",
                    color = Color(0xFF888888),
                    fontSize = 12.sp,
                    fontFamily = FontFamily.Monospace,
                )
            } else {
                LazyColumn(
                    state = listState,
                    modifier = Modifier.fillMaxSize(),
                ) {
                    items(logEntries) { entry ->
                        val fromCol = entry.fromState?.let { from ->
                            when (from) {
                                "已連接" -> Color(0xFF4CAF50)
                                "未連接" -> Color(0xFFF44336)
                                else -> Color(0xFFFF9800)
                            }
                        }
                        val toCol = when (entry.toState) {
                            "已連接" -> Color(0xFF4CAF50)
                            "未連接" -> Color(0xFFF44336)
                            else -> Color(0xFFFF9800)
                        }
                        val arrow = if (entry.fromState != null) " → " else "  "
                        Row(
                            modifier = Modifier.padding(vertical = 2.dp),
                        ) {
                            Text(
                                text = "[${entry.time}]",
                                color = Color(0xFF888888),
                                fontSize = 12.sp,
                                fontFamily = FontFamily.Monospace,
                            )
                            Spacer(Modifier.width(4.dp))
                            if (entry.fromState != null) {
                                Text(
                                    text = entry.fromState,
                                    color = fromCol ?: Color(0xFF888888),
                                    fontSize = 12.sp,
                                    fontFamily = FontFamily.Monospace,
                                )
                            }
                            Text(
                                text = arrow,
                                color = Color(0xFF888888),
                                fontSize = 12.sp,
                                fontFamily = FontFamily.Monospace,
                            )
                            Text(
                                text = entry.toState,
                                color = toCol,
                                fontSize = 12.sp,
                                fontFamily = FontFamily.Monospace,
                                fontWeight = FontWeight.Bold,
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun PermissionStatus() {
    val context = LocalContext.current
    val missing = remember { MainActivity.getMissingPermissions(context) }

    val (color, text) = if (missing.isEmpty()) {
        Color(0xFF4CAF50) to "✓ 所有權限已授予"
    } else {
        Color(0xFFF44336) to "缺少 ${missing.size} 項權限"
    }

    Row(
        verticalAlignment = Alignment.CenterVertically,
    ) {
        StatusDot(color)
        Spacer(Modifier.width(8.dp))
        Text(text, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun ConnectionCard(state: State) {
    val (color, label) = when (state) {
        State.CONNECTED    -> Color(0xFF4CAF50) to "已連接"
        State.DISCONNECTED -> Color(0xFFF44336) to "未連接"
        State.CHECKING     -> Color(0xFFFF9800) to "檢測中…"
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
        ),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            StatusDot(color, size = 16.dp)
            Spacer(Modifier.width(12.dp))
            Text(
                text = "連接狀態：$label",
                style = MaterialTheme.typography.bodyLarge,
            )
        }
    }
}

@Composable
private fun StatusDot(color: Color, size: Dp = 10.dp) {
    Surface(
        shape = CircleShape,
        color = color,
        modifier = Modifier.size(size),
    ) { }
}
