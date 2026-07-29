from __future__ import annotations

from itertools import combinations
from typing import TYPE_CHECKING

from .models import (
    CrimeFactionRelation,
    CrimeOperation,
    CrimeOperationStatus,
    CrimeOperationType,
    CrimeFactionType,
    CrimeOrganization,
    CrimeRole,
    IllegalCommodity,
)

if TYPE_CHECKING:
    from .models import Citizen
    from .world import World


FACTION_IDENTITIES: tuple[tuple[str, CrimeFactionType], ...] = (
    ("Les Éperviers du Bloc", CrimeFactionType.STREET_GANG),
    ("Union des Docks", CrimeFactionType.ORGANIZED_GANG),
    ("Famille Bellandi", CrimeFactionType.MAFIA),
    ("Triade du Lotus Gris", CrimeFactionType.TRIAD),
    ("Cartel de la Traverse", CrimeFactionType.CARTEL),
    ("Les Cavaliers d’Acier", CrimeFactionType.BIKER_GANG),
    ("Réseau Zéro", CrimeFactionType.CYBER_NETWORK),
    ("Clan des Arcades", CrimeFactionType.MAFIA),
    ("Les Chiens Rouges", CrimeFactionType.STREET_GANG),
    ("Syndicat du Canal", CrimeFactionType.ORGANIZED_GANG),
    ("Triade des Trois Ponts", CrimeFactionType.TRIAD),
    ("Route Noire", CrimeFactionType.BIKER_GANG),
    ("Collectif Spectre", CrimeFactionType.CYBER_NETWORK),
    ("Cartel du Levant", CrimeFactionType.CARTEL),
    ("Famille Orsini", CrimeFactionType.MAFIA),
    ("Les Cobras du Sud", CrimeFactionType.STREET_GANG),
)

SPECIALTIES: dict[CrimeFactionType, tuple[IllegalCommodity, ...]] = {
    CrimeFactionType.STREET_GANG: (
        IllegalCommodity.CANNABIS,
        IllegalCommodity.STOLEN_GOODS,
    ),
    CrimeFactionType.ORGANIZED_GANG: (
        IllegalCommodity.COCAINE,
        IllegalCommodity.STOLEN_GOODS,
        IllegalCommodity.COUNTERFEIT_GOODS,
    ),
    CrimeFactionType.MAFIA: (
        IllegalCommodity.COCAINE,
        IllegalCommodity.WEAPONS,
        IllegalCommodity.COUNTERFEIT_GOODS,
    ),
    CrimeFactionType.TRIAD: (
        IllegalCommodity.SYNTHETIC_DRUGS,
        IllegalCommodity.COUNTERFEIT_GOODS,
        IllegalCommodity.WEAPONS,
    ),
    CrimeFactionType.CARTEL: (
        IllegalCommodity.CANNABIS,
        IllegalCommodity.COCAINE,
        IllegalCommodity.SYNTHETIC_DRUGS,
    ),
    CrimeFactionType.BIKER_GANG: (
        IllegalCommodity.WEAPONS,
        IllegalCommodity.SYNTHETIC_DRUGS,
        IllegalCommodity.STOLEN_GOODS,
    ),
    CrimeFactionType.CYBER_NETWORK: (
        IllegalCommodity.COUNTERFEIT_GOODS,
        IllegalCommodity.STOLEN_GOODS,
    ),
}

PROFILE: dict[CrimeFactionType, tuple[float, float, float]] = {
    CrimeFactionType.STREET_GANG: (62.0, 35.0, 68.0),
    CrimeFactionType.ORGANIZED_GANG: (52.0, 61.0, 48.0),
    CrimeFactionType.MAFIA: (55.0, 82.0, 36.0),
    CrimeFactionType.TRIAD: (48.0, 88.0, 32.0),
    CrimeFactionType.CARTEL: (74.0, 72.0, 60.0),
    CrimeFactionType.BIKER_GANG: (78.0, 46.0, 58.0),
    CrimeFactionType.CYBER_NETWORK: (20.0, 94.0, 26.0),
}


