"""
Emulator Demo — Creates an Android Virtual Device and launches a fullscreen
website demo inside it. No Java / Gradle needed to run the emulator itself.

SDK assumed at D:\Android  (auto-detected if elsewhere)
System image: android-31 / google_apis / x86_64
"""

import tkinter as tk
from tkinter import simpledialog
import os, subprocess, threading, time, sys

# ─────────────────────────── THEME ────────────────────────────────────────────
BG      = "#0f0f1a"
CARD    = "#1a1a2e"
CARD2   = "#16213e"
ACCENT  = "#7c3aed"
ACCENT2 = "#a855f7"
SUCCESS = "#10b981"
ERROR   = "#ef4444"
WARNING = "#f59e0b"
TEXT    = "#e2e8f0"
SUBTEXT = "#94a3b8"

# ─────────────────────────── SDK / AVD PATHS ──────────────────────────────────
SDK_CANDIDATES = [
    r"D:\Android",
    os.environ.get("ANDROID_HOME", ""),
    os.environ.get("ANDROID_SDK_ROOT", ""),
    os.path.expanduser(r"~\AppData\Local\Android\Sdk"),
]
AVD_NAME    = "ShortcutDemo"
AVD_DIR     = os.path.join(os.path.expanduser("~"), ".android", "avd")
DEMO_URL    = "https://www.youtube.com"   # default demo URL
SYSIMG_REL  = r"system-images\android-31\google_apis\x86_64"


def find_sdk() -> str:
    for c in SDK_CANDIDATES:
        if c and os.path.isdir(c):
            return c
    return ""

def sdk_tool(sdk: str, *parts: str) -> str:
    return os.path.join(sdk, *parts)


# ─────────────────────────── AVD CREATOR ──────────────────────────────────────

def create_avd(sdk: str, avd_name: str) -> tuple[bool, str]:
    """
    Creates AVD config files directly (no Java / avdmanager needed).
    Returns (success, message).
    """
    avd_ini  = os.path.join(AVD_DIR, f"{avd_name}.ini")
    avd_data = os.path.join(AVD_DIR, f"{avd_name}.avd")

    if os.path.isfile(avd_ini):
        return True, f"AVD already exists: {avd_name}"

    os.makedirs(avd_data, exist_ok=True)

    sysimg_path = sdk_tool(sdk, SYSIMG_REL) + "\\"   # trailing backslash required

    # ── .ini (top-level registry entry) ───────────────────────────────────
    ini_content = (
        f"avd.ini.encoding=UTF-8\n"
        f"path={avd_data}\n"
        f"path.rel=avd\\{avd_name}.avd\n"
        f"target=android-31\n"
    )
    with open(avd_ini, "w") as f:
        f.write(ini_content)

    # ── config.ini (hardware profile) ────────────────────────────────────
    cfg = (
        f"AvdId={avd_name}\n"
        f"PlayStore.enabled=false\n"
        f"abi.type=x86_64\n"
        f"avd.ini.displayname=Shortcut Demo Phone\n"
        f"avd.ini.encoding=UTF-8\n"
        f"disk.dataPartition.size=2147483648\n"
        f"fastboot.forceColdBoot=no\n"
        f"hw.accelerometer=yes\n"
        f"hw.arc=false\n"
        f"hw.audioInput=yes\n"
        f"hw.battery=yes\n"
        f"hw.camera.back=none\n"
        f"hw.camera.front=none\n"
        f"hw.cpu.arch=x86_64\n"
        f"hw.cpu.ncore=4\n"
        f"hw.dPad=no\n"
        f"hw.gps=yes\n"
        f"hw.gpu.enabled=yes\n"
        f"hw.gpu.mode=auto\n"
        f"hw.initialOrientation=Portrait\n"
        f"hw.keyboard=yes\n"
        f"hw.lcd.density=420\n"
        f"hw.lcd.height=1920\n"
        f"hw.lcd.width=1080\n"
        f"hw.mainKeys=no\n"
        f"hw.ramSize=2048\n"
        f"hw.sdCard=no\n"
        f"hw.sensors.orientation=yes\n"
        f"hw.sensors.proximity=yes\n"
        f"hw.trackBall=no\n"
        f"image.sysdir.1={sysimg_path}\n"
        f"runtime.network.latency=none\n"
        f"runtime.network.speed=full\n"
        f"skin.dynamic=yes\n"
        f"skin.name=1080x1920\n"
        f"skin.path=_no_skin\n"
        f"tag.display=Google APIs\n"
        f"tag.id=google_apis\n"
        f"vm.heapSize=512\n"
    )
    with open(os.path.join(avd_data, "config.ini"), "w") as f:
        f.write(cfg)

    return True, f"AVD created: {avd_name}  →  {avd_data}"


