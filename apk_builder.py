"""
APK Builder — Generate fullscreen WebView APKs for Android from website URLs.

Outputs a complete Android Studio project ready to build.
Optionally auto-builds the debug APK if Android SDK + JDK are found.

Requirements: Python 3.8+  (no extra pip packages needed)
To build APK: Android Studio (free) — https://developer.android.com/studio
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import os, re, subprocess, threading, urllib.request, zlib, struct, shutil, json

# ─────────────────────────── THEME ────────────────────────────────────────────
BG        = "#0f0f1a"
CARD      = "#1a1a2e"
CARD2     = "#16213e"
ACCENT    = "#7c3aed"
ACCENT2   = "#a855f7"
SUCCESS   = "#10b981"
ERROR     = "#ef4444"
WARNING   = "#f59e0b"
TEXT      = "#e2e8f0"
SUBTEXT   = "#94a3b8"
ENTRY_BG  = "#111128"
FONT_HEAD = ("Segoe UI", 20, "bold")
FONT_BODY = ("Segoe UI", 11)
FONT_BOLD = ("Segoe UI", 11, "bold")
FONT_SM   = ("Segoe UI", 9)
FONT_MONO = ("Consolas", 9)

# ─────────────────────────── HELPERS ──────────────────────────────────────────
def normalize_url(url: str) -> str:
    url = url.strip()
    if url and not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    return url

def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower()) or "app"

def valid_package(pkg: str) -> bool:
    return bool(re.match(r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){1,}$', pkg))

def make_png(size: int, hex_color: str) -> bytes:
    """Create a minimal solid-color PNG — no external libraries needed."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    sig  = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
    row  = b"\x00" + bytes([r, g, b]) * size
    idat = chunk(b"IDAT", zlib.compress(row * size, 9))
    iend = chunk(b"IEND", b"")
    return sig + ihdr + idat + iend

