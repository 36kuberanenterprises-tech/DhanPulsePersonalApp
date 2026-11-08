package `in`.dhanpulse.personal.data

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import `in`.dhanpulse.personal.MainActivity

/**
 * Android 15 prohibits dataSync foreground-service starts from BOOT_COMPLETED.
 * Do not attempt a forbidden automatic restart; show an honest reminder instead.
 */
class MonitorBootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        if (intent?.action !in setOf(Intent.ACTION_BOOT_COMPLETED,
                Intent.ACTION_MY_PACKAGE_REPLACED)) return
        val state = MarketMonitorStore(context)
        state.running = false
        state.uiVisible = false
        if (!state.requested) return
        state.status = "RESTART REQUIRED"
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS)
            != PackageManager.PERMISSION_GRANTED) return
        val manager = context.getSystemService(NotificationManager::class.java)
        val channelId = "dhanpulse_market_status"
        manager.createNotificationChannel(NotificationChannel(channelId,
            "DhanPulse market monitoring", NotificationManager.IMPORTANCE_LOW))
        val open = PendingIntent.getActivity(context, 75,
            Intent(context, MainActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        manager.notify(7303, NotificationCompat.Builder(context, channelId)
            .setSmallIcon(android.R.drawable.stat_notify_sync)
            .setContentTitle("Restart DhanPulse monitoring")
            .setContentText("Android restarted. Open the app and start monitoring when logged in.")
            .setContentIntent(open)
            .setAutoCancel(true)
            .build())
    }
}
