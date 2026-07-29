from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .banking import deposit, withdraw
from .economy import terminate_employment
from .models import (
    Activity,
    BuildingType,
    Complaint,
    ComplaintStatus,
    InvestigationStatus,
    JudicialCase,
    JudicialCaseStatus,
    JudicialSentence,
    JudicialTimelineEntry,
    SentenceStatus,
    SentenceType,
    TravelStage,
)
from .work import building_operational, staff_count, weekday

if TYPE_CHECKING:
    from .models import Citizen, Incident, Investigation
    from .world import World

COURT_DAILY_CAPACITY = 3
MAX_JUSTICE_HISTORY = 80


def initialize_justice(world: World) -> None:
    world.complaints: dict[int, Complaint] = {}
    world.sentences: dict[int, JudicialSentence] = {}
    world._next_complaint_id = 1
    world._next_sentence_id = 1
    world.hearings_today = 0
    world.cases_dismissed_today = 0
    world.sentences_started_today = 0
    world.probation_violations_today = 0


def reset_justice_day(world: World) -> None:
    world.hearings_today = 0
    world.cases_dismissed_today = 0
    world.sentences_started_today = 0
    world.probation_violations_today = 0


def file_complaint(world: World, incident: Incident) -> Complaint:
    if incident.complaint_id is not None and incident.complaint_id in world.complaints:
        return world.complaints[incident.complaint_id]
    complaint = Complaint(
        id=world._next_complaint_id,
        incident_id=incident.id,
        complainant_id=incident.victim_ids[0] if incident.victim_ids else None,
        accused_id=incident.offender_id,
        status=ComplaintStatus.FILED,
        filed_tick=world.tick,
        updated_tick=world.tick,
        description=f"Plainte relative à l’incident « {incident.title} ».",
    )
    world._next_complaint_id += 1
    world.complaints[complaint.id] = complaint
    incident.complaint_id = complaint.id
    _check_probation_violation(world, incident.offender_id, incident.id)
    world._emit(
        "complaint_filed",
        f"La plainte #{complaint.id} est déposée après l’incident « {incident.title} ».",
        citizen_ids=incident.citizen_ids,
        building_id=incident.building_id,
        severity="warning",
        incident_id=incident.id,
    )
    return complaint


def link_investigation(world: World, investigation: Investigation, incident: Incident) -> None:
    complaint = file_complaint(world, incident)
    investigation.complaint_id = complaint.id
    complaint.status = ComplaintStatus.INVESTIGATING
    complaint.updated_tick = world.tick


def build_case(world: World, investigation: Investigation, incident: Incident, defendant: Citizen) -> JudicialCase:
    priority = 3 if incident.incident_type in {"serious_assault", "robbery", "kidnapping"} else 2 if incident.severity == "danger" else 1
    case = JudicialCase(
        id=world._next_case_id,
        investigation_id=investigation.id,
        incident_id=incident.id,
        defendant_id=defendant.id,
        charges=world._charges_for_incident(incident),
        status=JudicialCaseStatus.AWAITING_HEARING,
        filed_tick=world.tick,
        hearing_tick=_next_hearing_tick(world, priority),
        evidence_score=investigation.confidence,
        complaint_id=investigation.complaint_id,
        prosecutor_review_tick=world.tick + 6 * 60,
        priority=priority,
        timeline=[
            JudicialTimelineEntry(
                tick=world.tick,
                event_type="case_filed",
                label="Saisine du parquet",
                detail="Le dossier est transmis au parquet pour examen des charges.",
            )
        ],
    )
    world._next_case_id += 1
    if case.complaint_id in world.complaints:
        complaint = world.complaints[case.complaint_id]
        complaint.status = ComplaintStatus.REFERRED
        complaint.updated_tick = world.tick
    return case


def advance_justice(world: World) -> None:
    justice_hour = world.total_minutes // 60
    if world._last_justice_hour == justice_hour:
        return
    world._last_justice_hour = justice_hour
    _advance_investigations(world)
    _advance_cases(world)
    _advance_sentences(world)


