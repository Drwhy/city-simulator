from __future__ import annotations

from typing import TYPE_CHECKING

from .models import (
    Activity,
    Building,
    BuildingType,
    CareStatus,
    Citizen,
    HealthCase,
    HealthCondition,
    MedicalRecord,
    Vehicle,
    VehicleStatus,
    VehicleType,
)
from .transport import road_path
from .work import is_on_duty

if TYPE_CHECKING:
    from .world import World

ACTIVE_CARE = {
    CareStatus.WAITING_AMBULANCE,
    CareStatus.AMBULANCE_DISPATCHED,
    CareStatus.IN_AMBULANCE,
    CareStatus.WAITING_CONSULTATION,
    CareStatus.IN_CONSULTATION,
    CareStatus.HOSPITALIZED,
}


def hospital(world: World) -> Building | None:
    return next((row for row in world.buildings.values() if row.building_type == BuildingType.HOSPITAL), None)


def initialize_health(world: World) -> None:
    world.health_cases = {}
    world._next_health_case_id = 1
    world._last_health_hour = -1
    world.medical_cases_today = 0
    world.ambulance_dispatches_today = 0
    world.medical_wait_minutes_today = 0


def _record(citizen: Citizen, world: World, event_type: str, label: str, severity: float, source: str,
            *, incident_id: int | None = None, hospital_id: int | None = None,
            incapacity_minutes: int = 0) -> None:
    citizen.health_history.append(MedicalRecord(
        tick=world.tick,
        event_type=event_type,
        label=label,
        severity=round(severity, 1),
        source=source,
        incident_id=incident_id,
        hospital_id=hospital_id,
        incapacity_minutes=incapacity_minutes,
    ))
    citizen.health_history[:] = citizen.health_history[-40:]


def requires_medical_exam(citizen: Citizen) -> bool:
    return (
        citizen.health_condition in {HealthCondition.SERIOUS_INJURY, HealthCondition.SEVERE_ILLNESS}
        or citizen.pain >= 55
        or citizen.care_status in ACTIVE_CARE
    )


def create_health_case(world: World, citizen: Citizen, *, source: str, severity: float,
                       incident_id: int | None = None, transport_required: bool | None = None) -> HealthCase:
    active = world.health_cases.get(citizen.active_health_case_id or -1)
    if active is not None and active.status in ACTIVE_CARE:
        active.severity = max(active.severity, severity)
        if incident_id is not None:
            active.incident_id = incident_id
        return active
    medical_center = hospital(world)
    needs_ambulance = severity >= 55 if transport_required is None else transport_required
    status = CareStatus.WAITING_AMBULANCE if needs_ambulance else CareStatus.WAITING_CONSULTATION
    case = HealthCase(
        id=world._next_health_case_id,
        citizen_id=citizen.id,
        source=source,
        severity=max(1.0, min(100.0, severity)),
        created_tick=world.tick,
        status=status,
        hospital_id=medical_center.id if medical_center else None,
        incident_id=incident_id,
        transport_required=needs_ambulance,
    )
    world._next_health_case_id += 1
    world.health_cases[case.id] = case
    citizen.active_health_case_id = case.id
    citizen.care_status = status
    if incident_id is not None and incident_id in world.incidents:
        incident = world.incidents[incident_id]
        incident.health_case_ids = tuple(dict.fromkeys((*incident.health_case_ids, case.id)))
    if not needs_ambulance:
        admit_to_queue(world, case, private_transport=True)
    world.medical_cases_today += 1
    return case


def apply_injury(world: World, citizen: Citizen, severity: float, *, source: str,
                 incident_id: int | None = None) -> HealthCase:
    severity = max(1.0, min(100.0, severity))
    damage = 3.0 + severity * 0.34
    citizen.health = max(1.0, citizen.health - damage)
    citizen.injury_severity = max(citizen.injury_severity, severity)
    citizen.pain = min(100.0, max(citizen.pain, severity * 0.9))
    citizen.health_condition = HealthCondition.SERIOUS_INJURY if severity >= 50 else HealthCondition.MINOR_INJURY
    incapacity = int(120 + severity * 18)
    citizen.incapacity_until_tick = max(citizen.incapacity_until_tick or 0, world.tick + incapacity)
    citizen.medical_leave_until_tick = max(citizen.medical_leave_until_tick or 0, world.tick + incapacity)
    _record(citizen, world, "injury", "Blessure nécessitant une prise en charge", severity, source,
            incident_id=incident_id, incapacity_minutes=incapacity)
    case = create_health_case(world, citizen, source=source, severity=severity, incident_id=incident_id)
    world._emit(
        "medical_emergency" if severity >= 55 else "medical_case",
        f"{citizen.full_name} est blessé ({source}) et doit être pris en charge.",
        citizen_ids=(citizen.id,), building_id=case.hospital_id, severity="danger" if severity >= 55 else "warning",
        incident_id=incident_id,
    )
    if severity >= 55 and citizen.detained_until_tick is not None:
        citizen.detained_until_tick = None
        citizen.current_detention_type = None
    return case


