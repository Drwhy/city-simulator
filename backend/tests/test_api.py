import asyncio

from fastapi.testclient import TestClient

from app.main import app, service, websocket_city


def test_api_exposes_city_and_commands(tmp_path) -> None:
    service.save_path = tmp_path / "city_snapshot.json"
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"status": "ok"}

        city = client.get("/api/city")
        assert city.status_code == 200
        payload = city.json()
        assert len(payload["citizens"]) == 100

        citizen = client.get("/api/citizens/1")
        assert citizen.status_code == 200
        assert citizen.json()["id"] == 1

        vehicle_id = payload["vehicles"][0]["id"]
        vehicle = client.get(f"/api/vehicles/{vehicle_id}")
        assert vehicle.status_code == 200
        assert vehicle.json()["id"] == vehicle_id

        market = next(building for building in payload["buildings"] if building["type"] == "shop")
        building = client.get(f"/api/buildings/{market['id']}")
        assert building.status_code == 200
        assert building.json()["kind"] == "building"
        assert "employees" in building.json()
        assert "foodStock" in building.json()["services"]
        enterprise = client.get(f"/api/enterprises/{market['id']}")
        assert enterprise.status_code == 200
        assert "finance" in enterprise.json()
        assert "employmentHistory" in enterprise.json()["finance"]

        economy = client.get("/api/economy")
        assert economy.status_code == 200
        assert economy.json()["businesses"]
        assert "unemploymentRate" in economy.json()["metrics"]

        banking = client.get("/api/banking")
        assert banking.status_code == 200
        assert banking.json()["bank"]["reserves"] > 0
        assert banking.json()["metrics"]["deposits"] > 0

        crime = client.get("/api/crime")
        assert crime.status_code == 200
        assert crime.json()["metrics"]["organizations"] >= 1
        faction_id = crime.json()["organizations"][0]["id"]
        faction = client.get(f"/api/crime/factions/{faction_id}")
        assert faction.status_code == 200
        assert faction.json()["members"]
        assert faction.json()["markets"]

        housing = client.get("/api/housing")
        assert housing.status_code == 200
        assert housing.json()["metrics"]["vacancyRate"] > 0
        household_id = housing.json()["households"][0]["id"]
        household = client.get(f"/api/households/{household_id}")
        assert household.status_code == 200
        assert household.json()["home"]["rentMonthly"] > 0
        home_id = household.json()["home"]["id"]
        home = client.get(f"/api/buildings/{home_id}")
        assert home.json()["housing"]["households"]

        healthcare = client.get("/api/healthcare")
        assert healthcare.status_code == 200
        assert healthcare.json()["hospital"]["name"] == "Centre médical Saint-Roch"
        assert healthcare.json()["metrics"]["hospitalBeds"] == 8
        hospital_id = healthcare.json()["hospital"]["id"]
        hospital = client.get(f"/api/buildings/{hospital_id}")
        assert hospital.status_code == 200
        assert hospital.json()["healthcare"]["beds"] == 8
        assert hospital.json()["employees"]

        assert "workersOnDuty" in payload["stats"]
        assert "policeOfficersOnDuty" in payload["stats"]
        assert "shoppingTripsToday" in payload["stats"]
        assert "unemploymentRate" in payload["stats"]
        assert "openPositions" in payload["stats"]
        assert "medianSalary" in payload["stats"]
        assert "economy" in payload
        assert "banking" in payload
        assert "crime" in payload
        assert payload["simulation"]["maxCitizenCount"] == 5000

        assert client.post("/api/simulation/pause").status_code == 200
        assert client.post("/api/simulation/speed", json={"speed": 20}).status_code == 200
        assert client.post("/api/simulation/step", json={"minutes": 60}).status_code == 200
        assert client.post("/api/city/save").status_code == 200
        assert service.save_path.exists()
        assert client.post("/api/city/load").status_code == 200