# ─────────────────────────── ADB HELPERS ──────────────────────────────────────

def adb(sdk: str, *args, capture=True):
    adb_exe = sdk_tool(sdk, "platform-tools", "adb.exe")
    try:
        r = subprocess.run([adb_exe, *args],
                           capture_output=capture, text=True, timeout=30)
        return (r.stdout + r.stderr).strip()
    except Exception as e:
        return str(e)

def wait_for_boot(sdk: str, log, max_wait=180) -> bool:
    """Poll adb until device is fully booted."""
    adb_exe = sdk_tool(sdk, "platform-tools", "adb.exe")
    deadline = time.time() + max_wait
    log("⏳ Waiting for emulator to boot…")
    while time.time() < deadline:
        try:
            r = subprocess.run(
                [adb_exe, "shell", "getprop", "sys.boot_completed"],
                capture_output=True, text=True, timeout=5)
            if r.stdout.strip() == "1":
                return True
        except Exception:
            pass
        time.sleep(3)
    return False

def open_url_fullscreen(sdk: str, url: str):
    """Open URL in Chrome on the emulator."""
    adb(sdk,
        "shell", "am", "start",
        "-a", "android.intent.action.VIEW",
        "-d", url,
        "com.android.chrome/.Main")
    time.sleep(2)
    # Dismiss "Welcome to Chrome" if it pops up
    adb(sdk, "shell", "input", "keyevent", "4")   # back once
    time.sleep(1)
    # Re-open URL cleanly
    adb(sdk,
        "shell", "am", "start",
        "-n", "com.android.chrome/.Main",
        "--es", "url", url)

def install_and_run_apk(sdk: str, apk_path: str, package: str, log):
    log(f"📦  Installing APK…")
    out = adb(sdk, "install", "-r", apk_path)
    log(f"   {out}")
    if "Success" in out or "success" in out:
        log("▶️   Launching app…")
        adb(sdk, "shell", "monkey", "-p", package, "-c",
            "android.intent.category.LAUNCHER", "1")
        log("✅  App running in emulator!")
    else:
        log(f"⚠️   Install may have failed: {out}")


# ─────────────────────────── GUI ──────────────────────────────────────────────

