from __future__ import annotations

import random
import statistics
from typing import TYPE_CHECKING, Any

from .generator import generate_neighborhoods
from .models import Building, BuildingType, Incident, Neighborhood, NeighborhoodRecord, VehicleStatus, VehicleType
from .transport import road_path
from .work import refresh_police_crews, shift_active

if TYPE_CHECKING:
    from .world import World

MAX_HISTORY_DAYS = 90


def initialize_neighborhoods(world: World) -> None:
    world.neighborhood_rng = random.Random(world.seed ^ 0xB017E7)
    world.neighborhoods = generate_neighborhoods()
    world._last_neighborhood_hour = -1
    for building in world.buildings.values():
        building.neighborhood_id = neighborhood_at(world, building.x, building.y).id


def neighborhood_at(world: World, x: int, y: int) -> Neighborhood:
    for neighborhood in world.neighborhoods.values():
        if neighborhood.x_min <= x <= neighborhood.x_max and neighborhood.y_min <= y <= neighborhood.y_max:
            return neighborhood
    return world.neighborhoods[min(world.neighborhoods)]


def update_neighborhoods(world: World) -> None:
    for unit in world.vehicles.values():
        if unit.vehicle_type == VehicleType.POLICE and unit.status == VehicleStatus.IN_SERVICE and unit.patrol_neighborhood_id in world.neighborhoods:
            world.neighborhoods[unit.patrol_neighborhood_id].patrol_minutes_today += 1
    hour_key = world.total_minutes // 60
    if hour_key == world._last_neighborhood_hour:
        return
    world._last_neighborhood_hour = hour_key
    _manage_patrols(world)


def close_neighborhood_day(world: World, day: int) -> None:
    for neighborhood in world.neighborhoods.values():
        metrics = neighborhood_metrics(world, neighborhood)
        neighborhood.history.append(NeighborhoodRecord(day=day, **metrics))
        neighborhood.history[:] = neighborhood.history[-MAX_HISTORY_DAYS:]
        target_safety = max(8.0, min(96.0, 72.0 - metrics["criminality"] * 0.42 + metrics["police_coverage"] * 0.12 + neighborhood.lighting * 0.10))
        neighborhood.safety_perception = round(neighborhood.safety_perception * 0.76 + target_safety * 0.24, 2)
        target_attractiveness = 0.30 * neighborhood.safety_perception + 0.18 * metrics["healthcare_access"] + 0.16 * metrics["commerce_access"] + 0.16 * (100.0 - metrics["unemployment_rate"]) + 0.12 * min(100.0, metrics["commercial_activity"] / 8.0) + 0.08 * max(0.0, 100.0 - metrics["average_transport_minutes"] * 3.0)
        neighborhood.attractiveness = round(max(5.0, min(95.0, neighborhood.attractiveness * 0.72 + target_attractiveness * 0.28)), 2)
        neighborhood.incidents_today = 0
        neighborhood.incident_score_today = 0.0
        neighborhood.patrol_minutes_today = 0
        neighborhood.police_responses_today = 0
        neighborhood.police_response_minutes_today = 0


def record_incident(world: World, incident: Incident) -> None:
    neighborhood = world.neighborhoods.get(incident.neighborhood_id)
    if neighborhood is None:
        return
    weight = 3.0 if incident.severity == "danger" else 1.4
    weight += max(0, incident.conflict_level - 1) * 0.45
    neighborhood.incidents_today += 1
    neighborhood.incident_score_today += weight
    neighborhood.cumulative_incidents += 1
    neighborhood.safety_perception = round(max(5.0, neighborhood.safety_perception - weight * 0.32), 2)


def record_police_response(world: World, incident: Incident, response_minutes: int) -> None:
    neighborhood = world.neighborhoods.get(incident.neighborhood_id)
    if neighborhood is None:
        return
    neighborhood.police_responses_today += 1
    neighborhood.police_response_minutes_today += response_minutes


