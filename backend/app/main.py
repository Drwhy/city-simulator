from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import create_api_router
from .api.websocket import stream_city
from .simulation.service import SimulationService

service = SimulationService(seed=12345)

@asynccontextmanager
async def lifespan(_: FastAPI):
    await service.start()
    yield
    await service.stop()

app = FastAPI(title="City Simulator MVP", version="0.11.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(create_api_router(service))

@app.websocket("/ws/city")
async def websocket_city(websocket: WebSocket) -> None:
    await stream_city(websocket, service)
