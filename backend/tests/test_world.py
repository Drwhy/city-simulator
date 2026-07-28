import copy

import pytest

from app.simulation.models import Activity, IncidentStatus, TravelStage, VehicleStatus, VehicleType
from app.simulation.work import refresh_police_crews, update_work_and_consumption
from app.simulation.world import World


def test_generation_is_deterministic() -> None:
    first = World(seed=12345, citizen_count=100).snapshot()
    second = World(seed=12345, citizen_count=100).snapshot()
    assert first["citizens"] == second["citizens"]
    assert first["buildings"] == second["buildings"]


def test_world_runs_for_seven_days() -> None:
    world = World(seed=12345, citizen_count=100)
    world.run_minutes(7 * 24 * 60)
    assert world.day == 8
    assert len(world.citizens) == 100
    assert world.tick == 10080
    assert all(0 <= citizen.needs.hunger <= 100 for citizen in world.citizens.values())


def test_citizens_move_after_morning_starts() -> None:
    world = World(seed=12345, citizen_count=10)
    initial_positions = {citizen.id: (citizen.x, citizen.y) for citizen in world.citizens.values()}
    world.run_minutes(180)
    moved = [
        citizen.id
        for citizen in world.citizens.values()
        if (citizen.x, citizen.y) != initial_positions[citizen.id]
    ]
    assert moved


def test_state_round_trip() -> None:
    world = World(seed=9876, citizen_count=25)
    world.run_minutes(900)
    restored = World.from_state(world.export_state())
    assert restored.snapshot() == world.snapshot()
    restored.run_minutes(60)
    world.run_minutes(60)
    assert restored.snapshot() == world.snapshot()


def test_transport_network_and_vehicles_are_generated() -> None:
    world = World(seed=12345, citizen_count=100)
    snapshot = world.snapshot()
    assert snapshot["roads"]["cells"]
    assert len(snapshot["transport"]["busStops"]) == 10
    assert len([vehicle for vehicle in snapshot["vehicles"] if vehicle["type"] == "bus"]) == 2
    assert snapshot["stats"]["carOwners"] > 0


def test_morning_commute_uses_all_transport_modes() -> None:
    world = World(seed=12345, citizen_count=100)
    world.run_minutes(180)
    trips = world.snapshot()["stats"]["tripCountsToday"]
    assert trips["walk"] > 0
    assert trips["car"] > 0
    assert trips["bus"] > 0
    assert world.bus_boardings_today > 0


def test_vehicle_detail_exposes_owner_or_line() -> None:
    world = World(seed=12345, citizen_count=100)
    car = next(vehicle for vehicle in world.vehicles.values() if vehicle.vehicle_type.value == "car")
    bus = next(vehicle for vehicle in world.vehicles.values() if vehicle.vehicle_type.value == "bus")
    assert world.get_vehicle_detail(car.id)["owner"] is not None
    assert world.get_vehicle_detail(bus.id)["line"]["name"] == "Ligne circulaire C1"


def test_social_foundations_are_generated() -> None:
    world = World(seed=12345, citizen_count=100)
    snapshot = world.snapshot()
    assert snapshot["stats"]["households"] > 0
    assert snapshot["stats"]["friendships"] > 0
    assert all(citizen.household_id is not None for citizen in world.citizens.values())
    assert all(0 <= citizen.sociability <= 100 for citizen in world.citizens.values())


def test_evening_social_events_are_planned_and_completed() -> None:
    world = World(seed=12345, citizen_count=100)
    world.run_minutes(10 * 60 + 15)  # 16:15
    assert world.social_events
    assert world.snapshot()["stats"]["activeSocialEvents"] > 0
    world.run_minutes(4 * 60)
    assert any(event.status.value == "completed" for event in world.social_events.values())
    assert any(event.event_type == "social_gathering_completed" for event in world.events)


def test_household_evening_updates_cohesion() -> None:
    world = World(seed=12345, citizen_count=100)
    initial = {household.id: household.cohesion for household in world.households.values()}
    world.run_minutes(14 * 60)  # 20:00
    changed = [
        household.id
        for household in world.households.values()
        if household.cohesion != initial[household.id]
    ]
    assert changed
    assert sum(household.shared_meals for household in world.households.values()) > 0


