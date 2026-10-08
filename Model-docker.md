Moonshine Medium Streaming
Dockerized FastAPI service for Moonshine Medium Streaming ASR over WebSocket.
1. Build & Run
docker compose build
docker compose up
Run in background:
docker compose up -d
Check status:
docker compose ps
docker compose logs -f moonshine
Wait for:
Application startup complete.
2. Test HTTP API
Health check:
curl http://localhost:8000/health
Expected:
{"status":"ok","model":"medium-streaming"}
FastAPI docs:
http://localhost:8000/docs
3. Test WebSocket
Do not open ws://localhost:8000/ws/transcribe directly in Chrome.
Use a WebSocket client.
Option A — wscat
npm install -g wscat
wscat -c ws://localhost:8000/ws/transcribe
Expected:
Connected (press CTRL+C to quit)
Option B — Python
Install:
pip install websockets
Test connection:
import asyncio
import websockets

async def main():
    async with websockets.connect("ws://localhost:8000/ws/transcribe"):
        print("WebSocket connected")

asyncio.run(main())
4. Test Actual Transcription
Audio sent to the WebSocket should be:
- Mono
- 16 kHz
- 16-bit PCM (pcm_s16le)
Convert a test file:
ffmpeg -i test.wav -ar 16000 -ac 1 -sample_fmt s16 test_16k.wav
Then use a WebSocket client to send the PCM audio in small chunks.
Expected server responses:
{"type":"partial","text":"hello this is"}
and eventually:
{"type":"final","text":"hello this is a test","line_id":0}
5. Troubleshooting
Container keeps restarting
docker compose logs moonshine
Make sure Transcriber is initialized with the model path:
transcriber = Transcriber(
    model_path=model_path,
    model_arch=model_arch,
)
WebSocket URL shows “webpage unavailable”
That is normal when opening ws:// in a browser address bar. Use wscat or a Python WebSocket client instead.
Model downloads again
Persist the Moonshine cache in docker-compose.yml, for example:
volumes:
  - moonshine-cache:/root/.cache
6. Stop
docker compose down
Remove containers and volumes:
docker compose down -v