def crime_opportunity(world: World, building: Building, witnesses: int) -> float:
    neighborhood = world.neighborhoods[building.neighborhood_id]
    hour_darkness = 1.0 if world.hour >= 21 or world.hour < 6 else 0.25
    lighting_risk = (100.0 - neighborhood.lighting) / 100.0 * hour_darkness
    activity_protection = min(0.38, len(building.occupants) * 0.045)
    witness_protection = min(0.32, witnesses * 0.055)
    patrol_protection = min(0.38, neighborhood_metrics(world, neighborhood)["police_coverage"] / 220.0)
    pressure = (100.0 - neighborhood.safety_perception) / 180.0
    return max(0.35, min(1.8, 0.82 + lighting_risk + pressure - activity_protection - witness_protection - patrol_protection))


def reporting_probability(world: World, x: int, y: int, witness_count: int, base: float) -> float:
    neighborhood = neighborhood_at(world, x, y)
    witness_factor = min(0.22, witness_count * 0.035)
    visibility = neighborhood.lighting / 500.0 if world.hour >= 20 or world.hour < 7 else 0.14
    return max(0.03, min(0.99, base + witness_factor + visibility))


def neighborhood_metrics(world: World, neighborhood: Neighborhood) -> dict[str, Any]:
    residents = [citizen for citizen in world.citizens.values() if world.buildings[citizen.home_id].neighborhood_id == neighborhood.id]
    homes = [building for building in world.buildings.values() if building.neighborhood_id == neighborhood.id and building.building_type == BuildingType.HOME]
    businesses = [building for building in world.buildings.values() if building.neighborhood_id == neighborhood.id and building.building_type in {BuildingType.OFFICE, BuildingType.FACTORY, BuildingType.SHOP, BuildingType.CAFE}]
    shops = [building for building in world.buildings.values() if building.building_type in {BuildingType.SHOP, BuildingType.CAFE}]
    hospitals = [building for building in world.buildings.values() if building.building_type == BuildingType.HOSPITAL]
    center = neighborhood.center
    healthcare_distance = min((_distance(center, building.entrance) for building in hospitals), default=30)
    commerce_distance = min((_distance(center, building.entrance) for building in shops), default=30)
    hospital_level = statistics.fmean(building.service_level for building in hospitals) if hospitals else 0.0
    commerce_level = statistics.fmean(building.service_level for building in shops) if shops else 0.0
    healthcare_access = max(0.0, min(100.0, 100.0 - healthcare_distance * 3.2)) * hospital_level / 100.0
    commerce_access = max(0.0, min(100.0, 100.0 - commerce_distance * 3.0)) * commerce_level / 100.0
    elapsed = max(1, world.hour * 60 + world.minute)
    coverage = min(100.0, neighborhood.patrol_minutes_today / elapsed * 190.0)
    recent_scores = [record.criminality for record in neighborhood.history[-6:]]
    crime = (sum(recent_scores) + neighborhood.incident_score_today / max(1, len(residents)) * 100.0) / (len(recent_scores) + 1)
    response = neighborhood.police_response_minutes_today / max(1, neighborhood.police_responses_today)
    if not neighborhood.police_responses_today:
        past = [record.average_response_minutes for record in neighborhood.history[-7:] if record.average_response_minutes > 0]
        response = statistics.fmean(past) if past else _distance(center, _police_position(world)) / max(1, world.CAR_SPEED)
    transport_samples = [citizen.last_trip_minutes for citizen in residents if citizen.last_trip_minutes > 0]
    commute_distances = [_distance(world.buildings[citizen.home_id].entrance, world.buildings[citizen.workplace_id].entrance) for citizen in residents if citizen.workplace_id in world.buildings]
    transport = statistics.fmean(transport_samples) if transport_samples else (statistics.fmean(commute_distances) / 1.6 if commute_distances else 0.0)
    commercial_activity = sum(building.revenue_today + len(building.occupants) * 2.5 for building in businesses)
    unemployment = sum(citizen.workplace_id is None for citizen in residents) / max(1, len(residents)) * 100.0
    average_income = statistics.fmean([citizen.salary_daily * 22 for citizen in residents]) if residents else 0.0
    average_rent = statistics.fmean([home.rent_monthly for home in homes]) if homes else 0.0
    service_pressure = max(0.0, min(100.0, (200.0 - healthcare_access - commerce_access) / 2.0 + unemployment * 0.18))
    return {
        "population": len(residents), "average_income": round(average_income, 2), "unemployment_rate": round(unemployment, 2),
        "average_rent": round(average_rent, 2), "commercial_activity": round(commercial_activity, 2), "criminality": round(crime, 2),
        "safety_perception": round(neighborhood.safety_perception, 2), "police_coverage": round(coverage, 2), "average_response_minutes": round(response, 2),
        "healthcare_access": round(healthcare_access, 2), "commerce_access": round(commerce_access, 2), "average_transport_minutes": round(transport, 2),
        "attractiveness": round(neighborhood.attractiveness, 2), "service_pressure": round(service_pressure, 2),
    }