def find_android_sdk() -> str:
    candidates = [
        os.environ.get("ANDROID_HOME", ""),
        os.environ.get("ANDROID_SDK_ROOT", ""),
        os.path.expanduser(r"~\AppData\Local\Android\Sdk"),
        r"C:\Android\Sdk",
        r"C:\Users\Public\Android\Sdk",
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            return c
    return ""

def find_android_studio() -> str:
    candidates = [
        r"C:\Program Files\Android\Android Studio\bin\studio64.exe",
        r"C:\Program Files\Android\Android Studio\bin\studio.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Android Studio\bin\studio64.exe"),
        os.path.expanduser(r"~\AppData\Local\Programs\Android Studio\bin\studio.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return ""

def find_java() -> str:
    """Return path to java.exe or empty string."""
    if shutil.which("java"):
        return shutil.which("java")
    java_home = os.environ.get("JAVA_HOME", "")
    if java_home:
        j = os.path.join(java_home, "bin", "java.exe")
        if os.path.isfile(j):
            return j
    # Common Android Studio JBR
    candidates = [
        r"C:\Program Files\Android\Android Studio\jbr\bin\java.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Android Studio\jbr\bin\java.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return ""

# ─────────────────────────── ANDROID PROJECT TEMPLATES ────────────────────────

SETTINGS_GRADLE = """\
pluginManagement {{
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
rootProject.name = "{app_name}"
include ':app'
"""

ROOT_BUILD_GRADLE = """\
plugins {{
    id 'com.android.application' version '8.2.2' apply false
}}
"""

APP_BUILD_GRADLE = """\
plugins {{
    id 'com.android.application'
}}

android {{
    namespace '{package}'
    compileSdk 34

    defaultConfig {{
        applicationId "{package}"
        minSdk 21
        targetSdk 34
        versionCode {version_code}
        versionName "{version_name}"
    }}

    buildTypes {{
        release {{
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }}
    }}

    compileOptions {{
        sourceCompatibility JavaVersion.VERSION_1_8
        targetCompatibility JavaVersion.VERSION_1_8
    }}
}}

dependencies {{
    implementation 'androidx.appcompat:appcompat:1.6.1'
}}
"""

ANDROID_MANIFEST = """\
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />

    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:supportsRtl="true"
        android:theme="@style/Theme.App"
        android:usesCleartextTraffic="true"
        android:hardwareAccelerated="true">

        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:configChanges="orientation|screenSize|keyboardHidden|screenLayout"
            android:screenOrientation="unspecified">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

    </application>
</manifest>
"""

MAIN_ACTIVITY_JAVA = r"""package {package};

import android.annotation.SuppressLint;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.GeolocationPermissions;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.appcompat.app.AppCompatActivity;

public class MainActivity extends AppCompatActivity {{

    private WebView webView;
    private static final String TARGET_URL = "{url}";

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);

        // ── Full-screen setup ─────────────────────────────────────────────
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        if (getSupportActionBar() != null) getSupportActionBar().hide();

        Window win = getWindow();
        win.setFlags(
            WindowManager.LayoutParams.FLAG_FULLSCREEN,
            WindowManager.LayoutParams.FLAG_FULLSCREEN
        );

        // Immersive sticky (Android 4.4+)
        win.getDecorView().setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_LAYOUT_STABLE
            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
            | View.SYSTEM_UI_FLAG_FULLSCREEN
            | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
        );

        // Edge-to-edge (Android 11+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {{
            win.setDecorFitsSystemWindows(false);
        }}

        // ── WebView ───────────────────────────────────────────────────────
        webView = new WebView(this);
        webView.setBackgroundColor(Color.parseColor("{bg_color}"));
        setContentView(webView);

        WebSettings ws = webView.getSettings();
        ws.setJavaScriptEnabled(true);
        ws.setDomStorageEnabled(true);
        ws.setDatabaseEnabled(true);
        ws.setLoadWithOverviewMode(true);
        ws.setUseWideViewPort(true);
        ws.setBuiltInZoomControls(false);
        ws.setDisplayZoomControls(false);
        ws.setSupportZoom(false);
        ws.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        ws.setMediaPlaybackRequiresUserGesture(false);
        ws.setAllowFileAccess(true);
        ws.setCacheMode(WebSettings.LOAD_DEFAULT);
        ws.setUserAgentString(
            "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
            + "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        );

        webView.setWebViewClient(new WebViewClient() {{
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {{
                view.loadUrl(req.getUrl().toString());
                return false;
            }}
        }});

        webView.setWebChromeClient(new WebChromeClient() {{
            @Override
            public void onGeolocationPermissionsShowPrompt(String origin,
                    GeolocationPermissions.Callback callback) {{
                callback.invoke(origin, true, false);
            }}
            @Override
            public void onPermissionRequest(PermissionRequest request) {{
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {{
                    request.grant(request.getResources());
                }}
            }}
        }});

        webView.loadUrl(TARGET_URL);
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
    protected void onResume() {{
        super.onResume();
        // Re-apply immersive mode after notifications / dialogs
        getWindow().getDecorView().setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_LAYOUT_STABLE
            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
            | View.SYSTEM_UI_FLAG_FULLSCREEN
            | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
        );
    }}
}}
"""

THEMES_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="Theme.App" parent="Theme.AppCompat.NoActionBar">
        <item name="colorPrimary">{theme_color}</item>
        <item name="colorPrimaryDark">{theme_color}</item>
        <item name="android:windowFullscreen">true</item>
        <item name="android:windowNoTitle">true</item>
        <item name="android:windowBackground">@color/bg_color</item>
    </style>
</resources>
"""

COLORS_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="primary">{theme_color}</color>
    <color name="bg_color">{bg_color}</color>
</resources>
"""

STRINGS_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">{app_name}</string>
</resources>
"""

GRADLE_WRAPPER_PROPS = r"""distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\://services.gradle.org/distributions/gradle-8.4-bin.zip
networkTimeout=10000
validateDistributionUrl=true
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
"""

GRADLEW_BAT = r"""@rem Gradle startup script for Windows
@if "%DEBUG%"=="" @echo off
@rem ##########################################################################
@rem  Auto-generated by APK Builder
@rem ##########################################################################
setlocal
set DIRNAME=%~dp0
if "%DIRNAME%"=="" set DIRNAME=.
set APP_HOME=%DIRNAME%
set DEFAULT_JVM_OPTS="-Xmx64m" "-Xms64m"
if defined JAVA_HOME goto findJavaFromJavaHome
set JAVA_EXE=java.exe
%JAVA_EXE% -version >NUL 2>&1
if %ERRORLEVEL% equ 0 goto execute
echo.
echo ERROR: JAVA_HOME is not set and no 'java' could be found in PATH.
goto fail
:findJavaFromJavaHome
set JAVA_HOME=%JAVA_HOME:"=%
set JAVA_EXE=%JAVA_HOME%/bin/java.exe
if exist "%JAVA_EXE%" goto execute
echo ERROR: JAVA_HOME points to invalid directory: %JAVA_HOME%
goto fail
:execute
set CLASSPATH=%APP_HOME%\gradle\wrapper\gradle-wrapper.jar
"%JAVA_EXE%" %DEFAULT_JVM_OPTS% %JAVA_OPTS% %GRADLE_OPTS% ^
  "-Dorg.gradle.appname=%APP_BASE_NAME%" ^
  -classpath "%CLASSPATH%" ^
  org.gradle.wrapper.GradleWrapperMain %*
:end
if %ERRORLEVEL% equ 0 goto mainEnd
:fail
exit /b 1
:mainEnd
endlocal
"""

GITIGNORE = """\
*.iml
.gradle
/local.properties
/.idea
/build
/captures
.externalNativeBuild
.cxx
"""

PROGUARD = """\
# ProGuard rules
-keep class {package}.** {{ *; }}
"""

BUILD_INSTRUCTIONS = """\
# How to build the APK

## Option A — Android Studio (Recommended, free)
1. Download Android Studio: https://developer.android.com/studio
2. Open this folder as a project in Android Studio
3. Wait for Gradle sync to finish (first time takes a few minutes)
4. Click **Build ▶ Build Bundle(s) / APK(s) ▶ Build APK(s)**
5. Click "locate" in the notification — APK is in app/build/outputs/apk/debug/

## Option B — Command Line (requires Android SDK + JDK 17)
```
gradlew.bat assembleDebug
```
APK will be at: app\\build\\outputs\\apk\\debug\\app-debug.apk

## Option C — Install via ADB (USB debugging enabled on phone)
```
adb install app\\build\\outputs\\apk\\debug\\app-debug.apk
```

## Requirements
- JDK 17+ (bundled with Android Studio)
- Android SDK with Build Tools 34 (installed via SDK Manager)
- ANDROID_HOME environment variable pointing to the SDK
"""

# ─────────────────────────── PROJECT GENERATOR ────────────────────────────────

def generate_project(app_name: str, url: str, package: str,
                     theme_color: str, bg_color: str,
                     out_dir: str, version_code: int = 1,
                     version_name: str = "1.0",
                     log=None) -> str:
    """
    Generates a complete Android Studio project folder.
    Returns the project root path.
    """

    def report(msg: str):
        if log:
            log(msg)

    slug = slugify(app_name)
    proj = os.path.join(out_dir, slug + "_apk")
    pkg_path = package.replace(".", "/")

    # ── Create directories ────────────────────────────────────────────────
    report(f"📁  Creating project: {proj}")
    for sub in [
        "gradle/wrapper",
        "app/src/main/java/" + pkg_path,
        "app/src/main/res/layout",
        "app/src/main/res/values",
        *(f"app/src/main/res/mipmap-{d}" for d in
          ["mdpi", "hdpi", "xhdpi", "xxhdpi", "xxxhdpi"]),
    ]:
        os.makedirs(os.path.join(proj, sub.replace("/", os.sep)), exist_ok=True)

    def write_text(rel: str, content: str):
        p = os.path.join(proj, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

    def write_bin(rel: str, data: bytes):
        p = os.path.join(proj, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as f:
            f.write(data)

    # ── Write Gradle files ────────────────────────────────────────────────
    report("⚙️   Writing Gradle build files…")
    write_text("settings.gradle",      SETTINGS_GRADLE.format(app_name=app_name))
    write_text("build.gradle",         ROOT_BUILD_GRADLE)
    write_text("app/build.gradle",     APP_BUILD_GRADLE.format(
        package=package, version_code=version_code, version_name=version_name))
    write_text("gradle.properties",    "android.useAndroidX=true\nandroid.enableJetifier=true\n")
    write_text("gradle/wrapper/gradle-wrapper.properties", GRADLE_WRAPPER_PROPS)
    write_text("gradlew.bat",          GRADLEW_BAT)
    write_text(".gitignore",           GITIGNORE)
    write_text("app/proguard-rules.pro", PROGUARD.format(package=package))

    # ── Android SDK path ──────────────────────────────────────────────────
    sdk = find_android_sdk()
    if sdk:
        write_text("local.properties",
                   "sdk.dir=" + sdk.replace("\\", "\\\\") + "\n")
        report(f"✅  Android SDK found: {sdk}")
    else:
        write_text("local.properties",
                   "# sdk.dir=C:\\\\Users\\\\YourName\\\\AppData\\\\Local\\\\Android\\\\Sdk\n")
        report("⚠️   Android SDK not found — set sdk.dir in local.properties")

    # ── Android source files ──────────────────────────────────────────────
    report("📝  Writing Android source files…")
    write_text("app/src/main/AndroidManifest.xml", ANDROID_MANIFEST)
    write_text(
        f"app/src/main/java/{pkg_path}/MainActivity.java",
        MAIN_ACTIVITY_JAVA.format(package=package, url=url, bg_color=bg_color)
    )
    write_text("app/src/main/res/values/strings.xml",
               STRINGS_XML.format(app_name=app_name))
    write_text("app/src/main/res/values/themes.xml",
               THEMES_XML.format(theme_color=theme_color))
    write_text("app/src/main/res/values/colors.xml",
               COLORS_XML.format(theme_color=theme_color, bg_color=bg_color))

    # ── Launcher icons ────────────────────────────────────────────────────
    report("🎨  Generating launcher icons…")
    color = theme_color if re.match(r'^#[0-9a-fA-F]{6}$', theme_color) else "#7c3aed"
    for mip, sz in [("mdpi",48),("hdpi",72),("xhdpi",96),("xxhdpi",144),("xxxhdpi",192)]:
        ico = make_png(sz, color)
        write_bin(f"app/src/main/res/mipmap-{mip}/ic_launcher.png",       ico)
        write_bin(f"app/src/main/res/mipmap-{mip}/ic_launcher_round.png", ico)

    # ── Download gradle-wrapper.jar ───────────────────────────────────────
    jar_path = os.path.join(proj, "gradle", "wrapper", "gradle-wrapper.jar")
    report("⬇️   Downloading gradle-wrapper.jar…")
    jar_url = ("https://raw.githubusercontent.com/nicowillis/"
               "gradle-wrapper/main/gradle-wrapper.jar")
    # Fallback: pull directly from a gradle distribution mirror
    jar_urls = [
        jar_url,
        ("https://raw.githubusercontent.com/gradle/gradle/"
         "v8.4.0/gradle/wrapper/gradle-wrapper.jar"),
    ]
    downloaded = False
    for u in jar_urls:
        try:
            urllib.request.urlretrieve(u, jar_path)
            downloaded = True
            report("✅  gradle-wrapper.jar downloaded")
            break
        except Exception:
            continue
    if not downloaded:
        report("⚠️   Could not download gradle-wrapper.jar (need internet).")
        report("    Open the project in Android Studio — it will fix this automatically.")

    # ── Build instructions ────────────────────────────────────────────────
    write_text("HOW_TO_BUILD.md", BUILD_INSTRUCTIONS)

    report(f"\n✅  Project ready: {proj}\n")
    return proj


# ─────────────────────────── GUI ──────────────────────────────────────────────

class APKBuilderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("APK Builder — Fullscreen Website Shortcuts")
        self.geometry("820x780")
        self.minsize(700, 640)
        self.configure(bg=BG)

        self._proj_dir = ""
        self._build_running = False

        self._build_ui()

    # ── Layout ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=CARD, padx=28, pady=18)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📱 APK Builder", font=FONT_HEAD,
                 bg=CARD, fg=ACCENT2).pack(side="left")
        tk.Label(hdr, text="  Generate fullscreen Android apps from any website",
                 font=("Segoe UI", 10), bg=CARD, fg=SUBTEXT).pack(
                     side="left", pady=(8, 0))

        # Status badge
        self._sdk_badge = tk.Label(hdr, font=("Segoe UI", 9, "bold"),
                                   bg=CARD, padx=8, pady=3)
        self._sdk_badge.pack(side="right")
        self._refresh_sdk_badge()

        # Form
        form = tk.Frame(self, bg=BG, padx=24, pady=16)
        form.pack(fill="x")

        self._fields = {}
        rows = [
            ("App Name",     "app_name",      "e.g.  YouTube",              False),
            ("Website URL",  "url",           "e.g.  youtube.com",           False),
            ("Package Name", "package",       "e.g.  com.myname.youtube",    False),
            ("Version Name", "version_name",  "e.g.  1.0",                  False),
        ]
        for label, key, hint, _ in rows:
            self._make_field(form, label, key, hint)

        # Color row
        color_row = tk.Frame(form, bg=BG)
        color_row.pack(fill="x", pady=4)
        tk.Label(color_row, text="Theme Color", width=14, anchor="w",
                 font=FONT_BODY, bg=BG, fg=TEXT).pack(side="left")
        self._theme_var = tk.StringVar(value="#7c3aed")
        self._bg_var    = tk.StringVar(value="#0f0f1a")
        self._color_widget(color_row, self._theme_var, "Theme")
        tk.Label(color_row, text="   BG Color", font=FONT_BODY,
                 bg=BG, fg=TEXT).pack(side="left")
        self._color_widget(color_row, self._bg_var, "Background")

        # Output dir
        out_row = tk.Frame(form, bg=BG)
        out_row.pack(fill="x", pady=4)
        tk.Label(out_row, text="Output Folder", width=14, anchor="w",
                 font=FONT_BODY, bg=BG, fg=TEXT).pack(side="left")
        self._out_var = tk.StringVar(
            value=os.path.join(os.path.expanduser("~"), "Desktop", "APK Projects"))
        tk.Entry(out_row, textvariable=self._out_var, width=46,
                 bg=ENTRY_BG, fg=TEXT, insertbackground=TEXT,
                 relief="flat", font=FONT_BODY).pack(side="left", ipady=5, padx=(0, 6))
        self._btn(out_row, "Browse", self._browse, bg=CARD2, fg=ACCENT2)

        # ── Generate button (prominent, always visible) ──────────────────
        gen_zone = tk.Frame(self, bg=BG, pady=10)
        gen_zone.pack(fill="x", padx=24)

        self._btn_gen = tk.Button(
            gen_zone,
            text="📦  Generate Android Project",
            command=self._start_generate,
            bg=ACCENT, fg="#fff",
            activebackground=ACCENT2, activeforeground="#fff",
            relief="flat", cursor="hand2",
            font=("Segoe UI", 13, "bold"),
            padx=24, pady=12,
        )
        self._btn_gen.pack(fill="x")

        # Divider
        tk.Frame(self, bg=CARD, height=1).pack(fill="x", padx=0, pady=(8, 0))

        # ── Log area ──────────────────────────────────────────────────────
        log_frame = tk.Frame(self, bg=BG, padx=24, pady=10)
        log_frame.pack(fill="both", expand=True)
        tk.Label(log_frame, text="Build Log", font=("Segoe UI", 10, "bold"),
                 bg=BG, fg=SUBTEXT).pack(anchor="w", pady=(0, 4))

        txt_frame = tk.Frame(log_frame, bg=CARD, bd=1, relief="flat")
        txt_frame.pack(fill="both", expand=True)
        self._log = tk.Text(txt_frame, bg="#0a0a14", fg=TEXT, font=FONT_MONO,
                            wrap="word", relief="flat", padx=10, pady=8,
                            state="disabled", insertbackground=TEXT)
        sb = tk.Scrollbar(txt_frame, command=self._log.yview)
        self._log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._log.pack(fill="both", expand=True)

        self._log.tag_configure("ok",   foreground=SUCCESS)
        self._log.tag_configure("warn", foreground=WARNING)
        self._log.tag_configure("err",  foreground=ERROR)
        self._log.tag_configure("head", foreground=ACCENT2)

        # ── Bottom action bar (2 rows) ────────────────────────────────────
        bottom = tk.Frame(self, bg=CARD, padx=20, pady=10)
        bottom.pack(fill="x", side="bottom")

        # Row 1 — status
        row1 = tk.Frame(bottom, bg=CARD)
        row1.pack(fill="x", pady=(0, 6))
        self._status = tk.Label(row1, text="Ready — fill the form and click Generate",
                                font=("Segoe UI", 9), bg=CARD, fg=SUBTEXT)
        self._status.pack(side="left")

        # Row 2 — secondary action buttons
        row2 = tk.Frame(bottom, bg=CARD)
        row2.pack(fill="x")

        self._btn_build = tk.Button(
            row2, text="⚡  Build APK",
            command=self._start_build_apk,
            bg="#4c1d95", fg="#fff",
            activebackground=ACCENT2, activeforeground="#fff",
            relief="flat", cursor="hand2",
            font=("Segoe UI", 11, "bold"), padx=18, pady=8,
        )
        self._btn_build.pack(side="left", padx=(0, 8))

        self._btn_open_dir = tk.Button(
            row2, text="📁  Open Folder",
            command=self._open_folder,
            bg=CARD2, fg=TEXT,
            activebackground=CARD, activeforeground=ACCENT2,
            relief="flat", cursor="hand2",
            font=FONT_BODY, padx=12, pady=8, state="disabled",
        )
        self._btn_open_dir.pack(side="left", padx=(0, 8))

        self._btn_open_as = tk.Button(
            row2, text="📂  Open in Android Studio",
            command=self._open_android_studio,
            bg=CARD2, fg=ACCENT2,
            activebackground=CARD, activeforeground=ACCENT2,
            relief="flat", cursor="hand2",
            font=FONT_BODY, padx=12, pady=8, state="disabled",
        )
        self._btn_open_as.pack(side="left")

        self._log_line("head",
            "APK Builder — Python → Android WebView APK Generator\n"
            "Fill in the form above and click 'Generate Project'.\n"
            "Then click '⚡ Build APK' if you have Android SDK installed,\n"
            "or open the project in Android Studio (free).\n"
        )

    # ── Field helpers ────────────────────────────────────────────────────────
    def _make_field(self, parent, label, key, hint):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=4)
        tk.Label(row, text=label, width=14, anchor="w",
                 font=FONT_BODY, bg=BG, fg=TEXT).pack(side="left")
        var = tk.StringVar()
        e = tk.Entry(row, textvariable=var, width=50, bg=ENTRY_BG, fg=TEXT,
                     insertbackground=TEXT, relief="flat", font=FONT_BODY)
        e.insert(0, hint)
        e.config(fg=SUBTEXT)

        def _fi(event=None, _e=e, _h=hint):
            if _e.get() == _h: _e.delete(0, "end"); _e.config(fg=TEXT)
        def _fo(event=None, _e=e, _h=hint):
            if not _e.get(): _e.insert(0, _h); _e.config(fg=SUBTEXT)

        e.bind("<FocusIn>",  _fi)
        e.bind("<FocusOut>", _fo)
        e.pack(side="left", ipady=5)
        self._fields[key] = (var, e, hint)

    def _color_widget(self, parent, var, title):
        f = tk.Frame(parent, bg=BG)
        f.pack(side="left", padx=(4, 12))
        e = tk.Entry(f, textvariable=var, width=9, bg=ENTRY_BG, fg=TEXT,
                     insertbackground=TEXT, relief="flat", font=FONT_BODY)
        e.pack(side="left", ipady=4)
        sw = tk.Label(f, bg=var.get(), width=3, height=1, cursor="hand2")
        sw.pack(side="left", padx=(3, 0))

        def pick():
            from tkinter.colorchooser import askcolor
            c = askcolor(color=var.get(), title=f"Pick {title} color")[1]
            if c:
                var.set(c)
                sw.config(bg=c)

        sw.bind("<Button-1>", lambda _: pick())
        var.trace_add("write", lambda *_: sw.config(
            bg=var.get() if re.match(r'^#[0-9a-fA-F]{6}$', var.get()) else CARD))

    def _btn(self, parent, text, cmd, bg=CARD, fg=TEXT,
             side=None, padx=8, pady=6, font=FONT_BODY):
        b = tk.Button(parent, text=text, command=cmd,
                      bg=bg, fg=fg, activebackground=ACCENT2, activeforeground="#fff",
                      relief="flat", cursor="hand2", font=font, padx=padx, pady=pady)
        if side:
            b.pack(side=side, padx=4)
        return b

    def _refresh_sdk_badge(self):
        sdk = find_android_sdk()
        java = find_java()
        if sdk and java:
            self._sdk_badge.config(text="✅ SDK + JDK found", bg=SUCCESS, fg="#fff")
        elif sdk:
            self._sdk_badge.config(text="⚠ SDK found, no JDK", bg=WARNING, fg="#111")
        else:
            self._sdk_badge.config(text="⚠ SDK not found", bg=WARNING, fg="#111")

    # ── Log ─────────────────────────────────────────────────────────────────
    def _log_line(self, tag: str, text: str):
        self._log.config(state="normal")
        self._log.insert("end", text + "\n", tag)
        self._log.see("end")
        self._log.config(state="disabled")

    def _log_clear(self):
        self._log.config(state="normal")
        self._log.delete("1.0", "end")
        self._log.config(state="disabled")

    # ── Input validation ─────────────────────────────────────────────────────
    def _get_inputs(self):
        placeholders = {k: v[2] for k, v in self._fields.items()}
        values = {}
        for k, (var, e, hint) in self._fields.items():
            v = var.get().strip()
            values[k] = "" if v == hint else v

        errors = []
        if not values["app_name"]:
            errors.append("• App Name is required")
        url = normalize_url(values["url"])
        if not url or url == "https://":
            errors.append("• Website URL is required")
        else:
            values["url"] = url

        pkg = values["package"]
        if not pkg:
            # Auto-generate from app name
            slug = slugify(values.get("app_name", "app"))
            pkg = f"com.shortcut.{slug}"
            values["package"] = pkg
            self._log_line("warn", f"  Package auto-set to: {pkg}")
        elif not valid_package(pkg):
            errors.append("• Package Name must be like com.yourname.appname")

        if not values["version_name"]:
            values["version_name"] = "1.0"

        return values, errors

    # ── Generate ─────────────────────────────────────────────────────────────
    def _start_generate(self):
        values, errors = self._get_inputs()
        if errors:
            messagebox.showerror("Input Error", "\n".join(errors))
            return

        self._log_clear()
        self._log_line("head", "═" * 60)
        self._log_line("head", f"  Generating project: {values['app_name']}")
        self._log_line("head", "═" * 60)

        out = self._out_var.get().strip()
        theme = self._theme_var.get()
        bg    = self._bg_var.get()

        def _run():
            try:
                proj = generate_project(
                    app_name     = values["app_name"],
                    url          = values["url"],
                    package      = values["package"],
                    theme_color  = theme,
                    bg_color     = bg,
                    out_dir      = out,
                    version_name = values["version_name"],
                    log          = lambda m: self.after(0, self._log_line,
                                                        "ok" if "✅" in m else
                                                        "warn" if "⚠" in m else "", m),
                )
                self.after(0, self._generate_done, proj)
            except Exception as exc:
                self.after(0, self._log_line, "err", f"\n❌ Error: {exc}")
                self.after(0, self._status_set, "Generation failed", ERROR)

        self._status_set("Generating…", ACCENT2)
        self._btn_gen.config(state="disabled")
        threading.Thread(target=_run, daemon=True).start()

    def _generate_done(self, proj: str):
        self._proj_dir = proj
        self._btn_gen.config(state="normal")
        self._btn_open_dir.config(state="normal")

        as_exe = find_android_studio()
        if as_exe:
            self._btn_open_as.config(state="normal")

        self._status_set("Project generated ✅", SUCCESS)
        self._log_line("head", "\n📱 What to do next:")
        self._log_line("",
            "  1. Click '⚡ Build APK' (if Android SDK is installed)\n"
            "  OR\n"
            "  2. Click '📂 Open in Android Studio' → Build ▶ Build APK(s)\n"
            "  OR\n"
            "  3. Open the folder and read HOW_TO_BUILD.md\n"
        )

    # ── Build APK ────────────────────────────────────────────────────────────
    def _start_build_apk(self):
        if not self._proj_dir:
            messagebox.showinfo("Generate First",
                                "Click 'Generate Project' first to create the Android project.")
            return
        if self._build_running:
            return

        sdk  = find_android_sdk()
        java = find_java()

        if not sdk:
            self._log_line("err",
                "\n❌ Android SDK not found.\n"
                "   Please install Android Studio from https://developer.android.com/studio\n"
                "   then reopen APK Builder.")
            messagebox.showerror("Android SDK Missing",
                "Android SDK not found.\n\n"
                "Install Android Studio (free) which includes the SDK.\n"
                "https://developer.android.com/studio")
            return

        if not java:
            self._log_line("err",
                "\n❌ Java (JDK) not found.\n"
                "   Android Studio includes JBR — make sure it is installed.")
            messagebox.showerror("Java Not Found",
                "Java JDK not found.\n\n"
                "Android Studio bundles JBR — install Android Studio first.\n"
                "https://developer.android.com/studio")
            return

        jar = os.path.join(self._proj_dir, "gradle", "wrapper", "gradle-wrapper.jar")
        if not os.path.isfile(jar):
            self._log_line("warn",
                "\n⚠ gradle-wrapper.jar not found — attempting to fix with Android Studio's Gradle…")

        self._log_clear()
        self._log_line("head", "═" * 60)
        self._log_line("head", "  Building debug APK…")
        self._log_line("head", "═" * 60)
        self._log_line("", f"  Project: {self._proj_dir}\n")

        self._build_running = True
        self._btn_build.config(state="disabled", text="⏳ Building…")
        self._status_set("Building APK…", ACCENT2)

        def _run():
            gradlew = os.path.join(self._proj_dir, "gradlew.bat")
            env = os.environ.copy()
            env["ANDROID_HOME"] = sdk
            if java:
                env["JAVA_HOME"] = os.path.dirname(os.path.dirname(java))

            try:
                proc = subprocess.Popen(
                    [gradlew, "assembleDebug", "--stacktrace"],
                    cwd=self._proj_dir,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                )
                for line in proc.stdout:
                    line = line.rstrip()
                    tag = "err" if "error" in line.lower() else \
                          "warn" if "warning" in line.lower() else \
                          "ok" if "BUILD SUCCESSFUL" in line else ""
                    self.after(0, self._log_line, tag, "  " + line)
                proc.wait()
                success = proc.returncode == 0
                self.after(0, self._build_done, success)
            except FileNotFoundError:
                self.after(0, self._log_line, "err",
                           "❌  gradlew.bat not found or Gradle failed to start.")
                self.after(0, self._build_done, False)

        threading.Thread(target=_run, daemon=True).start()

    def _build_done(self, success: bool):
        self._build_running = False
        self._btn_build.config(state="normal", text="⚡ Build APK")
        if success:
            apk = os.path.join(self._proj_dir, "app", "build", "outputs",
                               "apk", "debug", "app-debug.apk")
            self._status_set("Build SUCCESS ✅", SUCCESS)
            self._log_line("ok", f"\n✅  APK ready: {apk}\n")
            if os.path.isfile(apk):
                if messagebox.askyesno("APK Built!",
                    f"APK built successfully!\n\n{apk}\n\nOpen the APK folder?"):
                    os.startfile(os.path.dirname(apk))
        else:
            self._status_set("Build FAILED ❌", ERROR)
            self._log_line("err",
                "\n❌  Build failed. Check the log above for details.\n"
                "   Tip: Open the project in Android Studio for easier debugging.")

    # ── Misc actions ─────────────────────────────────────────────────────────
    def _browse(self):
        d = filedialog.askdirectory(title="Select output folder")
        if d:
            self._out_var.set(d)

    def _open_folder(self):
        if self._proj_dir and os.path.isdir(self._proj_dir):
            os.startfile(self._proj_dir)

    def _open_android_studio(self):
        exe = find_android_studio()
        if exe and self._proj_dir:
            subprocess.Popen([exe, self._proj_dir])
        elif not exe:
            import webbrowser
            webbrowser.open("https://developer.android.com/studio")

    def _status_set(self, text: str, color: str = SUBTEXT):
        self._status.config(text=text, fg=color)


# ─────────────────────────── ENTRY ────────────────────────────────────────────
if __name__ == "__main__":
    app = APKBuilderApp()
    app.mainloop()