def test_incident_is_visible_then_expires() -> None:
    world = World(seed=12345, citizen_count=20)
    building = next(iter(world.buildings.values()))
    incident = world.create_incident(
        incident_type="test_alert",
        title="Incident temporaire",
        description="Un incident de test est observé.",
        severity="warning",
        building_id=building.id,
        lifetime_minutes=5,
    )
    assert any(row["id"] == incident.id for row in world.snapshot()["incidents"])
    world.run_minutes(6)
    assert all(row["id"] != incident.id for row in world.snapshot()["incidents"])
    assert world.get_incident_detail(incident.id)["status"] == "expired"


def test_social_graph_exposes_all_citizens_and_relationships() -> None:
    world = World(seed=12345, citizen_count=100)
    graph = world.get_social_graph()
    assert len(graph["nodes"]) == 100
    assert graph["edges"]
    assert {"source", "target", "status", "conflictLevel"}.issubset(graph["edges"][0])


def test_repeated_negative_interactions_escalate_conflict() -> None:
    from app.simulation.social import apply_interaction

    world = World(seed=12345, citizen_count=20)
    household = next(h for h in world.households.values() if len(h.member_ids) >= 2)
    a = world.citizens[household.member_ids[0]]
    b = world.citizens[household.member_ids[1]]
    for _ in range(35):
        apply_interaction(world, a, b, household.home_id, positive=False, strength=2.0)
    relation = a.relationships[b.id]
    assert relation.conflict_level >= 4
    assert any(incident.conflict_level >= 3 for incident in world.incidents.values())


def test_reported_incident_dispatches_and_is_resolved_by_police() -> None:
    world = World(seed=12345, citizen_count=20)
    building = next(b for b in world.buildings.values() if b.building_type.value == "shop")
    incident = world.create_incident(
        incident_type="theft",
        title="Vol signalé",
        description="Un vol est signalé au commerce.",
        severity="danger",
        building_id=building.id,
        reported=True,
        lifetime_minutes=300,
    )
    world.run_minutes(180)
    detail = world.get_incident_detail(incident.id)
    assert detail["timeline"]["arrivalTick"] is not None
    assert detail["status"] in {"resolved", "expired"}
    assert any(vehicle.vehicle_type.value == "police" for vehicle in world.vehicles.values())


def test_volatile_temperament_accelerates_conflict_pressure() -> None:
    from app.simulation.social import apply_interaction

    calm_world = World(seed=909, citizen_count=10)
    volatile_world = World(seed=909, citizen_count=10)

    calm_a, calm_b = list(calm_world.citizens.values())[:2]
    volatile_a, volatile_b = list(volatile_world.citizens.values())[:2]
    building_id = calm_a.home_id

    for citizen in (calm_a, calm_b):
        citizen.aggression = 5.0
        citizen.impulsivity = 5.0
        citizen.grudge_tendency = 5.0
    for citizen in (volatile_a, volatile_b):
        citizen.aggression = 95.0
        citizen.impulsivity = 95.0
        citizen.grudge_tendency = 90.0

    for _ in range(4):
        apply_interaction(calm_world, calm_a, calm_b, building_id, positive=False, strength=1.0, emit=False)
        apply_interaction(volatile_world, volatile_a, volatile_b, building_id, positive=False, strength=1.0, emit=False)

    calm_relation = calm_a.relationships[calm_b.id]
    volatile_relation = volatile_a.relationships[volatile_b.id]
    assert volatile_relation.conflict_score > calm_relation.conflict_score * 1.25
    assert volatile_relation.conflict_level >= calm_relation.conflict_level


