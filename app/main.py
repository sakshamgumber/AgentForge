import asyncio
import json

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from moonshine_voice import (
    Transcriber,
    ModelArch,
    get_model_for_language,
)


app = FastAPI(title="Moonshine Medium Streaming ASR")

transcriber = None


@app.on_event("startup")
def load_model():
    global transcriber

    # Resolve/download the English Medium Streaming model.
    model_path, model_arch = get_model_for_language(
        "en",
        ModelArch.MEDIUM_STREAMING,
    )

    print(f"Moonshine model path: {model_path}")
    print(f"Moonshine model arch: {model_arch}")

    transcriber = Transcriber(
        model_path=model_path,
        model_arch=model_arch,
    )

    print("Moonshine Medium Streaming loaded.")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model": "medium-streaming",
    }


@app.websocket("/ws/transcribe")
async def transcribe(websocket: WebSocket):
    await websocket.accept()

    if transcriber is None:
        await websocket.close(code=1011)
        return

    loop = asyncio.get_running_loop()

    async def send_result(result):
        await websocket.send_json(result)

    class Listener:
        def on_line_text_changed(self, event):
            asyncio.run_coroutine_threadsafe(
                send_result({
                    "type": "partial",
                    "text": event.line.text,
                    "line_id": event.line.id,
                }),
                loop,
            )

        def on_line_completed(self, event):
            asyncio.run_coroutine_threadsafe(
                send_result({
                    "type": "final",
                    "text": event.line.text,
                    "line_id": event.line.id,
                }),
                loop,
            )

    listener = Listener()

    stream = transcriber.create_stream()
    stream.add_listener(listener)
    stream.start()

    try:
        while True:
            message = await websocket.receive()

            if message.get("bytes") is not None:
                audio_bytes = message["bytes"]

                pcm16 = np.frombuffer(
                    audio_bytes,
                    dtype=np.int16,
                )

                audio = pcm16.astype(np.float32) / 32768.0

                stream.add_audio(
                    audio.tolist(),
                    16000,
                )

            elif message.get("text") is not None:
                command = json.loads(message["text"])

                if command.get("type") == "stop":
                    break

    except WebSocketDisconnect:
        pass

    finally:
        try:
            stream.stop()
            stream.remove_all_listeners()
        except Exception:
            pass