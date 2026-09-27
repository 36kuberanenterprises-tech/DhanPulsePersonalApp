plugins {
    id("com.android.application")
}

android {
    namespace = "com.dhanpulse.cryptofxnative"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.dhanpulse.cryptofxnative"
        minSdk = 24
        targetSdk = 34
        versionCode = 19
        versionName = "1.9.0"
    }

    buildTypes {
        getByName("release") {
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("androidx.annotation:annotation:1.9.1")
}