def test_conflict_history_is_reciprocal_and_survives_save() -> None:
    world = World(seed=707, citizen_count=20)
    household = next(row for row in world.households.values() if len(row.member_ids) >= 2)
    a = world.citizens[household.member_ids[0]]
    b = world.citizens[household.member_ids[1]]

    incident = world.create_conflict_incident(a, b, household.home_id, 3)
    a_history = a.relationships[b.id].conflict_history
    b_history = b.relationships[a.id].conflict_history
    assert a_history[-1].incident_id == incident.id
    assert b_history[-1].incident_id == incident.id
    assert {a_history[-1].role, b_history[-1].role} == {"auteur", "victime"}

    restored = World.from_state(world.export_state())
    restored_detail = restored.get_citizen_detail(a.id)
    assert restored_detail["conflictHistory"][0]["incidentId"] == incident.id
    assert restored_detail["relationships"][0]["peakConflictLevel"] >= 0


def test_investigation_collects_evidence_arrests_and_reaches_a_hearing() -> None:
    world = World(seed=5150, citizen_count=20)
    building = next(row for row in world.buildings.values() if row.building_type.value == "shop")
    citizens = list(world.citizens.values())[:6]
    offender, victim, *witnesses = citizens
    victim.health = 72.0
    incident = world.create_incident(
        incident_type="assault",
        title="Agression documentée",
        description="Une agression est observée par plusieurs témoins.",
        severity="danger",
        citizen_ids=tuple(citizen.id for citizen in citizens),
        offender_id=offender.id,
        victim_ids=(victim.id,),
        witness_ids=tuple(citizen.id for citizen in witnesses),
        building_id=building.id,
        reported=True,
        lifetime_minutes=360,
        conflict_level=4,
    )

    investigation = world._open_investigation(incident)
    assert investigation.evidence_ids
    assert investigation.lead_suspect_id == offender.id
    assert investigation.arrest_tick is not None
    assert investigation.case_id is not None
    assert offender.detained_until_tick is not None

    case = world.judicial_cases[investigation.case_id]
    case.hearing_tick = world.tick
    world._last_justice_hour = -1
    world._advance_justice()
    assert case.status.value in {"decided", "dismissed"}
    assert case.verdict is not None
    assert investigation.status.value == "closed"


def test_conflict_pressure_keeps_full_precision_across_save() -> None:
    from app.simulation.models import Relationship

    world = World(seed=303, citizen_count=10)
    a, b = list(world.citizens.values())[:2]
    relation_a = a.relationships.setdefault(b.id, Relationship(other_id=b.id))
    relation_b = b.relationships.setdefault(a.id, Relationship(other_id=a.id))
    relation_a.conflict_score = 2.55
    relation_b.conflict_score = 2.55

    restored = World.from_state(world.export_state())
    assert restored.citizens[a.id].relationships[b.id].conflict_score == 2.55
    assert restored.export_state() == world.export_state()

def test_old_save_versions_are_explicitly_rejected() -> None:
    state = World(seed=111, citizen_count=20).export_state()
    for version in range(1, 7):
        legacy = copy.deepcopy(state)
        legacy["version"] = version
        with pytest.raises(ValueError, match="Version de sauvegarde non prise en charge"):
            World.from_state(legacy)


def test_real_work_tracks_attendance_and_salary() -> None:
    world = World(seed=120, citizen_count=100)
    worker = next(c for c in world.citizens.values() if c.workplace_id is not None and c.job_title != "Policier municipal")
    workplace = world.buildings[worker.workplace_id]
    worker.work_days = (1, 2, 3, 4, 5, 6, 7)
    world.hour = worker.work_start_hour
    world.minute = 0
    worker.x, worker.y = workplace.entrance
    worker.destination_building_id = workplace.id
    worker.activity = Activity.WORKING
    worker.planned_activity = Activity.WORKING
    worker.travel_stage = TravelStage.IDLE
    update_work_and_consumption(world)
    assert worker.minutes_worked_today == 1

    worker.minutes_worked_today = (worker.work_end_hour - worker.work_start_hour) * 60
    money_before = worker.money
    world.hour = worker.work_end_hour
    world.minute = 0
    update_work_and_consumption(world)
    assert worker.money > money_before
    assert worker.shifts_completed == 1
    assert any(event.event_type == "salary_paid" and worker.id in event.citizen_ids for event in world.events)


