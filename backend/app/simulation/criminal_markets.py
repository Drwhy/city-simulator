from __future__ import annotations

from typing import TYPE_CHECKING

from .banking import available_funds, withdraw
from .models import (
    CrimeOperation,
    CrimeOperationStatus,
    CrimeOperationType,
    CrimeRole,
    CriminalMarket,
    IllegalCommodity,
    IllegalTransaction,
)

if TYPE_CHECKING:
    from .models import Citizen, CrimeOrganization
    from .world import World


MAX_ILLEGAL_TRANSACTIONS = 5_000
MARKET_HOURS = {8, 12, 17, 20, 23}
DRUGS = {
    IllegalCommodity.CANNABIS,
    IllegalCommodity.COCAINE,
    IllegalCommodity.SYNTHETIC_DRUGS,
}
COMMODITY_PROFILE: dict[IllegalCommodity, tuple[float, float, float]] = {
    # prix, effet addictif, dommage santé
    IllegalCommodity.CANNABIS: (18.0, 1.4, 0.35),
    IllegalCommodity.COCAINE: (72.0, 4.8, 1.4),
    IllegalCommodity.SYNTHETIC_DRUGS: (42.0, 6.2, 2.0),
    IllegalCommodity.STOLEN_GOODS: (55.0, 0.0, 0.0),
    IllegalCommodity.WEAPONS: (380.0, 0.0, 0.0),
    IllegalCommodity.COUNTERFEIT_GOODS: (32.0, 0.0, 0.0),
}


def initialize_criminal_markets(world: World) -> None:
    world.criminal_markets: dict[int, CriminalMarket] = {}
    world.illegal_transactions: dict[int, IllegalTransaction] = {}
    world._next_criminal_market_id = 1
    world._next_illegal_transaction_id = 1
    world._last_illegal_market_slot = -1
    world._last_illegal_market_day = 0
    world.illegal_sales_today = 0
    world.illegal_revenue_today = 0.0
    world.drug_sales_today = 0
    world.police_seizures_today = 0.0
    for organization in sorted(world.crime_organizations.values(), key=lambda item: item.id):
        for index, commodity in enumerate(organization.specialties):
            neighborhood_id = (
                organization.territory_ids[index % len(organization.territory_ids)]
                if organization.territory_ids
                else organization.territory_id
            )
            base_price = COMMODITY_PROFILE[commodity][0]
            market = CriminalMarket(
                id=world._next_criminal_market_id,
                organization_id=organization.id,
                neighborhood_id=neighborhood_id,
                commodity=commodity,
                supply=round(organization.inventory.get(commodity.value, 25.0), 2),
                demand=world.crime_rng.uniform(32.0, 74.0),
                unit_price=round(base_price * world.crime_rng.uniform(0.82, 1.24), 2),
                police_pressure=world.crime_rng.uniform(4.0, 22.0),
            )
            world._next_criminal_market_id += 1
            world.criminal_markets[market.id] = market


def update_criminal_markets(world: World) -> None:
    if world.minute == 15 and world.hour in MARKET_HOURS:
        slot = world.day * 24 + world.hour
        if slot != world._last_illegal_market_slot:
            world._last_illegal_market_slot = slot
            _run_market_slot(world)

    if world.hour == 3 and world.minute == 5 and world._last_illegal_market_day != world.day:
        world._last_illegal_market_day = world.day
        _close_market_day(world)

    if world.hour == 4 and world.minute == 20:
        _attempt_police_raid(world)

    if world.hour == 22 and world.minute == 30:
        _apply_substance_consequences(world)


def reset_criminal_market_day(world: World) -> None:
    world.illegal_sales_today = 0
    world.illegal_revenue_today = 0.0
    world.drug_sales_today = 0
    world.police_seizures_today = 0.0
    for market in world.criminal_markets.values():
        market.transactions_today = 0
        market.revenue_today = 0.0
        market.seized_today = 0.0