def _advance_investigations(world: World) -> None:
    for investigation in world.investigations.values():
        if investigation.status not in {InvestigationStatus.OPEN, InvestigationStatus.SUSPECT_IDENTIFIED}:
            continue
        if world.tick - investigation.updated_tick < 360:
            continue
        incident = world.incidents.get(investigation.incident_id)
        if incident is None:
            continue
        if investigation.lead_suspect_id is None and incident.offender_id is not None and world.rng.random() < 0.45:
            investigation.lead_suspect_id = incident.offender_id
            if incident.offender_id not in investigation.suspect_ids:
                investigation.suspect_ids.append(incident.offender_id)
            investigation.status = InvestigationStatus.SUSPECT_IDENTIFIED
        world._add_evidence(
            investigation,
            "follow_up",
            "Vérification complémentaire réalisée par les enquêteurs.",
            world.rng.uniform(0.35, 0.72),
            citizen_id=investigation.lead_suspect_id,
        )
        investigation.confidence = world._investigation_confidence(investigation)
        if investigation.lead_suspect_id is not None and investigation.confidence >= 72.0:
            world._arrest_suspect(investigation, reason="recoupements de l’enquête")
        elif world.tick - investigation.opened_tick > 5 * 24 * 60 and investigation.confidence < 45.0:
            investigation.status = InvestigationStatus.CLOSED
            investigation.notes.append("Enquête classée faute d’éléments suffisants.")
            _dismiss_complaint(world, investigation.complaint_id, "Éléments insuffisants après enquête.")


def _advance_cases(world: World) -> None:
    candidates = sorted(
        (case for case in world.judicial_cases.values() if case.status == JudicialCaseStatus.AWAITING_HEARING),
        key=lambda case: (-case.priority, case.hearing_tick, case.id),
    )
    for case in candidates:
        forced_legacy_hearing = case.hearing_tick <= case.filed_tick
        if case.prosecutor_decision is None:
            review_due = case.prosecutor_review_tick or case.filed_tick
            if world.tick < review_due and not forced_legacy_hearing:
                continue
            if not _prosecutor_review(world, case):
                continue
        if world.tick < case.hearing_tick:
            continue
        if not forced_legacy_hearing and not _court_can_hear(world):
            case.hearing_tick += 60
            case.delay_count += 1
            if case.delay_count in {1, 8, 24}:
                _timeline(case, world.tick, "hearing_delayed", "Audience reportée", "La capacité du tribunal est momentanément insuffisante.")
            continue
        _hold_hearing(world, case)


def _prosecutor_review(world: World, case: JudicialCase) -> bool:
    if case.evidence_score < 55.0:
        case.status = JudicialCaseStatus.DISMISSED
        case.decided_tick = world.tick
        case.verdict = "classé sans suite"
        case.sentence = "aucune peine"
        case.prosecutor_decision = "classement sans suite"
        _timeline(case, world.tick, "prosecutor_dismissal", "Classement sans suite", "Le parquet estime les charges insuffisamment étayées.")
        _dismiss_complaint(world, case.complaint_id, "Classement sans suite par le parquet.")
        world.cases_dismissed_today += 1
        world._emit("case_dismissed", f"Le dossier #{case.id} est classé sans suite par le parquet.", citizen_ids=(case.defendant_id,), severity="info", incident_id=case.incident_id)
        return False
    case.prosecutor_decision = "poursuites"
    if case.complaint_id in world.complaints:
        complaint = world.complaints[case.complaint_id]
        complaint.status = ComplaintStatus.PROSECUTED
        complaint.updated_tick = world.tick
    _timeline(case, world.tick, "prosecution", "Poursuites engagées", "Le parquet renvoie le dossier devant le tribunal.")
    return True


