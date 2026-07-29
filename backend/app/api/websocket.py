from __future__ import annotations
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from ..simulation.service import SimulationService

async def stream_city(websocket: WebSocket, service: SimulationService, *, interval_seconds: float = 0.5) -> None:
    await websocket.accept()
    initial = True
    try:
        while True:
            payload = await service.snapshot() if initial else await service.delta()
            initial = False
            try: await websocket.send_json(payload)
            except (WebSocketDisconnect, RuntimeError, OSError): return
            population_interval = min(2.0, max(interval_seconds, len(service.world.citizens) / 2500.0))
            await asyncio.sleep(population_interval)
    except WebSocketDisconnect: return