def test_websocket_endpoint_tolerates_closed_transport(monkeypatch) -> None:
    class ClosedWebSocket:
        async def accept(self) -> None:
            return None

        async def send_json(self, _: dict) -> None:
            raise RuntimeError("transport closed")

    async def snapshot() -> dict:
        return {"type": "city_snapshot"}

    monkeypatch.setattr(service, "snapshot", snapshot)
    asyncio.run(websocket_city(ClosedWebSocket()))  # type: ignore[arg-type]


def test_websocket_stream_contains_mobility_data(tmp_path) -> None:
    service.save_path = tmp_path / "city_snapshot.json"
    with TestClient(app) as client:
        with client.websocket_connect("/ws/city") as websocket:
            payload = websocket.receive_json()
            assert payload["type"] == "city_snapshot"
            assert payload["vehicles"]
            assert payload["roads"]["cells"]
            assert payload["transport"]["busStops"]
            delta = websocket.receive_json()
            assert delta["type"] == "city_delta"
            assert "economy" in delta
            assert "banking" in delta
            assert "crime" in delta
            assert "health" in delta
            assert "housing" in delta
            assert "justice" in delta
            assert "unemploymentRate" in delta["stats"]
            assert "medicalStaffOnDuty" in delta["stats"]
            assert "medianRent" in delta["stats"]
            assert "cells" not in delta["roads"]


def test_city_and_citizen_expose_social_monitoring(tmp_path) -> None:
    service.save_path = tmp_path / "city_snapshot.json"
    with TestClient(app) as client:
        client.post("/api/city/reset", json={"seed": 12345})
        client.post("/api/simulation/step", json={"minutes": 615})
        city = client.get("/api/city").json()
        assert city["stats"]["households"] > 0
        assert city["stats"]["friendships"] > 0
        assert city["social"]["events"]

        citizen = client.get("/api/citizens/1").json()
        assert citizen["personality"]["sociability"] >= 0
        assert citizen["household"] is not None
        assert "favoritePlaces" in citizen["social"]
        assert citizen["relationships"]


def test_incident_and_social_graph_endpoints(tmp_path) -> None:
    service.save_path = tmp_path / "city_snapshot.json"
    with TestClient(app) as client:
        client.post("/api/simulation/pause")
        client.post("/api/city/reset", json={"seed": 12345})
        building = next(iter(service.world.buildings.values()))
        incident = service.world.create_incident(
            incident_type="dispute",
            title="Dispute test",
            description="Deux habitants se disputent.",
            severity="warning",
            building_id=building.id,
            lifetime_minutes=90,
        )
        response = client.get(f"/api/incidents/{incident.id}")
        assert response.status_code == 200
        assert response.json()["kind"] == "incident"

        graph = client.get("/api/social/graph")
        assert graph.status_code == 200
        assert len(graph.json()["nodes"]) == 100


def test_investigation_and_case_endpoints(tmp_path) -> None:
    service.save_path = tmp_path / "city_snapshot.json"
    with TestClient(app) as client:
        client.post("/api/simulation/pause")
        client.post("/api/city/reset", json={"seed": 5150})
        building = next(row for row in service.world.buildings.values() if row.building_type.value == "shop")
        citizens = list(service.world.citizens.values())[:6]
        offender, victim, *witnesses = citizens
        victim.health = 75.0
        incident = service.world.create_incident(
            incident_type="assault",
            title="Agression API",
            description="Incident utilisé pour valider les endpoints d'enquête.",
            severity="danger",
            citizen_ids=tuple(citizen.id for citizen in citizens),
            offender_id=offender.id,
            victim_ids=(victim.id,),
            witness_ids=tuple(citizen.id for citizen in witnesses),
            building_id=building.id,
            reported=True,
            conflict_level=4,
        )
        investigation = service.world._open_investigation(incident)

        investigation_response = client.get(f"/api/investigations/{investigation.id}")
        assert investigation_response.status_code == 200
        assert investigation_response.json()["evidence"]

        assert investigation.case_id is not None
        case_response = client.get(f"/api/cases/{investigation.case_id}")
        assert case_response.status_code == 200
        assert case_response.json()["defendant"]["id"] == offender.id
