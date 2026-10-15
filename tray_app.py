import os
import sys
import threading
import time
import webbrowser
import logging
from PIL import Image
import pyperclip
import pystray
from pystray import MenuItem as item
import uvicorn

import os
import sys

# Ensure sys.stdout and sys.stderr are safe for PyInstaller --noconsole
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tray_app")

from main import app, LOCAL_IP, audio_engine, get_bundle_dir

BUNDLE_DIR = get_bundle_dir()
ICON_PATH = os.path.join(BUNDLE_DIR, "app_icon.png")
if not os.path.exists(ICON_PATH):
    ICON_PATH = "app_icon.png"

class AirStreamTrayApp:
    def __init__(self):
        self.server = None
        self.server_thread = None
        self.icon = None
        self.is_running = True

    def start_server(self):
        config = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=8000,
            log_level="warning"
        )
        self.server = uvicorn.Server(config)
        self.server_thread = threading.Thread(target=self.server.run, daemon=True)
        self.server_thread.start()
        logger.info(f"AirStream Pro server thread running on port 8000.")

    def open_dashboard(self, icon=None, item=None):
        webbrowser.open("http://localhost:8000")

    def copy_mobile_link(self, icon=None, item=None):
        url = f"http://{LOCAL_IP}:8000"
        pyperclip.copy(url)
        if self.icon:
            self.icon.notify(
                f"Link copied to clipboard:\n{url}\nOpen in Safari/Chrome on phone!",
                "AirStream Pro"
            )

    def restart_engine(self, icon=None, item=None):
        audio_engine.restart()
        if self.icon:
            self.icon.notify(
                f"Audio engine restarted on: {audio_engine.device_name}",
                "AirStream Pro"
            )

    def exit_app(self, icon=None, item=None):
        logger.info("Exiting AirStream Pro...")
        self.is_running = False
        if self.server:
            self.server.should_exit = True
        audio_engine.shutdown()
        if self.icon:
            self.icon.stop()
        sys.exit(0)

    def get_status_text(self, item=None):
        dev = audio_engine.device_name[:24] if audio_engine.device_name else "Default"
        return f"Device: {dev}"

    def run(self):
        # 1. Start Server
        self.start_server()

        # 2. Load Icon
        try:
            image = Image.open(ICON_PATH)
        except Exception:
            # Fallback icon if file missing
            image = Image.new("RGBA", (64, 64), "#00f2fe")

        # 3. Create Tray Menu
        menu = pystray.Menu(
            item("🎧 AirStream Pro (Live)", lambda icon, item: None, enabled=False),
            item(f"📱 Phone Link: http://{LOCAL_IP}:8000", lambda icon, item: None, enabled=False),
            pystray.Menu.SEPARATOR,
            item("🌐 Open Dashboard & QR Code", self.open_dashboard, default=True),
            item("📋 Copy Phone Link", self.copy_mobile_link),
            pystray.Menu.SEPARATOR,
            item(self.get_status_text, lambda icon, item: None, enabled=False),
            item("🔄 Restart Audio Engine", self.restart_engine),
            pystray.Menu.SEPARATOR,
            item("❌ Exit AirStream Pro", self.exit_app)
        )

        self.icon = pystray.Icon(
            "AirStreamPro",
            image,
            "AirStream Pro - Streaming PC Audio to AirPods",
            menu
        )

        # Notify on startup in background
        def notify_startup():
            time.sleep(1.5)
            if self.icon and self.is_running:
                try:
                    self.icon.notify(
                        f"AirStream Pro is running!\nOpen on phone: http://{LOCAL_IP}:8000\nDouble-click icon for QR code.",
                        "AirStream Pro"
                    )
                except Exception:
                    pass

        threading.Thread(target=notify_startup, daemon=True).start()

        # Run tray loop (blocking call on main thread as required by Windows GUI)
        logger.info("AirStream Pro system tray loop starting...")
        self.icon.run()

if __name__ == "__main__":
    app_instance = AirStreamTrayApp()
    app_instance.run()
