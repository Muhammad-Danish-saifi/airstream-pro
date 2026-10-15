<div align="center">

# 🎧 AirStream Pro
### Real-Time PC Audio to Phone & AirPods (Zero Mobile App Required)

**Stream your PC game, movie, and music audio directly to your phone and AirPods with ultra-low latency (~15ms – 25ms) over local Wi-Fi.**

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![WebRTC](https://img.shields.io/badge/Protocol-WebRTC%20(UDP)-FF6B6B?logo=webrtc&logoColor=white)](https://webrtc.org)
[![Windows](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6?logo=windows&logoColor=white)](https://microsoft.com)
[![iOS & Android](https://img.shields.io/badge/Receiver-Safari%20%7C%20Chrome-000000?logo=apple&logoColor=white)](https://apple.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## 💡 The Problem It Solves

Ever faced one of these frustrating situations?
* **No Bluetooth on PC:** Your desktop motherboard doesn't have Bluetooth, or your cheap USB Bluetooth dongle has terrible 200ms audio lag that desyncs video and audio.
* **Tethered by Wires:** You want to watch a movie or play games from your bed or couch, but your wired headphones can't reach.
* **Expensive & Clunky Alternatives:** Existing tools like *AudioRelay* or *SoundWire* require downloading 30–50MB apps from the App Store, dealing with ads, paying subscriptions, or struggling with iOS configuration.

### 🌟 The AirStream Pro Solution:
> **Zero Mobile Installation:** You do **not** need to install any app on your iPhone or Android phone.  
> Just double-click the Windows app, point your phone camera at the **QR Code** on your PC screen, and Safari/Chrome starts streaming studio-grade 48 kHz stereo audio directly into your **AirPods in under 20 milliseconds**.

---

## ⚡ Comparison

| Feature | 🎧 **AirStream Pro** | AudioRelay | SoundWire | Bluetooth Dongle |
|:---|:---:|:---:|:---:|:---:|
| **Phone App Required?** | ❌ **No (Web-First)** | ✅ Yes (App Store) | ✅ Yes (Play Store) | ❌ No |
| **Real-Time Latency** | ⚡ **~15ms – 25ms (UDP)** | ~30ms – 50ms | ~60ms – 120ms | ~150ms – 250ms |
| **iOS / AirPods Support** | ✅ **Native Safari** | ⚠️ Limited / Paid | ❌ Not on iOS | ✅ Yes |
| **Plays While Screen Locked**| ✅ **Yes (WebRTC Media)**| ⚠️ Needs Pro | ⚠️ Android Only | ✅ Yes |
| **Hardware Required** | ❌ None (Local Wi-Fi) | ❌ None | ❌ None | 💸 $20–$50 Dongle |
| **Price & Ads** | 🆓 **100% Free & No Ads** | Freemium ($) | Freemium ($) | Hardware Cost |

---

## ✨ Features

- 🚀 **WebRTC Ultra-Low Latency (UDP + Opus 48 kHz):** Hardware-clocked PortAudio C callback captures audio every 20ms and streams it over UDP with zero TCP buffer bloat.
- 📱 **Instant QR Code Connection:** The desktop dashboard renders a scannable QR code. Scan with your iPhone/Android camera to open immediately.
- 🔒 **iOS Lock-Screen Audio:** Uses WebRTC `MediaStream` and the HTML5 `MediaSession` API so audio keeps playing in your AirPods even when your phone locks or Safari is backgrounded.
- 💻 **Native Windows System Tray App:** Runs quietly near the Windows clock without cluttering your desktop with console windows. Double-click to open dashboard.
- 🎚️ **Live Audio Visualizer & VU Meter:** Real-time 60 FPS neon frequency spectrum and stereo dB meters.
- 🔊 **200% Volume Boost:** Clean digital pre-amp slider for quiet PC media or gaming audio.
- 🔄 **On-the-Fly Sound Device Selector:** Switch between **VB-Audio Virtual Cable**, **Stereo Mix**, or your microphone directly from your phone.
- ⏱️ **WebSocket Fallback Mode:** Secondary adaptive playback engine with drift-correcting jitter buffer.

---

## 🏗️ Architecture

```text
[ PC Audio Output (VB-Cable / Stereo Mix) ]
                   │
                   ▼
[ PortAudio C Hardware Callback (20ms frames @ 48kHz Stereo) ]  <-- audio_engine.py
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
 [ WebRTC (UDP + Opus) ]   [ WebSocket (TCP) ]                 <-- main.py
   ~15 - 25ms Latency        ~35ms Adaptive Buffer
         │                   │
         └─────────┬─────────┘
                   ▼
 [ Mobile Browser (Safari / Chrome) + AirPods ]                <-- Index.html
   - iOS Lock-Screen & Background Audio
   - Live Frequency Visualizer & VU Meter
   - Scannable QR Code on Desktop
   - Live Latency Display (ms)
```

---

## 🚀 Quick Start Guide

### Option 1: Standalone `.exe` (No Python Needed)
1. Download **`AirStreamPro.exe`** from the [GitHub Releases](https://github.com/Muhammad-Danish-saifi/airstream-pro/releases) tab.
2. Double-click `AirStreamPro.exe`. A headphone icon will appear in your Windows System Tray (near the clock).
3. The dashboard will automatically open in your browser displaying your **QR Code**.

### Option 2: Run From Source (Developers)
```bash
# Clone the repository
git clone https://github.com/Muhammad-Danish-saifi/airstream-pro.git
cd airstream-pro

# Install dependencies
pip install -r requirements.txt

# Run the system tray app
python tray_app.py
```

---

## 🎧 Windows Sound Setup (2 Options)

### Method A: Using VB-Audio Cable (Recommended)
1. Install the free [VB-Audio Virtual Cable](https://vb-audio.com/Cable/).
2. In Windows Sound Settings, set your Default Output Device to **CABLE Input (VB-Audio Virtual Cable)**.
3. In AirStream Pro, select **CABLE Output** as the capture source.

### Method B: Using Windows Stereo Mix (No Virtual Cable Needed)
1. Keep your normal PC speakers as the default Windows output.
2. In AirStream Pro, select **Stereo Mix** as the capture source.

---

## 📱 How to Listen on Your Phone

1. Ensure your phone and PC are connected to the same Wi-Fi network.
2. Put in your **AirPods** or wireless earbuds.
3. Scan the **QR Code** shown on your PC screen (or open `http://<PC-IP>:8000` in Safari/Chrome).
4. Tap **Connect & Listen**. That's it!

---

## 🛠️ Tech Stack

- **Audio Capture:** PyAudio / PortAudio (C Callbacks, 20ms chunks, 48kHz Stereo)
- **WebRTC Engine:** `aiortc` (Opus encoder, RTP/SRTP over UDP)
- **Backend:** FastAPI, Uvicorn, Python 3.13
- **Frontend:** Vanilla HTML5, Web Audio API, Canvas 2D Visualizer, Google Outfit Typography
- **Desktop Wrapper:** PyStray, Pillow, PyInstaller

---

## 🤝 Contributing

Pull requests are welcome! If you'd like to help add:
- Direct Windows WASAPI loopback without needing VB-Cable
- Reverse phone microphone streaming (using phone as PC mic)
- Android / iOS PWA shortcuts

Feel free to fork the repo and submit a PR!

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.