def neighborhood_summary(world: World, neighborhood: Neighborhood) -> dict[str, Any]:
    metrics = neighborhood_metrics(world, neighborhood)
    return {"id": neighborhood.id, "name": neighborhood.name, "bounds": {"xMin": neighborhood.x_min, "yMin": neighborhood.y_min, "xMax": neighborhood.x_max, "yMax": neighborhood.y_max}, "lighting": neighborhood.lighting, **_camel_metrics(metrics)}


def neighborhood_detail(world: World, neighborhood_id: int) -> dict[str, Any]:
    neighborhood = world.neighborhoods[neighborhood_id]
    buildings = [building for building in world.buildings.values() if building.neighborhood_id == neighborhood_id]
    incidents = [incident for incident in world.incidents.values() if incident.neighborhood_id == neighborhood_id]
    patrols = [unit for unit in world.vehicles.values() if unit.vehicle_type == VehicleType.POLICE and unit.patrol_neighborhood_id == neighborhood_id]
    return {"kind": "neighborhood", **neighborhood_summary(world, neighborhood), "buildings": [{"id": row.id, "name": row.name, "type": row.building_type.value, "serviceLevel": round(row.service_level, 1)} for row in buildings], "businesses": [{"id": row.id, "name": row.name, "type": row.building_type.value, "revenueToday": round(row.revenue_today, 2), "serviceLevel": round(row.service_level, 1)} for row in buildings if row.building_type in {BuildingType.OFFICE, BuildingType.FACTORY, BuildingType.SHOP, BuildingType.CAFE}], "services": [{"id": row.id, "name": row.name, "type": row.building_type.value, "serviceLevel": round(row.service_level, 1)} for row in buildings if row.building_type in {BuildingType.PUBLIC, BuildingType.POLICE, BuildingType.HOSPITAL, BuildingType.COURT}], "incidents": [world._incident_summary(row) for row in sorted(incidents, key=lambda item: item.created_tick, reverse=True)[:30]], "patrols": [world._vehicle_summary(row) for row in patrols], "history": [{"day": row.day, **_camel_metrics(row.__dict__ if hasattr(row, "__dict__") else {field: getattr(row, field) for field in row.__dataclass_fields__ if field != "day"})} for row in neighborhood.history]}


def neighborhood_overview(world: World) -> dict[str, Any]:
    rows = [neighborhood_summary(world, row) for row in world.neighborhoods.values()]
    safety_values = [row["safetyPerception"] for row in rows]
    attractiveness_values = [row["attractiveness"] for row in rows]
    return {"tick": world.tick, "neighborhoods": rows, "metrics": {"averageSafety": round(statistics.fmean(safety_values), 2), "averageAttractiveness": round(statistics.fmean(attractiveness_values), 2), "highestServicePressure": round(max(row["servicePressure"] for row in rows), 2), "slowestResponseMinutes": round(max(row["averageResponseMinutes"] for row in rows), 2), "lowestHealthcareAccess": round(min(row["healthcareAccess"] for row in rows), 2), "safetyGap": round(max(safety_values) - min(safety_values), 2)}}