def _court_can_hear(world: World) -> bool:
    if weekday(world) > 5 or not 9 <= world.hour < 17 or world.hearings_today >= COURT_DAILY_CAPACITY:
        return False
    court = world._first_building(BuildingType.COURT)
    return court is not None and building_operational(world, court.id)


def _hold_hearing(world: World, case: JudicialCase) -> None:
    defendant = world.citizens.get(case.defendant_id)
    incident = world.incidents.get(case.incident_id)
    if defendant is None or incident is None:
        case.status = JudicialCaseStatus.DISMISSED
        case.verdict = "classé"
        case.decided_tick = world.tick
        return
    case.status = JudicialCaseStatus.IN_HEARING
    world.hearings_today += 1
    _timeline(case, world.tick, "hearing", "Audience", "Le tribunal examine les faits, les preuves et la situation du prévenu.")
    conviction_threshold = 61.0 + world.rng.uniform(-8.0, 8.0)
    case.decided_tick = world.tick
    if case.evidence_score < conviction_threshold:
        case.status = JudicialCaseStatus.DISMISSED
        case.verdict = "relaxé"
        case.sentence = "aucune peine"
        defendant.detained_until_tick = None
        defendant.current_detention_type = None
        message = f"Le dossier #{case.id} est jugé : {defendant.full_name} est relaxé faute de preuves suffisantes."
        _timeline(case, world.tick, "acquittal", "Relaxe", "Les preuves ne franchissent pas le seuil requis.")
    else:
        case.status = JudicialCaseStatus.DECIDED
        case.verdict = "coupable"
        sentences = _sentence_case(world, case, incident, defendant)
        case.sentence = ", ".join(sentence.label for sentence in sentences)
        defendant.criminal_record_count += 1
        message = f"Le dossier #{case.id} est jugé : {defendant.full_name} est déclaré coupable ({case.sentence})."
        _timeline(case, world.tick, "conviction", "Condamnation", case.sentence)
    investigation = world.investigations.get(case.investigation_id)
    if investigation is not None:
        investigation.status = InvestigationStatus.CLOSED
        investigation.updated_tick = world.tick
    if case.complaint_id in world.complaints:
        complaint = world.complaints[case.complaint_id]
        complaint.status = ComplaintStatus.CLOSED
        complaint.updated_tick = world.tick
    world._update_conflict_outcome(incident, message)
    court = world._first_building(BuildingType.COURT)
    world._emit("case_decided", message, citizen_ids=(defendant.id, *incident.victim_ids), building_id=court.id if court else incident.building_id, severity="warning" if case.verdict == "coupable" else "info", incident_id=incident.id)


