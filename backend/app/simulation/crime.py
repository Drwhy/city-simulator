from __future__ import annotations

import random
from typing import TYPE_CHECKING

from .banking import available_funds, withdraw
from .criminal_factions import initialize_factions, reset_faction_day, update_faction_dynamics
from .criminal_markets import initialize_criminal_markets, reset_criminal_market_day, update_criminal_markets
from .crime_monitoring import crime_faction_detail, crime_overview
from .models import (
    Activity,
    BuildingType,
    CrimeOperation,
    CrimeOperationStatus,
    CrimeOperationType,
    CrimeOrganization,
)

if TYPE_CHECKING:
    from .world import World


MAX_CRIME_OPERATIONS = 2_000
MAX_CRIME_HISTORY_DAYS = 120

ORGANIZATION_NAMES = (
    "Le Cercle des Docks",
    "La Fratrie du Canal",
    "Le Réseau des Arcades",
    "Les Loups du Faubourg",
)


def initialize_crime(world: World) -> None:
    world.crime_rng = random.Random(world.seed + 73_019)
    world.crime_organizations: dict[int, CrimeOrganization] = {}
    world.crime_operations: dict[int, CrimeOperation] = {}
    world._next_crime_operation_id = 1
    world._last_crime_hour = -1
    world.organized_crimes_today = 0
    world.ransom_paid_today = 0.0
    world.crime_history: list[dict[str, object]] = []
    world._last_crime_faction_day = 0
    initialize_factions(world)
    initialize_criminal_markets(world)


def reset_crime_day(world: World) -> None:
    world.crime_history.append({
        "day": world.day - 1,
        "organizedCrimes": world.organized_crimes_today,
        "illegalSales": world.illegal_sales_today,
        "drugSales": world.drug_sales_today,
        "illegalRevenue": round(world.illegal_revenue_today, 2),
        "policeSeizures": round(world.police_seizures_today, 2),
        "dependentCitizens": sum(citizen.addiction_level >= 35.0 for citizen in world.citizens.values()),
    })
    world.crime_history[:] = world.crime_history[-MAX_CRIME_HISTORY_DAYS:]
    world.organized_crimes_today = 0
    world.ransom_paid_today = 0.0
    reset_faction_day(world)
    reset_criminal_market_day(world)
    for citizen in world.citizens.values():
        citizen.criminal_income_today = 0.0
        citizen.illegal_spending_today = 0.0


def update_crime(world: World) -> None:
    update_faction_dynamics(world)
    update_criminal_markets(world)
    hour_key = world.day * 24 + world.hour
    if world.minute != 35 or world._last_crime_hour == hour_key:
        return
    world._last_crime_hour = hour_key
    _resolve_kidnappings(world)
    for organization in world.crime_organizations.values():
        organization.police_heat = max(0.0, organization.police_heat - 0.08)
        if not organization.active:
            continue
        nighttime = world.hour >= 19 or world.hour <= 4
        risk = 0.014 + organization.notoriety / 9_000.0 + (0.012 if nighttime else 0.0)
        if world.crime_rng.random() < risk:
            _execute_operation(world, organization)
    _prune_operations(world)