def neighborhood_city_metrics(world: World) -> dict[str, float]:
    metrics = neighborhood_overview(world)["metrics"]
    return {"averageNeighborhoodSafety": metrics["averageSafety"], "averageNeighborhoodAttractiveness": metrics["averageAttractiveness"], "highestServicePressure": metrics["highestServicePressure"], "slowestNeighborhoodResponseMinutes": metrics["slowestResponseMinutes"], "lowestHealthcareAccess": metrics["lowestHealthcareAccess"], "neighborhoodSafetyGap": metrics["safetyGap"]}


def _manage_patrols(world: World) -> None:
    refresh_police_crews(world)
    units = [unit for unit in world.vehicles.values() if unit.vehicle_type == VehicleType.POLICE]
    for unit in units:
        if unit.status == VehicleStatus.IN_SERVICE and (not unit.crew_ids or any(not shift_active(world, world.citizens[officer_id]) for officer_id in unit.crew_ids)):
            world._send_police_home(unit)
            unit.patrol_neighborhood_id = None
    candidates = [unit for unit in units if unit.status == VehicleStatus.PARKED and len(unit.crew_ids) >= min(2, unit.capacity)]
    ordered = sorted(world.neighborhoods.values(), key=lambda row: (neighborhood_metrics(world, row)["police_coverage"], row.safety_perception, row.id))
    for unit, neighborhood in zip(candidates, ordered):
        target = _patrol_target(world, neighborhood)
        unit.status = VehicleStatus.IN_SERVICE
        unit.patrol_neighborhood_id = neighborhood.id
        unit.current_building_id = None
        unit.target_building_id = None
        unit.route = road_path((unit.x, unit.y), target, world.road_cells)
        unit.route_index = 0
        unit.passenger_ids = set(unit.crew_ids)
        unit.service_started_tick = world.tick
        world._sync_police_crew(unit)
        world._emit("neighborhood_patrol_started", f"L’unité #{unit.id} commence une patrouille dans {neighborhood.name}.", citizen_ids=tuple(sorted(unit.crew_ids)), vehicle_id=unit.id)


def continue_patrol(world: World, unit: Any) -> None:
    if unit.patrol_neighborhood_id not in world.neighborhoods:
        return
    neighborhood = world.neighborhoods[unit.patrol_neighborhood_id]
    unit.route = road_path((unit.x, unit.y), _patrol_target(world, neighborhood), world.road_cells)
    unit.route_index = 0


def _patrol_target(world: World, neighborhood: Neighborhood) -> tuple[int, int]:
    cells = [cell for cell in world.road_cells if neighborhood.x_min <= cell[0] <= neighborhood.x_max and neighborhood.y_min <= cell[1] <= neighborhood.y_max]
    return cells[world.neighborhood_rng.randrange(len(cells))] if cells else neighborhood.center


def _police_position(world: World) -> tuple[int, int]:
    station = next((building for building in world.buildings.values() if building.building_type == BuildingType.POLICE), None)
    return station.entrance if station else (world.MAP_WIDTH // 2, world.MAP_HEIGHT // 2)


def _distance(first: tuple[int, int], second: tuple[int, int]) -> int:
    return abs(first[0] - second[0]) + abs(first[1] - second[1])


def _camel_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    names = {"average_income": "averageIncome", "unemployment_rate": "unemploymentRate", "average_rent": "averageRent", "commercial_activity": "commercialActivity", "safety_perception": "safetyPerception", "police_coverage": "policeCoverage", "average_response_minutes": "averageResponseMinutes", "healthcare_access": "healthcareAccess", "commerce_access": "commerceAccess", "average_transport_minutes": "averageTransportMinutes", "service_pressure": "servicePressure"}
    return {names.get(key, key): value for key, value in metrics.items()}
