from __future__ import annotations

from itertools import combinations
from typing import TYPE_CHECKING

from .banking import available_funds, withdraw
from .justice import contact_forbidden
from .models import (
    BuildingType,
    Citizen,
    Relationship,
    SocialEvent,
    SocialEventStatus,
    SocialEventType,
)

if TYPE_CHECKING:
    from .world import World


CONFLICT_LABELS = {
    0: "calme",
    1: "dispute",
    2: "grosse_dispute",
    3: "bagarre",
    4: "agression",
    5: "agression_grave",
}


def relationship_label(relationship: Relationship) -> str:
    if relationship.affection <= -12 and relationship.negative_interactions >= 3:
        return "rival"
    if relationship.affection >= 52 and relationship.trust >= 38:
        return "close_friend"
    if relationship.affection >= 25 and relationship.familiarity >= 28:
        return "friend"
    if relationship.familiarity >= 10:
        return "acquaintance"
    return "unknown"


def conflict_label(relationship: Relationship) -> str:
    return CONFLICT_LABELS.get(max(0, min(5, relationship.conflict_level)), "calme")


def conflict_propensity(citizen: Citizen) -> float:
    """Indice 0..1 combinant agressivité, impulsivité et rancune."""
    return max(
        0.0,
        min(
            1.0,
            citizen.aggression * 0.45 / 100.0
            + citizen.impulsivity * 0.35 / 100.0
            + citizen.grudge_tendency * 0.20 / 100.0,
        ),
    )


def temperament_label(citizen: Citizen) -> str:
    score = conflict_propensity(citizen)
    if score >= 0.72:
        return "très volatil"
    if score >= 0.54:
        return "conflictuel"
    if score >= 0.36:
        return "réactif"
    return "posé"


def _level_from_pressure(score: float, consecutive: int) -> int:
    # L'escalade doit émerger de conflits répétés sur plusieurs jours, pas de deux
    # interactions malheureuses dans la même heure.
    if consecutive >= 42:
        return 5
    if score >= 96 or consecutive >= 28:
        return 4
    if score >= 75 or consecutive >= 18:
        return 3
    if score >= 40 or consecutive >= 10:
        return 2
    if score >= 14 or consecutive >= 4:
        return 1
    return 0



def cool_down_conflicts(world: World) -> None:
    """Fait redescendre la pression sans effacer la mémoire historique.

    Une relation rancunière récupère plus lentement. Les épisodes restent dans
    ``conflict_history`` et ``peak_conflict_level`` même lorsque le niveau actif
    finit par diminuer.
    """
    for citizen in world.citizens.values():
        for relationship in citizen.relationships.values():
            if relationship.conflict_score <= 0 and relationship.consecutive_negative_interactions <= 0:
                continue
            other = world.citizens.get(relationship.other_id)
            average_grudge = (
                (citizen.grudge_tendency + other.grudge_tendency) / 200.0
                if other is not None
                else citizen.grudge_tendency / 100.0
            )
            since_conflict = (
                world.tick - relationship.last_conflict_tick
                if relationship.last_conflict_tick is not None
                else 10_000
            )
            quiet = since_conflict >= 12 * 60
            recovery = (3.2 if quiet else 0.8) * max(0.22, 1.0 - average_grudge * 0.72)
            relationship.conflict_score = max(0.0, relationship.conflict_score - recovery)
            if quiet:
                relationship.consecutive_negative_interactions = max(
                    0, relationship.consecutive_negative_interactions - 2
                )
            computed_level = _level_from_pressure(
                relationship.conflict_score,
                relationship.consecutive_negative_interactions,
            )
            relationship.conflict_level = min(relationship.conflict_level, computed_level)

def social_commitment(world: World, citizen: Citizen) -> SocialEvent | None:
    if citizen.social_event_id is None:
        return None
    event = world.social_events.get(citizen.social_event_id)
    if event is None or event.status in {SocialEventStatus.COMPLETED, SocialEventStatus.CANCELLED}:
        citizen.social_event_id = None
        return None
    if citizen.id not in event.participant_ids:
        return None
    if world.tick < event.planned_tick - 30 or world.tick >= event.end_tick:
        return None
    return event


def update_social_calendar(world: World) -> None:
    _activate_or_complete_events(world)
    if world.hour == 16 and world.minute == 0 and world._last_social_planning_day != world.day:
        world._last_social_planning_day = world.day
        _plan_evening_events(world)


