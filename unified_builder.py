"""
Unified Builder — Creates, compiles, and runs an Android PWA shortcut app on the
virtual phone with just 1 input URL! 🚀

Imports core project generator logic from `apk_builder.py`.
"""

import tkinter as tk
from tkinter import messagebox
import os, sys, re, urllib.parse, threading, subprocess, time

# Import generation helpers from the existing file
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    import apk_builder
except ImportError:
    messagebox.showerror("Error", "Could not import apk_builder.py! Make sure both files are in the same folder.")
    sys.exit(1)

# ─────────────────────────── THEME & STYLE ────────────────────────────────────
BG          = "#0f0f1a"
CARD        = "#1a1a2e"
CARD2       = "#16213e"
ACCENT      = "#7c3aed"
ACCENT2     = "#a855f7"
SUCCESS     = "#10b981"
ERROR       = "#ef4444"
WARNING     = "#f59e0b"
TEXT        = "#e2e8f0"
SUBTEXT     = "#94a3b8"
ENTRY_BG    = "#111128"

FONT_TITLE  = ("Segoe UI", 16, "bold")
FONT_BODY   = ("Segoe UI", 11)
FONT_CONSOLE= ("Consolas", 9)

# ─────────────────────────── APP CLASS ────────────────────────────────────────

class UnifiedBuilderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🚀 Unified Android Shortcut Creator")
        self.geometry("780x620")
        self.minsize(700, 520)
        self.configure(bg=BG)
        
        self._sdk = apk_builder.find_android_sdk() or r"D:\Android"
        self._jdk = r"D:\Java\jdk-17"
        self._is_running = False
        
        self._build_ui()

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=CARD, padx=24, pady=16)
        hdr.pack(fill="x")
        
        tk.Label(hdr, text="🚀 Unified Shortcut Creator", 
                 font=FONT_TITLE, bg=CARD, fg=ACCENT2).pack(side="left")
        
        sdk_status = f"SDK: {self._sdk}" if os.path.exists(self._sdk) else "⚠ SDK Missing"
        tk.Label(hdr, text=sdk_status, font=("Segoe UI", 8),
                 bg=CARD2 if os.path.exists(self._sdk) else ERROR, 
                 fg=TEXT, padx=8, pady=4).pack(side="right")

        # Form Zone
        form = tk.Frame(self, bg=BG, padx=24, pady=16)
        form.pack(fill="x")

        # 1-Input URL Field
        tk.Label(form, text="Website URL:", font=FONT_BODY, bg=BG, fg=TEXT).pack(anchor="w", pady=(0, 4))
        self._url_var = tk.StringVar()
        self._url_entry = tk.Entry(form, textvariable=self._url_var, bg=ENTRY_BG, fg=TEXT,
                                   insertbackground=TEXT, relief="flat", font=FONT_BODY)
        self._url_entry.pack(fill="x", ipady=8, pady=(0, 12))
        self._url_entry.insert(0, "https://")
        
        # Action Button
        self._btn_run = tk.Button(
            form, text="⚡  Build & Run in Virtual Phone",
            command=self._start_pipeline,
            bg=ACCENT, fg="#fff",
            activebackground=ACCENT2, activeforeground="#fff",
            relief="flat", cursor="hand2",
            font=("Segoe UI", 12, "bold"),
            pady=12
        )
        self._btn_run.pack(fill="x")

        # Divider
        tk.Frame(self, bg=CARD, height=1).pack(fill="x", pady=10)

        # Log Terminal
        log_frame = tk.Frame(self, bg=BG, padx=24, pady=8)
        log_frame.pack(fill="both", expand=True)
        
        tk.Label(log_frame, text="Execution Log", font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=SUBTEXT).pack(anchor="w", pady=(0, 4))
        
        txt_wrap = tk.Frame(log_frame, bg=CARD)
        txt_wrap.pack(fill="both", expand=True)
        
        self._log = tk.Text(txt_wrap, bg="#08080f", fg=TEXT,
                            font=FONT_CONSOLE, wrap="word",
                            relief="flat", padx=12, pady=10,
                            state="disabled")
        sb = tk.Scrollbar(txt_wrap, command=self._log.yview)
        self._log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._log.pack(fill="both", expand=True)
        
        self._log.tag_configure("ok",   foreground=SUCCESS)
        self._log.tag_configure("warn", foreground=WARNING)
        self._log.tag_configure("err",  foreground=ERROR)
        self._log.tag_configure("info",  foreground=ACCENT2)

        # Status Bar
        self._status = tk.Label(self, text="Ready", font=("Segoe UI", 9),
                                bg=CARD, fg=SUBTEXT, anchor="w", padx=16, pady=6)
        self._status.pack(fill="x", side="bottom")

        self._log_line("info", "Welcome! Enter a website URL above to start.")

    def _log_line(self, tag, text):
        self._log.config(state="normal")
        self._log.insert("end", text + "\n", tag)
        self._log.see("end")
        self._log.config(state="disabled")

    def _log_cb(self, text):
        tag = ""
        if "✅" in text or "SUCCESS" in text or "successful" in text:
            tag = "ok"
        elif "⚠️" in text or "⏳" in text or "Warning" in text:
            tag = "warn"
        elif "❌" in text or "FAILED" in text or "error" in text:
            tag = "err"
        elif "🚀" in text or "⚙️" in text:
            tag = "info"
        self.after(0, self._log_line, tag, text)

    def _status_set(self, text, fg=SUBTEXT):
        self.after(0, lambda: self._status.config(text=text, fg=fg))

    def _parse_url(self, raw_url: str) -> tuple[str, str, str]:
        """Guesses App Name, Clean URL, and Package Name from URL."""
        if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
            raw_url = "https://" + raw_url
            
        parsed = urllib.parse.urlparse(raw_url)
        netloc = parsed.netloc or parsed.path
        parts = netloc.split(".")
        
        # Guess App Name (e.g. facebook.com -> Facebook)
        domain = parts[-2] if len(parts) >= 2 else parts[0]
        app_name = domain.capitalize()
        
        # Package Name
        package = f"com.khangsocute.{domain.lower()}"
        
        return app_name, raw_url, package

    def _start_pipeline(self):
        if self._is_running:
            return
        
        raw_url = self._url_var.get().strip()
        if not raw_url or raw_url in ("https://", "http://"):
            messagebox.showwarning("Warning", "Please enter a valid website URL.")
            return
            
        self._is_running = True
        self._btn_run.config(state="disabled", text="⏳ Pipeline Running...")
        self._log.config(state="normal")
        self._log.delete("1.0", "end")
        self._log.config(state="disabled")
        
        threading.Thread(target=self._run_pipeline, args=(raw_url,), daemon=True).start()

    def _run_pipeline(self, raw_url: str):
        log = self._log_cb
        
        # 1. Parse URL & settings
        app_name, url, package = self._parse_url(raw_url)
        log(f"🚀 Parsing URL: {raw_url}")
        log(f"   Name: {app_name}")
        log(f"   Package: {package}")
        
        # Colors & folders
        theme_color = "#7c3aed"
        bg_color    = "#0f0f1a"
        out_dir     = os.path.join(os.path.expanduser("~"), "Desktop", "APK Projects")
        
        # 2. Generate Project
        self._status_set("Generating Android project...", WARNING)
        try:
            proj_path = apk_builder.generate_project(
                app_name=app_name, url=url, package=package,
                theme_color=theme_color, bg_color=bg_color,
                out_dir=out_dir, log=log
            )
        except Exception as e:
            log(f"❌ Failed to generate project: {e}")
            self._status_set("Generation Failed", ERROR)
            self.after(0, self._reset_btn)
            return

        # 3. Build APK
        self._status_set("Compiling APK...", WARNING)
        log("⚙️   Starting Gradle build...")
        
        env = os.environ.copy()
        env["JAVA_HOME"] = self._jdk
        env["ANDROID_HOME"] = self._sdk
        
        cmd = [os.path.join(proj_path, "gradlew.bat"), "assembleDebug"]
        try:
            proc = subprocess.Popen(
                cmd, cwd=proj_path, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in proc.stdout:
                line_str = line.strip()
                if line_str:
                    log(line_str)
            proc.wait()
            
            if proc.returncode != 0:
                log("❌ Gradle build failed.")
                self._status_set("Build Failed", ERROR)
                self.after(0, self._reset_btn)
                return
        except Exception as e:
            log(f"❌ Error during compilation: {e}")
            self._status_set("Build Failed", ERROR)
            self.after(0, self._reset_btn)
            return

        apk_path = os.path.join(proj_path, "app", "build", "outputs", "apk", "debug", "app-debug.apk")
        log(f"✅ APK Compiled successfully: {apk_path}")

        # 4. Check/Start Emulator
        self._status_set("Starting virtual phone...", WARNING)
        adb = os.path.join(self._sdk, "platform-tools", "adb.exe")
        
        # Check if already running
        r = subprocess.run([adb, "devices"], capture_output=True, text=True)
        if "emulator-" not in r.stdout:
            log("⏳ Virtual phone not detected. Booting virtual phone...")
            emu_path = os.path.join(self._sdk, "emulator", "emulator.exe")
            try:
                subprocess.Popen(
                    [emu_path, "-avd", "ShortcutDemo", "-gpu", "auto", "-memory", "2048", "-no-snapshot-load"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            except Exception as e:
                log(f"❌ Failed to start emulator: {e}")
                self._status_set("Emulator failed to launch", ERROR)
                self.after(0, self._reset_btn)
                return
        else:
            log("✅ Virtual phone is already running.")

        # 5. Wait for Boot
        log("⏳ Waiting for device to finish loading...")
        booted = False
        for _ in range(60):
            try:
                res = subprocess.run([adb, "shell", "getprop", "sys.boot_completed"], 
                                     capture_output=True, text=True, timeout=5)
                if res.stdout.strip() == "1":
                    booted = True
                    break
            except Exception:
                pass
            time.sleep(3)

        if not booted:
            log("⚠️   Boot timeout. Attempting to install anyway...")

        # 6. Install & Run
        self._status_set("Installing shortcut app...", WARNING)
        log("📦  Installing APK...")
        install_res = subprocess.run([adb, "install", "-r", apk_path], capture_output=True, text=True)
        log(install_res.stdout + install_res.stderr)
        
        log("▶️   Launching app on virtual phone...")
        subprocess.run([adb, "shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"],
                       capture_output=True, text=True)
        
        log(f"✅ SUCCESS! Your {app_name} shortcut is now live on the virtual phone!")
        self._status_set("Successfully Installed & Opened! 🎉", SUCCESS)
        self.after(0, self._reset_btn)

    def _reset_btn(self):
        self._is_running = False
        self._btn_run.config(state="normal", text="⚡  Build & Run in Virtual Phone")


if __name__ == "__main__":
    app = UnifiedBuilderApp()
    app.mainloop()