def _sentence_case(world: World, case: JudicialCase, incident: Incident, defendant: Citizen) -> list[JudicialSentence]:
    rows: list[JudicialSentence] = []
    victim_id = incident.victim_ids[0] if incident.victim_ids else None
    if incident.incident_type == "theft":
        rows.append(_new_sentence(world, case, defendant, SentenceType.FINE, "Amende", amount=world.rng.uniform(90, 260)))
        rows.append(_new_sentence(world, case, defendant, SentenceType.COMPENSATION, "Indemnisation de la victime", amount=world.rng.uniform(40, 140), beneficiary_id=victim_id))
        rows.append(_new_sentence(world, case, defendant, SentenceType.PROBATION, "Probation de 14 jours", duration=14 * 24 * 60))
    elif incident.incident_type == "extortion":
        rows.append(_new_sentence(world, case, defendant, SentenceType.SHORT_DETENTION, "Détention de 2 jours", duration=2 * 24 * 60))
        rows.append(_new_sentence(world, case, defendant, SentenceType.FINE, "Amende pour extorsion", amount=world.rng.uniform(500, 1400)))
        rows.append(_new_sentence(world, case, defendant, SentenceType.PROBATION, "Probation de 30 jours", duration=30 * 24 * 60))
    elif incident.incident_type == "robbery":
        rows.append(_new_sentence(world, case, defendant, SentenceType.LONG_DETENTION, "Détention de 6 jours", duration=6 * 24 * 60))
        rows.append(_new_sentence(world, case, defendant, SentenceType.COMPENSATION, "Réparation du préjudice", amount=world.rng.uniform(600, 1800), beneficiary_id=victim_id))
    elif incident.incident_type == "kidnapping":
        rows.append(_new_sentence(world, case, defendant, SentenceType.LONG_DETENTION, "Détention de 10 jours", duration=10 * 24 * 60))
        rows.append(_new_sentence(world, case, defendant, SentenceType.COMPENSATION, "Indemnisation de la victime", amount=world.rng.uniform(1000, 3000), beneficiary_id=victim_id))
        if victim_id is not None:
            rows.append(_new_sentence(world, case, defendant, SentenceType.RESTRAINING_ORDER, "Interdiction de contact de 60 jours", duration=60 * 24 * 60, beneficiary_id=victim_id))
    elif incident.incident_type in {"drug_dealing", "criminal_market_raid"}:
        rows.append(_new_sentence(world, case, defendant, SentenceType.LONG_DETENTION, "Détention de 5 jours pour trafic", duration=5 * 24 * 60))
        rows.append(_new_sentence(world, case, defendant, SentenceType.FINE, "Confiscation et amende", amount=world.rng.uniform(900, 2800)))
        rows.append(_new_sentence(world, case, defendant, SentenceType.PROBATION, "Probation renforcée de 45 jours", duration=45 * 24 * 60))
    elif incident.incident_type == "arms_trafficking":
        rows.append(_new_sentence(world, case, defendant, SentenceType.LONG_DETENTION, "Détention de 9 jours pour trafic d’armes", duration=9 * 24 * 60))
        rows.append(_new_sentence(world, case, defendant, SentenceType.FINE, "Amende pour trafic d’armes", amount=world.rng.uniform(1800, 5200)))
    elif incident.incident_type in {"illegal_goods_trafficking", "money_laundering"}:
        rows.append(_new_sentence(world, case, defendant, SentenceType.SHORT_DETENTION, "Détention de 3 jours", duration=3 * 24 * 60))
        rows.append(_new_sentence(world, case, defendant, SentenceType.FINE, "Amende et confiscation des profits", amount=world.rng.uniform(1200, 4200)))
    elif incident.incident_type == "turf_war":
        rows.append(_new_sentence(world, case, defendant, SentenceType.LONG_DETENTION, "Détention de 8 jours pour violences en bande", duration=8 * 24 * 60))
        rows.append(_new_sentence(world, case, defendant, SentenceType.PROBATION, "Probation renforcée de 60 jours", duration=60 * 24 * 60))
    elif incident.incident_type == "corruption":
        rows.append(_new_sentence(world, case, defendant, SentenceType.SHORT_DETENTION, "Détention de 2 jours pour corruption", duration=2 * 24 * 60))
        rows.append(_new_sentence(world, case, defendant, SentenceType.FINE, "Amende pour corruption", amount=world.rng.uniform(1000, 3500)))
    elif incident.incident_type == "restraining_order_violation":
        rows.append(_new_sentence(world, case, defendant, SentenceType.SHORT_DETENTION, "Détention pour violation d’ordonnance", duration=24 * 60))
        rows.append(_new_sentence(world, case, defendant, SentenceType.PROBATION, "Probation renforcée de 30 jours", duration=30 * 24 * 60))
    elif incident.incident_type == "serious_assault":
        rows.append(_new_sentence(world, case, defendant, SentenceType.LONG_DETENTION, "Détention de 4 jours", duration=4 * 24 * 60))
        if victim_id is not None:
            rows.append(_new_sentence(world, case, defendant, SentenceType.RESTRAINING_ORDER, "Interdiction de contact de 30 jours", duration=30 * 24 * 60, beneficiary_id=victim_id))
    elif incident.incident_type in {"assault", "fight"}:
        rows.append(_new_sentence(world, case, defendant, SentenceType.COMMUNITY_SERVICE, "Travail d’intérêt général de 8 heures", required_minutes=8 * 60))
        rows.append(_new_sentence(world, case, defendant, SentenceType.PROBATION, "Probation de 14 jours", duration=14 * 24 * 60))
        if incident.incident_type == "assault" and victim_id is not None:
            rows.append(_new_sentence(world, case, defendant, SentenceType.RESTRAINING_ORDER, "Interdiction de contact de 21 jours", duration=21 * 24 * 60, beneficiary_id=victim_id))
    else:
        rows.append(_new_sentence(world, case, defendant, SentenceType.JUDICIAL_WARNING, "Rappel judiciaire"))
    for sentence in rows:
        _activate_sentence(world, sentence, defendant)
    case.sentence_ids = [sentence.id for sentence in rows]
    return rows