def test_shopping_replenishes_simple_household_reserves() -> None:
    world = World(seed=121, citizen_count=100)
    market = next(b for b in world.buildings.values() if b.building_type.value == "shop")
    employees = [c for c in world.citizens.values() if c.workplace_id == market.id][:2]
    shopper = next(c for c in world.citizens.values() if c.workplace_id != market.id)
    world.hour = 10
    world.minute = 0
    for employee in employees:
        employee.work_days = (1, 2, 3, 4, 5, 6, 7)
        employee.work_start_hour = 8
        employee.work_end_hour = 19
        employee.x, employee.y = market.entrance
        employee.destination_building_id = market.id
        employee.activity = Activity.WORKING
        employee.travel_stage = TravelStage.IDLE

    shopper.food_units = 0.0
    shopper.goods_units = 0.0
    shopper.money = 100.0
    shopper.x, shopper.y = market.entrance
    shopper.destination_building_id = market.id
    shopper.activity = Activity.SHOPPING
    shopper.travel_stage = TravelStage.IDLE
    update_work_and_consumption(world)

    assert shopper.food_units > 0
    assert shopper.goods_units > 0
    assert shopper.shopping_visits == 1
    assert world.shopping_trips_today == 1
    assert market.revenue_today > 0


def test_police_patrols_require_real_on_duty_citizens() -> None:
    world = World(seed=122, citizen_count=100)
    station = next(b for b in world.buildings.values() if b.building_type.value == "police")
    officers = [c for c in world.citizens.values() if c.workplace_id == station.id][:4]
    world.hour = 7
    world.minute = 0
    for officer in officers:
        officer.work_days = (1, 2, 3, 4, 5, 6, 7)
        officer.work_start_hour = 6
        officer.work_end_hour = 14
        officer.x, officer.y = station.entrance
        officer.destination_building_id = station.id
        officer.activity = Activity.WORKING
        officer.travel_stage = TravelStage.IDLE
    refresh_police_crews(world)
    staffed = [v for v in world.vehicles.values() if v.vehicle_type == VehicleType.POLICE and len(v.crew_ids) >= 2]
    assert staffed
    assert all(world.citizens[citizen_id].job_title == "Policier municipal" for unit in staffed for citizen_id in unit.crew_ids)


def test_police_intervention_records_a_consequence_on_the_citizen() -> None:
    world = World(seed=123, citizen_count=100)
    station = next(b for b in world.buildings.values() if b.building_type.value == "police")
    market = next(b for b in world.buildings.values() if b.building_type.value == "shop")
    offender = next(c for c in world.citizens.values() if c.workplace_id != station.id)
    officers = [c for c in world.citizens.values() if c.workplace_id == station.id][:2]
    unit = next(v for v in world.vehicles.values() if v.vehicle_type == VehicleType.POLICE)
    unit.crew_ids = {officer.id for officer in officers}
    unit.status = VehicleStatus.ON_SCENE
    incident = world.create_incident(
        incident_type="theft",
        title="Vol constaté",
        description="Les agents constatent les faits.",
        severity="danger",
        citizen_ids=(offender.id,),
        offender_id=offender.id,
        building_id=market.id,
        reported=True,
        lifetime_minutes=300,
    )
    incident.status = IncidentStatus.ON_SCENE
    world._resolve_police_incident(incident, unit)
    assert incident.police_action in {"Mise en cellule", "Garde à vue"}
    assert offender.police_history
    assert offender.police_history[-1].incident_id == incident.id
    assert offender.detained_until_tick is not None
    assert incident.detained_ids == (offender.id,)


def test_delta_snapshot_does_not_serialize_static_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    world = World(seed=321, citizen_count=30)

    def fail_if_called(*_: object) -> dict:
        raise AssertionError("A static serializer was called while building a delta")

    monkeypatch.setattr(World, "_bus_stop_to_dict", fail_if_called)
    monkeypatch.setattr(World, "_bus_line_to_dict", fail_if_called)
    delta = world.delta_snapshot()

    assert delta["type"] == "city_delta"
    assert "map" not in delta
    assert "cells" not in delta["roads"]
    assert "busStops" not in delta["transport"]
    assert "busLines" not in delta["transport"]