def _execute_operation(world: World, organization: CrimeOrganization) -> None:
    available_members = [
        world.citizens[citizen_id]
        for citizen_id in organization.member_ids
        if citizen_id in world.citizens
        and world.citizens[citizen_id].detained_until_tick is None
        and world.citizens[citizen_id].kidnapped_until_tick is None
    ]
    if not available_members:
        return
    if world.crime_rng.random() < organization.sophistication / 420.0:
        _launder_money(world, organization, available_members)
        return
    if world.crime_rng.random() < 0.04:
        _attempt_corruption(world, organization, available_members)
        return
    weights = [
        CrimeOperationType.THEFT,
        CrimeOperationType.THEFT,
        CrimeOperationType.ROBBERY,
        CrimeOperationType.EXTORTION,
        CrimeOperationType.KIDNAPPING,
    ]
    operation_type = world.crime_rng.choice(weights)
    perpetrators = available_members[: world.crime_rng.randint(1, min(3, len(available_members)))]
    outsiders = [
        citizen
        for citizen in world.citizens.values()
        if citizen.crime_organization_id != organization.id
        and citizen.detained_until_tick is None
        and citizen.kidnapped_until_tick is None
    ]
    if not outsiders:
        return
    victim = world.crime_rng.choice(outsiders)
    building = _target_building(world, operation_type, victim.home_id)
    amount = round(
        world.crime_rng.uniform(
            25.0 if operation_type == CrimeOperationType.THEFT else 120.0,
            160.0 if operation_type == CrimeOperationType.THEFT else 1_200.0,
        ),
        2,
    )
    operation = CrimeOperation(
        id=world._next_crime_operation_id,
        organization_id=organization.id,
        operation_type=operation_type,
        status=CrimeOperationStatus.ACTIVE,
        planned_tick=world.tick,
        perpetrator_ids=[citizen.id for citizen in perpetrators],
        victim_ids=[victim.id],
        building_id=building.id if building else victim.home_id,
        amount=amount,
        started_tick=world.tick,
    )
    world._next_crime_operation_id += 1
    world.crime_operations[operation.id] = operation
    organization.operation_ids.append(operation.id)
    if operation_type == CrimeOperationType.KIDNAPPING:
        _kidnap(world, organization, operation, victim)
        return
    success_chance = 0.62 - organization.police_heat / 180.0
    succeeded = world.crime_rng.random() < max(0.18, success_chance)
    stolen = 0.0
    if succeeded:
        if operation_type in {CrimeOperationType.ROBBERY, CrimeOperationType.EXTORTION} and building:
            stolen = min(amount, max(0.0, building.cash))
            building.cash = round(building.cash - stolen, 2)
            if building.building_type == BuildingType.BANK:
                reserve_loss = min(amount - stolen, building.bank_reserves)
                building.bank_reserves = round(building.bank_reserves - reserve_loss, 2)
                stolen += reserve_loss
        else:
            stolen = withdraw(
                world,
                victim,
                min(amount, available_funds(victim)),
                label=f"Préjudice criminel — {organization.name}",
                transaction_type="crime_loss",
            )
        organization.treasury = round(organization.treasury + stolen, 2)
        operation.status = CrimeOperationStatus.SUCCEEDED
        operation.outcome = f"{stolen:.2f} € dérobés"
    else:
        operation.status = CrimeOperationStatus.FAILED
        operation.outcome = "échec de l'opération"
    operation.resolved_tick = world.tick
    _report_operation(world, organization, operation, victim, building, succeeded)


def _kidnap(world: World, organization: CrimeOrganization, operation: CrimeOperation, victim) -> None:
    duration = world.crime_rng.randint(6 * 60, 30 * 60)
    victim.kidnapped_until_tick = world.tick + duration
    victim.kidnapped_by_organization_id = organization.id
    victim.activity = Activity.KIDNAPPED
    victim.planned_activity = Activity.KIDNAPPED
    victim.needs.stress = min(100.0, victim.needs.stress + 35.0)
    operation.ransom_due_tick = world.tick + duration
    operation.outcome = "victime retenue, rançon exigée"
    _report_operation(world, organization, operation, victim, world.buildings.get(operation.building_id), True)


def _resolve_kidnappings(world: World) -> None:
    for operation in list(world.crime_operations.values()):
        if (
            operation.operation_type != CrimeOperationType.KIDNAPPING
            or operation.status != CrimeOperationStatus.ACTIVE
            or operation.ransom_due_tick is None
            or world.tick < operation.ransom_due_tick
        ):
            continue
        victim = world.citizens[operation.victim_ids[0]]
        household = world.households.get(victim.household_id)
        payers = [world.citizens[cid] for cid in household.member_ids if cid != victim.id] if household else []
        remaining = operation.amount
        paid = 0.0
        for payer in sorted(payers, key=available_funds, reverse=True):
            contribution = withdraw(
                world,
                payer,
                remaining,
                label=f"Rançon pour {victim.full_name}",
                transaction_type="ransom",
            )
            paid += contribution
            remaining -= contribution
            if remaining <= 0.01:
                break
        organization = world.crime_organizations[operation.organization_id]
        ransom_operation = CrimeOperation(id=world._next_crime_operation_id, organization_id=organization.id, operation_type=CrimeOperationType.RANSOM, status=CrimeOperationStatus.SUCCEEDED if paid >= operation.amount * 0.5 else CrimeOperationStatus.FAILED, planned_tick=operation.ransom_due_tick, perpetrator_ids=list(operation.perpetrator_ids), victim_ids=list(operation.victim_ids), building_id=operation.building_id, amount=operation.amount, incident_id=operation.incident_id, started_tick=operation.ransom_due_tick, resolved_tick=world.tick, outcome=f"{paid:.2f} € versés")
        world._next_crime_operation_id += 1
        world.crime_operations[ransom_operation.id] = ransom_operation
        organization.operation_ids.append(ransom_operation.id)
        organization.treasury = round(organization.treasury + paid, 2)
        world.ransom_paid_today = round(world.ransom_paid_today + paid, 2)
        victim.kidnapped_until_tick = None
        victim.kidnapped_by_organization_id = None
        victim.activity = Activity.AT_HOME
        victim.planned_activity = Activity.AT_HOME
        operation.status = CrimeOperationStatus.SUCCEEDED if paid >= operation.amount * 0.5 else CrimeOperationStatus.FAILED
        operation.resolved_tick = world.tick
        operation.outcome = f"victime libérée, rançon versée : {paid:.2f} €"
        world._emit(
            "kidnapping_resolved",
            f"{victim.full_name} est libéré après le versement de {paid:.2f} €.",
            citizen_ids=tuple(operation.perpetrator_ids + operation.victim_ids),
            building_id=operation.building_id,
            severity="danger",
            incident_id=operation.incident_id,
        )