class EmulatorDemo(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("📱 Emulator Demo — Virtual Android Phone")
        self.geometry("760x620")
        self.minsize(640, 500)
        self.configure(bg=BG)
        self._sdk        = find_sdk()
        self._emu_proc   = None
        self._running    = False
        self._build_ui()

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=CARD, padx=24, pady=16)
        hdr.pack(fill="x")
        tk.Label(hdr, text="📱 Virtual Android Demo",
                 font=("Segoe UI", 18, "bold"), bg=CARD, fg=ACCENT2).pack(side="left")
        badge_text = f"SDK: {self._sdk}" if self._sdk else "⚠ SDK not found"
        badge_bg   = CARD2 if self._sdk else ERROR
        tk.Label(hdr, text=badge_text, font=("Segoe UI", 8),
                 bg=badge_bg, fg=TEXT, padx=8, pady=4).pack(side="right")

        # URL input
        url_frame = tk.Frame(self, bg=BG, padx=24, pady=14)
        url_frame.pack(fill="x")
        tk.Label(url_frame, text="Demo URL:", font=("Segoe UI", 11),
                 bg=BG, fg=TEXT, width=12, anchor="w").pack(side="left")
        self._url_var = tk.StringVar(value=DEMO_URL)
        tk.Entry(url_frame, textvariable=self._url_var, width=48,
                 bg="#111128", fg=TEXT, insertbackground=TEXT,
                 relief="flat", font=("Segoe UI", 11)).pack(
                     side="left", ipady=6, padx=(0, 8))

        # APK row
        apk_frame = tk.Frame(self, bg=BG, padx=24, pady=4)
        apk_frame.pack(fill="x")
        tk.Label(apk_frame, text="APK (optional):", font=("Segoe UI", 11),
                 bg=BG, fg=TEXT, width=12, anchor="w").pack(side="left")
        self._apk_var = tk.StringVar(value="")
        tk.Entry(apk_frame, textvariable=self._apk_var, width=40,
                 bg="#111128", fg=SUBTEXT, insertbackground=TEXT,
                 relief="flat", font=("Segoe UI", 10)).pack(
                     side="left", ipady=5, padx=(0, 8))
        tk.Button(apk_frame, text="Browse APK",
                  command=self._browse_apk,
                  bg=CARD2, fg=ACCENT2, relief="flat",
                  cursor="hand2", font=("Segoe UI", 10),
                  padx=8, pady=5).pack(side="left")

        # Package (for APK launch)
        pkg_frame = tk.Frame(self, bg=BG, padx=24, pady=4)
        pkg_frame.pack(fill="x")
        tk.Label(pkg_frame, text="Package name:", font=("Segoe UI", 11),
                 bg=BG, fg=TEXT, width=12, anchor="w").pack(side="left")
        self._pkg_var = tk.StringVar(value="")
        tk.Entry(pkg_frame, textvariable=self._pkg_var, width=40,
                 bg="#111128", fg=SUBTEXT, insertbackground=TEXT,
                 relief="flat", font=("Segoe UI", 10)).pack(
                     side="left", ipady=5)
        tk.Label(pkg_frame, text="  ← only needed when installing APK",
                 font=("Segoe UI", 8), bg=BG, fg=SUBTEXT).pack(side="left")

        # Big launch button
        btn_zone = tk.Frame(self, bg=BG, padx=24, pady=12)
        btn_zone.pack(fill="x")
        self._launch_btn = tk.Button(
            btn_zone,
            text="🚀  Launch Virtual Android Phone",
            command=self._launch,
            bg=ACCENT, fg="#fff",
            activebackground=ACCENT2, activeforeground="#fff",
            relief="flat", cursor="hand2",
            font=("Segoe UI", 13, "bold"),
            padx=24, pady=12,
        )
        self._launch_btn.pack(fill="x")

        # Secondary buttons
        sec = tk.Frame(self, bg=BG, padx=24)
        sec.pack(fill="x", pady=(0, 8))
        self._open_url_btn = tk.Button(
            sec, text="🌐  Open URL in emulator",
            command=self._open_url,
            bg=CARD2, fg=ACCENT2, relief="flat", cursor="hand2",
            font=("Segoe UI", 10), padx=10, pady=7, state="disabled")
        self._open_url_btn.pack(side="left", padx=(0, 8))

        self._install_btn = tk.Button(
            sec, text="📦  Install & Run APK",
            command=self._install_apk,
            bg=CARD2, fg=ACCENT2, relief="flat", cursor="hand2",
            font=("Segoe UI", 10), padx=10, pady=7, state="disabled")
        self._install_btn.pack(side="left", padx=(0, 8))

        self._kill_btn = tk.Button(
            sec, text="⏹  Stop Emulator",
            command=self._stop,
            bg="#3b0000", fg=ERROR, relief="flat", cursor="hand2",
            font=("Segoe UI", 10), padx=10, pady=7, state="disabled")
        self._kill_btn.pack(side="right")

        # Divider
        tk.Frame(self, bg=CARD, height=1).pack(fill="x")

        # Log
        log_f = tk.Frame(self, bg=BG, padx=24, pady=10)
        log_f.pack(fill="both", expand=True)
        tk.Label(log_f, text="Console", font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=SUBTEXT).pack(anchor="w", pady=(0, 4))
        txt_wrap = tk.Frame(log_f, bg=CARD)
        txt_wrap.pack(fill="both", expand=True)
        self._log = tk.Text(txt_wrap, bg="#08080f", fg=TEXT,
                            font=("Consolas", 9), wrap="word",
                            relief="flat", padx=10, pady=8,
                            state="disabled")
        sb = tk.Scrollbar(txt_wrap, command=self._log.yview)
        self._log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._log.pack(fill="both", expand=True)
        self._log.tag_configure("ok",   foreground=SUCCESS)
        self._log.tag_configure("warn", foreground=WARNING)
        self._log.tag_configure("err",  foreground=ERROR)
        self._log.tag_configure("hi",   foreground=ACCENT2)

        # Status bar
        self._status = tk.Label(self, text="Ready", font=("Segoe UI", 9),
                                bg=CARD, fg=SUBTEXT, anchor="w", padx=16, pady=6)
        self._status.pack(fill="x", side="bottom")

        # Welcome message
        self._log_line("hi",
            "Virtual Android Demo\n"
            "════════════════════\n"
            "1. Enter the URL you want to demo\n"
            "2. Click 🚀 Launch Virtual Android Phone\n"
            "3. Wait ~60s for the emulator to boot\n"
            "4. Click 🌐 Open URL to see it fullscreen\n"
            "   — or —\n"
            "   Browse to your APK file and click 📦 Install & Run APK\n"
        )

    # ── helpers ──────────────────────────────────────────────────────────────
    def _log_line(self, tag, text):
        self._log.config(state="normal")
        self._log.insert("end", text + "\n", tag)
        self._log.see("end")
        self._log.config(state="disabled")

    def _log_cb(self, text):
        tag = "ok"  if "✅" in text or "▶" in text else \
              "warn" if "⚠" in text or "⏳" in text else \
              "err"  if "❌" in text else ""
        self.after(0, self._log_line, tag, text)

    def _status_set(self, t, c=SUBTEXT):
        self.after(0, lambda: self._status.config(text=t, fg=c))

    def _browse_apk(self):
        from tkinter import filedialog
        f = filedialog.askopenfilename(
            title="Select APK file",
            filetypes=[("APK files", "*.apk"), ("All files", "*.*")])
        if f:
            self._apk_var.set(f)

    # ── launch ───────────────────────────────────────────────────────────────
    def _launch(self):
        if self._running:
            return
        if not self._sdk:
            self._log_line("err", "❌  Android SDK not found.")
            return

        self._running = True
        self._launch_btn.config(state="disabled", text="⏳ Booting…")
        self._kill_btn.config(state="normal")

        def _run():
            sdk = self._sdk
            log = self._log_cb

            # 1. Create AVD
            log(f"🛠️  Setting up AVD '{AVD_NAME}'…")
            ok, msg = create_avd(sdk, AVD_NAME)
            log(("✅  " if ok else "❌  ") + msg)
            if not ok:
                self._status_set("Failed to create AVD", ERROR)
                self.after(0, self._reset_launch_btn)
                return

            # 2. Start emulator
            emulator = sdk_tool(sdk, "emulator", "emulator.exe")
            log(f"🚀  Starting emulator…")
            log(f"    {emulator} -avd {AVD_NAME}")
            try:
                self._emu_proc = subprocess.Popen(
                    [emulator, "-avd", AVD_NAME,
                     "-no-boot-anim",
                     "-gpu", "auto",
                     "-memory", "2048",
                     "-no-snapshot-load"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception as e:
                log(f"❌  Failed to start emulator: {e}")
                self._status_set("Emulator failed to start", ERROR)
                self.after(0, self._reset_launch_btn)
                return

            log("📱  Emulator window launching… (takes 30–90 seconds first time)")
            self._status_set("Emulator booting…", WARNING)

            # 3. Wait for boot
            booted = wait_for_boot(sdk, log)
            if booted:
                log("✅  Device booted!")
                self._status_set("Emulator ready ✅", SUCCESS)
                self.after(0, self._on_booted)
                # Auto-open demo URL
                time.sleep(2)
                url = self._url_var.get().strip() or DEMO_URL
                log(f"🌐  Opening: {url}")
                open_url_fullscreen(sdk, url)
                log("✅  URL opened in emulator!")
            else:
                log("⚠️   Boot timed out — emulator may still be loading.")
                log("    Click '🌐 Open URL' manually once the phone screen appears.")
                self._status_set("Boot timeout — open URL manually", WARNING)
                self.after(0, self._on_booted)   # still enable buttons

        threading.Thread(target=_run, daemon=True).start()

    def _on_booted(self):
        self._launch_btn.config(state="normal", text="🚀  Launch Virtual Android Phone")
        self._open_url_btn.config(state="normal")
        self._install_btn.config(state="normal")

    def _reset_launch_btn(self):
        self._running = False
        self._launch_btn.config(state="normal", text="🚀  Launch Virtual Android Phone")

    # ── open url ─────────────────────────────────────────────────────────────
    def _open_url(self):
        url = self._url_var.get().strip() or DEMO_URL
        self._log_cb(f"🌐  Opening {url}…")

        def _run():
            open_url_fullscreen(self._sdk, url)
            self._log_cb("✅  URL sent to emulator!")

        threading.Thread(target=_run, daemon=True).start()

    # ── install apk ──────────────────────────────────────────────────────────
    def _install_apk(self):
        apk  = self._apk_var.get().strip()
        pkg  = self._pkg_var.get().strip()
        if not apk or not os.path.isfile(apk):
            self._log_cb("⚠️   Please select a valid APK file first.")
            return
        if not pkg:
            self._log_cb("⚠️   Please enter the package name (e.g. com.myname.youtube).")
            return

        def _run():
            install_and_run_apk(self._sdk, apk, pkg, self._log_cb)

        threading.Thread(target=_run, daemon=True).start()

    # ── stop ─────────────────────────────────────────────────────────────────
    def _stop(self):
        if self._emu_proc:
            self._log_cb("⏹  Stopping emulator…")
            adb(self._sdk, "emu", "kill")
            try:
                self._emu_proc.terminate()
            except Exception:
                pass
            self._emu_proc = None
        self._running = False
        self._kill_btn.config(state="disabled")
        self._open_url_btn.config(state="disabled")
        self._install_btn.config(state="disabled")
        self._launch_btn.config(state="normal", text="🚀  Launch Virtual Android Phone")
        self._status.config(text="Emulator stopped", fg=SUBTEXT)
        self._log_cb("✅  Emulator stopped.")

    def on_close(self):
        self._stop()
        self.destroy()


# ─────────────────────────── ENTRY ────────────────────────────────────────────
if __name__ == "__main__":
    app = EmulatorDemo()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
