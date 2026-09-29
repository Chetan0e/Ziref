import os
import shutil
import zipfile
import base64
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("ziref.android_generator")

class AndroidProjectGenerator:
    PERMISSION_MAP = {
        "camera": ["android.permission.CAMERA"],
        "location": [
            "android.permission.ACCESS_FINE_LOCATION",
            "android.permission.ACCESS_COARSE_LOCATION"
        ],
        "notifications": ["android.permission.POST_NOTIFICATIONS"],
        "audio": ["android.permission.RECORD_AUDIO"]
    }

    def generate(self, config: Dict[str, Any], output_dir: str) -> str:
        app_name = config.get("app_name", "Ziref App")
        package_id = config.get("package_id", "com.ziref.app")
        version = config.get("version", "1.0.0")
        version_code = int(config.get("version_code", 1))
        website_url = config.get("website_url", "https://ziref.app")
        theme = config.get("theme", "system")
        orientation = config.get("orientation", "portrait")
        user_permissions = config.get("permissions", [])
        icon_base64 = config.get("icon_base64")

        abs_out = os.path.abspath(output_dir)
        os.makedirs(abs_out, exist_ok=True)
        package_path = package_id.replace(".", "/")

        # 1. settings.gradle.kts
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

        # 2. build.gradle.kts
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
    }}

    buildTypes {{
        release {{
            isMinifyEnabled = false
        }}
        debug {{
            isDebuggable = true
        }}
    }}
}}

