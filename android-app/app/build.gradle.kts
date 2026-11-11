plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

val appVersion = "2.9.7"

// Only the GitHub Actions secret supplies the private host. It must never
// appear in committed source, public workflow logs, or a public APK release.
val provisionedUrl = providers.environmentVariable("DHANPULSE_PRIVATE_BACKEND_URL").orNull
    ?.trim()?.trimEnd('/') ?: ""
val escapedUrl = provisionedUrl.replace("\\", "\\\\").replace("\"", "\\\"")

android {
    namespace = "in.dhanpulse.personal"
    compileSdk = 35

    defaultConfig {
        applicationId = "in.dhanpulse.personal.stable"
        minSdk = 26
        targetSdk = 35
        versionCode = 82
        versionName = appVersion
        buildConfigField("String", "PRIVATE_API_BASE_URL", "\"$escapedUrl\"")
    }

    buildTypes {
        getByName("debug") {
            // Distinct installable preview until the original Stable signing key is available.
            // It cannot replace an existing Stable installation or read its private data.
            applicationIdSuffix = ".monitor82"
            manifestPlaceholders["appLabel"] = "DhanPulse Monitor 82"
        }
        getByName("release") {
            manifestPlaceholders["appLabel"] = "DhanPulse Stable"
        }
    }

    buildFeatures { compose = true; buildConfig = true }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    testImplementation("junit:junit:4.13.2")
    implementation(platform("androidx.compose:compose-bom:2024.12.01"))
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.10.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    debugImplementation("androidx.compose.ui:ui-tooling")
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")
    implementation("androidx.security:security-crypto:1.1.0-alpha06")
}