def _new_sentence(world: World, case: JudicialCase, citizen: Citizen, sentence_type: SentenceType, label: str, *, duration: int = 0, amount: float = 0.0, beneficiary_id: int | None = None, required_minutes: int = 0) -> JudicialSentence:
    sentence = JudicialSentence(id=world._next_sentence_id, case_id=case.id, citizen_id=citizen.id, sentence_type=sentence_type, label=label, status=SentenceStatus.PENDING, start_tick=world.tick, end_tick=world.tick + duration if duration else None, amount=round(amount, 2), beneficiary_id=beneficiary_id, required_minutes=required_minutes)
    world._next_sentence_id += 1
    world.sentences[sentence.id] = sentence
    citizen.sentence_ids.append(sentence.id)
    world.sentences_started_today += 1
    return sentence


def _activate_sentence(world: World, sentence: JudicialSentence, citizen: Citizen) -> None:
    sentence.status = SentenceStatus.ACTIVE
    if sentence.sentence_type in {SentenceType.FINE, SentenceType.COMPENSATION}:
        paid = withdraw(world, citizen, sentence.amount, label=sentence.label, transaction_type="judicial_payment", counterparty_id=sentence.beneficiary_id, allow_credit=True)
        citizen.financial_stress = min(100.0, citizen.financial_stress + 8.0)
        if sentence.beneficiary_id in world.citizens:
            beneficiary = world.citizens[sentence.beneficiary_id]
            deposit(world, beneficiary, paid, label="Indemnisation judiciaire", transaction_type="compensation", counterparty_id=citizen.id)
        sentence.status = SentenceStatus.COMPLETED
    elif sentence.sentence_type in {SentenceType.SHORT_DETENTION, SentenceType.LONG_DETENTION}:
        citizen.detained_until_tick = max(citizen.detained_until_tick or 0, sentence.end_tick or world.tick)
        citizen.current_detention_type = "judicial_detention"
        center = world._first_building(BuildingType.DETENTION_CENTER)
        if center is not None:
            citizen.destination_building_id = center.id
            citizen.planned_activity = Activity.DETAINED
        if sentence.sentence_type == SentenceType.LONG_DETENTION and citizen.workplace_id is not None:
            terminate_employment(world, citizen, "dismissal", "Rupture du contrat liée à une détention prolongée.")
    elif sentence.sentence_type == SentenceType.RESTRAINING_ORDER and sentence.beneficiary_id in world.citizens:
        beneficiary = world.citizens[sentence.beneficiary_id]
        for source, target in ((citizen, beneficiary), (beneficiary, citizen)):
            relationship = source.relationships.get(target.id)
            if relationship is not None:
                relationship.trust = max(-100.0, relationship.trust - 18.0)
                relationship.affection = max(-100.0, relationship.affection - 12.0)
        citizen.needs.stress = min(100.0, citizen.needs.stress + 6.0)
    elif sentence.sentence_type == SentenceType.JUDICIAL_WARNING:
        sentence.status = SentenceStatus.COMPLETED


