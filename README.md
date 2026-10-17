<div align="center">

# 🎧 AirStream Pro
### Real-Time PC Audio to Phone & AirPods (Zero Mobile App Required)

**Stream your PC game, movie, and music audio directly to your phone and AirPods with authentic ultra-low latency (10ms – 40ms) over local Wi-Fi.**

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![WebRTC](https://img.shields.io/badge/Protocol-WebRTC%20(UDP)-FF6B6B?logo=webrtc&logoColor=white)](https://webrtc.org)
[![Windows](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6?logo=windows&logoColor=white)](https://microsoft.com)
[![iOS & Android](https://img.shields.io/badge/Receiver-Safari%20%7C%20Chrome-000000?logo=apple&logoColor=white)](https://apple.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Latest Release](https://img.shields.io/badge/Release-v1.1.0-brightgreen.svg)](https://github.com/Muhammad-Danish-saifi/airstream-pro/releases/tag/v1.1.0)

</div>

---

## ⚡ Latency Benchmark: Previous (v1.0.0) vs. Updated (v1.1.0)

In earlier builds (v1.0.0), testing audio-video sync on mobile devices exhibited ~100ms on WebSocket and >200ms on WebRTC due to default mobile browser jitter buffers and double audio pipelines. In **v1.1.0**, the entire pipeline has been overhauled to deliver authentic **10ms – 40ms real-time sync** across both protocols:

| Stream Protocol | Previous Latency (v1.0.0) | **Updated Latency (v1.1.0)** | Live Sync Status | Optimization Mechanism |
|:---|:---:|:---:|:---:|:---|
| ⚡ **WebRTC (UDP + Opus)** | ~200ms+ (Browser NetEQ Buffer) | **10ms – 25ms** | 🎮 Perfect for Gaming / Movies | `playoutDelayHint=0` + 10ms hardware chunks |
| ⏱️ **WebSocket (TCP PCM)** | ~100ms (Queue Accumulation) | **20ms – 40ms** | 🎬 Perfect Audio/Video Sync | 12ms target buffer + 35ms drift snap-back |

### 🔬 How Was The 10ms – 40ms Real-Time Latency Achieved?
1. **10ms Hardware PCM Capture Chunks:** Reduced hardware callback buffer from 20ms down to **10ms (480 samples @ 48kHz)**. Audio is encoded and dispatched twice as fast.
2. **Mobile Browser NetEQ Jitter Buffer Zeroed:** Mobile Safari & Chrome default to a conservative 150ms–200ms jitter buffer. AirStream Pro v1.1.0 programmatically injects `receiver.playoutDelayHint = 0` and `receiver.jitterBufferTarget = 0`, forcing the browser engine to present audio immediately.
3. **Double Audio Playout Eliminated:** Fixed an audio routing issue where streams played through both the HTML5 media element and Web Audio simultaneously. The stream now routes cleanly to low-latency output while the frequency visualizer runs on an isolated non-buffering analyser.
4. **Adaptive WebSocket Drift Correction:** The Web Audio context requests `latencyHint: 0` (hardware minimum ~3ms buffer) and maintains an ultra-tight 12ms playback target with immediate snap-back if jitter exceeds 35ms.
5. **Zero-Cable Native WASAPI Loopback:** Captures digital PC audio directly from the Windows audio mixer endpoint before it reaches the DAC, eliminating sound card DSP delay.

---

## 💡 The Problem It Solves

Ever faced one of these frustrating situations?
* **No Bluetooth on PC:** Your desktop motherboard doesn't have Bluetooth, or your cheap USB Bluetooth dongle has terrible 200ms audio lag that desyncs video and audio.
* **Tethered by Wires:** You want to watch a movie or play games from your bed or couch, but your wired headphones can't reach.
* **Expensive & Clunky Alternatives:** Existing tools like *AudioRelay* or *SoundWire* require downloading 30–50MB apps from the App Store, dealing with ads, paying subscriptions, or struggling with iOS configuration.

### 🌟 The AirStream Pro Solution:
> **Zero Mobile Installation:** You do **not** need to install any app on your iPhone or Android phone.  
> Just double-click the Windows app, point your phone camera at the **QR Code** on your PC screen, and Safari/Chrome starts streaming studio-grade 48 kHz stereo audio directly into your **AirPods in 10ms – 40ms**.

---

## ⚡ Comparison

| Feature | 🎧 **AirStream Pro (v1.1.0)** | AudioRelay | SoundWire | Bluetooth Dongle |
|:---|:---:|:---:|:---:|:---:|
| **Phone App Required?** | ❌ **No (Web-First)** | ✅ Yes (App Store) | ✅ Yes (Play Store) | ❌ No |
| **Real-Time Latency** | ⚡ **10ms – 40ms (UDP & TCP)** | ~30ms – 50ms | ~60ms – 120ms | ~150ms – 250ms |
| **iOS / AirPods Support** | ✅ **Native Safari** | ⚠️ Limited / Paid | ❌ Not on iOS | ✅ Yes |
| **Plays While Screen Locked**| ✅ **Yes (WebRTC Media)**| ⚠️ Needs Pro | ⚠️ Android Only | ✅ Yes |
| **Hardware Required** | ❌ None (Local Wi-Fi) | ❌ None | ❌ None | 💸 $20–$50 Dongle |
| **Price & Ads** | 🆓 **100% Free & No Ads** | Freemium ($) | Freemium ($) | Hardware Cost |

---

## ✨ Features

- 🚀 **WebRTC Ultra-Low Latency (UDP + Opus 48 kHz):** Hardware-clocked PortAudio C callback captures audio every 10ms and streams it over UDP with zero TCP buffer bloat.
- 📱 **Instant QR Code Connection:** The desktop dashboard renders a scannable QR code. Scan with your iPhone/Android camera to open immediately.
- 🔒 **iOS Lock-Screen Audio:** Uses WebRTC `MediaStream` and the HTML5 `MediaSession` API so audio keeps playing in your AirPods even when your phone locks or Safari is backgrounded.
- 💻 **Native Windows System Tray App:** Runs quietly near the Windows clock without cluttering your desktop with console windows. Double-click to open dashboard.
- 🎚️ **Live Audio Visualizer & VU Meter:** Real-time 60 FPS neon frequency spectrum and stereo dB meters.
- 🔊 **200% Volume Boost:** Clean digital pre-amp slider for quiet PC media or gaming audio.
- 🔄 **On-the-Fly Sound Device Selector:** Switch between **PC Audio (What You Hear)**, **VB-Audio Virtual Cable**, **Stereo Mix**, or your microphone directly from your phone.
- ⏱️ **WebSocket Fallback Mode:** Secondary adaptive playback engine with 12ms target buffer and drift correction.

---

## 🏗️ Architecture

```text
[ PC Audio Output (WASAPI Loopback / Stereo Mix / VB-Cable) ]
                           │
                           ▼
[ PortAudio C Hardware Callback (10ms frames @ 48kHz Stereo) ]  <-- audio_engine.py
                           │
                 ┌─────────┴─────────┐
                 ▼                   ▼
         [ WebRTC (UDP + Opus) ]   [ WebSocket (TCP) ]                 <-- main.py
           10ms - 25ms Latency       20ms - 40ms Adaptive Buffer
                 │                   │
                 └─────────┬─────────┘
                           ▼
         [ Mobile Browser (Safari / Chrome) + AirPods ]                <-- Index.html
           - Zero Jitter Buffer (playoutDelayHint = 0)
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

## 🎧 Windows Sound Setup

### Default Method: Zero Configuration (Recommended)
1. In AirStream Pro, **PC Audio (What You Hear)** is selected by default!
2. You do not need to install any extra software or change your Windows default sound devices.
3. Just tap **Connect & Listen** on your phone!

### Alternative Methods:
* **VB-Audio Virtual Cable:** If you prefer routing audio through [VB-Cable](https://vb-audio.com/Cable/), select `CABLE Output` in the device dropdown.
* **Stereo Mix:** You can also select Realtek `Stereo Mix` if enabled on your motherboard.

---

## 📱 How to Listen on Your Phone

1. Ensure your phone and PC are connected to the same Wi-Fi network.
2. Put in your **AirPods** or wireless earbuds (or listen directly via phone speaker).
3. Scan the **QR Code** shown on your PC screen (or open `http://<PC-IP>:8000` in Safari/Chrome).
4. Tap **Connect & Listen**. Enjoy real-time synced audio!

---

## 🛠️ Tech Stack

- **Audio Capture:** PyAudio / PyAudioWPatch (C Callbacks, 10ms chunks, 48kHz Stereo, WASAPI Loopback)
- **WebRTC Engine:** `aiortc` (Opus encoder, RTP/SRTP over UDP)
- **Backend:** FastAPI, Uvicorn, Python 3.13
- **Frontend:** Vanilla HTML5, Web Audio API (`latencyHint: 0`), Canvas 2D Visualizer, Google Outfit Typography
- **Desktop Wrapper:** PyStray, Pillow, PyInstaller

---

## 🤝 Contributing

Pull requests are welcome! If you'd like to help add:
- Reverse phone microphone streaming (using phone as PC mic)
- Android / iOS PWA shortcuts

Feel free to fork the repo and submit a PR!

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.
