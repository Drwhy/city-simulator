from app.simulation.health import (
    admit_to_queue,
    apply_injury,
    dispatch_ambulances,
    move_ambulances,
    update_hospital,
)
from app.simulation.models import (
    Activity,
    BuildingType,
    CareStatus,
    HealthCondition,
    TravelStage,
    VehicleStatus,
    VehicleType,
)
from app.simulation.persistence import SAVE_VERSION
from app.simulation.world import World


def _put_medical_staff_on_duty(world: World, count: int = 4) -> list[int]:
    center = world._first_building(BuildingType.HOSPITAL)
    assert center is not None
    world.hour = 8
    world.minute = 0
    workers = [citizen for citizen in world.citizens.values() if citizen.workplace_id == center.id]
    active = [worker for worker in workers if worker.work_start_hour <= 8 < worker.work_end_hour][:count]
    for worker in workers:
        worker.destination_building_id = center.id if worker in active else worker.home_id
        worker.x, worker.y = center.entrance if worker in active else world.buildings[worker.home_id].entrance
        worker.travel_stage = TravelStage.IDLE
        worker.activity = Activity.WORKING if worker in active else Activity.AT_HOME
    return [worker.id for worker in active]


def test_fight_creates_injury_and_medical_leave() -> None:
    world = World(seed=31, citizen_count=100)
    building = world._first_building(BuildingType.CAFE)
    assert building is not None
    victim, offender = world.citizens[20], world.citizens[21]
    incident = world.create_conflict_incident(victim, offender, building.id, 4)
    injured = world.citizens[incident.victim_ids[0]]

    assert injured.health_condition == HealthCondition.SERIOUS_INJURY
    assert injured.active_health_case_id is not None
    assert injured.medical_leave_until_tick is not None
    assert injured.medical_leave_until_tick > world.tick
    assert incident.health_case_ids


def test_ambulance_requires_real_citizen_crew_and_transports_patient() -> None:
    world = World(seed=32, citizen_count=100)
    patient = world.citizens[30]
    case = apply_injury(world, patient, 78, source="accident de circulation")

    world.hour = 23
    dispatch_ambulances(world)
    assert case.status == CareStatus.WAITING_AMBULANCE

    staff_ids = set(_put_medical_staff_on_duty(world, 4))
    dispatch_ambulances(world)
    ambulance = next(vehicle for vehicle in world.vehicles.values() if vehicle.health_case_id == case.id)
    assert ambulance.vehicle_type == VehicleType.AMBULANCE
    assert len(ambulance.crew_ids) == 2
    assert ambulance.crew_ids <= staff_ids
    assert ambulance.status == VehicleStatus.RESPONDING

    start = (ambulance.x, ambulance.y)
    for _ in range(120):
        move_ambulances(world)
        if case.status in {CareStatus.WAITING_CONSULTATION, CareStatus.IN_CONSULTATION, CareStatus.HOSPITALIZED}:
            break
    assert ambulance.distance_today > 0
    assert case.status == CareStatus.WAITING_CONSULTATION
    assert patient.active_vehicle_id is None
    center = world._first_building(BuildingType.HOSPITAL)
    assert center is not None and (patient.x, patient.y) == center.entrance


def test_understaffed_hospital_has_longer_queue_delay() -> None:
    staffed = World(seed=33, citizen_count=100)
    understaffed = World(seed=33, citizen_count=100)
    _put_medical_staff_on_duty(staffed, 4)
    _put_medical_staff_on_duty(understaffed, 1)
    staffed_case = apply_injury(staffed, staffed.citizens[30], 25, source="chute")
    understaffed_case = apply_injury(understaffed, understaffed.citizens[30], 25, source="chute")

    staffed.tick = understaffed.tick = 15
    update_hospital(staffed)
    update_hospital(understaffed)

    assert staffed_case.status == CareStatus.IN_CONSULTATION
    assert understaffed_case.status == CareStatus.WAITING_CONSULTATION


def test_consultation_adds_medical_evidence_and_strengthens_investigation() -> None:
    world = World(seed=34, citizen_count=100)
    _put_medical_staff_on_duty(world, 4)
    building = world._first_building(BuildingType.CAFE)
    assert building is not None
    incident = world.create_conflict_incident(world.citizens[30], world.citizens[31], building.id, 4)
    investigation = world._open_investigation(incident)
    initial_confidence = investigation.confidence
    case = world.health_cases[incident.health_case_ids[0]]
    admit_to_queue(world, case)
    world.tick = 15
    update_hospital(world)

    medical_evidence = [world.evidence[evidence_id] for evidence_id in investigation.evidence_ids if world.evidence[evidence_id].evidence_type == "medical_report"]
    assert medical_evidence
    assert case.medical_report_created is True
    assert investigation.confidence > initial_confidence


def test_health_state_round_trip_preserves_active_patient() -> None:
    world = World(seed=35, citizen_count=100)
    case = apply_injury(world, world.citizens[30], 72, source="agression")
    restored = World.from_state(world.export_state())

    assert restored.export_state()["version"] == SAVE_VERSION
    assert restored.health_cases[case.id].severity == case.severity
    assert restored.citizens[30].care_status == CareStatus.WAITING_AMBULANCE
    assert restored.citizens[30].health_history[0].source == "agression"

def test_no_patient_stays_stuck_in_transport_or_queue() -> None:
    world = World(seed=36, citizen_count=100)
    world.hour = 23
    apply_injury(world, world.citizens[30], 82, source="urgence nocturne")
    world.run_minutes(2 * 24 * 60)

    blocked = [
        case for case in world.health_cases.values()
        if case.status in {
            CareStatus.WAITING_AMBULANCE,
            CareStatus.AMBULANCE_DISPATCHED,
            CareStatus.IN_AMBULANCE,
            CareStatus.WAITING_CONSULTATION,
            CareStatus.IN_CONSULTATION,
        } and world.tick - case.created_tick > 12 * 60
    ]
    assert blocked == []
