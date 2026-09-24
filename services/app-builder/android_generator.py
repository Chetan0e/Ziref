import os
import shutil
import zipfile
import base64
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("ziref.android_generator")

class AndroidProjectGenerator:
    """
    Generates a production-ready Android Studio / Gradle project
    wrapping the deployed web application with an optimized native WebView shell.
    """

    def generate(self, config: Dict[str, Any], output_dir: str) -> str:
        app_name = config.get("app_name", "Ziref App")
        package_id = config.get("package_id", "com.ziref.app")
        version = config.get("version", "1.0.0")
        version_code = int(config.get("version_code", 1))
        website_url = config.get("website_url", "https://ziref.app")
        theme = config.get("theme", "system")
        orientation = config.get("orientation", "portrait")

        abs_out = os.path.abspath(output_dir)
        os.makedirs(abs_out, exist_ok=True)

        package_path = package_id.replace(".", "/")

        # 1. Root settings.gradle.kts
        with open(os.path.join(abs_out, "settings.gradle.kts"), "w", encoding="utf-8") as f:
            f.write(f"""pluginManagement {{
    repositories {{
        google()
        mavenCentral()
        gradlePluginPortal()
    }}
}}
dependencyResolutionManagement {{
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {{
        google()
        mavenCentral()
    }}
}}
rootProject.name = "{app_name.replace(' ', '')}"
include(":app")
""")

        # 2. Root build.gradle.kts
        with open(os.path.join(abs_out, "build.gradle.kts"), "w", encoding="utf-8") as f:
            f.write("""plugins {
    id("com.android.application") version "8.2.2" apply false
    id("org.jetbrains.kotlin.android") version "1.9.22" apply false
}
""")

        # 3. app/build.gradle.kts
        app_dir = os.path.join(abs_out, "app")
        os.makedirs(app_dir, exist_ok=True)

        screen_orientation_attr = 'android:screenOrientation="portrait"' if orientation == "portrait" else ""

        with open(os.path.join(app_dir, "build.gradle.kts"), "w", encoding="utf-8") as f:
            f.write(f"""plugins {{
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}}

android {{
    namespace = "{package_id}"
    compileSdk = 34

    defaultConfig {{
        applicationId = "{package_id}"
        minSdk = 24
        targetSdk = 34
        versionCode = {version_code}
        versionName = "{version}"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }}

    buildTypes {{
        release {{
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }}
        debug {{
            isDebuggable = true
        }}
    }}
    compileOptions {{
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }}
    kotlinOptions {{
        jvmTarget = "17"
    }}
}}

dependencies {{
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.11.0")
    implementation("androidx.swiperefreshlayout:swiperefreshlayout:1.1.0")
    implementation("androidx.webkit:webkit:1.10.0")
}}
""")

        # 4. app/src/main/AndroidManifest.xml
        main_dir = os.path.join(app_dir, "src", "main")
        java_src_dir = os.path.join(main_dir, "java", package_path)
        res_dir = os.path.join(main_dir, "res")
        os.makedirs(java_src_dir, exist_ok=True)
        os.makedirs(res_dir, exist_ok=True)

        with open(os.path.join(main_dir, "AndroidManifest.xml"), "w", encoding="utf-8") as f:
            f.write(f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:roundIcon="@mipmap/ic_launcher"
        android:supportsRtl="true"
        android:theme="@style/Theme.ZirefApp"
        android:usesCleartextTraffic="true">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:configChanges="orientation|screenSize|keyboardHidden"
            {screen_orientation_attr}>
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>

</manifest>
""")

        # 5. MainActivity.kt
        with open(os.path.join(java_src_dir, "MainActivity.kt"), "w", encoding="utf-8") as f:
            f.write(f"""package {package_id}

import android.annotation.SuppressLint
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.webkit.*
import android.widget.Button
import android.widget.ProgressBar
import androidx.appcompat.app.AppCompatActivity
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout

class MainActivity : AppCompatActivity() {{

    private lateinit var webView: WebView
    private lateinit var progressBar: ProgressBar
    private lateinit var swipeRefresh: SwipeRefreshLayout
    private lateinit var errorLayout: View
    private lateinit var retryButton: Button

    private val targetUrl = "{website_url}"

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webView)
        progressBar = findViewById(R.id.progressBar)
        swipeRefresh = findViewById(R.id.swipeRefresh)
        errorLayout = findViewById(R.id.errorLayout)
        retryButton = findViewById(R.id.retryButton)

        setupWebView()

        swipeRefresh.setOnRefreshListener {{
            webView.reload()
        }}

        retryButton.setOnClickListener {{
            errorLayout.visibility = View.GONE
            webView.visibility = View.VISIBLE
            loadWebsite()
        }}

        loadWebsite()
    }}

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {{
        val settings = webView.settings
        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.databaseEnabled = true
        settings.allowFileAccess = true
        settings.useWideViewPort = true
        settings.loadWithOverviewMode = true
        settings.cacheMode = WebSettings.LOAD_DEFAULT

        webView.webViewClient = object : WebViewClient() {{
            override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {{
                progressBar.visibility = View.VISIBLE
            }}

            override fun onPageFinished(view: WebView?, url: String?) {{
                progressBar.visibility = View.GONE
                swipeRefresh.isRefreshing = false
            }}

            override fun onReceivedError(view: WebView?, request: WebResourceRequest?, error: WebResourceError?) {{
                if (request?.isForMainFrame == true) {{
                    progressBar.visibility = View.GONE
                    swipeRefresh.isRefreshing = false
                    webView.visibility = View.GONE
                    errorLayout.visibility = View.VISIBLE
                }}
            }}

            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {{
                val url = request?.url?.toString() ?: return false
                val targetHost = Uri.parse(targetUrl).host

                return if (url.contains(targetHost ?: "")) {{
                    false
                }} else {{
                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                    startActivity(intent)
                    true
                }}
            }}
        }}

        webView.webChromeClient = object : WebChromeClient() {{
            override fun onProgressChanged(view: WebView?, newProgress: Int) {{
                progressBar.progress = newProgress
                if (newProgress == 100) {{
                    progressBar.visibility = View.GONE
                }}
            }}
        }}
    }}

    private fun loadWebsite() {{
        if (isNetworkAvailable()) {{
            webView.loadUrl(targetUrl)
        }} else {{
            webView.visibility = View.GONE
            errorLayout.visibility = View.VISIBLE
        }}
    }}

    private fun isNetworkAvailable(): Boolean {{
        val cm = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val network = cm.activeNetwork ?: return false
        val capabilities = cm.getNetworkCapabilities(network) ?: return false
        return capabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }}

    override fun onBackPressed() {{
        if (webView.canGoBack()) {{
            webView.goBack()
        }} else {{
            super.onBackPressed()
        }}
    }}
}}
""")

        # 6. Resources: layout/activity_main.xml
        layout_dir = os.path.join(res_dir, "layout")
        values_dir = os.path.join(res_dir, "values")
        mipmap_dir = os.path.join(res_dir, "mipmap")
        os.makedirs(layout_dir, exist_ok=True)
        os.makedirs(values_dir, exist_ok=True)
        os.makedirs(mipmap_dir, exist_ok=True)

        with open(os.path.join(layout_dir, "activity_main.xml"), "w", encoding="utf-8") as f:
            f.write("""<?xml version="1.0" encoding="utf-8"?>
