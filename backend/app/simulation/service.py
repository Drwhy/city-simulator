from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path

from .world import World


@dataclass(slots=True)
class SimulationStatus:
    paused: bool = False
    speed: int = 1


class SimulationService:
    ALLOWED_SPEEDS = {1, 5, 20, 60}

    def __init__(self, *, seed: int = 12345, citizen_count: int = 100) -> None:
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

    async def social_graph(self) -> dict:
        async with self._lock:
            return self.world.get_social_graph()

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

    async def reset(self, *, seed: int | None = None) -> None:
        async with self._lock:
            if seed is not None:
                self.seed = seed
            self.world = World(seed=self.seed, citizen_count=self.citizen_count)

    async def save(self) -> Path:
        async with self._lock:
            payload = self.world.export_state()
            self.save_path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = self.save_path.with_suffix(self.save_path.suffix + ".tmp")
            temporary_path.write_text(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )
            temporary_path.replace(self.save_path)
            return self.save_path

    async def load(self) -> None:
        async with self._lock:
            if not self.save_path.exists():
                raise FileNotFoundError("Aucune sauvegarde n'est disponible.")
            payload = json.loads(self.save_path.read_text(encoding="utf-8"))
            self.world = World.from_state(payload)
            self.seed = self.world.seed
