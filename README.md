# Shortcut Creator

A Python desktop app to create **fullscreen website shortcuts** for iOS & Android.

## 🚀 Quick Start

Double-click **`Run App.bat`** — or run:

```
python shortcut_creator.py
```

> Requires **Python 3.8+** (tkinter is included by default). No extra packages needed.

---

## ✨ What it does

1. You enter a **URL** + **App Name** (e.g. `youtube.com` / `YouTube`)
2. The app generates a folder with:
   - `index.html` — the shortcut page with fullscreen support
   - `manifest.json` — PWA manifest (enables "Install as App" on Android)
   - `README.md` — instructions for the user

---

## 📱 How to install the shortcut on iOS

1. Transfer/host the shortcut folder (or open `index.html` in Safari via AirDrop / local server)
2. In **Safari**, tap the **Share** icon (📤)
3. Tap **"Add to Home Screen"**
4. Tap **Add** — icon appears on your home screen, opens fullscreen!

## 🤖 How to install on Android

1. Open `index.html` in **Chrome**
2. Tap **⋮ → Add to Home Screen** (or the banner that says "Install App")
3. Tap **Add** — done!

---

## 📂 File Structure

```
shortcut_creator.py   ← Main app
Run App.bat           ← Double-click launcher (Windows)
README.md             ← This file

[Output folder] /
  ├── youtube/
  │   ├── index.html
  │   ├── manifest.json
  │   └── README.md
  └── facebook/
      ├── index.html
      ├── manifest.json
      └── README.md
```

---

## ⚙️ Settings

| Setting | Description |
|---------|-------------|
| **Output folder** | Where shortcut folders are saved (default: Desktop\Shortcuts) |
| **Theme color** | Browser chrome / status bar tint color |
| **BG color** | Splash screen background color |
| **Icon URL** | Optional PNG icon URL for the home screen icon |