def apply_illness(world: World, citizen: Citizen, severity: float, *, source: str = "illness") -> HealthCase:
    severity = max(5.0, min(100.0, severity))
    citizen.illness_severity = max(citizen.illness_severity, severity)
    citizen.health = max(1.0, citizen.health - severity * 0.18)
    citizen.pain = max(citizen.pain, severity * 0.35)
    citizen.health_condition = HealthCondition.SEVERE_ILLNESS if severity >= 65 else HealthCondition.MILD_ILLNESS
    incapacity = int(180 + severity * 22)
    citizen.incapacity_until_tick = max(citizen.incapacity_until_tick or 0, world.tick + incapacity)
    citizen.medical_leave_until_tick = max(citizen.medical_leave_until_tick or 0, world.tick + incapacity)
    _record(citizen, world, "illness", "Épisode de maladie", severity, source, incapacity_minutes=incapacity)
    return create_health_case(world, citizen, source=source, severity=severity)


def _medical_staff(world: World) -> list[Citizen]:
    center = hospital(world)
    if center is None:
        return []
    return sorted(
        (citizen for citizen in world.citizens.values()
         if citizen.workplace_id == center.id and is_on_duty(world, citizen)),
        key=lambda citizen: citizen.id,
    )


def _available_ambulance(world: World) -> Vehicle | None:
    return next((vehicle for vehicle in world.vehicles.values()
                 if vehicle.vehicle_type == VehicleType.AMBULANCE
                 and vehicle.status == VehicleStatus.PARKED
                 and vehicle.health_case_id is None), None)


def dispatch_ambulances(world: World) -> None:
    center = hospital(world)
    if center is None:
        return
    waiting = sorted(
        (case for case in world.health_cases.values() if case.status == CareStatus.WAITING_AMBULANCE),
        key=lambda case: (-case.severity, case.created_tick, case.id),
    )
    for case in waiting:
        staff = [person for person in _medical_staff(world)
                 if person.active_vehicle_id is None and person.care_status not in ACTIVE_CARE]
        ambulance = _available_ambulance(world)
        if ambulance is None or len(staff) < 2:
            if world.tick - case.created_tick >= 120:
                admit_to_queue(world, case, private_transport=True)
            continue
        crew = staff[:2]
        ambulance.crew_ids = {person.id for person in crew}
        ambulance.health_case_id = case.id
        ambulance.status = VehicleStatus.RESPONDING
        ambulance.current_building_id = None
        patient = world.citizens[case.citizen_id]
        ambulance.route = road_path((ambulance.x, ambulance.y), (patient.x, patient.y), world.road_cells)
        ambulance.route_index = 0
        ambulance.target_building_id = None
        ambulance.service_started_tick = world.tick
        case.ambulance_id = ambulance.id
        case.status = CareStatus.AMBULANCE_DISPATCHED
        patient.care_status = case.status
        for person in crew:
            world._cancel_active_trip(person)
            world._remove_from_all_buildings(person.id)
            person.active_vehicle_id = ambulance.id
            person.activity = Activity.DRIVING
        world.ambulance_dispatches_today += 1
        world._emit("ambulance_dispatched", f"L’ambulance #{ambulance.id} part pour {patient.full_name}.",
                    citizen_ids=(patient.id, *(person.id for person in crew)), vehicle_id=ambulance.id,
                    severity="danger", incident_id=case.incident_id)


