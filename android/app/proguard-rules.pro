# SMSBridge ProGuard rules

# OkHttp
-dontwarn okhttp3.**
-dontwarn okio.**
-keep class okhttp3.** { *; }
-keep interface okhttp3.** { *; }

# Keep SMS data model
-keep class com.example.smsbridge.SmsData { *; }
