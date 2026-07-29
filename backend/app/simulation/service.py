from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path

from .world import World
from .communication import communication_summary, send_communication
from .models import CommunicationChannel, CommunicationTone
from .persistence import read_snapshot, write_snapshot


@dataclass(slots=True)
class SimulationStatus:
    paused: bool = False
    speed: int = 1


class SimulationService:
    ALLOWED_SPEEDS = {1, 5, 20, 60}
    MIN_CITIZENS = 20
    MAX_CITIZENS = 5000

    def __init__(self, *, seed: int = 12345, citizen_count: int | None = None) -> None:
        citizen_count = citizen_count or int(os.getenv("CITYSIM_CITIZEN_COUNT", "100"))
        if not self.MIN_CITIZENS <= citizen_count <= self.MAX_CITIZENS:
            raise ValueError(f"La population doit être comprise entre {self.MIN_CITIZENS} et {self.MAX_CITIZENS}.")
        self.seed = seed
        self.citizen_count = citizen_count
        self.world = World(seed=seed, citizen_count=citizen_count)
        self.status = SimulationStatus()
        self.save_path = Path(os.getenv("CITYSIM_SAVE_PATH", "city_snapshot.json"))
        self._task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run_loop(), name="city-simulation-loop")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _run_loop(self) -> None:
        while True:
            await asyncio.sleep(0.25)
            if self.status.paused:
                continue
            async with self._lock:
                self.world.run_minutes(self.status.speed)

    async def snapshot(self) -> dict:
        async with self._lock:
            data = self.world.snapshot()
            data["simulation"] = {
                "paused": self.status.paused,
                "speed": self.status.speed,
                "allowedSpeeds": sorted(self.ALLOWED_SPEEDS),
                "hasSave": self.save_path.exists(),
                "citizenCount": self.citizen_count,
                "maxCitizenCount": self.MAX_CITIZENS,
            }
            return data

    async def delta(self) -> dict:
        async with self._lock:
            data = self.world.delta_snapshot()
            data["simulation"] = {
                "paused": self.status.paused,
                "speed": self.status.speed,
                "allowedSpeeds": sorted(self.ALLOWED_SPEEDS),
                "hasSave": self.save_path.exists(),
                "citizenCount": self.citizen_count,
                "maxCitizenCount": self.MAX_CITIZENS,
            }
            return data

    async def citizen_detail(self, citizen_id: int) -> dict:
        async with self._lock:
            return self.world.get_citizen_detail(citizen_id)

    async def vehicle_detail(self, vehicle_id: int) -> dict:
        async with self._lock:
            return self.world.get_vehicle_detail(vehicle_id)

    async def incident_detail(self, incident_id: int) -> dict:
        async with self._lock:
            return self.world.get_incident_detail(incident_id)

    async def building_detail(self, building_id: int) -> dict:
        async with self._lock:
            return self.world.get_building_detail(building_id)

    async def enterprise_detail(self, building_id: int) -> dict:
        async with self._lock:
            return self.world.get_enterprise_detail(building_id)

    async def economy_overview(self) -> dict:
        async with self._lock:
            return self.world.get_economy_overview()

    async def banking_overview(self) -> dict:
        async with self._lock:
            return self.world.get_banking_overview()

    async def health_overview(self) -> dict:
        async with self._lock:
            return self.world.get_health_overview()

    async def housing_overview(self) -> dict:
        async with self._lock:
            return self.world.get_housing_overview()

    async def household_detail(self, household_id: int) -> dict:
        async with self._lock:
            return self.world.get_household_detail(household_id)

    async def crime_overview(self) -> dict:
        async with self._lock:
            return self.world.get_crime_overview()

    async def crime_faction_detail(self, organization_id: int) -> dict:
        async with self._lock:
            return self.world.get_crime_faction_detail(organization_id)

    async def justice_overview(self) -> dict:
        async with self._lock:
            return self.world.get_justice_overview()

    async def neighborhood_overview(self) -> dict:
        async with self._lock:
            return self.world.get_neighborhood_overview()

    async def neighborhood_detail(self, neighborhood_id: int) -> dict:
        async with self._lock:
            return self.world.get_neighborhood_detail(neighborhood_id)

    async def social_graph(self) -> dict:
        async with self._lock:
            return self.world.get_social_graph()

    async def communication_overview(self) -> dict:
        async with self._lock:
            return self.world.get_communication_overview()

    async def citizen_communications(self, citizen_id: int) -> dict:
        async with self._lock:
            return self.world.get_citizen_communications(citizen_id)

    async def send_communication(self, *, sender_id: int, recipient_id: int, channel: CommunicationChannel, tone: CommunicationTone, subject: str, body: str, attempt_order_violation: bool = False) -> dict:
        async with self._lock:
            item = send_communication(self.world, sender_id=sender_id, recipient_id=recipient_id, channel=channel, tone=tone, subject=subject, body=body, attempt_order_violation=attempt_order_violation)
            return communication_summary(self.world, item)

    async def investigation_detail(self, investigation_id: int) -> dict:
        async with self._lock:
            return self.world.get_investigation_detail(investigation_id)

    async def case_detail(self, case_id: int) -> dict:
        async with self._lock:
            return self.world.get_case_detail(case_id)

    async def set_paused(self, paused: bool) -> None:
        self.status.paused = paused

    async def set_speed(self, speed: int) -> None:
        if speed not in self.ALLOWED_SPEEDS:
            raise ValueError(f"Vitesse invalide : {speed}")
        self.status.speed = speed

    async def step(self, minutes: int = 1) -> None:
        if minutes < 1 or minutes > 1440:
            raise ValueError("Le pas doit être compris entre 1 et 1440 minutes.")
        async with self._lock:
            self.world.run_minutes(minutes)

    async def reset(self, *, seed: int | None = None, citizen_count: int | None = None) -> None:
        async with self._lock:
            if seed is not None:
                self.seed = seed
            if citizen_count is not None:
                if not self.MIN_CITIZENS <= citizen_count <= self.MAX_CITIZENS:
                    raise ValueError(f"La population doit être comprise entre {self.MIN_CITIZENS} et {self.MAX_CITIZENS}.")
                self.citizen_count = citizen_count
            self.world = World(seed=self.seed, citizen_count=self.citizen_count)

    async def save(self) -> Path:
        async with self._lock:
            return write_snapshot(self.save_path, self.world.export_state())

    async def load(self) -> None:
        async with self._lock:
            self.world = World.from_state(read_snapshot(self.save_path))
            self.seed = self.world.seed
            self.citizen_count = len(self.world.citizens)