def _advance_sentences(world: World) -> None:
    for sentence in world.sentences.values():
        if sentence.status not in {SentenceStatus.ACTIVE, SentenceStatus.VIOLATED}:
            continue
        citizen = world.citizens.get(sentence.citizen_id)
        if citizen is None:
            continue
        if sentence.sentence_type == SentenceType.COMMUNITY_SERVICE:
            if citizen.activity == Activity.COMMUNITY_SERVICE and citizen.travel_stage == TravelStage.IDLE:
                sentence.completed_minutes = min(sentence.required_minutes, sentence.completed_minutes + 60)
                citizen.community_service_minutes += 60
            if sentence.completed_minutes >= sentence.required_minutes:
                sentence.status = SentenceStatus.COMPLETED
                world._emit("community_service_completed", f"{citizen.full_name} termine son travail d’intérêt général.", citizen_ids=(citizen.id,), severity="info")
        elif sentence.end_tick is not None and world.tick >= sentence.end_tick:
            sentence.status = SentenceStatus.COMPLETED
            if sentence.sentence_type in {SentenceType.SHORT_DETENTION, SentenceType.LONG_DETENTION} and citizen.current_detention_type == "judicial_detention":
                citizen.detained_until_tick = None
                citizen.current_detention_type = None


def community_service_due(world: World, citizen_id: int) -> bool:
    return any(sentence.citizen_id == citizen_id and sentence.sentence_type == SentenceType.COMMUNITY_SERVICE and sentence.status in {SentenceStatus.ACTIVE, SentenceStatus.VIOLATED} and sentence.completed_minutes < sentence.required_minutes for sentence in world.sentences.values())


def contact_forbidden(world: World, first_id: int, second_id: int) -> bool:
    return any(sentence.sentence_type == SentenceType.RESTRAINING_ORDER and sentence.status in {SentenceStatus.ACTIVE, SentenceStatus.VIOLATED} and {sentence.citizen_id, sentence.beneficiary_id} == {first_id, second_id} for sentence in world.sentences.values())



def attempt_contact_violation(world: World, offender_id: int, recipient_id: int) -> bool:
    sentence = next((item for item in world.sentences.values() if item.sentence_type == SentenceType.RESTRAINING_ORDER and item.status in {SentenceStatus.ACTIVE, SentenceStatus.VIOLATED} and item.citizen_id == offender_id and item.beneficiary_id == recipient_id), None)
    if sentence is None:
        return False
    offender = world.citizens[offender_id]
    chance = min(0.82, 0.05 + offender.impulsivity / 180.0 + offender.aggression / 260.0)
    if world.rng.random() >= chance:
        world._emit("restraining_order_respected", f"{offender.full_name} renonce à contourner l’interdiction de communication.", citizen_ids=(offender_id, recipient_id), severity="warning")
        return False
    sentence.status = SentenceStatus.VIOLATED
    sentence.violation_count += 1
    offender.probation_violations += 1
    world.probation_violations_today += 1
    incident = world.create_incident(incident_type="restraining_order_violation", title="Violation d’une interdiction de communication", description=f"{offender.full_name} tente de contacter une personne protégée par décision de justice.", severity="danger", citizen_ids=(offender_id, recipient_id), offender_id=offender_id, victim_ids=(recipient_id,), reported=world.rng.random() < 0.7, lifetime_minutes=360, conflict_level=3)
    world._emit("restraining_order_violated", f"{offender.full_name} enfreint une interdiction de communication.", citizen_ids=(offender_id, recipient_id), severity="danger", incident_id=incident.id)
    return True

def _check_probation_violation(world: World, citizen_id: int | None, incident_id: int) -> None:
    if citizen_id is None:
        return
    for sentence in world.sentences.values():
        if sentence.citizen_id != citizen_id or sentence.sentence_type != SentenceType.PROBATION or sentence.status != SentenceStatus.ACTIVE:
            continue
        sentence.status = SentenceStatus.VIOLATED
        sentence.violation_count += 1
        citizen = world.citizens[citizen_id]
        citizen.probation_violations += 1
        citizen.needs.stress = min(100.0, citizen.needs.stress + 12.0)
        world.probation_violations_today += 1
        world._emit("probation_violated", f"{citizen.full_name} viole sa probation à la suite d’un nouvel incident.", citizen_ids=(citizen_id,), severity="danger", incident_id=incident_id)


