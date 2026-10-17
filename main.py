import asyncio
import logging
import socket
import struct
import re
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from aiortc import RTCPeerConnection, RTCSessionDescription
from audio_engine import AudioEngine

import os
import sys

# Ensure sys.stdout and sys.stderr are safe for PyInstaller --noconsole
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("server")

# Initialize Audio Engine with 10ms chunk size (480 samples @ 48kHz)
audio_engine = AudioEngine(sample_rate=48000, channels=2, chunk_size=480)

# Set of active WebRTC peer connections
pcs = set()

def get_local_ip() -> str:
    """Retrieve local network IPv4 address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

LOCAL_IP = get_local_ip()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Set event loop reference on audio engine
    loop = asyncio.get_running_loop()
    audio_engine.set_loop(loop)

    # Start audio capture
    res = audio_engine.start()
    started = res[0] if isinstance(res, tuple) else bool(res)
    msg = res[1] if isinstance(res, tuple) and len(res) > 1 else str(res)
    if started:
        logger.info(f"Audio engine started: {msg}")
    else:
        logger.warning(f"Audio engine warning: {msg}")

    print("\n" + "=" * 60)
    print(">> REAL-TIME AUDIO STREAMER READY!")
    print(f">> Desktop URL:   http://localhost:8000")
    print(f">> Phone/AirPods: http://{LOCAL_IP}:8000")
    print(">> Protocol:      WebRTC (Ultra-Low Latency) & WebSocket")
    print("=" * 60 + "\n")

    yield

    # Shutdown
    logger.info("Shutting down server and WebRTC connections...")
    for pc in list(pcs):
        try:
            await pc.close()
        except Exception:
            pass
    pcs.clear()
    audio_engine.shutdown()

app = FastAPI(title="Real-Time PC Audio Streamer", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DeviceSelectRequest(BaseModel):
    device_index: int
    channels: Optional[int] = 2
    sample_rate: Optional[int] = 48000

class WebRTCOfferRequest(BaseModel):
    sdp: str
    type: str

@app.get("/api/info")
def get_info():
    return {
        "localIp": LOCAL_IP,
        "port": 8000,
        "url": f"http://{LOCAL_IP}:8000",
        "audio": audio_engine.get_status()
    }

@app.get("/api/devices")
def get_devices():
    return {
        "devices": audio_engine.get_input_devices(),
        "selectedDeviceIndex": audio_engine.device_index,
        "selectedDeviceName": audio_engine.device_name
    }

@app.post("/api/device/select")
def select_device(req: DeviceSelectRequest):
    ok, msg = audio_engine.change_device(
        device_index=req.device_index,
        channels=req.channels,
        sample_rate=req.sample_rate
    )
    if not ok:
        raise HTTPException(status_code=400, detail=f"Failed to change device: {msg}")
    return {
        "success": True,
        "message": msg,
        "status": audio_engine.get_status()
    }

@app.get("/api/status")
def get_status():
    return audio_engine.get_status()

# ----------------- WebRTC Low-Latency Endpoint -----------------
@app.post("/api/webrtc/offer")
async def webrtc_offer(req: WebRTCOfferRequest):
    """
    Handle WebRTC SDP offer from browser.
    Creates peer connection, attaches PC audio track, returns SDP answer.
    """
    offer = RTCSessionDescription(sdp=req.sdp, type=req.type)
    pc = RTCPeerConnection()
    pcs.add(pc)

    track = audio_engine.create_webrtc_track()
    pc.addTrack(track)

    @pc.on("iceconnectionstatechange")
    async def on_ice():
        logger.debug(f"WebRTC ICE state: {pc.iceConnectionState}")
        if pc.iceConnectionState in ["failed", "closed", "disconnected"]:
            audio_engine.remove_webrtc_track(track)
            await pc.close()
            pcs.discard(pc)

    @pc.on("connectionstatechange")
    async def on_conn():
        logger.debug(f"WebRTC connection state: {pc.connectionState}")
        if pc.connectionState in ["failed", "closed"]:
            audio_engine.remove_webrtc_track(track)
            await pc.close()
            pcs.discard(pc)

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    # Inject ultra-low latency Opus SDP fmtp parameters (10ms frames, constant bitrate)
    raw_sdp = pc.localDescription.sdp
    optimized_sdp = re.sub(
        r"(a=rtpmap:(\d+)\s+opus/48000/2)",
        r"\1\r\na=fmtp:\2 minptime=10;ptime=10;maxptime=20;stereo=1;sprop-stereo=1;cbr=1",
        raw_sdp
    )

    return {
        "sdp": optimized_sdp,
        "type": pc.localDescription.type
    }

# ----------------- WebSocket Real-Time Endpoint -----------------
@app.websocket("/ws/audio")
async def websocket_audio(websocket: WebSocket):
    await websocket.accept()
    queue = audio_engine.register_websocket_queue()
    logger.info("WebSocket audio client connected.")

    # Send audio configuration header
    await websocket.send_json({
        "type": "config",
        "sampleRate": audio_engine.sample_rate,
        "channels": audio_engine.channels,
        "chunkSize": audio_engine.chunk_size
    })

    async def pcm_sender():
        try:
            while True:
                data = await queue.get()
                await websocket.send_bytes(data)
        except Exception:
            pass

    async def ping_receiver():
        try:
            while True:
                msg = await websocket.receive_json()
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "t": msg.get("t")})
        except Exception:
            pass

    sender_task = asyncio.create_task(pcm_sender())
    receiver_task = asyncio.create_task(ping_receiver())

    try:
        done, pending = await asyncio.wait(
            [sender_task, receiver_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending:
            task.cancel()
    finally:
        audio_engine.unregister_websocket_queue(queue)
        logger.info("WebSocket audio client disconnected.")

# ----------------- Legacy HTTP WAV Streaming -----------------
def make_wav_header(sample_rate: int, bits_per_sample: int, channels: int) -> bytes:
    byte_rate = sample_rate * channels * (bits_per_sample // 8)
    block_align = channels * (bits_per_sample // 8)
    header = struct.pack('<4sI4s', b'RIFF', 0, b'WAVE')
    header += struct.pack('<4sIHHIIHH',
                          b'fmt ', 16, 1, channels, sample_rate,
                          byte_rate, block_align, bits_per_sample)
    header += struct.pack('<4sI', b'data', 0)
    return header

@app.get("/audio-stream")
async def audio_stream():
    queue = audio_engine.register_http_queue()

    async def generator():
        # Yield WAV header
        yield make_wav_header(audio_engine.sample_rate, 16, audio_engine.channels)
        try:
            while True:
                chunk = await queue.get()
                yield chunk
        except (asyncio.CancelledError, GeneratorExit):
            pass
        finally:
            audio_engine.unregister_http_queue(queue)

    return StreamingResponse(
        generator(),
        media_type="audio/wav",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

import os
import sys

def get_bundle_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

BUNDLE_DIR = get_bundle_dir()

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    path = os.path.join(BUNDLE_DIR, "Index.html")
    if not os.path.exists(path):
        path = "Index.html"
    with open(path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, log_level="info")
