plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

val appVersion = "2.9.7"
// Every GitHub run uses a distinct Android package because debug signing
// certificates are not retained across runners. Production in-place updates
// require a separate, securely retained production signing key.
val previewRunId = System.getenv("GITHUB_RUN_ID")
    ?.takeIf { it.matches(Regex("[0-9]{6,20}")) } ?: "local"

android {
    namespace = "in.dhanpulse.personal"
    compileSdk = 35

    defaultConfig {
        applicationId = "in.dhanpulse.personal.stable"
        minSdk = 26
        targetSdk = 35
        versionCode = 90
        versionName = appVersion
    }

    buildTypes {
        getByName("debug") {
            // Distinct installable preview until the original Stable signing key is available.
            // It cannot replace an existing Stable installation or read its private data.
            applicationIdSuffix = ".monitor90.r${previewRunId}"
            manifestPlaceholders["appLabel"] = "DhanPulse Monitor 90"
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