def _target_building(world: World, operation_type: CrimeOperationType, fallback_id: int):
    if operation_type == CrimeOperationType.ROBBERY:
        candidates = [
            building
            for building in world.buildings.values()
            if building.building_type in {BuildingType.BANK, BuildingType.SHOP}
        ]
    elif operation_type == CrimeOperationType.EXTORTION:
        candidates = [
            building
            for building in world.buildings.values()
            if building.building_type
            in {BuildingType.CAFE, BuildingType.SHOP, BuildingType.OFFICE, BuildingType.FACTORY}
        ]
    else:
        candidates = []
    return world.crime_rng.choice(candidates) if candidates else world.buildings.get(fallback_id)


def _report_operation(world: World, organization, operation, victim, building, succeeded: bool) -> None:
    labels = {
        CrimeOperationType.THEFT: ("Vol organisé", "theft"),
        CrimeOperationType.ROBBERY: ("Braquage", "robbery"),
        CrimeOperationType.EXTORTION: ("Extorsion mafieuse", "extortion"),
        CrimeOperationType.KIDNAPPING: ("Enlèvement et demande de rançon", "kidnapping"),
    }
    title, incident_type = labels[operation.operation_type]
    reported = operation.operation_type in {CrimeOperationType.ROBBERY, CrimeOperationType.KIDNAPPING} or world.crime_rng.random() < 0.68
    incident = world.create_incident(
        incident_type=incident_type,
        title=title,
        description=f"{organization.name} mène une opération de {title.lower()} : {operation.outcome}.",
        severity="danger",
        citizen_ids=tuple(operation.perpetrator_ids + operation.victim_ids),
        offender_id=operation.perpetrator_ids[0],
        victim_ids=tuple(operation.victim_ids),
        building_id=building.id if building else operation.building_id,
        reported=reported,
        lifetime_minutes=12 * 60,
        conflict_level=4 if operation.operation_type == CrimeOperationType.KIDNAPPING else 3,
    )
    operation.incident_id = incident.id
    victim.victimizations += 1
    for perpetrator_id in operation.perpetrator_ids:
        world.citizens[perpetrator_id].offenses_committed += 1
    organization.notoriety = min(100.0, organization.notoriety + (4.0 if succeeded else 1.0))
    organization.police_heat = min(100.0, organization.police_heat + (9.0 if reported else 3.0))
    world.organized_crimes_today += 1



def _launder_money(world: World, organization: CrimeOrganization, members: list) -> None:
    businesses = [building for building in world.buildings.values() if building.building_type in {BuildingType.CAFE, BuildingType.SHOP, BuildingType.OFFICE} and building.business_status.value != "closed"]
    if not businesses or organization.treasury < 80.0:
        return
    building = world.crime_rng.choice(businesses)
    amount = round(min(organization.treasury * world.crime_rng.uniform(0.03, 0.12), organization.laundering_capacity), 2)
    fee = round(amount * world.crime_rng.uniform(0.08, 0.18), 2)
    organization.treasury = round(organization.treasury - amount, 2)
    organization.expenses_today = round(organization.expenses_today + fee, 2)
    building.cash = round(building.cash + amount - fee, 2)
    detected = world.crime_rng.random() < max(0.01, organization.police_heat / 500.0 - organization.sophistication / 1200.0)
    actor = next((member for member in members if member.criminal_role and member.criminal_role.value == "money_launderer"), members[0])
    operation = CrimeOperation(id=world._next_crime_operation_id, organization_id=organization.id, operation_type=CrimeOperationType.MONEY_LAUNDERING, status=CrimeOperationStatus.SUCCEEDED, planned_tick=world.tick, perpetrator_ids=[actor.id], victim_ids=[], building_id=building.id, amount=amount, started_tick=world.tick, resolved_tick=world.tick, outcome=f"{amount-fee:.2f} € intégrés à une activité légale", neighborhood_id=building.neighborhood_id, detected=detected)
    world._next_crime_operation_id += 1
    world.crime_operations[operation.id] = operation
    organization.operation_ids.append(operation.id)
    if detected:
        incident = world.create_incident(incident_type="money_laundering", title="Soupçon de blanchiment", description=f"Des flux suspects relient {building.name} à {organization.name}.", severity="warning", citizen_ids=(actor.id,), offender_id=actor.id, building_id=building.id, reported=True, lifetime_minutes=12*60, conflict_level=1)
        operation.incident_id = incident.id
        organization.police_heat = min(100.0, organization.police_heat + 5.0)