def _run_market_slot(world: World) -> None:
    markets = sorted(world.criminal_markets.values(), key=lambda item: item.id)
    # Une tentative par marché et par créneau : volume linéaire et coût borné.
    for market in markets:
        if not market.active or market.supply <= 0.05:
            continue
        organization = world.crime_organizations.get(market.organization_id)
        if organization is None or not organization.active:
            continue
        seller = _select_seller(world, organization)
        buyer = _select_buyer(world, market, organization)
        if seller is None or buyer is None:
            continue
        probability = min(
            0.9,
            0.18
            + market.demand / 150.0
            + buyer.addiction_level / 220.0
            + buyer.financial_stress / 600.0,
        )
        if world.crime_rng.random() >= probability:
            continue
        _complete_sale(world, market, organization, seller, buyer)


def _select_seller(world: World, organization: CrimeOrganization) -> Citizen | None:
    dealers = [
        world.citizens[citizen_id]
        for citizen_id, role in sorted(organization.role_by_member.items())
        if role in {CrimeRole.DEALER, CrimeRole.LIEUTENANT}
        and citizen_id in world.citizens
        and world.citizens[citizen_id].detained_until_tick is None
        and world.citizens[citizen_id].kidnapped_until_tick is None
    ]
    return world.crime_rng.choice(dealers) if dealers else None


