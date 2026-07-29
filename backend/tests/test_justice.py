from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app, service
from app.simulation.justice import (
    _hold_hearing,
    build_case,
    contact_forbidden,
)
from app.simulation.models import (
    Activity,
    BuildingType,
    JudicialCaseStatus,
    SentenceStatus,
    SentenceType,
    TravelStage,
)
from app.simulation.persistence import SAVE_VERSION
from app.simulation.world import World


def documented_incident(world: World, incident_type: str = "assault"):
    citizens = list(world.citizens.values())[:6]
    offender, victim, *witnesses = citizens
    incident = world.create_incident(
        incident_type=incident_type,
        title="Faits documentés",
        description="Un incident utilisé pour valider la chaîne judiciaire.",
        severity="danger",
        citizen_ids=tuple(citizen.id for citizen in citizens),
        offender_id=offender.id,
        victim_ids=(victim.id,),
        witness_ids=tuple(citizen.id for citizen in witnesses),
        building_id=next(iter(world.buildings)),
        reported=True,
        lifetime_minutes=360,
        conflict_level=5,
    )
    investigation = world._open_investigation(incident)
    return offender, victim, incident, investigation


def test_institutional_staff_are_citizens() -> None:
    world = World(seed=1001, citizen_count=100)
    court = world._first_building(BuildingType.COURT)
    detention = world._first_building(BuildingType.DETENTION_CENTER)

    assert court is not None and detention is not None
    court_staff = [citizen for citizen in world.citizens.values() if citizen.workplace_id == court.id]
    detention_staff = [citizen for citizen in world.citizens.values() if citizen.workplace_id == detention.id]
    assert {citizen.job_title for citizen in court_staff} >= {"Juge", "Greffier"}
    assert detention_staff and all(citizen.job_title == "Surveillant" for citizen in detention_staff)


def test_insufficient_investigation_is_dismissed_with_explicit_complaint_state() -> None:
    world = World(seed=1002, citizen_count=20)
    offender, victim = list(world.citizens.values())[:2]
    incident = world.create_incident(
        incident_type="theft",
        title="Signalement incertain",
        description="Aucun témoin ni élément matériel exploitable.",
        severity="warning",
        citizen_ids=(offender.id, victim.id),
        offender_id=offender.id,
        victim_ids=(victim.id,),
        witness_ids=(),
        building_id=offender.home_id,
        reported=True,
        conflict_level=1,
    )
    investigation = world._open_investigation(incident)
    investigation.confidence = 0
    investigation.updated_tick = 0
    world.tick = 6 * 24 * 60
    world._last_justice_hour = -1
    world._advance_justice()

    assert investigation.status.value == "closed"
    complaint = world.complaints[investigation.complaint_id]
    assert complaint.status.value == "dismissed"
    assert complaint.dismissal_reason


def test_court_capacity_delays_excess_hearings() -> None:
    world = World(seed=1003, citizen_count=100)
    court = world._first_building(BuildingType.COURT)
    assert court is not None
    world.hour, world.minute, world.tick = 10, 0, 4 * 24 * 60 + 10 * 60
    for citizen in world.citizens.values():
        if citizen.workplace_id == court.id:
            citizen.activity = Activity.WORKING
            citizen.destination_building_id = court.id
            citizen.x, citizen.y = court.entrance
            citizen.travel_stage = TravelStage.IDLE

    cases = []
    for index in range(4):
        offender, _, incident, investigation = documented_incident(world)
        if investigation.case_id is None:
            investigation.confidence = 100
            case = build_case(world, investigation, incident, offender)
            world.judicial_cases[case.id] = case
        else:
            case = world.judicial_cases[investigation.case_id]
        case.evidence_score = 100
        case.prosecutor_decision = "poursuites"
        case.hearing_tick = world.tick + index
        cases.append(case)
    for case in cases:
        case.filed_tick = world.tick - 1
        case.hearing_tick = world.tick
    world._last_justice_hour = -1
    world._advance_justice()

    decided = [case for case in cases if case.status == JudicialCaseStatus.DECIDED]
    delayed = [case for case in cases if case.status == JudicialCaseStatus.AWAITING_HEARING]
    assert len(decided) == 3
    assert len(delayed) == 1 and delayed[0].delay_count == 1


