from fastapi.testclient import TestClient

from app.main import app, service
from app.simulation.models import BuildingType, VehicleStatus, VehicleType
from app.simulation.neighborhood import crime_opportunity, neighborhood_at
from app.simulation.persistence import SAVE_VERSION
from app.simulation.world import World


def test_four_neighborhoods_have_real_and_different_metrics() -> None:
    world = World(seed=11001, citizen_count=100)
    rows = world.get_neighborhood_overview()["neighborhoods"]
    assert len(rows) == 4
    assert sum(row["population"] for row in rows) == 100
    assert len({row["averageRent"] for row in rows}) > 1
    assert len({row["healthcareAccess"] for row in rows}) > 1
    assert len({row["averageResponseMinutes"] for row in rows}) > 1


def test_repeated_incidents_reduce_local_safety_without_affecting_every_zone() -> None:
    world = World(seed=11002, citizen_count=20)
    building = next(row for row in world.buildings.values() if row.neighborhood_id == 3)
    affected = world.neighborhoods[3]
    other = world.neighborhoods[2]
    before, other_before = affected.safety_perception, other.safety_perception
    for index in range(5):
        world.create_incident(incident_type="theft", title=f"Vol répété {index}", description="Incident territorial de test.", severity="danger", building_id=building.id, reported=True)
    assert affected.safety_perception < before - 4
    assert other.safety_perception == other_before
    assert affected.incidents_today == 5


def test_distance_to_services_changes_access_and_estimated_response() -> None:
    world = World(seed=11003, citizen_count=100)
    rows = {row["id"]: row for row in world.get_neighborhood_overview()["neighborhoods"]}
    assert rows[1]["healthcareAccess"] < rows[2]["healthcareAccess"]
    assert rows[1]["averageResponseMinutes"] > rows[4]["averageResponseMinutes"]
    assert rows[1]["servicePressure"] > rows[2]["servicePressure"]


def test_lighting_activity_witnesses_and_police_reduce_but_never_remove_crime() -> None:
    world = World(seed=11004, citizen_count=100)
    shop = next(row for row in world.buildings.values() if row.building_type == BuildingType.SHOP)
    neighborhood = world.neighborhoods[shop.neighborhood_id]
    world.hour = 23
    neighborhood.lighting = 20
    neighborhood.safety_perception = 30
    shop.occupants.clear()
    high_risk = crime_opportunity(world, shop, 0)
    neighborhood.lighting = 100
    neighborhood.safety_perception = 95
    neighborhood.patrol_minutes_today = 23 * 60
    shop.occupants.update(range(1, 10))
    protected_risk = crime_opportunity(world, shop, 8)
    assert protected_risk < high_risk
    assert protected_risk >= 0.35


def test_patrols_use_real_staffed_units_and_cover_zones() -> None:
    world = World(seed=11005, citizen_count=100)
    world.run_minutes(180)
    patrols = [unit for unit in world.vehicles.values() if unit.vehicle_type == VehicleType.POLICE and unit.status == VehicleStatus.IN_SERVICE]
    assert patrols
    assert all(len(unit.crew_ids) == 2 and unit.patrol_neighborhood_id in world.neighborhoods for unit in patrols)
    assert any(neighborhood.patrol_minutes_today > 0 for neighborhood in world.neighborhoods.values())
    assert all(world.citizens[officer_id].active_vehicle_id == unit.id for unit in patrols for officer_id in unit.crew_ids)


def test_neighborhood_save_resume_is_exact_and_deterministic() -> None:
    world = World(seed=11006, citizen_count=40)
    world.run_minutes(26 * 60)
    state = world.export_state()
    restored = World.from_state(state)
    assert state["version"] == SAVE_VERSION
    assert restored.export_state() == state
    world.run_minutes(6 * 60)
    restored.run_minutes(6 * 60)
    assert restored.snapshot() == world.snapshot()


def test_neighborhood_api_and_websocket_domain(tmp_path) -> None:
    service.save_path = tmp_path / "city.json"
    with TestClient(app) as client:
        client.post("/api/simulation/pause")
        client.post("/api/city/reset", json={"seed": 11007})
        overview = client.get("/api/neighborhoods")
        assert overview.status_code == 200
        assert len(overview.json()["neighborhoods"]) == 4
        detail = client.get("/api/neighborhoods/1")
        assert detail.status_code == 200
        assert detail.json()["kind"] == "neighborhood"
        assert detail.json()["buildings"]
        assert client.get("/api/neighborhoods/999").status_code == 404
        with client.websocket_connect("/ws/city") as websocket:
            payload = websocket.receive_json()
            assert "neighborhoods" in payload
            assert "highestServicePressure" in payload["stats"]


def test_thirty_days_keep_histories_bounded_and_zones_distinct() -> None:
    world = World(seed=11008, citizen_count=20)
    world.run_minutes(30 * 24 * 60)
    rows = world.get_neighborhood_overview()["neighborhoods"]
    assert all(len(neighborhood.history) == 30 for neighborhood in world.neighborhoods.values())
    assert len({round(row["safetyPerception"], 1) for row in rows}) > 1
    assert len({round(row["attractiveness"], 1) for row in rows}) > 1
    assert all(0 <= row["servicePressure"] <= 100 for row in rows)
    assert all(unit.status not in {VehicleStatus.RESPONDING, VehicleStatus.RETURNING} or unit.route for unit in world.vehicles.values() if unit.vehicle_type == VehicleType.POLICE)