def _advance_vehicle(world: World, ambulance: Vehicle) -> bool:
    if ambulance.route_index >= len(ambulance.route):
        return True
    for _ in range(world.CAR_SPEED):
        if ambulance.route_index >= len(ambulance.route):
            break
        ambulance.x, ambulance.y = ambulance.route[ambulance.route_index]
        ambulance.route_index += 1
        ambulance.distance_today += 1
    for citizen_id in (*ambulance.crew_ids, *ambulance.passenger_ids):
        citizen = world.citizens.get(citizen_id)
        if citizen:
            citizen.x, citizen.y = ambulance.x, ambulance.y
    return ambulance.route_index >= len(ambulance.route)


def move_ambulances(world: World) -> None:
    center = hospital(world)
    if center is None:
        return
    for ambulance in (v for v in world.vehicles.values() if v.vehicle_type == VehicleType.AMBULANCE):
        case = world.health_cases.get(ambulance.health_case_id or -1)
        if case is None:
            continue
        if ambulance.status == VehicleStatus.RESPONDING and _advance_vehicle(world, ambulance):
            patient = world.citizens[case.citizen_id]
            ambulance.passenger_ids.add(patient.id)
            patient.active_vehicle_id = ambulance.id
            patient.care_status = CareStatus.IN_AMBULANCE
            patient.activity = Activity.IN_TREATMENT
            case.status = CareStatus.IN_AMBULANCE
            ambulance.status = VehicleStatus.TRANSPORTING
            ambulance.route = road_path((ambulance.x, ambulance.y), center.entrance, world.road_cells)
            ambulance.route_index = 0
            ambulance.target_building_id = center.id
        elif ambulance.status == VehicleStatus.TRANSPORTING and _advance_vehicle(world, ambulance):
            ambulance.passenger_ids.discard(case.citizen_id)
            world.citizens[case.citizen_id].active_vehicle_id = None
            admit_to_queue(world, case)
            ambulance.status = VehicleStatus.RETURNING
            ambulance.route = []
            ambulance.route_index = 0
            ambulance.x, ambulance.y = center.entrance
            ambulance.current_building_id = center.id
            ambulance.target_building_id = center.id
        elif ambulance.status == VehicleStatus.RETURNING:
            for crew_id in list(ambulance.crew_ids):
                crew = world.citizens.get(crew_id)
                if crew:
                    crew.active_vehicle_id = None
                    crew.x, crew.y = center.entrance
                    center.occupants.add(crew.id)
                    crew.activity = Activity.WORKING if is_on_duty(world, crew) else Activity.AT_HOME
            ambulance.crew_ids.clear()
            ambulance.health_case_id = None
            ambulance.status = VehicleStatus.PARKED


def admit_to_queue(world: World, case: HealthCase, *, private_transport: bool = False) -> None:
    center = hospital(world)
    patient = world.citizens[case.citizen_id]
    if center is None:
        case.status = CareStatus.RECOVERING
        patient.care_status = CareStatus.RECOVERING
        return
    world._cancel_active_trip(patient)
    world._remove_from_all_buildings(patient.id)
    patient.x, patient.y = center.entrance
    center.occupants.add(patient.id)
    if case.id not in center.medical_queue:
        center.medical_queue.append(case.id)
    case.status = CareStatus.WAITING_CONSULTATION
    case.queued_tick = world.tick
    case.hospital_id = center.id
    patient.care_status = case.status
    patient.activity = Activity.WAITING_MEDICAL
    if private_transport:
        world._emit("medical_transport", f"{patient.full_name} rejoint le centre médical par transport non urgent.",
                    citizen_ids=(patient.id,), building_id=center.id, severity="info", incident_id=case.incident_id)


def _add_medical_evidence(world: World, case: HealthCase, patient: Citizen) -> None:
    if case.medical_report_created or case.incident_id is None:
        return
    incident = world.incidents.get(case.incident_id)
    if incident is None or incident.investigation_id is None:
        return
    investigation = world.investigations.get(incident.investigation_id)
    if investigation is None:
        return
    world._add_evidence(investigation, "medical_report",
                        f"Certificat médical documentant les blessures de {patient.full_name}.",
                        min(0.98, 0.78 + case.severity / 500), citizen_id=patient.id)
    investigation.confidence = world._investigation_confidence(investigation)
    case.medical_report_created = True