def test_sentence_changes_life_and_contact_order_blocks_interaction() -> None:
    world = World(seed=1004, citizen_count=20)
    offender, victim, incident, investigation = documented_incident(world, "assault")
    case = world.judicial_cases[investigation.case_id]
    case.evidence_score = 100
    case.prosecutor_decision = "poursuites"
    _hold_hearing(world, case)

    sentences = [world.sentences[sentence_id] for sentence_id in case.sentence_ids]
    assert {sentence.sentence_type for sentence in sentences} >= {
        SentenceType.COMMUNITY_SERVICE,
        SentenceType.PROBATION,
        SentenceType.RESTRAINING_ORDER,
    }
    assert contact_forbidden(world, offender.id, victim.id)
    relation_before = offender.relationships.get(victim.id)
    familiarity_before = relation_before.familiarity if relation_before else 0
    from app.simulation.social import apply_interaction
    apply_interaction(world, offender, victim, incident.building_id, positive=True)
    relation_after = offender.relationships.get(victim.id)
    assert (relation_after.familiarity if relation_after else 0) == familiarity_before

    offender.detained_until_tick = None
    offender.current_detention_type = None
    offender.needs.fatigue = offender.needs.hunger = offender.needs.social = 0
    world.hour = 20
    world.buildings[offender.home_id].occupants.add(victim.id)
    world._plan_activities()
    park = world._first_building(BuildingType.PARK)
    assert park is not None and offender.destination_building_id == park.id
    assert "interdiction de contact" in offender.last_decision_reason


def test_long_detention_interrupts_work_but_preserves_household() -> None:
    world = World(seed=1005, citizen_count=30)
    offender, _, _, investigation = documented_incident(world, "serious_assault")
    previous_household = offender.household_id
    assert offender.workplace_id is not None
    case = world.judicial_cases[investigation.case_id]
    case.evidence_score = 100
    case.prosecutor_decision = "poursuites"
    _hold_hearing(world, case)

    assert offender.current_detention_type == "judicial_detention"
    assert offender.workplace_id is None
    assert offender.household_id == previous_household
    assert any(world.sentences[sid].sentence_type == SentenceType.LONG_DETENTION for sid in case.sentence_ids)


def test_criminal_record_reduces_access_to_sensitive_jobs() -> None:
    from app.simulation.economy import _application_score

    world = World(seed=1009, citizen_count=100)
    citizen = next(row for row in world.citizens.values() if row.workplace_id is not None)
    court = world._first_building(BuildingType.COURT)
    assert court is not None
    rng_state = world.rng.getstate()
    clean_score = _application_score(world, citizen, court)
    world.rng.setstate(rng_state)
    citizen.criminal_record_count = 2
    citizen.probation_violations = 1
    recorded_score = _application_score(world, citizen, court)
    assert recorded_score <= clean_score - 19.0


def test_v10_save_round_trip_preserves_active_sentences() -> None:
    world = World(seed=1006, citizen_count=20)
    _, _, _, investigation = documented_incident(world, "assault")
    case = world.judicial_cases[investigation.case_id]
    case.evidence_score = 100
    case.prosecutor_decision = "poursuites"
    _hold_hearing(world, case)

    restored = World.from_state(world.export_state())
    assert restored.export_state()["version"] == SAVE_VERSION
    assert restored.complaints.keys() == world.complaints.keys()
    assert restored.sentences.keys() == world.sentences.keys()
    assert restored.export_state() == world.export_state()


def test_justice_api_and_websocket_domain(tmp_path) -> None:
    service.save_path = tmp_path / "city_snapshot.json"
    with TestClient(app) as client:
        client.post("/api/city/reset", json={"seed": 1007})
        overview = client.get("/api/justice")
        assert overview.status_code == 200
        assert overview.json()["court"]["type"] == "court"
        assert overview.json()["detentionCenter"]["type"] == "detention_center"
        with client.websocket_connect("/ws/city") as socket:
            payload = socket.receive_json()
            assert payload["type"] == "city_snapshot"
            assert payload["justice"]["metrics"]["courtCapacityToday"] == 3


def test_thirty_days_leave_no_case_or_sentence_in_transient_state() -> None:
    world = World(seed=1008, citizen_count=20)
    world.run_minutes(30 * 24 * 60)

    assert all(case.status != JudicialCaseStatus.IN_HEARING for case in world.judicial_cases.values())
    assert all(
        sentence.end_tick is None
        or sentence.status in {SentenceStatus.COMPLETED, SentenceStatus.VIOLATED}
        or sentence.end_tick > world.tick
        for sentence in world.sentences.values()
    )
    assert all(
        citizen.detained_until_tick is None
        or citizen.detained_until_tick > world.tick
        for citizen in world.citizens.values()
    )