def _plan_evening_events(world: World) -> None:
    cafe = world._first_building(BuildingType.CAFE)
    park = world._first_building(BuildingType.PARK)
    if cafe is None or park is None:
        return

    candidates = sorted(
        world.citizens.values(),
        key=lambda citizen: (citizen.needs.social + citizen.sociability * 0.45, -citizen.id),
        reverse=True,
    )
    scheduled: set[int] = set()
    created = 0
    for host in candidates:
        if created >= 12 or host.id in scheduled or host.social_event_id is not None:
            continue
        if host.needs.social < 32 and host.sociability < 58:
            continue

        possible_guests = _guest_candidates(world, host)
        if not possible_guests:
            continue
        guest_limit = 2 if host.sociability >= 68 else 1
        invited = possible_guests[:guest_limit]
        accepted: list[int] = []
        declined: list[int] = []
        for guest in invited:
            host.invitations_sent += 1
            world.social_invitations_today += 1
            relation = host.relationships.get(guest.id, Relationship(other_id=guest.id))
            acceptance_score = (
                34
                + relation.affection * 0.42
                + relation.trust * 0.23
                + guest.needs.social * 0.24
                + guest.sociability * 0.16
                + guest.spontaneity * 0.08
                - guest.needs.stress * 0.28
                - relation.conflict_level * 12
            )
            if guest.social_event_id is None and world.rng.uniform(0, 100) <= acceptance_score:
                accepted.append(guest.id)
                guest.invitations_accepted += 1
                world.social_acceptances_today += 1
            else:
                declined.append(guest.id)

        if not accepted:
            continue

        use_cafe = host.money >= 16 and world.rng.random() < 0.56
        building = cafe if use_cafe else park
        event_type = SocialEventType.COFFEE if use_cafe else SocialEventType.PARK_MEETUP
        planned_tick = world.tick + 120 + (host.id % 4) * 15
        event = SocialEvent(
            id=world._next_social_event_id,
            event_type=event_type,
            host_id=host.id,
            guest_ids=[guest.id for guest in invited],
            accepted_ids=accepted,
            declined_ids=declined,
            building_id=building.id,
            planned_tick=planned_tick,
        )
        world._next_social_event_id += 1
        world.social_events[event.id] = event
        for participant_id in event.participant_ids:
            world.citizens[participant_id].social_event_id = event.id
            scheduled.add(participant_id)
        created += 1
        accepted_names = ", ".join(world.citizens[citizen_id].full_name for citizen_id in accepted)
        world._emit(
            "social_invitation_accepted",
            f"{host.full_name} organise une sortie à {building.name} avec {accepted_names}.",
            citizen_ids=tuple(event.participant_ids),
            building_id=building.id,
        )


def _guest_candidates(world: World, host: Citizen) -> list[Citizen]:
    candidates: list[tuple[float, Citizen]] = []
    for other in world.citizens.values():
        if other.id == host.id or other.social_event_id is not None:
            continue
        if contact_forbidden(world, host.id, other.id):
            continue
        relation = host.relationships.get(other.id)
        same_work = host.workplace_id is not None and host.workplace_id == other.workplace_id
        same_household = host.household_id is not None and host.household_id == other.household_id
        if relation is None and not same_work and not same_household:
            continue
        relation = relation or Relationship(other_id=other.id)
        score = relation.affection * 1.5 + relation.trust + relation.familiarity * 0.35
        score -= relation.conflict_level * 25
        score += 12 if same_work else 0
        score += 8 if same_household else 0
        score += other.needs.social * 0.15
        candidates.append((score, other))
    candidates.sort(key=lambda row: (row[0], -row[1].id), reverse=True)
    return [candidate for _, candidate in candidates]