def _select_buyer(
    world: World,
    market: CriminalMarket,
    organization: CrimeOrganization,
) -> Citizen | None:
    candidates = [
        citizen
        for citizen in world.citizens.values()
        if citizen.age >= 18
        and citizen.crime_organization_id != organization.id
        and citizen.detained_until_tick is None
        and citizen.kidnapped_until_tick is None
        and world.buildings[citizen.home_id].neighborhood_id == market.neighborhood_id
        and available_funds(citizen) >= market.unit_price * 0.25
    ]
    if not candidates:
        candidates = [
            citizen
            for citizen in world.citizens.values()
            if citizen.age >= 18
            and citizen.crime_organization_id != organization.id
            and citizen.detained_until_tick is None
            and available_funds(citizen) >= market.unit_price * 0.25
        ]
    if not candidates:
        return None
    ranked = sorted(
        candidates,
        key=lambda citizen: (
            _buyer_propensity(citizen, market.commodity),
            -citizen.id,
        ),
        reverse=True,
    )
    pool = ranked[: max(3, min(30, len(ranked) // 8 + 1))]
    return world.crime_rng.choice(pool)


def _buyer_propensity(citizen: Citizen, commodity: IllegalCommodity) -> float:
    if commodity in DRUGS:
        return (
            citizen.addiction_level * 1.4
            + citizen.substance_use_risk
            + citizen.needs.stress * 0.28
            + citizen.impulsivity * 0.18
            + citizen.financial_stress * 0.1
        )
    if commodity == IllegalCommodity.WEAPONS:
        return citizen.aggression * 0.55 + citizen.criminal_record_count * 12.0
    return citizen.financial_stress * 0.35 + citizen.impulsivity * 0.25


def _complete_sale(
    world: World,
    market: CriminalMarket,
    organization: CrimeOrganization,
    seller: Citizen,
    buyer: Citizen,
) -> None:
    quantity = min(
        market.supply,
        world.crime_rng.uniform(0.2, 1.2)
        * (1.0 + buyer.addiction_level / 140.0),
    )
    requested = round(quantity * market.unit_price, 2)
    paid = withdraw(
        world,
        buyer,
        min(requested, available_funds(buyer)),
        label=f"Achat illégal — {market.commodity.value}",
        transaction_type="illegal_purchase",
        counterparty_id=seller.id,
    )
    if paid <= 0.0:
        return
    quantity = round(quantity * paid / max(0.01, requested), 3)
    detected = world.crime_rng.random() < _detection_probability(world, market, seller)
    transaction = IllegalTransaction(
        id=world._next_illegal_transaction_id,
        tick=world.tick,
        organization_id=organization.id,
        market_id=market.id,
        seller_id=seller.id,
        buyer_id=buyer.id,
        commodity=market.commodity,
        quantity=quantity,
        unit_price=market.unit_price,
        total=paid,
        neighborhood_id=market.neighborhood_id,
        building_id=buyer.home_id,
        detected=detected,
    )
    world._next_illegal_transaction_id += 1
    world.illegal_transactions[transaction.id] = transaction
    _prune_transactions(world)

    market.supply = round(max(0.0, market.supply - quantity), 3)
    market.transactions_today += 1
    market.revenue_today = round(market.revenue_today + paid, 2)
    organization.inventory[market.commodity.value] = market.supply
    seller_share = round(paid * 0.18, 2)
    organization_share = round(paid - seller_share, 2)
    organization.treasury = round(organization.treasury + organization_share, 2)
    organization.revenue_today = round(organization.revenue_today + organization_share, 2)
    seller.criminal_income_today = round(seller.criminal_income_today + seller_share, 2)
    seller.money = round(seller.money + seller_share, 2)
    buyer.illegal_spending_today = round(buyer.illegal_spending_today + paid, 2)
    buyer.illegal_purchase_count += 1
    buyer.last_illegal_purchase_tick = world.tick
    if seller.id not in buyer.criminal_contact_ids:
        buyer.criminal_contact_ids.append(seller.id)
        buyer.criminal_contact_ids[:] = buyer.criminal_contact_ids[-20:]
    if buyer.id not in seller.criminal_contact_ids:
        seller.criminal_contact_ids.append(buyer.id)
        seller.criminal_contact_ids[:] = seller.criminal_contact_ids[-40:]
    world.illegal_sales_today += 1
    world.illegal_revenue_today = round(world.illegal_revenue_today + paid, 2)
    if market.commodity in DRUGS:
        world.drug_sales_today += 1
        _apply_drug_effect(world, buyer, market.commodity, quantity)
    if detected:
        _report_detected_sale(world, transaction, seller, buyer)
    elif world.crime_rng.random() < 0.12:
        world._emit(
            "illegal_market_sale",
            f"Une transaction clandestine de {market.commodity.value} a lieu dans le quartier #{market.neighborhood_id}.",
            citizen_ids=(seller.id, buyer.id),
            building_id=buyer.home_id,
            severity="warning",
        )


def _apply_drug_effect(
    world: World,
    buyer: Citizen,
    commodity: IllegalCommodity,
    quantity: float,
) -> None:
    _, addictive_effect, health_damage = COMMODITY_PROFILE[commodity]
    buyer.addiction_level = min(
        100.0,
        buyer.addiction_level + addictive_effect * quantity * world.crime_rng.uniform(0.65, 1.25),
    )
    buyer.substance_use_risk = min(100.0, buyer.substance_use_risk + addictive_effect * 0.35)
    buyer.health = max(5.0, buyer.health - health_damage * quantity)
    buyer.needs.stress = max(0.0, buyer.needs.stress - min(12.0, addictive_effect * 0.9))
    buyer.job_performance = max(0.0, buyer.job_performance - health_damage * 0.18)


def _report_detected_sale(
    world: World,
    transaction: IllegalTransaction,
    seller: Citizen,
    buyer: Citizen,
) -> None:
    incident_type = (
        "drug_dealing"
        if transaction.commodity in DRUGS
        else "arms_trafficking"
        if transaction.commodity == IllegalCommodity.WEAPONS
        else "illegal_goods_trafficking"
    )
    incident = world.create_incident(
        incident_type=incident_type,
        title="Transaction clandestine détectée",
        description=f"La police détecte une vente de {transaction.commodity.value} entre {seller.full_name} et {buyer.full_name}.",
        severity="danger" if transaction.commodity == IllegalCommodity.WEAPONS else "warning",
        citizen_ids=(seller.id, buyer.id),
        offender_id=seller.id,
        witness_ids=(buyer.id,),
        building_id=transaction.building_id,
        reported=True,
        lifetime_minutes=8 * 60,
        conflict_level=2,
    )
    transaction.incident_id = incident.id
    organization = world.crime_organizations[transaction.organization_id]
    organization.police_heat = min(100.0, organization.police_heat + 3.5)
    market = world.criminal_markets[transaction.market_id]
    market.police_pressure = min(100.0, market.police_pressure + 5.0)


def _detection_probability(world: World, market: CriminalMarket, seller: Citizen) -> float:
    neighborhood = world.neighborhoods.get(market.neighborhood_id)
    coverage = (
        min(100.0, neighborhood.patrol_minutes_today / 8.0)
        if neighborhood is not None
        else 0.0
    )
    organization = world.crime_organizations[market.organization_id]
    lookout_available = any(
        role == CrimeRole.LOOKOUT
        and citizen_id in world.citizens
        and world.citizens[citizen_id].detained_until_tick is None
        for citizen_id, role in organization.role_by_member.items()
    )
    lookout_bonus = 0.45 if lookout_available else 1.0
    concealment = organization.sophistication / 280.0
    return max(
        0.01,
        min(
            0.42,
            (0.025 + market.police_pressure / 500.0 + coverage / 900.0 - concealment * 0.08)
            * lookout_bonus,
        ),
    )


def _close_market_day(world: World) -> None:
    for market in world.criminal_markets.values():
        profile_price = COMMODITY_PROFILE[market.commodity][0]
        scarcity = max(0.72, min(1.8, 35.0 / max(8.0, market.supply)))
        demand_factor = 0.75 + market.demand / 135.0
        market.unit_price = round(
            profile_price * scarcity * demand_factor * world.crime_rng.uniform(0.96, 1.04),
            2,
        )
        market.demand = max(
            5.0,
            min(
                100.0,
                market.demand
                + world.crime_rng.uniform(-4.0, 4.0)
                + market.transactions_today * 0.35
                - market.police_pressure * 0.025,
            ),
        )
        market.police_pressure = max(0.0, market.police_pressure * 0.94)
        organization = world.crime_organizations[market.organization_id]
        if market.supply < 12.0:
            shipment = world.crime_rng.uniform(18.0, 55.0)
            market.supply = round(market.supply + shipment, 2)
            organization.inventory[market.commodity.value] = market.supply
            cost = round(shipment * COMMODITY_PROFILE[market.commodity][0] * 0.22, 2)
            organization.treasury = round(max(0.0, organization.treasury - cost), 2)
            organization.expenses_today = round(organization.expenses_today + cost, 2)
            _record_trafficking_operation(world, organization, market, shipment, cost)


def _record_trafficking_operation(
    world: World,
    organization: CrimeOrganization,
    market: CriminalMarket,
    quantity: float,
    cost: float,
) -> None:
    operation_type = (
        CrimeOperationType.DRUG_TRAFFICKING
        if market.commodity in DRUGS
        else CrimeOperationType.ARMS_TRAFFICKING
        if market.commodity == IllegalCommodity.WEAPONS
        else CrimeOperationType.STOLEN_GOODS
    )
    detected = world.crime_rng.random() < 0.08 + organization.police_heat / 400.0
    operation = CrimeOperation(
        id=world._next_crime_operation_id,
        organization_id=organization.id,
        operation_type=operation_type,
        status=CrimeOperationStatus.SUCCEEDED,
        planned_tick=world.tick,
        perpetrator_ids=[
            citizen_id
            for citizen_id, role in organization.role_by_member.items()
            if role == CrimeRole.SUPPLIER
        ][:2]
        or [organization.leader_id],
        victim_ids=[],
        building_id=None,
        amount=cost,
        started_tick=world.tick,
        resolved_tick=world.tick,
        outcome=f"approvisionnement de {quantity:.1f} unités",
        commodity=market.commodity,
        quantity=quantity,
        neighborhood_id=market.neighborhood_id,
        detected=detected,
    )
    world._next_crime_operation_id += 1
    world.crime_operations[operation.id] = operation
    organization.operation_ids.append(operation.id)
    if detected:
        organization.police_heat = min(100.0, organization.police_heat + 8.0)
        incident_type = (
            "drug_dealing" if market.commodity in DRUGS
            else "arms_trafficking" if market.commodity == IllegalCommodity.WEAPONS
            else "illegal_goods_trafficking"
        )
        incident = world.create_incident(
            incident_type=incident_type,
            title="Approvisionnement clandestin détecté",
            description=f"Un approvisionnement de {quantity:.1f} unités de {market.commodity.value} lié à {organization.name} est détecté.",
            severity="danger" if market.commodity == IllegalCommodity.WEAPONS else "warning",
            citizen_ids=tuple(operation.perpetrator_ids),
            offender_id=operation.perpetrator_ids[0],
            reported=True,
            lifetime_minutes=12 * 60,
            conflict_level=3,
        )
        operation.incident_id = incident.id
        for perpetrator_id in operation.perpetrator_ids:
            world.citizens[perpetrator_id].offenses_committed += 1


def _attempt_police_raid(world: World) -> None:
    candidates = [
        market
        for market in world.criminal_markets.values()
        if market.supply > 5.0
        and market.police_pressure + world.crime_organizations[market.organization_id].police_heat >= 72.0
    ]
    if not candidates:
        return
    market = max(
        candidates,
        key=lambda item: (
            item.police_pressure + world.crime_organizations[item.organization_id].police_heat,
            -item.id,
        ),
    )
    organization = world.crime_organizations[market.organization_id]
    chance = min(0.72, 0.15 + market.police_pressure / 180.0)
    if world.crime_rng.random() >= chance:
        return
    seized = round(market.supply * world.crime_rng.uniform(0.18, 0.55), 2)
    market.supply = round(max(0.0, market.supply - seized), 2)
    market.seized_today += seized
    market.police_pressure = min(100.0, market.police_pressure + 12.0)
    organization.inventory[market.commodity.value] = market.supply
    organization.police_heat = min(100.0, organization.police_heat + 10.0)
    world.police_seizures_today = round(world.police_seizures_today + seized, 2)
    suspects = [
        citizen_id
        for citizen_id, role in organization.role_by_member.items()
        if role in {CrimeRole.DEALER, CrimeRole.SUPPLIER, CrimeRole.LIEUTENANT}
    ][:5]
    incident = world.create_incident(
        incident_type="criminal_market_raid",
        title="Opération contre un trafic",
        description=f"La police saisit {seized:.1f} unités de {market.commodity.value} liées à {organization.name}.",
        severity="danger",
        citizen_ids=tuple(suspects),
        offender_id=suspects[0] if suspects else organization.leader_id,
        building_id=world.citizens[suspects[0]].home_id if suspects else None,
        reported=True,
        lifetime_minutes=12 * 60,
        conflict_level=3,
    )
    for transaction in sorted(
        (
            item
            for item in world.illegal_transactions.values()
            if item.market_id == market.id
        ),
        key=lambda item: item.id,
        reverse=True,
    )[:5]:
        if transaction.incident_id is None:
            transaction.incident_id = incident.id


def _apply_substance_consequences(world: World) -> None:
    for citizen in world.citizens.values():
        if citizen.addiction_level <= 0.0:
            continue
        days_since_purchase = (
            99
            if citizen.last_illegal_purchase_tick is None
            else (world.tick - citizen.last_illegal_purchase_tick) / (24 * 60)
        )
        if days_since_purchase >= 1.0:
            citizen.needs.stress = min(100.0, citizen.needs.stress + citizen.addiction_level * 0.025)
            citizen.needs.fatigue = min(100.0, citizen.needs.fatigue + citizen.addiction_level * 0.012)
        recovery = 0.18 if days_since_purchase >= 2.0 else 0.035
        citizen.addiction_level = max(0.0, citizen.addiction_level - recovery)
        if citizen.addiction_level >= 65.0:
            citizen.health = max(5.0, citizen.health - 0.08)
            citizen.job_performance = max(0.0, citizen.job_performance - 0.12)
            citizen.financial_stress = min(100.0, citizen.financial_stress + 0.18)


def _prune_transactions(world: World) -> None:
    overflow = len(world.illegal_transactions) - MAX_ILLEGAL_TRANSACTIONS
    if overflow <= 0:
        return
    for transaction_id in sorted(world.illegal_transactions)[:overflow]:
        del world.illegal_transactions[transaction_id]