def update_hospital(world: World) -> None:
    center = hospital(world)
    if center is None:
        return
    staff = _medical_staff(world)
    queue = [case_id for case_id in center.medical_queue if case_id in world.health_cases]
    center.medical_queue[:] = queue
    center.medical_wait_minutes_today += len(queue)
    world.medical_wait_minutes_today += len(queue)
    interval = max(5, 35 - len(staff) * 5)
    if staff and world.tick % interval == 0:
        starts = max(1, len(staff) // 2)
        for case_id in list(center.medical_queue[:starts]):
            case = world.health_cases[case_id]
            patient = world.citizens[case.citizen_id]
            center.medical_queue.remove(case_id)
            case.status = CareStatus.IN_CONSULTATION
            case.consultation_started_tick = world.tick
            patient.care_status = case.status
            patient.activity = Activity.IN_TREATMENT
            _record(patient, world, "consultation", "Consultation médicale", case.severity, case.source,
                    incident_id=case.incident_id, hospital_id=center.id)
            _add_medical_evidence(world, case, patient)
    for case in list(world.health_cases.values()):
        if case.status != CareStatus.IN_CONSULTATION or case.consultation_started_tick is None:
            continue
        duration = 15 + int(case.severity / 4)
        if world.tick - case.consultation_started_tick < duration:
            continue
        patient = world.citizens[case.citizen_id]
        if case.severity >= 65 and len(center.hospitalized_ids) < center.medical_beds:
            case.status = CareStatus.HOSPITALIZED
            patient.care_status = case.status
            patient.health_condition = HealthCondition.RECOVERING
            patient.activity = Activity.HOSPITALIZED
            patient.hospitalized_until_tick = world.tick + int(180 + case.severity * 8)
            center.hospitalized_ids.add(patient.id)
        else:
            complete_case(world, case)
        center.patients_treated_today += 1
    for patient_id in list(center.hospitalized_ids):
        patient = world.citizens.get(patient_id)
        case = world.health_cases.get(patient.active_health_case_id or -1) if patient else None
        if patient is None or case is None or world.tick >= (patient.hospitalized_until_tick or world.tick):
            center.hospitalized_ids.discard(patient_id)
            if case:
                complete_case(world, case)


def complete_case(world: World, case: HealthCase) -> None:
    patient = world.citizens[case.citizen_id]
    center = hospital(world)
    if center:
        if case.id in center.medical_queue:
            center.medical_queue.remove(case.id)
        center.hospitalized_ids.discard(patient.id)
        center.occupants.discard(patient.id)
    case.status = CareStatus.RECOVERING
    case.completed_tick = world.tick
    patient.care_status = CareStatus.RECOVERING
    patient.health_condition = HealthCondition.RECOVERING
    patient.hospitalized_until_tick = None
    patient.injury_severity *= 0.45
    patient.illness_severity *= 0.4
    patient.pain *= 0.45
    patient.health = min(100.0, patient.health + 12.0)
    patient.active_health_case_id = None
    home = world.buildings[patient.home_id]
    patient.x, patient.y = home.entrance
    home.occupants.add(patient.id)
    patient.activity = Activity.AT_HOME
    _record(patient, world, "discharge", "Retour à domicile après soins", case.severity, case.source,
            incident_id=case.incident_id, hospital_id=case.hospital_id)
    world._emit("medical_discharge", f"{patient.full_name} quitte le centre médical et poursuit sa convalescence.",
                citizen_ids=(patient.id,), building_id=case.hospital_id, severity="info", incident_id=case.incident_id)


def _ambient_health_events(world: World) -> None:
    hour_key = world.day * 24 + world.hour
    if world.minute != 0 or world._last_health_hour == hour_key:
        return
    world._last_health_hour = hour_key
    candidates = [c for c in world.citizens.values() if c.care_status in {CareStatus.NONE, CareStatus.RECOVERING}]
    if not candidates:
        return
    moving_cars = [vehicle for vehicle in world.vehicles.values() if vehicle.vehicle_type == VehicleType.CAR and vehicle.status == VehicleStatus.DRIVING and vehicle.passenger_ids]
    if moving_cars and world.health_rng.random() < min(0.04, len(moving_cars) * 0.002):
        vehicle = world.health_rng.choice(moving_cars)
        patient_id = next(iter(vehicle.passenger_ids))
        patient = world.citizens[patient_id]
        severity = world.health_rng.uniform(35, 82)
        incident = world.create_incident(
            incident_type="traffic_accident", title="Accident de circulation",
            description=f"{patient.full_name} est blessé dans un accident de circulation.", severity="danger",
            citizen_ids=(patient.id,), victim_ids=(patient.id,), vehicle_id=vehicle.id,
            reported=True, lifetime_minutes=360,
        )
        apply_injury(world, patient, severity, source="accident de circulation", incident_id=incident.id)

    citizen = world.health_rng.choice(candidates)
    risk = 0.006 + max(0, citizen.age - 50) * 0.00025
    risk += max(0, citizen.needs.fatigue - 75) * 0.0007
    risk += max(0, citizen.needs.hunger - 75) * 0.0005
    risk += citizen.intoxication * 0.00012
    if world.health_rng.random() < min(0.12, risk):
        severity = world.health_rng.uniform(18, 42)
        if world.health_rng.random() < 0.035:
            severity = world.health_rng.uniform(66, 82)
        apply_illness(world, citizen, severity, source="fatigue, nutrition ou maladie")
        world._emit("illness", f"{citizen.full_name} tombe malade.", citizen_ids=(citizen.id,),
                    severity="danger" if severity >= 65 else "warning")


def update_recovery(world: World) -> None:
    if world.tick % 10:
        return
    for citizen in world.citizens.values():
        if citizen.care_status != CareStatus.RECOVERING:
            continue
        citizen.health = min(100.0, citizen.health + 0.8)
        citizen.pain = max(0.0, citizen.pain - 1.2)
        citizen.injury_severity = max(0.0, citizen.injury_severity - 0.8)
        citizen.illness_severity = max(0.0, citizen.illness_severity - 0.8)
        if citizen.health >= 96 and citizen.pain <= 4 and citizen.injury_severity <= 4 and citizen.illness_severity <= 4:
            citizen.health_condition = HealthCondition.HEALTHY
            citizen.care_status = CareStatus.NONE
            citizen.medical_leave_until_tick = None
            citizen.incapacity_until_tick = None


def update_health(world: World) -> None:
    _ambient_health_events(world)
    dispatch_ambulances(world)
    move_ambulances(world)
    update_hospital(world)
    update_recovery(world)


def health_metrics(world: World) -> dict[str, int | float]:
    center = hospital(world)
    active = [case for case in world.health_cases.values() if case.status in ACTIVE_CARE]
    completed_waits = [case.consultation_started_tick - case.queued_tick for case in world.health_cases.values()
                       if case.consultation_started_tick is not None and case.queued_tick is not None]
    ambulances = [v for v in world.vehicles.values() if v.vehicle_type == VehicleType.AMBULANCE]
    return {
        "activeMedicalCases": len(active),
        "medicalEmergencies": sum(1 for case in active if case.severity >= 55),
        "patientsWaiting": len(center.medical_queue) if center else 0,
        "hospitalizedPatients": len(center.hospitalized_ids) if center else 0,
        "hospitalBeds": center.medical_beds if center else 0,
        "medicalStaffOnDuty": len(_medical_staff(world)),
        "ambulancesAvailable": sum(1 for v in ambulances if v.status == VehicleStatus.PARKED),
        "ambulanceDispatchesToday": world.ambulance_dispatches_today,
        "averageMedicalWaitMinutes": round(sum(completed_waits) / max(1, len(completed_waits)), 1),
    }


def case_summary(world: World, case: HealthCase) -> dict[str, object]:
    patient = world.citizens[case.citizen_id]
    return {
        "id": case.id,
        "citizen": {"id": patient.id, "name": patient.full_name},
        "source": case.source,
        "severity": round(case.severity, 1),
        "status": case.status.value,
        "hospitalId": case.hospital_id,
        "ambulanceId": case.ambulance_id,
        "incidentId": case.incident_id,
        "createdTick": case.created_tick,
        "waitingMinutes": max(0, world.tick - (case.queued_tick or world.tick)) if case.status == CareStatus.WAITING_CONSULTATION else 0,
    }


def health_overview(world: World) -> dict[str, object]:
    center = hospital(world)
    return {
        "tick": world.tick,
        "metrics": health_metrics(world),
        "hospital": {"id": center.id, "name": center.name} if center else None,
        "cases": [case_summary(world, case) for case in world.health_cases.values() if case.status in ACTIVE_CARE],
    }