def _activate_or_complete_events(world: World) -> None:
    for event in list(world.social_events.values()):
        if event.status == SocialEventStatus.PLANNED and world.tick >= event.planned_tick:
            event.status = SocialEventStatus.ACTIVE
            event.started_tick = world.tick
            building = world.buildings[event.building_id]
            world._emit(
                "social_gathering_started",
                f"Une rencontre commence à {building.name}.",
                citizen_ids=tuple(event.participant_ids),
                building_id=building.id,
            )

        if event.status != SocialEventStatus.ACTIVE or world.tick < event.end_tick:
            continue

        building = world.buildings[event.building_id]
        present = [
            world.citizens[citizen_id]
            for citizen_id in event.participant_ids
            if citizen_id in building.occupants
        ]
        missing = [citizen_id for citizen_id in event.participant_ids if citizen_id not in building.occupants]
        if len(present) >= 2:
            for a, b in combinations(present, 2):
                relation = a.relationships.get(b.id)
                conflict_risk = relation.conflict_level * 0.08 if relation else 0.0
                positive = world.rng.random() > conflict_risk
                apply_interaction(world, a, b, building.id, positive=positive, strength=3.2, emit=False)
            for citizen in present:
                citizen.needs.social = max(0.0, citizen.needs.social - 18.0)
                citizen.needs.stress = max(0.0, citizen.needs.stress - 5.0)
                if event.event_type == SocialEventType.COFFEE and available_funds(citizen) >= 6:
                    withdraw(world, citizen, 6.0, label=f"Sortie à {building.name}", transaction_type="social", counterparty_id=building.id)
            event.status = SocialEventStatus.COMPLETED
            world.social_gatherings_completed += 1
            world._emit(
                "social_gathering_completed",
                f"La rencontre à {building.name} se termine.",
                citizen_ids=tuple(citizen.id for citizen in present),
                building_id=building.id,
            )
        else:
            event.status = SocialEventStatus.CANCELLED
            world._emit(
                "social_gathering_cancelled",
                f"La rencontre prévue à {building.name} est annulée faute de participants.",
                citizen_ids=tuple(event.participant_ids),
                building_id=building.id,
                severity="warning",
            )

        host = world.citizens[event.host_id]
        for missing_id in missing:
            guest = world.citizens[missing_id]
            _adjust_pair(host, guest, affection=-2.0, trust=-3.0, positive=False, tick=world.tick, conflict_delta=2.0)
        event.completed_tick = world.tick
        for participant_id in event.participant_ids:
            participant = world.citizens[participant_id]
            if participant.social_event_id == event.id:
                participant.social_event_id = None


def apply_interaction(
    world: World,
    a: Citizen,
    b: Citizen,
    building_id: int,
    *,
    positive: bool,
    strength: float = 1.0,
    emit: bool = True,
) -> None:
    if contact_forbidden(world, a.id, b.id):
        return
    relation_a = a.relationships.setdefault(b.id, Relationship(other_id=b.id))
    relation_b = b.relationships.setdefault(a.id, Relationship(other_id=a.id))
    old_label = relationship_label(relation_a)
    old_conflict_level = max(relation_a.conflict_level, relation_b.conflict_level)

    familiarity = world.rng.uniform(0.8, 2.2) * strength
    relation_a.familiarity = min(100.0, relation_a.familiarity + familiarity)
    relation_b.familiarity = min(100.0, relation_b.familiarity + familiarity)
    if positive:
        affection = world.rng.uniform(0.45, 1.35) * strength
        trust = affection * world.rng.uniform(0.35, 0.65)
        average_grudge = (a.grudge_tendency + b.grudge_tendency) / 200.0
        conflict_decay = -1.2 * strength * max(0.18, 1.0 - average_grudge * 0.78)
        _adjust_pair(
            a,
            b,
            affection=affection,
            trust=trust,
            positive=True,
            tick=world.tick,
            conflict_delta=conflict_decay,
        )
        a.needs.social = max(0.0, a.needs.social - 3.0 * strength)
        b.needs.social = max(0.0, b.needs.social - 3.0 * strength)
        a.needs.stress = max(0.0, a.needs.stress - 0.25 * strength)
        b.needs.stress = max(0.0, b.needs.stress - 0.25 * strength)
    else:
        affection = -world.rng.uniform(0.7, 1.9) * strength
        trust = -world.rng.uniform(0.2, 0.9) * strength
        volatility = max(conflict_propensity(a), conflict_propensity(b))
        mutual_reactivity = (conflict_propensity(a) + conflict_propensity(b)) / 2.0
        escalation_factor = 1.0 + volatility * 0.48 + mutual_reactivity * 0.18
        conflict_delta = ((abs(affection) + abs(trust) * 0.55) * 0.24 + strength * 0.28) * escalation_factor
        _adjust_pair(
            a,
            b,
            affection=affection,
            trust=trust,
            positive=False,
            tick=world.tick,
            conflict_delta=conflict_delta,
        )
        a.needs.stress = min(100.0, a.needs.stress + 1.2 * strength)
        b.needs.stress = min(100.0, b.needs.stress + 1.2 * strength)

    a.social_interactions_today += 1
    b.social_interactions_today += 1
    new_label = relationship_label(relation_a)
    building = world.buildings[building_id]

    if new_label != old_label and new_label in {"friend", "close_friend", "rival"}:
        if new_label in {"friend", "close_friend"}:
            world._emit(
                "friendship_formed",
                f"{a.full_name} et {b.full_name} deviennent plus proches.",
                citizen_ids=(a.id, b.id),
                building_id=building_id,
            )
        else:
            world._emit(
                "rivalry_formed",
                f"Une rivalité s'installe entre {a.full_name} et {b.full_name}.",
                citizen_ids=(a.id, b.id),
                building_id=building_id,
                severity="warning",
            )

    if not positive:
        new_conflict_level = max(relation_a.conflict_level, relation_b.conflict_level)
        if new_conflict_level > old_conflict_level:
            world.create_conflict_incident(a, b, building_id, new_conflict_level)
        elif emit and world.rng.random() < (
            0.003
            + new_conflict_level * 0.0015
            + max(conflict_propensity(a), conflict_propensity(b)) * 0.006
        ):
            if new_conflict_level >= 1:
                world.create_conflict_incident(a, b, building_id, new_conflict_level, repeat=True)
            else:
                world._emit(
                    "social_tension",
                    f"Un échange tendu oppose {a.full_name} et {b.full_name} à {building.name}.",
                    citizen_ids=(a.id, b.id),
                    building_id=building_id,
                    severity="warning",
                )
    elif emit and world.rng.random() < 0.06:
        world._emit(
            "positive_meeting",
            f"{a.full_name} échange agréablement avec {b.full_name} à {building.name}.",
            citizen_ids=(a.id, b.id),
            building_id=building_id,
        )


