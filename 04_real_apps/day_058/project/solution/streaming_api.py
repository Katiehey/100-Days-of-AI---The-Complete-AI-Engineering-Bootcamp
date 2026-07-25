"""streaming_api.py — Day 058: streaming chat API with SSE and WebSocket.

Run:  uvicorn streaming_api:app --reload
Docs: http://localhost:8000/docs
"""
import json
import os
from datetime import datetime

import ollama
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

MODEL       = os.environ.get("MODEL", "llama3.2")
APP_VERSION = "1.0.0"


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1)
    system: str = ""


app = FastAPI(title="Streaming Chat API", version=APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": APP_VERSION,
    }


@app.get("/stream/count")
def stream_count(n: int = 5):
    """Demo SSE endpoint — streams n count events (no Ollama)."""
    def generate():
        for i in range(n):
            yield "data: " + str(i) + "\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    """Stream Ollama response tokens as SSE events."""
    messages = []
    if req.system:
        messages.append({"role": "system", "content": req.system})
    messages.append({"role": "user", "content": req.prompt})

    def generate():
        chunks = ollama.chat(model=MODEL, messages=messages, stream=True)
        for chunk in chunks:
            token = chunk["message"]["content"]
            if token:
                payload = json.dumps({"token": token})
                yield "data: " + payload + "\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.websocket("/ws")
async def websocket_chat(ws: WebSocket):
    """WebSocket endpoint — receives prompts, streams response token by token."""
    await ws.accept()
    try:
        while True:
            prompt = await ws.receive_text()
            chunks = ollama.chat(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )
            for chunk in chunks:
                token = chunk["message"]["content"]
                if token:
                    await ws.send_text(token)
            await ws.send_text("[DONE]")
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    PORT = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=PORT)