def _attempt_corruption(world: World, organization: CrimeOrganization, members: list) -> None:
    officers = [citizen for citizen in world.citizens.values() if citizen.workplace_id in world.buildings and world.buildings[citizen.workplace_id].building_type == BuildingType.POLICE and citizen.detained_until_tick is None]
    if not officers or organization.treasury < 150.0:
        return
    target = max(officers, key=lambda citizen: (citizen.financial_stress + citizen.impulsivity*.25, -citizen.id))
    actor = members[0]
    bribe = round(min(organization.treasury*.025, world.crime_rng.uniform(120.0,500.0)),2)
    accepted = world.crime_rng.random() < min(.36,.02+target.financial_stress/420.0+target.impulsivity/700.0)
    detected = world.crime_rng.random() < .12 + organization.police_heat/500.0
    if accepted:
        organization.treasury = round(organization.treasury-bribe,2)
        organization.expenses_today = round(organization.expenses_today+bribe,2)
        target.money = round(target.money+bribe,2)
        target.criminal_contact_ids.append(actor.id); target.criminal_contact_ids[:] = target.criminal_contact_ids[-20:]
        organization.police_heat = max(0.0,organization.police_heat-2.0)
    operation = CrimeOperation(id=world._next_crime_operation_id, organization_id=organization.id, operation_type=CrimeOperationType.CORRUPTION, status=CrimeOperationStatus.SUCCEEDED if accepted else CrimeOperationStatus.FAILED, planned_tick=world.tick, perpetrator_ids=[actor.id], victim_ids=[target.id], building_id=target.workplace_id, amount=bribe, started_tick=world.tick, resolved_tick=world.tick, outcome="pot-de-vin accepté" if accepted else "approche refusée", neighborhood_id=world.buildings[target.workplace_id].neighborhood_id, detected=detected)
    world._next_crime_operation_id += 1
    world.crime_operations[operation.id] = operation
    organization.operation_ids.append(operation.id)
    if detected:
        incident = world.create_incident(incident_type="corruption", title="Tentative de corruption", description=f"Une tentative de corruption relie {organization.name} à un agent public.", severity="danger", citizen_ids=(actor.id,target.id), offender_id=actor.id, witness_ids=(target.id,), building_id=target.workplace_id, reported=True, lifetime_minutes=12*60, conflict_level=2)
        operation.incident_id = incident.id

def _legacy_crime_overview(world: World) -> dict[str, object]:
    active_kidnappings = sum(
        operation.operation_type == CrimeOperationType.KIDNAPPING
        and operation.status == CrimeOperationStatus.ACTIVE
        for operation in world.crime_operations.values()
    )
    return {
        "tick": world.tick,
        "metrics": {
            "organizations": sum(organization.active for organization in world.crime_organizations.values()),
            "operations": len(world.crime_operations),
            "organizedCrimesToday": world.organized_crimes_today,
            "activeKidnappings": active_kidnappings,
            "ransomPaidToday": round(world.ransom_paid_today, 2),
        },
        "organizations": [
            {
                "id": organization.id,
                "name": organization.name,
                "leaderId": organization.leader_id,
                "memberCount": len(organization.member_ids),
                "territoryId": organization.territory_id,
                "treasury": round(organization.treasury, 2),
                "notoriety": round(organization.notoriety, 1),
                "policeHeat": round(organization.police_heat, 1),
                "active": organization.active,
            }
            for organization in world.crime_organizations.values()
        ],
        "operations": [
            {
                "id": operation.id,
                "organizationId": operation.organization_id,
                "type": operation.operation_type.value,
                "status": operation.status.value,
                "victimIds": operation.victim_ids,
                "buildingId": operation.building_id,
                "amount": operation.amount,
                "incidentId": operation.incident_id,
                "startedTick": operation.started_tick,
                "resolvedTick": operation.resolved_tick,
                "outcome": operation.outcome,
            }
            for operation in sorted(world.crime_operations.values(), key=lambda item: item.id, reverse=True)[:80]
        ],
    }


def _prune_operations(world: World) -> None:
    if len(world.crime_operations) <= MAX_CRIME_OPERATIONS:
        return
    removable = sorted(world.crime_operations)[: len(world.crime_operations) - MAX_CRIME_OPERATIONS]
    for operation_id in removable:
        world.crime_operations.pop(operation_id, None)
    removed = set(removable)
    for organization in world.crime_organizations.values():
        organization.operation_ids[:] = [operation_id for operation_id in organization.operation_ids if operation_id not in removed]