dependencies {{
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.11.0")
    implementation("androidx.swiperefreshlayout:swiperefreshlayout:1.1.0")
}}
""")

        # 4. AndroidManifest.xml
        main_dir = os.path.join(app_dir, "src", "main")
        java_src_dir = os.path.join(main_dir, "java", package_path)
        res_dir = os.path.join(main_dir, "res")
        os.makedirs(java_src_dir, exist_ok=True)
        os.makedirs(res_dir, exist_ok=True)

        manifest_permissions = [
            '<uses-permission android:name="android.permission.INTERNET" />',
            '<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />'
        ]
        for p_key in user_permissions:
            if p_key in self.PERMISSION_MAP:
                for perm in self.PERMISSION_MAP[p_key]:
                    manifest_permissions.append(f'<uses-permission android:name="{perm}" />')

        permissions_xml = "\n    ".join(manifest_permissions)

        with open(os.path.join(main_dir, "AndroidManifest.xml"), "w", encoding="utf-8") as f:
            f.write(f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{package_id}"
    android:versionCode="{version_code}"
    android:versionName="{version}">

    <uses-sdk
        android:minSdkVersion="24"
        android:targetSdkVersion="34" />

    {permissions_xml}

    <application
        android:allowBackup="true"
        android:label="@string/app_name"
        android:icon="@mipmap/ic_launcher"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:supportsRtl="true"
        android:usesCleartextTraffic="true"
        android:theme="@style/Theme.ZirefApp">
        <activity
            android:name=".MainActivity"
            android:exported="true"
            {screen_orientation_attr}>
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>

</manifest>
""")

        # 5. MainActivity.kt with SwipeRefresh & Offline handling
        with open(os.path.join(java_src_dir, "MainActivity.kt"), "w", encoding="utf-8") as f:
            f.write(f"""package {package_id}

import android.annotation.SuppressLint
import android.content.Intent
import android.graphics.Bitmap
import android.net.Uri
import android.net.http.SslError
import android.os.Bundle
import android.view.View
import android.webkit.SslErrorHandler
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.appcompat.app.AppCompatActivity
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout

class MainActivity : AppCompatActivity() {{
    private lateinit var webView: WebView
    private lateinit var swipeRefresh: SwipeRefreshLayout
    private val targetUrl = "{website_url}"

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)

        swipeRefresh = SwipeRefreshLayout(this)
        webView = WebView(this)
        swipeRefresh.addView(webView)
        setContentView(swipeRefresh)

        // Hardware Acceleration
        webView.setLayerType(View.LAYER_TYPE_HARDWARE, null)

        // Modern WebView Settings for Web App & SPA compatibility
        webView.settings.apply {{
            javaScriptEnabled = true
            domStorageEnabled = true
            databaseEnabled = true
            allowFileAccess = true
            allowContentAccess = true
            useWideViewPort = true
            loadWithOverviewMode = true
            mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
            javaScriptCanOpenWindowsAutomatically = true
            mediaPlaybackRequiresUserGesture = false
            cacheMode = WebSettings.LOAD_DEFAULT
            userAgentString = userAgentString + " ZirefMobileApp/1.0"
        }}

        swipeRefresh.setOnRefreshListener {{
            webView.reload()
        }}

        webView.webChromeClient = object : WebChromeClient() {{
            override fun onProgressChanged(view: WebView?, newProgress: Int) {{
                if (newProgress >= 100) {{
                    swipeRefresh.isRefreshing = false
                }}
            }}
        }}

        webView.webViewClient = object : WebViewClient() {{
            override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {{
                swipeRefresh.post {{ swipeRefresh.isRefreshing = true }}
            }}

            override fun onPageFinished(view: WebView?, url: String?) {{
                swipeRefresh.isRefreshing = false
            }}

            override fun onReceivedSslError(view: WebView?, handler: SslErrorHandler?, error: SslError?) {{
                handler?.proceed()
            }}

            override fun onReceivedError(view: WebView?, request: WebResourceRequest?, error: WebResourceError?) {{
                swipeRefresh.isRefreshing = false
                if (request?.isForMainFrame == true) {{
                    val offlineHtml = \"\"\"
                        <html>
                        <head>
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                        <style>
                            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #09090b; color: #ffffff; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; padding: 20px; text-align: center; }}
                            h2 {{ font-size: 22px; margin-bottom: 8px; font-weight: 700; }}
                            p {{ font-size: 14px; color: #a1a1aa; margin-bottom: 20px; }}
                            button {{ background: #0284c7; color: #ffffff; border: none; padding: 12px 24px; border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; }}
                            button:active {{ opacity: 0.8; }}
                        </style>
                        </head>
                        <body>
                            <div>
                                <h2>Unable to Connect</h2>
                                <p>Please check your network connection and try again.</p>
                                <button onclick="window.location.href='{website_url}'">Retry</button>
                            </div>
                        </body>
                        </html>
                    \"\"\".trimIndent()
                    webView.loadDataWithBaseURL("{website_url}", offlineHtml, "text/html", "UTF-8", "{website_url}")
                }}
            }}

            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {{
                val url = request?.url?.toString() ?: return false
                if (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("file://") || url.startsWith("data:")) {{
                    return false
                }}
                return try {{
                    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                    startActivity(intent)
                    true
                }} catch (e: Exception) {{
                    false
                }}
            }}
        }}

        webView.loadUrl(targetUrl)
    }}

    override fun onBackPressed() {{
        if (::webView.isInitialized && webView.canGoBack()) {{
            webView.goBack()
        }} else {{
            super.onBackPressed()
        }}
    }}
}}
""")

        # 6. Resources: Values & Adaptive Launcher Drawables
        values_dir = os.path.join(res_dir, "values")
        drawable_dir = os.path.join(res_dir, "drawable")
        mipmap_v26_dir = os.path.join(res_dir, "mipmap-anydpi-v26")
        os.makedirs(values_dir, exist_ok=True)
        os.makedirs(drawable_dir, exist_ok=True)
        os.makedirs(mipmap_v26_dir, exist_ok=True)

        with open(os.path.join(values_dir, "strings.xml"), "w", encoding="utf-8") as f:
            f.write(f"<resources><string name='app_name'>{app_name}</string></resources>")

        with open(os.path.join(values_dir, "colors.xml"), "w", encoding="utf-8") as f:
            f.write("""<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="ic_launcher_background">#0284C7</color>
    <color name="primary">#0284C7</color>
    <color name="background">#09090B</color>
</resources>
""")

        with open(os.path.join(values_dir, "themes.xml"), "w", encoding="utf-8") as f:
            f.write("""<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="Theme.ZirefApp" parent="@android:style/Theme.DeviceDefault.NoActionBar">
        <item name="android:statusBarColor">#09090B</item>
        <item name="android:navigationBarColor">#09090B</item>
    </style>
</resources>
""")

        # Generate mipmap launcher icons (supports custom user logo & branded fallbacks)
        self._generate_app_icons(res_dir, app_name, icon_base64)

        # Adaptive icon descriptors
        for name in ["ic_launcher.xml", "ic_launcher_round.xml"]:
            with open(os.path.join(mipmap_v26_dir, name), "w", encoding="utf-8") as f:
                f.write("""<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background" />
    <foreground android:drawable="@drawable/ic_launcher_foreground" />
</adaptive-icon>
""")

        # 7. manifest.json
        with open(os.path.join(abs_out, "manifest.json"), "w", encoding="utf-8") as f:
            f.write(f"""{{
  "name": "{app_name}",
  "short_name": "{app_name}",
  "start_url": "{website_url}",
  "display": "standalone",
  "background_color": "#09090b",
  "theme_color": "#0284c7"
}}""")

        return abs_out

    def _generate_app_icons(self, res_dir: str, app_name: str, icon_base64: Optional[str] = None) -> None:
        """
        Generates standard Android launcher icons for all screen densities:
        - mdpi (48x48)
        - hdpi (72x72)
        - xhdpi (96x96)
        - xxhdpi (144x144)
        - xxxhdpi (192x192)
        Both ic_launcher.png (standard) and ic_launcher_round.png (circular).
        """
        import io
        density_sizes = {
            "mipmap-mdpi": (48, 48),
            "mipmap-hdpi": (72, 72),
            "mipmap-xhdpi": (96, 96),
            "mipmap-xxhdpi": (144, 144),
            "mipmap-xxxhdpi": (192, 192),
        }

        drawable_dir = os.path.join(res_dir, "drawable")
        os.makedirs(drawable_dir, exist_ok=True)

        source_img = None
        if icon_base64:
            try:
                # Strip data URL prefix if present
                raw_b64 = icon_base64
                if "," in raw_b64:
                    raw_b64 = raw_b64.split(",", 1)[1]
                img_data = base64.b64decode(raw_b64)
                from PIL import Image
                source_img = Image.open(io.BytesIO(img_data)).convert("RGBA")
                logger.info(f"Loaded user app icon: {source_img.size[0]}x{source_img.size[1]} px")
            except Exception as e:
                logger.warning(f"Failed to decode custom app icon: {e}. Falling back to default.")
                source_img = None

        if source_img is None:
            # Generate a clean, branded default app icon with Pillow
            try:
                from PIL import Image, ImageDraw, ImageFont
                base_size = 512
                source_img = Image.new("RGBA", (base_size, base_size), (2, 132, 199, 255))
                draw = ImageDraw.Draw(source_img)

                # Draw modern rounded accent inside
                initial = (app_name[0].upper() if app_name else "Z")
                # Draw lettermark
                font_size = int(base_size * 0.45)
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except Exception:
                    font = ImageFont.load_default()
                bbox = draw.textbbox((0, 0), initial, font=font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                x = (base_size - text_w) / 2
                y = (base_size - text_h) / 2 - (bbox[1] if bbox[1] != 0 else 0)
                draw.text((x, y), initial, fill=(255, 255, 255, 255), font=font)
            except Exception as e:
                logger.warning(f"Pillow fallback error: {e}")
                source_img = None

        # Write ic_launcher_foreground.xml vector fallback
        initial_char = app_name[0].upper() if app_name else "Z"
        with open(os.path.join(drawable_dir, "ic_launcher_foreground.xml"), "w", encoding="utf-8") as f:
            f.write(f"""<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="#FFFFFF"
        android:pathData="M34,34 L74,34 L74,74 L34,74 Z" />
</vector>
""")

        if source_img:
            from PIL import Image, ImageDraw
            for folder_name, (w, h) in density_sizes.items():
                target_dir = os.path.join(res_dir, folder_name)
                os.makedirs(target_dir, exist_ok=True)

                # 1. Standard square/squircle icon
                resized = source_img.resize((w, h), Image.Resampling.LANCZOS)
                standard_path = os.path.join(target_dir, "ic_launcher.png")
                resized.save(standard_path, format="PNG")

                # 2. Round icon (circular mask)
                mask = Image.new("L", (w, h), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0, 0, w - 1, h - 1), fill=255)
                round_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                round_img.paste(resized, (0, 0), mask=mask)
                round_path = os.path.join(target_dir, "ic_launcher_round.png")
                round_img.save(round_path, format="PNG")

        logger.info(f"Generated Android launcher mipmaps for: '{app_name}' (custom logo: {icon_base64 is not None})")

android_project_generator = AndroidProjectGenerator()