def initialize_factions(world: World) -> None:
    world.crime_organizations = {}
    world.crime_relations: dict[tuple[int, int], CrimeFactionRelation] = {}
    candidates = sorted(
        (
            citizen
            for citizen in world.citizens.values()
            if citizen.age >= 18
            and not _protected_profession(world, citizen)
        ),
        key=lambda citizen: (
            citizen.aggression * 0.34
            + citizen.impulsivity * 0.26
            + citizen.financial_stress * 0.28
            + citizen.spontaneity * 0.12,
            citizen.id,
        ),
        reverse=True,
    )
    faction_count = min(len(FACTION_IDENTITIES), max(4, len(world.citizens) // 300))
    desired_members = max(7, len(world.citizens) // max(18, faction_count * 22))
    member_target = max(3, min(12, len(candidates) // faction_count, desired_members))
    cursor = 0
    neighborhood_ids = sorted(world.neighborhoods)
    for organization_id in range(1, faction_count + 1):
        members = candidates[cursor : cursor + member_target]
        cursor += member_target
        if len(members) < 2:
            break
        name, faction_type = FACTION_IDENTITIES[(organization_id - 1) % len(FACTION_IDENTITIES)]
        violence, sophistication, recruitment = PROFILE[faction_type]
        home_territory = neighborhood_ids[(organization_id - 1) % len(neighborhood_ids)]
        specialties = list(SPECIALTIES[faction_type])
        organization = CrimeOrganization(
            id=organization_id,
            name=name,
            leader_id=members[0].id,
            member_ids=[citizen.id for citizen in members],
            territory_id=home_territory,
            territory_ids=[home_territory],
            treasury=round(world.crime_rng.uniform(1_200.0, 8_000.0), 2),
            faction_type=faction_type,
            specialties=specialties,
            inventory={
                commodity.value: round(world.crime_rng.uniform(18.0, 65.0), 2)
                for commodity in specialties
            },
            influence_by_neighborhood={
                neighborhood_id: (
                    world.crime_rng.uniform(52.0, 78.0)
                    if neighborhood_id == home_territory
                    else world.crime_rng.uniform(2.0, 18.0)
                )
                for neighborhood_id in neighborhood_ids
            },
            cohesion=world.crime_rng.uniform(48.0, 82.0),
            violence=violence + world.crime_rng.uniform(-8.0, 8.0),
            sophistication=sophistication + world.crime_rng.uniform(-7.0, 7.0),
            recruitment_pressure=recruitment + world.crime_rng.uniform(-8.0, 8.0),
            laundering_capacity=world.crime_rng.uniform(120.0, 600.0),
        )
        _assign_roles(organization)
        world.crime_organizations[organization.id] = organization
        for citizen in members:
            citizen.crime_organization_id = organization.id
            citizen.criminal_role = organization.role_by_member[citizen.id]
            citizen.recruited_tick = world.tick
            citizen.criminal_contact_ids = sorted(
                member.id for member in members if member.id != citizen.id
            )[:12]

    for first, second in combinations(world.crime_organizations.values(), 2):
        same_territory = first.territory_id == second.territory_id
        relation = CrimeFactionRelation(
            first_id=first.id,
            second_id=second.id,
            tension=world.crime_rng.uniform(58.0, 84.0) if same_territory else world.crime_rng.uniform(18.0, 58.0),
            trust=world.crime_rng.uniform(-35.0, 18.0),
        )
        world.crime_relations[(first.id, second.id)] = relation
        if relation.tension >= 52.0:
            first.rival_ids.append(second.id)
            second.rival_ids.append(first.id)
        elif relation.trust >= 8.0:
            first.ally_ids.append(second.id)
            second.ally_ids.append(first.id)


def update_faction_dynamics(world: World) -> None:
    if world.hour == 2 and world.minute == 10 and world._last_crime_faction_day != world.day:
        world._last_crime_faction_day = world.day
        for organization in sorted(world.crime_organizations.values(), key=lambda item: item.id):
            _daily_recruitment(world, organization)
            organization.cohesion = _clamp(
                organization.cohesion
                + world.crime_rng.uniform(-1.5, 1.5)
                - organization.police_heat * 0.004
            )
            organization.influence_by_neighborhood = {
                neighborhood_id: _clamp(
                    influence
                    + world.crime_rng.uniform(-0.7, 0.7)
                    - organization.police_heat * 0.002
                )
                for neighborhood_id, influence in organization.influence_by_neighborhood.items()
            }
        for relation in world.crime_relations.values():
            relation.tension = _clamp(relation.tension + world.crime_rng.uniform(-1.2, 1.2))

    if world.minute == 45 and world.crime_rng.random() < min(
        0.12, len(world.crime_organizations) * 0.008
    ):
        _attempt_turf_conflict(world)


def reset_faction_day(world: World) -> None:
    for organization in world.crime_organizations.values():
        organization.revenue_today = 0.0
        organization.expenses_today = 0.0


def relation_key(first_id: int, second_id: int) -> tuple[int, int]:
    return (min(first_id, second_id), max(first_id, second_id))


def _assign_roles(organization: CrimeOrganization) -> None:
    role_cycle = (
        CrimeRole.BOSS,
        CrimeRole.LIEUTENANT,
        CrimeRole.DEALER,
        CrimeRole.DEALER,
        CrimeRole.ENFORCER,
        CrimeRole.SUPPLIER,
        CrimeRole.LOOKOUT,
        CrimeRole.MONEY_LAUNDERER,
        CrimeRole.RECRUITER,
    )
    organization.role_by_member = {
        citizen_id: role_cycle[index % len(role_cycle)]
        for index, citizen_id in enumerate(organization.member_ids)
    }


def _daily_recruitment(world: World, organization: CrimeOrganization) -> None:
    if len(organization.member_ids) >= max(18, len(world.citizens) // 120):
        return
    chance = organization.recruitment_pressure / 260.0 * (organization.cohesion / 100.0)
    if world.crime_rng.random() >= chance:
        return
    candidates = [
        citizen
        for citizen in world.citizens.values()
        if citizen.age >= 18
        and citizen.crime_organization_id is None
        and not _protected_profession(world, citizen)
        and (
            citizen.is_homeless
            or citizen.workplace_id is None
            or citizen.financial_stress >= 55.0
            or citizen.aggression + citizen.impulsivity >= 115.0
        )
    ]
    if not candidates:
        return
    recruit = max(
        candidates,
        key=lambda citizen: (
            citizen.financial_stress
            + citizen.aggression * 0.5
            + citizen.impulsivity * 0.5
            + (25.0 if citizen.is_homeless else 0.0),
            -citizen.id,
        ),
    )
    recruit.crime_organization_id = organization.id
    recruit.criminal_role = (
        CrimeRole.DEALER
        if sum(role == CrimeRole.DEALER for role in organization.role_by_member.values()) < 4
        else CrimeRole.LOOKOUT
    )
    recruit.recruited_tick = world.tick
    recruit.criminal_contact_ids = organization.member_ids[-12:]
    organization.member_ids.append(recruit.id)
    organization.role_by_member[recruit.id] = recruit.criminal_role
    organization.members_recruited += 1
    organization.cohesion = min(100.0, organization.cohesion + 0.8)
    operation = CrimeOperation(
        id=world._next_crime_operation_id,
        organization_id=organization.id,
        operation_type=CrimeOperationType.RECRUITMENT,
        status=CrimeOperationStatus.SUCCEEDED,
        planned_tick=world.tick,
        perpetrator_ids=[organization.leader_id],
        victim_ids=[recruit.id],
        building_id=recruit.home_id,
        amount=0.0,
        started_tick=world.tick,
        resolved_tick=world.tick,
        outcome=f"recrutement comme {recruit.criminal_role.value}",
        neighborhood_id=world.buildings[recruit.home_id].neighborhood_id,
        detected=False,
    )
    world._next_crime_operation_id += 1
    world.crime_operations[operation.id] = operation
    organization.operation_ids.append(operation.id)
    world._emit(
        "criminal_recruitment",
        f"{recruit.full_name} rejoint {organization.name} comme {recruit.criminal_role.value}.",
        citizen_ids=(recruit.id, organization.leader_id),
        severity="warning",
    )


def _attempt_turf_conflict(world: World) -> None:
    eligible = [
        relation
        for relation in world.crime_relations.values()
        if relation.tension >= 62.0
        and (relation.truce_until_tick is None or world.tick >= relation.truce_until_tick)
    ]
    if not eligible:
        return
    relation = world.crime_rng.choice(sorted(eligible, key=lambda item: (item.first_id, item.second_id)))
    first = world.crime_organizations[relation.first_id]
    second = world.crime_organizations[relation.second_id]
    first_members = _available_enforcers(world, first)
    second_members = _available_enforcers(world, second)
    if not first_members or not second_members:
        return
    first_actor = world.crime_rng.choice(first_members)
    second_actor = world.crime_rng.choice(second_members)
    neighborhood_id = max(
        world.neighborhoods,
        key=lambda neighborhood_id: min(
            first.influence_by_neighborhood.get(neighborhood_id, 0.0),
            second.influence_by_neighborhood.get(neighborhood_id, 0.0),
        ),
    )
    buildings = [
        building
        for building in world.buildings.values()
        if building.neighborhood_id == neighborhood_id
    ]
    building = world.crime_rng.choice(buildings) if buildings else None
    incident = world.create_incident(
        incident_type="turf_war",
        title="Affrontement entre factions",
        description=f"{first.name} et {second.name} s’affrontent pour le contrôle du quartier.",
        severity="danger",
        citizen_ids=(first_actor.id, second_actor.id),
        offender_id=first_actor.id,
        victim_ids=(second_actor.id,),
        building_id=building.id if building else None,
        reported=True,
        lifetime_minutes=10 * 60,
        conflict_level=4,
    )
    operation = CrimeOperation(
        id=world._next_crime_operation_id,
        organization_id=first.id,
        operation_type=CrimeOperationType.TURF_WAR,
        status=CrimeOperationStatus.SUCCEEDED,
        planned_tick=world.tick,
        perpetrator_ids=[first_actor.id, second_actor.id],
        victim_ids=[second_actor.id],
        building_id=building.id if building else None,
        amount=0.0,
        incident_id=incident.id,
        started_tick=world.tick,
        resolved_tick=world.tick,
        outcome=f"affrontement avec {second.name}",
        neighborhood_id=neighborhood_id,
        detected=True,
    )
    world._next_crime_operation_id += 1
    world.crime_operations[operation.id] = operation
    first.operation_ids.append(operation.id)
    world.organized_crimes_today += 1
    relation.conflict_count += 1
    relation.last_conflict_tick = world.tick
    relation.tension = min(100.0, relation.tension + 8.0)
    first.police_heat = min(100.0, first.police_heat + 7.0)
    second.police_heat = min(100.0, second.police_heat + 7.0)
    first.influence_by_neighborhood[neighborhood_id] = _clamp(
        first.influence_by_neighborhood.get(neighborhood_id, 0.0)
        + world.crime_rng.uniform(-3.0, 4.0)
    )
    second.influence_by_neighborhood[neighborhood_id] = _clamp(
        second.influence_by_neighborhood.get(neighborhood_id, 0.0)
        + world.crime_rng.uniform(-3.0, 4.0)
    )
    from .health import apply_injury

    apply_injury(
        world,
        second_actor,
        severity=world.crime_rng.uniform(25.0, 62.0),
        source="guerre de territoire",
        incident_id=incident.id,
    )


def _available_enforcers(world: World, organization: CrimeOrganization) -> list[Citizen]:
    preferred = [
        world.citizens[citizen_id]
        for citizen_id, role in organization.role_by_member.items()
        if role in {CrimeRole.ENFORCER, CrimeRole.LIEUTENANT, CrimeRole.BOSS}
        and citizen_id in world.citizens
        and world.citizens[citizen_id].detained_until_tick is None
    ]
    return preferred or [
        world.citizens[citizen_id]
        for citizen_id in organization.member_ids
        if citizen_id in world.citizens
        and world.citizens[citizen_id].detained_until_tick is None
    ]


def _protected_profession(world: World, citizen: Citizen) -> bool:
    if citizen.workplace_id not in world.buildings:
        return False
    return world.buildings[citizen.workplace_id].building_type.value in {
        "police",
        "court",
        "detention_center",
    }


def _clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 2)