def _adjust_pair(
    a: Citizen,
    b: Citizen,
    *,
    affection: float,
    trust: float,
    positive: bool,
    tick: int,
    conflict_delta: float,
) -> None:
    relation_a = a.relationships.setdefault(b.id, Relationship(other_id=b.id))
    relation_b = b.relationships.setdefault(a.id, Relationship(other_id=a.id))
    for relationship in (relation_a, relation_b):
        relationship.affection = max(-100.0, min(100.0, relationship.affection + affection))
        relationship.trust = max(-100.0, min(100.0, relationship.trust + trust))
        relationship.last_interaction_tick = tick
        relationship.conflict_score = max(0.0, min(100.0, relationship.conflict_score + conflict_delta))
        if positive:
            relationship.positive_interactions += 1
            relationship.consecutive_negative_interactions = max(
                0, relationship.consecutive_negative_interactions - 1
            )
        else:
            relationship.negative_interactions += 1
            relationship.consecutive_negative_interactions += 1
        computed_level = _level_from_pressure(
            relationship.conflict_score,
            relationship.consecutive_negative_interactions,
        )
        if positive:
            relationship.conflict_level = min(relationship.conflict_level, computed_level)
        else:
            relationship.conflict_level = max(relationship.conflict_level, computed_level)
            relationship.last_conflict_tick = tick
        relationship.peak_conflict_level = max(relationship.peak_conflict_level, relationship.conflict_level)


def resolve_ambient_social_life(world: World) -> None:
    social_slot = world.total_minutes // 30
    if social_slot == world._last_social_slot:
        return
    world._last_social_slot = social_slot

    for building in world.buildings.values():
        occupants = sorted(building.occupants)
        if len(occupants) < 2:
            continue
        world.rng.shuffle(occupants)
        for citizen_a_id, citizen_b_id in zip(occupants[::2], occupants[1::2]):
            a = world.citizens[citizen_a_id]
            b = world.citizens[citizen_b_id]
            compatibility = (a.agreeableness + b.agreeableness) / 200.0
            stress_risk = (a.needs.stress + b.needs.stress) / 200.0
            volatility_risk = (conflict_propensity(a) + conflict_propensity(b)) / 2.0
            prior = a.relationships.get(b.id)
            interaction_probability = (
                0.30
                + (a.sociability + b.sociability) / 200.0 * 0.35
                + (min(100.0, prior.familiarity) / 100.0 * 0.12 if prior else 0.0)
                + volatility_risk * 0.12
                - (prior.conflict_level * 0.02 if prior else 0.0)
            )
            if world.rng.random() > max(0.24, min(0.78, interaction_probability)):
                continue
            prior_bonus = 0.08 if prior and prior.affection > 20 else 0.0
            conflict_penalty = min(0.05, prior.conflict_level * 0.014) if prior else 0.0
            negative_history = min(0.035, (prior.consecutive_negative_interactions * 0.0025)) if prior else 0.0
            positive_probability = (
                0.64 + compatibility * 0.20 + prior_bonus
                - stress_risk * 0.28 - conflict_penalty - negative_history
                - volatility_risk * 0.10
            )
            positive = world.rng.random() < max(0.40, min(0.93, positive_probability))
            strength = 1.0
            if not positive:
                strength += max(conflict_propensity(a), conflict_propensity(b)) * 0.30
            apply_interaction(world, a, b, building.id, positive=positive, strength=strength)


