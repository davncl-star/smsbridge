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
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat

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

@Composable
fun SmsBridgeApp(onRequestPermissions: () -> Unit) {
    val context = LocalContext.current

    var state by remember { mutableStateOf(ForwardService.currentState) }
    var serviceRunning by remember { mutableStateOf(false) }

    // 監聽 ForwardService 狀態廣播
    DisposableEffect(Unit) {
        val receiver = object : BroadcastReceiver() {
            override fun onReceive(context: Context, intent: Intent) {
                state = try {
                    State.valueOf(intent.getStringExtra(ForwardService.EXTRA_STATE) ?: "")
                } catch (_: IllegalArgumentException) {
                    ForwardService.currentState
                }
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
            .padding(24.dp),
        verticalArrangement = Arrangement.Top,
    ) {
        Text(
            text = "SMSBridge",
            style = MaterialTheme.typography.headlineMedium,
        )

        Spacer(Modifier.height(16.dp))

        // ── 權限狀態 ──
        PermissionStatus()

        Spacer(Modifier.height(12.dp))

        // ── 連接狀態 ──
        ConnectionCard(state = state)

        Spacer(Modifier.height(16.dp))

        // ── 控制按鈕 ──
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
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(if (serviceRunning) "停止服務" else "啟動服務")
        }

        Spacer(Modifier.height(12.dp))

        // ── 設備 ID ──
        val deviceId = remember {
            ForwardService.getOrCreateDeviceId(context)
        }
        Text(
            text = "設備 ID: $deviceId",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
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
