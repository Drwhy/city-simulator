from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..simulation.models import CommunicationChannel, CommunicationTone
from ..simulation.service import SimulationService


class SpeedRequest(BaseModel):
    speed: int


class StepRequest(BaseModel):
    minutes: int = Field(default=1, ge=1, le=1440)


class ResetRequest(BaseModel):
    seed: int | None = None
    citizen_count: int | None = Field(default=None, alias="citizenCount", ge=20, le=5000)


class CommunicationRequest(BaseModel):
    sender_id: int = Field(alias="senderId", gt=0)
    recipient_id: int = Field(alias="recipientId", gt=0)
    channel: CommunicationChannel
    tone: CommunicationTone = CommunicationTone.FRIENDLY
    subject: str = Field(default="", max_length=120)
    body: str = Field(default="", max_length=800)
    attempt_order_violation: bool = Field(default=False, alias="attemptOrderViolation")


def create_api_router(service: SimulationService) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @router.get("/city")
    async def city_snapshot() -> dict:
        return await service.snapshot()

    @router.get("/banking")
    async def banking_overview() -> dict:
        return await service.banking_overview()

    @router.get("/healthcare")
    async def healthcare_overview() -> dict:
        return await service.health_overview()

    @router.get("/housing")
    async def housing_overview() -> dict:
        return await service.housing_overview()

    @router.get("/economy")
    async def economy_overview() -> dict:
        return await service.economy_overview()

    @router.get("/crime")
    async def crime_overview() -> dict:
        return await service.crime_overview()

    @router.get("/crime/factions/{organization_id}")
    async def crime_faction_detail(organization_id: int) -> dict:
        return await _detail_or_404(service.crime_faction_detail, organization_id, "Faction criminelle introuvable")

    @router.get("/justice")
    async def justice_overview() -> dict:
        return await service.justice_overview()

    @router.get("/neighborhoods")
    async def neighborhoods_overview() -> dict:
        return await service.neighborhood_overview()

    @router.get("/neighborhoods/{neighborhood_id}")
    async def neighborhood_detail(neighborhood_id: int) -> dict:
        return await _detail_or_404(service.neighborhood_detail, neighborhood_id, "Quartier introuvable")

    @router.get("/social/graph")
    async def social_graph() -> dict:
        return await service.social_graph()

    @router.get("/communications")
    async def communications_overview() -> dict:
        return await service.communication_overview()

    @router.get("/citizens/{citizen_id}/communications")
    async def citizen_communications(citizen_id: int) -> dict:
        return await _detail_or_404(service.citizen_communications, citizen_id, "Habitant introuvable")

    @router.post("/communications", status_code=201)
    async def create_communication(request: CommunicationRequest) -> dict:
        try:
            return await service.send_communication(sender_id=request.sender_id, recipient_id=request.recipient_id, channel=request.channel, tone=request.tone, subject=request.subject, body=request.body, attempt_order_violation=request.attempt_order_violation)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Expéditeur ou destinataire introuvable") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get("/households/{household_id}")
    async def household_detail(household_id: int) -> dict:
        return await _detail_or_404(service.household_detail, household_id, "Foyer introuvable")

    @router.get("/citizens/{citizen_id}")
    async def citizen_detail(citizen_id: int) -> dict:
        return await _detail_or_404(service.citizen_detail, citizen_id, "Habitant introuvable")

    @router.get("/vehicles/{vehicle_id}")
    async def vehicle_detail(vehicle_id: int) -> dict:
        return await _detail_or_404(service.vehicle_detail, vehicle_id, "Véhicule introuvable")

    @router.get("/incidents/{incident_id}")
    async def incident_detail(incident_id: int) -> dict:
        return await _detail_or_404(service.incident_detail, incident_id, "Incident introuvable")

    @router.get("/buildings/{building_id}")
    async def building_detail(building_id: int) -> dict:
        return await _detail_or_404(service.building_detail, building_id, "Bâtiment introuvable")

    @router.get("/enterprises/{building_id}")
    async def enterprise_detail(building_id: int) -> dict:
        return await _detail_or_404(service.enterprise_detail, building_id, "Entreprise introuvable")

    @router.get("/investigations/{investigation_id}")
    async def investigation_detail(investigation_id: int) -> dict:
        return await _detail_or_404(service.investigation_detail, investigation_id, "Enquête introuvable")

    @router.get("/cases/{case_id}")
    async def case_detail(case_id: int) -> dict:
        return await _detail_or_404(service.case_detail, case_id, "Dossier judiciaire introuvable")

    @router.post("/simulation/pause")
    async def pause() -> dict:
        await service.set_paused(True)
        return {"paused": True}

    @router.post("/simulation/resume")
    async def resume() -> dict:
        await service.set_paused(False)
        return {"paused": False}

    @router.post("/simulation/speed")
    async def set_speed(request: SpeedRequest) -> dict:
        try:
            await service.set_speed(request.speed)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"speed": request.speed}

    @router.post("/simulation/step")
    async def step(request: StepRequest) -> dict:
        try:
            await service.step(request.minutes)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return await service.snapshot()

    @router.post("/city/save")
    async def save_city() -> dict:
        path = await service.save()
        return {"saved": True, "path": str(path)}

    @router.post("/city/load")
    async def load_city() -> dict:
        try:
            await service.load()
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (ValueError, KeyError, TypeError) as exc:
            raise HTTPException(status_code=422, detail="Sauvegarde invalide") from exc
        return await service.snapshot()

    @router.post("/city/reset")
    async def reset(request: ResetRequest) -> dict:
        await service.reset(seed=request.seed, citizen_count=request.citizen_count)
        return await service.snapshot()

    return router


async def _detail_or_404(loader, object_id: int, message: str) -> dict:
    try:
        return await loader(object_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=message) from exc