def resolve_household_life(world: World) -> None:
    household_slot = world.day * 24 + world.hour
    if world.hour != 20 or world.minute != 0 or household_slot == world._last_household_slot:
        return
    world._last_household_slot = household_slot

    emitted = 0
    for household in world.households.values():
        home = world.buildings[household.home_id]
        present_ids = [citizen_id for citizen_id in household.member_ids if citizen_id in home.occupants]
        if len(present_ids) < 2:
            household.cohesion = max(0.0, household.cohesion - 0.25)
            continue
        household.shared_meals += 1
        participants = [world.citizens[citizen_id] for citizen_id in present_ids]
        average_stress = sum(citizen.needs.stress for citizen in participants) / len(participants)
        active_conflict = max(
            (
                a.relationships.get(b.id, Relationship(other_id=b.id)).conflict_level
                for a, b in combinations(participants, 2)
            ),
            default=0,
        )
        average_volatility = sum(conflict_propensity(citizen) for citizen in participants) / len(participants)
        positive = world.rng.random() > max(
            0.08,
            average_stress / 150.0 + active_conflict * 0.06 + average_volatility * 0.05
            + household.financial_stress / 260.0,
        )
        for a, b in combinations(participants, 2):
            apply_interaction(world, a, b, home.id, positive=positive, strength=0.75, emit=False)
        if positive:
            household.cohesion = min(100.0, household.cohesion + 0.8)
            for citizen in participants:
                citizen.needs.social = max(0.0, citizen.needs.social - 4.0)
            if emitted < 2 and world.rng.random() < 0.18:
                world._emit(
                    "household_evening",
                    f"Le foyer de {home.name} partage une soirée calme.",
                    citizen_ids=tuple(present_ids),
                    building_id=home.id,
                )
                emitted += 1
        else:
            household.cohesion = max(0.0, household.cohesion - 1.4)
            household.conflicts += 1
            # Le couple le plus conflictuel porte l'escalade domestique.
            pairs = list(combinations(participants, 2))
            if pairs:
                a, b = max(
                    pairs,
                    key=lambda pair: pair[0].relationships.get(
                        pair[1].id, Relationship(other_id=pair[1].id)
                    ).conflict_score,
                )
                apply_interaction(world, a, b, home.id, positive=False, strength=1.25, emit=True)
            if emitted < 2:
                world._emit(
                    "household_conflict",
                    f"La tension monte dans le foyer de {home.name}.",
                    citizen_ids=tuple(present_ids[:3]),
                    building_id=home.id,
                    severity="warning",
                )
                emitted += 1


def friendship_counts(world: World) -> tuple[int, int, int, float]:
    friendship_pairs: set[tuple[int, int]] = set()
    rivalry_pairs: set[tuple[int, int]] = set()
    network_sizes: list[int] = []
    isolated = 0
    for citizen in world.citizens.values():
        social_links = 0
        for relationship in citizen.relationships.values():
            label = relationship_label(relationship)
            pair = tuple(sorted((citizen.id, relationship.other_id)))
            if label in {"friend", "close_friend"}:
                friendship_pairs.add(pair)
                social_links += 1
            elif label == "rival":
                rivalry_pairs.add(pair)
        network_sizes.append(social_links)
        if social_links == 0 and citizen.needs.social >= 55:
            isolated += 1
    average_network = sum(network_sizes) / max(1, len(network_sizes))
    return len(friendship_pairs), len(rivalry_pairs), isolated, average_network
