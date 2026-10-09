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

    sourceSets {{
        getByName("main") {{
            java.exclude("**/MainActivity.java")
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
        android:theme="@style/Theme.ZirefApp"
        android:hardwareAccelerated="true"
        android:networkSecurityConfig="@xml/network_security_config">
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

        # 5a. MainActivity.kt for Kotlin Android Studio source zip
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
    private val targetUrl = "{website_url}"

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {{
        super.onCreate(savedInstanceState)
        val swipeRefresh = SwipeRefreshLayout(this)
        webView = WebView(this)
        swipeRefresh.addView(webView)
        setContentView(swipeRefresh)

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

        val prefs = getSharedPreferences("ziref_prefs", MODE_PRIVATE)
        val initialUrl = prefs.getString("target_url", targetUrl) ?: targetUrl

        swipeRefresh.setOnRefreshListener {{ webView.reload() }}
        webView.webViewClient = object : WebViewClient() {{
            override fun onPageFinished(view: WebView?, url: String?) {{
                swipeRefresh.isRefreshing = false
                if (url != null && !url.startsWith("data:")) {{
                    prefs.edit().putString("target_url", url).apply()
                }}
            }}
            override fun onReceivedSslError(view: WebView?, handler: SslErrorHandler?, error: SslError?) {{
                handler?.proceed()
            }}
        }}
        webView.loadUrl(initialUrl)
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

        # 5b. MainActivity.java for fast, standalone SDK compilation (javac + d8) into classes.dex
        with open(os.path.join(java_src_dir, "MainActivity.java"), "w", encoding="utf-8") as f:
            f.write(f"""package {package_id};

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.net.Uri;
import android.net.http.SslError;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.PermissionRequest;
import android.webkit.SslErrorHandler;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.ProgressBar;

public class MainActivity extends Activity {{
    private WebView webView;
    private ProgressBar progressBar;
    private final String targetUrl = "{website_url}";

    @Override
    @SuppressLint("SetJavaScriptEnabled")
    protected void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);

        FrameLayout rootLayout = new FrameLayout(this);
        rootLayout.setBackgroundColor(Color.parseColor("#09090B"));

        webView = new WebView(this);
        webView.setLayoutParams(new FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.MATCH_PARENT
        ));
        webView.setLayerType(View.LAYER_TYPE_HARDWARE, null);
        webView.setBackgroundColor(Color.parseColor("#09090B"));

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setUseWideViewPort(true);
        settings.setLoadWithOverviewMode(true);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        settings.setJavaScriptCanOpenWindowsAutomatically(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setUserAgentString(settings.getUserAgentString() + " ZirefMobileApp/1.0");

        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setLayoutParams(new FrameLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            8
        ));
        progressBar.setMax(100);
        progressBar.setVisibility(View.GONE);

        rootLayout.addView(webView);
        rootLayout.addView(progressBar);
        setContentView(rootLayout);

        webView.addJavascriptInterface(new Object() {{
            @android.webkit.JavascriptInterface
            public void saveAndLoad(final String newUrl) {{
                runOnUiThread(new Runnable() {{
                    @Override
                    public void run() {{
                        if (newUrl != null && !newUrl.trim().isEmpty()) {{
                            getSharedPreferences("ziref_prefs", MODE_PRIVATE)
                                .edit()
                                .putString("target_url", newUrl.trim())
                                .apply();
                            webView.loadUrl(newUrl.trim());
                        }}
                    }}
                }});
            }}
        }}, "AndroidBridge");

        webView.setWebChromeClient(new WebChromeClient() {{
            @Override
            public void onProgressChanged(WebView view, int newProgress) {{
                if (newProgress < 100) {{
                    progressBar.setVisibility(View.VISIBLE);
                    progressBar.setProgress(newProgress);
                }} else {{
                    progressBar.setVisibility(View.GONE);
                }}
            }}

            @Override
            public void onPermissionRequest(final PermissionRequest request) {{
                try {{
                    request.grant(request.getResources());
                }} catch (Exception ignored) {{}}
            }}
        }});

        webView.setWebViewClient(new WebViewClient() {{
            @Override
            public void onPageFinished(WebView view, String url) {{
                if (url != null && !url.startsWith("data:") && !url.contains("showOfflinePage")) {{
                    getSharedPreferences("ziref_prefs", MODE_PRIVATE)
                        .edit()
                        .putString("target_url", url)
                        .apply();
                }}
            }}

            @Override
            public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {{
                if (handler != null) {{
                    handler.proceed();
                }}
            }}

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {{
                String url = request.getUrl().toString();
                if (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("file://") || url.startsWith("data:")) {{
                    return false;
                }}
                try {{
                    Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                    startActivity(intent);
                    return true;
                }} catch (Exception e) {{
                    return false;
                }}
            }}

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {{
                if (request != null && request.isForMainFrame()) {{
                    showOfflinePage(view, request.getUrl().toString());
                }}
            }}
        }});

        String savedUrl = getSharedPreferences("ziref_prefs", MODE_PRIVATE).getString("target_url", targetUrl);
        webView.loadUrl(savedUrl != null && !savedUrl.isEmpty() ? savedUrl : targetUrl);
    }}

    private void showOfflinePage(WebView view, String failedUrl) {{
        boolean isLocal = failedUrl != null && (failedUrl.contains("localhost") || failedUrl.contains("127.0.0.1"));
        String hint = isLocal
            ? "<p style='color:#eab308;font-size:13px;margin:12px 0;'>Notice: Target URL is set to localhost. Physical Android devices cannot connect to PC localhost directly. Make sure your PC and phone are on the same Wi-Fi and use your PC's IP address (e.g. http://192.168.x.x:8000), or deploy to a public URL.</p>"
            : "<p style='color:#a1a1aa;font-size:14px;margin:12px 0;'>Please check your network connection and try again.</p>";

        String html = "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width, initial-scale=1.0'>"
            + "<style>"
            + "body{{font-family:-apple-system,BlinkMacSystemFont,\\"Segoe UI\\",Roboto,sans-serif;background:#09090b;color:#ffffff;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;padding:24px;box-sizing:border-box;text-align:center;}}"
            + ".card{{background:#18181b;border:1px solid #27272a;border-radius:16px;padding:32px 24px;max-width:420px;width:100%;box-shadow:0 10px 25px rgba(0,0,0,0.5);}}"
            + "h2{{font-size:22px;margin:0 0 10px 0;font-weight:700;color:#f4f4f5;}}"
            + "input{{width:100%;padding:12px;margin:14px 0;border-radius:8px;border:1px solid #3f3f46;background:#09090b;color:#fff;font-size:14px;box-sizing:border-box;}}"
            + "button{{background:#0284c7;color:#ffffff;border:none;padding:12px 24px;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;width:100%;transition:background 0.2s;}}"
            + "button:active{{background:#0369a1;}}"
            + "</style></head><body>"
            + "<div class='card'>"
            + "<h2>Unable to Connect</h2>"
            + hint
            + "<input id='urlInput' type='text' value='" + (failedUrl != null ? failedUrl : targetUrl) + "' placeholder='http://192.168.x.x:8000/sites/...'>"
            + "<button onclick='retryConnection()'>Connect / Retry</button>"
            + "</div>"
            + "<script>"
            + "function retryConnection(){{"
            + "  var url = document.getElementById('urlInput').value.trim();"
            + "  if(url){{"
            + "    if(window.AndroidBridge && window.AndroidBridge.saveAndLoad){{"
            + "      window.AndroidBridge.saveAndLoad(url);"
            + "    }} else {{"
            + "      window.location.href = url;"
            + "    }}"
            + "  }}"
            + "}}"
            + "</script>"
            + "</body></html>";

        view.loadDataWithBaseURL(failedUrl, html, "text/html", "UTF-8", failedUrl);
    }}

    @Override
    public void onBackPressed() {{
        if (webView != null && webView.canGoBack()) {{
            webView.goBack();
        }} else {{
            super.onBackPressed();
        }}
    }}

    @Override
    protected void onPause() {{
        super.onPause();
        if (webView != null) webView.onPause();
    }}

    @Override
    protected void onResume() {{
        super.onResume();
        if (webView != null) webView.onResume();
    }}

    @Override
    protected void onDestroy() {{
        if (webView != null) webView.destroy();
        super.onDestroy();
    }}
}}
""")

        # 6. Resources: Values & Adaptive Launcher Drawables
        values_dir = os.path.join(res_dir, "values")
        drawable_dir = os.path.join(res_dir, "drawable")
        xml_dir = os.path.join(res_dir, "xml")
        mipmap_v26_dir = os.path.join(res_dir, "mipmap-anydpi-v26")
        os.makedirs(values_dir, exist_ok=True)
        os.makedirs(drawable_dir, exist_ok=True)
        os.makedirs(xml_dir, exist_ok=True)
        os.makedirs(mipmap_v26_dir, exist_ok=True)

        with open(os.path.join(values_dir, "strings.xml"), "w", encoding="utf-8") as f:
            f.write(f"<resources><string name='app_name'>{app_name}</string></resources>")

        # Generate mipmap launcher icons from user uploaded logo & detect background color
        try:
            detected_bg_color = self._generate_app_icons(res_dir, app_name, icon_base64)
        except Exception as e:
            logger.error(f"Icon generation failed: {e}. Using default color.")
            detected_bg_color = "#0284C7"

        with open(os.path.join(values_dir, "colors.xml"), "w", encoding="utf-8") as f:
            f.write(f"""<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="ic_launcher_background">{detected_bg_color}</color>
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

        # Adaptive icon descriptors point to the actual generated foreground mipmaps
        for name in ["ic_launcher.xml", "ic_launcher_round.xml"]:
            with open(os.path.join(mipmap_v26_dir, name), "w", encoding="utf-8") as f:
                f.write("""<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background" />
    <foreground android:drawable="@mipmap/ic_launcher_foreground" />
    <monochrome android:drawable="@mipmap/ic_launcher_foreground" />
</adaptive-icon>
""")

        # Network security config to allow cleartext traffic (for development/local URLs)
        with open(os.path.join(xml_dir, "network_security_config.xml"), "w", encoding="utf-8") as f:
            f.write("""<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="true">
        <trust-anchors>
            <certificates src="system" />
            <certificates src="user" />
        </trust-anchors>
    </base-config>
</network-security-config>
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

    def _generate_app_icons(self, res_dir: str, app_name: str, icon_base64: Optional[str] = None) -> str:
        """
        Generates standard Android launcher icons for all screen densities:
        - mdpi (48x48 icon, 108x108 adaptive foreground)
        - hdpi (72x72 icon, 162x162 adaptive foreground)
        - xhdpi (96x96 icon, 216x216 adaptive foreground)
        - xxhdpi (144x144 icon, 324x324 adaptive foreground)
        - xxxhdpi (192x192 icon, 432x432 adaptive foreground)

        Generates:
        - ic_launcher.png (exact user-uploaded logo)
        - ic_launcher_round.png (circular crop of user logo)
        - ic_launcher_foreground.png (properly centered adaptive layer)

        Returns detected background color (hex string) for adaptive icon background.
        """
        import io
        from PIL import Image, ImageDraw, ImageFont, ImageOps

        density_sizes = {
            "mipmap-mdpi": ((48, 48), (108, 108)),
            "mipmap-hdpi": ((72, 72), (162, 162)),
            "mipmap-xhdpi": ((96, 96), (216, 216)),
            "mipmap-xxhdpi": ((144, 144), (324, 324)),
            "mipmap-xxxhdpi": ((192, 192), (432, 432)),
        }

        source_img = None
        detected_bg_color = "#0284C7"
        has_trans = False

        if icon_base64:
            try:
                raw_b64 = icon_base64
                if "," in raw_b64:
                    raw_b64 = raw_b64.split(",", 1)[1]
                img_data = base64.b64decode(raw_b64)
                raw_img = Image.open(io.BytesIO(img_data))
                # Transpose EXIF orientation so mobile camera / portrait photos display upright!
                raw_img = ImageOps.exif_transpose(raw_img)
                source_img = raw_img.convert("RGBA")
                logger.info(f"Loaded user app icon: {source_img.size[0]}x{source_img.size[1]} px")

                # Ensure rectangular logos are square-padded to prevent squishing/distortion
                w_s, h_s = source_img.size
                if w_s != h_s:
                    side = max(w_s, h_s)
                    sq_canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
                    sq_canvas.paste(source_img, ((side - w_s) // 2, (side - h_s) // 2))
                    source_img = sq_canvas
                    w_s, h_s = side, side

                corner_samples = [
                    source_img.getpixel((0, 0)),
                    source_img.getpixel((w_s - 1, 0)),
                    source_img.getpixel((0, h_s - 1)),
                    source_img.getpixel((w_s - 1, h_s - 1)),
                ]
                has_trans = any(p[3] < 200 for p in corner_samples)

                if has_trans:
                    detected_bg_color = "#09090B"
                else:
                    top_left = corner_samples[0]
                    detected_bg_color = f"#{top_left[0]:02X}{top_left[1]:02X}{top_left[2]:02X}"
            except Exception as e:
                logger.warning(f"Failed to decode custom app icon: {e}. Falling back to branded default.")
                source_img = None

        if source_img is None:
            # Generate a clean, branded default app icon with Pillow
            try:
                base_size = 512
                source_img = Image.new("RGBA", (base_size, base_size), (2, 132, 199, 255))
                draw = ImageDraw.Draw(source_img)
                initial = (app_name[0].upper() if app_name else "Z")
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
                detected_bg_color = "#0284C7"
                has_trans = False
            except Exception as e:
                logger.warning(f"Pillow fallback error: {e}")
                return "#0284C7"

        # Generate mipmaps for all densities
        for folder_name, ((w, h), (fw, fh)) in density_sizes.items():
            target_dir = os.path.join(res_dir, folder_name)
            os.makedirs(target_dir, exist_ok=True)

            try:
                # 1. Standard square/exact icon (pure user logo)
                resized = source_img.resize((w, h), Image.Resampling.LANCZOS)
                standard_path = os.path.join(target_dir, "ic_launcher.png")
                resized.save(standard_path, format="PNG")
                logger.debug(f"Generated standard icon: {standard_path}")

                # 2. Round icon (smooth circular mask)
                mask = Image.new("L", (w, h), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0, 0, w - 1, h - 1), fill=255)
                round_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                round_img.paste(resized, (0, 0), mask=mask)
                round_path = os.path.join(target_dir, "ic_launcher_round.png")
                round_img.save(round_path, format="PNG")
                logger.debug(f"Generated round icon: {round_path}")

                # 3. Adaptive icon foreground (centered within 72dp safe zone)
                fg_canvas = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
                scale_ratio = 0.70 if has_trans else 0.74
                target_max = int(min(fw, fh) * scale_ratio)
                src_w, src_h = source_img.size
                if src_w > src_h:
                    fit_w = target_max
                    fit_h = max(1, int(src_h * target_max / src_w))
                else:
                    fit_h = target_max
                    fit_w = max(1, int(src_w * target_max / src_h))

                fg_resized = source_img.resize((fit_w, fit_h), Image.Resampling.LANCZOS)
                offset_x = (fw - fit_w) // 2
                offset_y = (fh - fit_h) // 2
                fg_canvas.paste(fg_resized, (offset_x, offset_y), mask=fg_resized if fg_resized.mode == "RGBA" else None)
                fg_path = os.path.join(target_dir, "ic_launcher_foreground.png")
                fg_canvas.save(fg_path, format="PNG")
                logger.debug(f"Generated adaptive foreground: {fg_path}")
            except Exception as e:
                logger.error(f"Failed to generate icons for density {folder_name}: {e}")
                raise

        logger.info(f"Generated Android launcher mipmaps for: '{app_name}' (custom logo: {icon_base64 is not None}, bg: {detected_bg_color})")
        return detected_bg_color

android_project_generator = AndroidProjectGenerator()