<androidx.constraintlayout.widget.ConstraintLayout xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:background="#09090b">

    <ProgressBar
        android:id="@+id/progressBar"
        style="?android:attr/progressBarStyleHorizontal"
        android:layout_width="match_parent"
        android:layout_height="4dp"
        android:max="100"
        android:visibility="gone"
        app:layout_constraintTop_toTopOf="parent" />

    <androidx.swiperefreshlayout.widget.SwipeRefreshLayout
        android:id="@+id/swipeRefresh"
        android:layout_width="match_parent"
        android:layout_height="0dp"
        app:layout_constraintBottom_toBottomOf="parent"
        app:layout_constraintTop_toBottomOf="@id/progressBar">

        <WebView
            android:id="@+id/webView"
            android:layout_width="match_parent"
            android:layout_height="match_parent" />

    </androidx.swiperefreshlayout.widget.SwipeRefreshLayout>

    <LinearLayout
        android:id="@+id/errorLayout"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:gravity="center"
        android:orientation="vertical"
        android:padding="24dp"
        android:visibility="gone"
        app:layout_constraintBottom_toBottomOf="parent"
        app:layout_constraintEnd_toEndOf="parent"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintTop_toTopOf="parent">

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:text="Connection Offline"
            android:textColor="#fafafa"
            android:textSize="20sp"
            android:textStyle="bold" />

        <TextView
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_marginTop="8dp"
            android:text="Unable to reach the server. Check internet connection."
            android:textColor="#a1a1aa" />

        <Button
            android:id="@+id/retryButton"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_marginTop="16dp"
            android:text="Retry" />

    </LinearLayout>

</androidx.constraintlayout.widget.ConstraintLayout>
""")

        # 7. strings.xml, colors.xml, themes.xml
        with open(os.path.join(values_dir, "strings.xml"), "w", encoding="utf-8") as f:
            f.write(f"""<resources>
    <string name="app_name">{app_name}</string>
</resources>
""")

        with open(os.path.join(values_dir, "colors.xml"), "w", encoding="utf-8") as f:
            f.write("""<resources>
    <color name="primary">#0284c7</color>
    <color name="background">#09090b</color>
</resources>
""")

        with open(os.path.join(values_dir, "themes.xml"), "w", encoding="utf-8") as f:
            f.write("""<resources>
    <style name="Theme.ZirefApp" parent="Theme.MaterialComponents.DayNight.NoActionBar">
        <item name="colorPrimary">@color/primary</item>
        <item name="android:windowBackground">@color/background</item>
    </style>
</resources>
""")

        # 8. PWA Web Manifest (Bonus compatibility)
        with open(os.path.join(abs_out, "manifest.json"), "w", encoding="utf-8") as f:
            f.write(f"""{{
  "name": "{app_name}",
  "short_name": "{app_name}",
  "start_url": "{website_url}",
  "display": "standalone",
  "background_color": "#09090b",
  "theme_color": "#0284c7",
  "orientation": "{orientation}"
}}
""")

        logger.info(f"Android project generated at: {abs_out}")
        return abs_out

android_project_generator = AndroidProjectGenerator()
