"""
Shortcut Creator — Create fullscreen website shortcuts for iOS & Android
Generates PWA-compatible HTML + manifest.json so users can "Add to Home Screen"
and open the site as a fullscreen app on any mobile device.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import re
import threading
import webbrowser
from urllib.parse import urlparse

# ─────────────────────────── THEME ───────────────────────────
BG        = "#0f0f1a"
CARD      = "#1a1a2e"
CARD2     = "#16213e"
ACCENT    = "#7c3aed"
ACCENT2   = "#a855f7"
SUCCESS   = "#10b981"
ERROR     = "#ef4444"
TEXT      = "#e2e8f0"
SUBTEXT   = "#94a3b8"
BORDER    = "#2d2d4e"
ENTRY_BG  = "#0f0f1a"
FONT_HEAD = ("Segoe UI", 22, "bold")
FONT_SUB  = ("Segoe UI", 10)
FONT_BODY = ("Segoe UI", 11)
FONT_BOLD = ("Segoe UI", 11, "bold")
FONT_SM   = ("Segoe UI", 9)


# ─────────────────────────── HELPER ───────────────────────────
def normalize_url(url: str) -> str:
    url = url.strip()
    if url and not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    return url


def get_domain(url: str) -> str:
    try:
        return urlparse(url).netloc or url
    except Exception:
        return url


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "-", name.lower().strip()).strip("-") or "shortcut"


def generate_files(name: str, url: str, short_name: str, color: str,
                   bg_color: str, icon_url: str, out_dir: str) -> tuple[str, str]:
    """
    Returns (html_path, manifest_path).
    Creates the shortcut HTML and manifest.json inside out_dir/<slug>/
    """
    slug = slugify(name)
    folder = os.path.join(out_dir, slug)
    os.makedirs(folder, exist_ok=True)

    # ── manifest.json ──────────────────────────────────────────
    icons = []
    if icon_url:
        icons = [
            {"src": icon_url, "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": icon_url, "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ]

    manifest = {
        "name": name,
        "short_name": short_name or name[:12],
        "start_url": url,
        "display": "fullscreen",
        "orientation": "any",
        "theme_color": color,
        "background_color": bg_color,
        "icons": icons,
        "scope": "/"
    }
    manifest_path = os.path.join(folder, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # ── shortcut HTML ──────────────────────────────────────────
    icon_tag = f'<link rel="apple-touch-icon" href="{icon_url}">' if icon_url else ""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <title>{name}</title>

  <!-- PWA / Fullscreen -->
  <link rel="manifest" href="manifest.json">
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="{short_name or name[:12]}">
  {icon_tag}

  <!-- Theme -->
  <meta name="theme-color" content="{color}">
  <meta name="msapplication-navbutton-color" content="{color}">

  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    html, body {{ width: 100%; height: 100%; overflow: hidden; background: {bg_color}; }}
    iframe {{
      position: fixed;
      top: 0; left: 0;
      width: 100vw; height: 100vh;
      border: none;
    }}
    .fallback {{
      display: none;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100vh;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      color: #fff;
      text-align: center;
      padding: 2rem;
      background: linear-gradient(135deg, {bg_color} 0%, {color} 100%);
    }}
    .fallback h1 {{ font-size: 1.8rem; margin-bottom: 1rem; }}
    .fallback p  {{ opacity: .8; margin-bottom: 2rem; font-size: 1rem; }}
    .open-btn {{
      display: inline-block;
      padding: .9rem 2.5rem;
      background: {color};
      color: #fff;
      border-radius: 50px;
      font-size: 1rem;
      font-weight: 700;
      text-decoration: none;
      box-shadow: 0 4px 20px rgba(0,0,0,.3);
    }}
  </style>
</head>
<body>
  <iframe
    id="app-frame"
    src="{url}"
    allow="fullscreen; accelerometer; autoplay; camera; geolocation; gyroscope; microphone; payment"
    allowfullscreen
    sandbox="allow-forms allow-modals allow-pointer-lock allow-popups allow-same-origin allow-scripts allow-top-navigation"
  ></iframe>

  <noscript>
    <div class="fallback" style="display:flex">
      <h1>{name}</h1>
      <p>Enable JavaScript or tap the button below.</p>
      <a class="open-btn" href="{url}" target="_blank">Open {name}</a>
    </div>
  </noscript>

  <script>
    // Attempt to request real fullscreen (works on Android Chrome)
    const frame = document.getElementById('app-frame');

    function goFullscreen() {{
      const el = document.documentElement;
      const fn = el.requestFullscreen || el.webkitRequestFullscreen || el.mozRequestFullScreen;
      if (fn) fn.call(el).catch(() => {{}});
    }}

    document.addEventListener('click', goFullscreen, {{ once: true }});
    document.addEventListener('touchstart', goFullscreen, {{ once: true }});

    // Handle X-Frame-Options / CSP blocks — show fallback
    frame.addEventListener('error', () => {{
      frame.style.display = 'none';
      document.querySelector('.fallback').style.display = 'flex';
    }});
  </script>
</body>
</html>"""

    html_path = os.path.join(folder, "index.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    # ── README ──────────────────────────────────────────────────
    readme = f"""# {name} — Fullscreen Shortcut

## 📱 How to install on iOS
1. Open **Safari** and navigate to the `index.html` file (or host it online).
2. Tap the **Share** button (box with arrow).
3. Tap **"Add to Home Screen"**.
4. Tap **Add** — done! The app icon appears on your home screen.

## 🤖 How to install on Android
1. Open **Chrome** and navigate to the `index.html` file (or host it online).
2. Tap the **three-dot menu** (⋮).
3. Tap **"Add to Home Screen"** or **"Install App"**.
4. Tap **Add** — done!

## 🌐 Target URL
{url}

## 📂 Files
- `index.html` — Shortcut page (open this in browser)
- `manifest.json` — PWA manifest for fullscreen & home-screen install
"""
    with open(os.path.join(folder, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme)

    return html_path, manifest_path


# ─────────────────────────── UI ───────────────────────────────
class ShortcutCreatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Shortcut Creator")
        self.geometry("780x700")
        self.minsize(680, 600)
        self.configure(bg=BG)
        self.resizable(True, True)

        # State
        self.out_dir = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Desktop", "Shortcuts"))
        self.theme_color = tk.StringVar(value="#7c3aed")
        self.bg_color    = tk.StringVar(value="#0f0f1a")
        self.entries: list[dict] = []  # list of shortcut rows
        self.last_result: list[str] = []

        self._build_ui()
        self._add_row()  # start with one blank row

    # ── Layout ──────────────────────────────────────────────────
    def _build_ui(self):
        # ── Header ────────────────────────────────────────────
        hdr = tk.Frame(self, bg=CARD, padx=30, pady=20)
        hdr.pack(fill="x")

        tk.Label(hdr, text="⚡ Shortcut Creator", font=FONT_HEAD,
                 bg=CARD, fg=ACCENT2).pack(side="left")
        tk.Label(hdr, text="iOS & Android fullscreen shortcuts",
                 font=FONT_SUB, bg=CARD, fg=SUBTEXT).pack(side="left", padx=(12, 0), pady=(8, 0))

        # ── Scrollable shortcut list ───────────────────────────
        list_frame = tk.Frame(self, bg=BG)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(20, 0))

        tk.Label(list_frame, text="Shortcuts to create", font=FONT_BOLD,
                 bg=BG, fg=TEXT).pack(anchor="w", pady=(0, 8))

        # canvas + scrollbar
        canvas = tk.Canvas(list_frame, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.rows_frame = tk.Frame(canvas, bg=BG)
        self.canvas_window = canvas.create_window((0, 0), window=self.rows_frame, anchor="nw")

        def _on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(self.canvas_window, width=canvas.winfo_width())

        self.rows_frame.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(self.canvas_window, width=e.width))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        self.canvas = canvas

        # ── Column headers ────────────────────────────────────
        col_hdr = tk.Frame(self.rows_frame, bg=BG)
        col_hdr.pack(fill="x", padx=4, pady=(0, 4))
        for txt, w in [("App Name", 16), ("Website URL", 26), ("Short Name", 12), ("Icon URL (optional)", 22)]:
            tk.Label(col_hdr, text=txt, font=FONT_SM, bg=BG, fg=SUBTEXT, width=w, anchor="w").pack(side="left", padx=4)

        # ── Add row button ────────────────────────────────────
        btn_row = tk.Frame(self, bg=BG)
        btn_row.pack(fill="x", padx=20, pady=8)
        self._btn(btn_row, "+ Add Shortcut", self._add_row,
                  bg=CARD2, fg=ACCENT2, side="left")

        # ── Settings strip ────────────────────────────────────
        settings = tk.LabelFrame(self, text=" Settings ", font=FONT_SM,
                                 bg=CARD, fg=SUBTEXT, bd=1, relief="groove",
                                 padx=16, pady=12)
        settings.pack(fill="x", padx=20, pady=(0, 8))

        # Output dir
        tk.Label(settings, text="Output folder:", font=FONT_BODY,
                 bg=CARD, fg=TEXT).grid(row=0, column=0, sticky="w", padx=(0, 8))
        tk.Entry(settings, textvariable=self.out_dir, width=38,
                 bg=ENTRY_BG, fg=TEXT, insertbackground=TEXT,
                 relief="flat", font=FONT_BODY, bd=0).grid(row=0, column=1, sticky="ew")
        self._btn(settings, "Browse", lambda: self._browse_dir(),
                  bg=ACCENT, fg="#fff", pady=2).grid(row=0, column=2, padx=(8, 0))

        # Color pickers
        tk.Label(settings, text="Theme color:", font=FONT_BODY,
                 bg=CARD, fg=TEXT).grid(row=1, column=0, sticky="w", pady=(8, 0))
        self._color_entry(settings, self.theme_color).grid(row=1, column=1, sticky="w", pady=(8, 0))

        tk.Label(settings, text="BG color:", font=FONT_BODY,
                 bg=CARD, fg=TEXT).grid(row=2, column=0, sticky="w", pady=(4, 0))
        self._color_entry(settings, self.bg_color).grid(row=2, column=1, sticky="w", pady=(4, 0))

        settings.columnconfigure(1, weight=1)

        # ── Action bar ────────────────────────────────────────
        action = tk.Frame(self, bg=BG, padx=20, pady=12)
        action.pack(fill="x")

        self.status_lbl = tk.Label(action, text="", font=FONT_SM,
                                   bg=BG, fg=SUBTEXT)
        self.status_lbl.pack(side="left")

        self._btn(action, "🗂  Open Output Folder", self._open_folder,
                  bg=CARD2, fg=ACCENT2, side="right", padx=10)
        self._btn(action, "⚡  Create Shortcuts", self._create,
                  bg=ACCENT, fg="#fff", side="right", padx=16, font=FONT_BOLD)

    # ── Helpers ───────────────────────────────────────────────
    def _btn(self, parent, text, cmd, bg=CARD, fg=TEXT,
             side=None, padx=8, pady=5, font=FONT_BODY, **grid_kw):
        b = tk.Button(parent, text=text, command=cmd,
                      bg=bg, fg=fg, activebackground=ACCENT2, activeforeground="#fff",
                      relief="flat", cursor="hand2", font=font,
                      padx=padx, pady=pady, bd=0)
        if side:
            b.pack(side=side, padx=4)
        return b

    def _color_entry(self, parent, var):
        f = tk.Frame(parent, bg=CARD)
        e = tk.Entry(f, textvariable=var, width=10,
                     bg=ENTRY_BG, fg=TEXT, insertbackground=TEXT,
                     relief="flat", font=FONT_BODY)
        e.pack(side="left")

        swatch = tk.Label(f, bg=var.get(), width=3, cursor="hand2")
        swatch.pack(side="left", padx=(4, 0))

        def pick():
            from tkinter.colorchooser import askcolor
            c = askcolor(color=var.get(), title="Pick color")[1]
            if c:
                var.set(c)
                swatch.configure(bg=c)

        swatch.bind("<Button-1>", lambda e: pick())
        var.trace_add("write", lambda *_: swatch.configure(bg=var.get() if var.get().startswith("#") else CARD))
        return f

    def _browse_dir(self):
        d = filedialog.askdirectory(title="Select output folder")
        if d:
            self.out_dir.set(d)

    def _open_folder(self):
        p = self.out_dir.get()
        os.makedirs(p, exist_ok=True)
        os.startfile(p)

    # ── Row management ────────────────────────────────────────
    def _add_row(self):
        idx = len(self.entries)
        row = tk.Frame(self.rows_frame, bg=CARD, bd=0, pady=8, padx=8)
        row.pack(fill="x", padx=4, pady=3)

        vars_ = {k: tk.StringVar() for k in ("name", "url", "short", "icon")}
        placeholders = {
            "name":  "e.g. YouTube",
            "url":   "e.g. youtube.com",
            "short": "e.g. YT",
            "icon":  "https://…/icon.png",
        }

        def _entry(key, width):
            e = tk.Entry(row, textvariable=vars_[key], width=width,
                         bg=ENTRY_BG, fg=TEXT, insertbackground=TEXT,
                         relief="flat", font=FONT_BODY)
            e.insert(0, placeholders[key])
            e.config(fg=SUBTEXT)

            def _focus_in(_):
                if e.get() == placeholders[key]:
                    e.delete(0, "end")
                    e.config(fg=TEXT)

            def _focus_out(_):
                if not e.get():
                    e.insert(0, placeholders[key])
                    e.config(fg=SUBTEXT)

            e.bind("<FocusIn>",  _focus_in)
            e.bind("<FocusOut>", _focus_out)
            e.pack(side="left", padx=4, ipady=5)
            return e

        _entry("name",  16)
        _entry("url",   26)
        _entry("short", 12)
        _entry("icon",  22)

        # Delete button
        def _delete(r=row, v=vars_, i=idx):
            r.destroy()
            self.entries = [e for e in self.entries if e is not v]

        tk.Button(row, text="✕", command=_delete,
                  bg=CARD, fg=ERROR, relief="flat", cursor="hand2",
                  font=FONT_SM, padx=4).pack(side="left", padx=4)

        placeholders_ref = placeholders  # keep reference

        def _get_val(key):
            v = vars_[key].get().strip()
            return "" if v == placeholders_ref[key] else v

        vars_["_get"] = _get_val
        self.entries.append(vars_)

    # ── Create ────────────────────────────────────────────────
    def _create(self):
        valid = []
        for entry in self.entries:
            get = entry["_get"]
            name = get("name")
            url  = normalize_url(get("url"))
            if not name or not url:
                continue
            valid.append({
                "name":  name,
                "url":   url,
                "short": get("short") or name[:12],
                "icon":  get("icon"),
            })

        if not valid:
            messagebox.showwarning("Nothing to create",
                                   "Please fill in at least one shortcut (App Name + URL).")
            return

        out_dir      = self.out_dir.get().strip() or os.path.join(os.path.expanduser("~"), "Desktop", "Shortcuts")
        theme_color  = self.theme_color.get() or "#7c3aed"
        bg_color     = self.bg_color.get()    or "#0f0f1a"

        self.status_lbl.config(text="⏳ Creating shortcuts…", fg=SUBTEXT)
        self.update_idletasks()

        def _run():
            results = []
            errors  = []
            for item in valid:
                try:
                    html_path, _ = generate_files(
                        name      = item["name"],
                        url       = item["url"],
                        short_name= item["short"],
                        color     = theme_color,
                        bg_color  = bg_color,
                        icon_url  = item["icon"],
                        out_dir   = out_dir,
                    )
                    results.append((item["name"], html_path))
                except Exception as exc:
                    errors.append(f"{item['name']}: {exc}")

            self.after(0, lambda: self._done(results, errors, out_dir))

        threading.Thread(target=_run, daemon=True).start()

    def _done(self, results, errors, out_dir):
        if errors:
            messagebox.showerror("Errors", "\n".join(errors))

        if results:
            lines = "\n".join(f"✔ {n}  →  {p}" for n, p in results)
            self.status_lbl.config(
                text=f"✅ Created {len(results)} shortcut(s) in {out_dir}", fg=SUCCESS)
            self.last_result = [p for _, p in results]

            # Show success popup with instructions
            win = tk.Toplevel(self)
            win.title("Shortcuts Created!")
            win.configure(bg=CARD)
            win.geometry("540x420")
            win.resizable(False, False)

            tk.Label(win, text="🎉 Shortcuts Created!", font=FONT_HEAD,
                     bg=CARD, fg=SUCCESS).pack(pady=(24, 4))
            tk.Label(win, text=f"{len(results)} shortcut(s) saved to:\n{out_dir}",
                     font=FONT_BODY, bg=CARD, fg=TEXT, justify="center").pack(pady=4)

            box = tk.Text(win, height=5, bg=ENTRY_BG, fg=TEXT, font=FONT_SM,
                          relief="flat", wrap="word", padx=8, pady=8)
            box.insert("1.0", lines)
            box.config(state="disabled")
            box.pack(fill="x", padx=20, pady=8)

            instr = (
                "📱 How to install on iOS (Safari):\n"
                "  1. Open index.html in Safari\n"
                "  2. Tap Share → Add to Home Screen → Add\n\n"
                "🤖 How to install on Android (Chrome):\n"
                "  1. Open index.html in Chrome\n"
                "  2. Tap ⋮ → Add to Home Screen → Add"
            )
            tk.Label(win, text=instr, font=FONT_SM, bg=CARD, fg=SUBTEXT,
                     justify="left").pack(padx=24, pady=4, anchor="w")

            btn_frame = tk.Frame(win, bg=CARD)
            btn_frame.pack(pady=12)
            tk.Button(btn_frame, text="📂 Open Folder", bg=ACCENT, fg="#fff",
                      relief="flat", cursor="hand2", font=FONT_BODY, padx=12, pady=6,
                      command=lambda: os.startfile(out_dir)).pack(side="left", padx=8)
            tk.Button(btn_frame, text="✅ Done", bg=CARD2, fg=TEXT,
                      relief="flat", cursor="hand2", font=FONT_BODY, padx=12, pady=6,
                      command=win.destroy).pack(side="left", padx=8)
        else:
            self.status_lbl.config(text="⚠ No shortcuts were created.", fg=ERROR)


# ─────────────────────────── ENTRY ────────────────────────────
if __name__ == "__main__":
    app = ShortcutCreatorApp()
    app.mainloop()
