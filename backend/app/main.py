from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .simulation.service import SimulationService

service = SimulationService(seed=12345, citizen_count=100)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await service.start()
    yield
    await service.stop()


app = FastAPI(
    title="City Simulator MVP",
    version="0.8.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SpeedRequest(BaseModel):
    speed: int


class StepRequest(BaseModel):
    minutes: int = Field(default=1, ge=1, le=1440)


class ResetRequest(BaseModel):
    seed: int | None = None


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/city")
async def city_snapshot() -> dict:
    return await service.snapshot()


@app.get("/api/healthcare")
async def healthcare_overview() -> dict:
    return await service.health_overview()


@app.get("/api/citizens/{citizen_id}")
async def citizen_detail(citizen_id: int) -> dict:
    try:
        return await service.citizen_detail(citizen_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Habitant introuvable") from exc


@app.get("/api/vehicles/{vehicle_id}")
async def vehicle_detail(vehicle_id: int) -> dict:
    try:
        return await service.vehicle_detail(vehicle_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Véhicule introuvable") from exc


@app.get("/api/incidents/{incident_id}")
async def incident_detail(incident_id: int) -> dict:
    try:
        return await service.incident_detail(incident_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Incident introuvable") from exc


@app.get("/api/buildings/{building_id}")
async def building_detail(building_id: int) -> dict:
    try:
        return await service.building_detail(building_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Bâtiment introuvable") from exc


@app.get("/api/economy")
async def economy_overview() -> dict:
    return await service.economy_overview()


@app.get("/api/enterprises/{building_id}")
async def enterprise_detail(building_id: int) -> dict:
    try:
        return await service.enterprise_detail(building_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Entreprise introuvable") from exc

@app.get("/api/social/graph")
async def social_graph() -> dict:
    return await service.social_graph()


@app.get("/api/investigations/{investigation_id}")
async def investigation_detail(investigation_id: int) -> dict:
    try:
        return await service.investigation_detail(investigation_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Enquête introuvable") from exc


@app.get("/api/cases/{case_id}")
async def case_detail(case_id: int) -> dict:
    try:
        return await service.case_detail(case_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Dossier judiciaire introuvable") from exc


@app.post("/api/simulation/pause")
async def pause() -> dict:
    await service.set_paused(True)
    return {"paused": True}


@app.post("/api/simulation/resume")
async def resume() -> dict:
    await service.set_paused(False)
    return {"paused": False}


@app.post("/api/simulation/speed")
async def set_speed(request: SpeedRequest) -> dict:
    try:
        await service.set_speed(request.speed)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"speed": request.speed}


@app.post("/api/simulation/step")
async def step(request: StepRequest) -> dict:
    try:
        await service.step(request.minutes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await service.snapshot()


@app.post("/api/city/save")
async def save_city() -> dict:
    path = await service.save()
    return {"saved": True, "path": str(path)}


@app.post("/api/city/load")
async def load_city() -> dict:
    try:
        await service.load()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=422, detail="Sauvegarde invalide") from exc
    return await service.snapshot()


@app.post("/api/city/reset")
async def reset(request: ResetRequest) -> dict:
    await service.reset(seed=request.seed)
    return await service.snapshot()


@app.websocket("/ws/city")
async def websocket_city(websocket: WebSocket) -> None:
    await websocket.accept()
    initial = True
    try:
        while True:
            payload = await service.snapshot() if initial else await service.delta()
            initial = False
            try:
                await websocket.send_json(payload)
            except (WebSocketDisconnect, RuntimeError, OSError):
                # Le navigateur peut fermer le transport entre le snapshot et l'envoi.
                # Cette déconnexion est normale (rechargement, fermeture d'onglet, réseau).
                return
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        return