def _dismiss_complaint(world: World, complaint_id: int | None, reason: str) -> None:
    if complaint_id not in world.complaints:
        return
    complaint = world.complaints[complaint_id]
    complaint.status = ComplaintStatus.DISMISSED
    complaint.updated_tick = world.tick
    complaint.dismissal_reason = reason


def _next_hearing_tick(world: World, priority: int) -> int:
    delay_days = 1 if priority >= 3 else 2 if priority == 2 else 3
    target = world.tick + delay_days * 24 * 60
    return target - (target % (24 * 60)) + 9 * 60 + (world._next_case_id % COURT_DAILY_CAPACITY) * 120


def _timeline(case: JudicialCase, tick: int, event_type: str, label: str, detail: str) -> None:
    case.timeline.append(JudicialTimelineEntry(tick=tick, event_type=event_type, label=label, detail=detail))
    case.timeline[:] = case.timeline[-MAX_JUSTICE_HISTORY:]


def justice_metrics(world: World) -> dict[str, int | float]:
    active_sentences = [sentence for sentence in world.sentences.values() if sentence.status in {SentenceStatus.ACTIVE, SentenceStatus.VIOLATED}]
    court = world._first_building(BuildingType.COURT)
    detention = world._first_building(BuildingType.DETENTION_CENTER)
    return {
        "complaintsFiled": len(world.complaints),
        "casesAwaitingHearing": sum(case.status == JudicialCaseStatus.AWAITING_HEARING for case in world.judicial_cases.values()),
        "hearingsToday": world.hearings_today,
        "courtCapacityToday": COURT_DAILY_CAPACITY,
        "courtStaffOnDuty": staff_count(world, court.id) if court else 0,
        "activeSentences": len(active_sentences),
        "citizensOnProbation": sum(sentence.sentence_type == SentenceType.PROBATION for sentence in active_sentences),
        "restrainingOrders": sum(sentence.sentence_type == SentenceType.RESTRAINING_ORDER for sentence in active_sentences),
        "detainedCitizens": sum(citizen.current_detention_type == "judicial_detention" for citizen in world.citizens.values()),
        "detentionCapacity": detention.capacity if detention else 0,
        "probationViolationsToday": world.probation_violations_today,
    }


def justice_overview(world: World) -> dict[str, Any]:
    court = world._first_building(BuildingType.COURT)
    detention = world._first_building(BuildingType.DETENTION_CENTER)
    return {
        "metrics": justice_metrics(world),
        "court": world._building_to_dict(court) if court else None,
        "detentionCenter": world._building_to_dict(detention) if detention else None,
        "queue": [world._case_summary(case) for case in sorted(world.judicial_cases.values(), key=lambda row: (-row.priority, row.hearing_tick, row.id)) if case.status == JudicialCaseStatus.AWAITING_HEARING],
        "activeSentences": [sentence_summary(world, sentence) for sentence in world.sentences.values() if sentence.status in {SentenceStatus.ACTIVE, SentenceStatus.VIOLATED}],
    }


def sentence_summary(world: World, sentence: JudicialSentence) -> dict[str, Any]:
    return {
        "id": sentence.id,
        "caseId": sentence.case_id,
        "citizen": world._citizen_ref(sentence.citizen_id),
        "type": sentence.sentence_type.value,
        "label": sentence.label,
        "status": sentence.status.value,
        "startTick": sentence.start_tick,
        "endTick": sentence.end_tick,
        "amount": sentence.amount,
        "beneficiary": world._citizen_ref(sentence.beneficiary_id),
        "requiredMinutes": sentence.required_minutes,
        "completedMinutes": sentence.completed_minutes,
        "violationCount": sentence.violation_count,
    }