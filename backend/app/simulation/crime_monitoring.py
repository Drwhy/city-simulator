from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from .criminal_factions import relation_key
from .criminal_markets import DRUGS
from .models import CrimeOperationStatus, CrimeOperationType

if TYPE_CHECKING:
    from .world import World


def crime_overview(world: World) -> dict[str, object]:
    organizations = list(world.crime_organizations.values())
    markets = list(world.criminal_markets.values())
    transactions = list(world.illegal_transactions.values())
    active_kidnappings = sum(
        operation.operation_type == CrimeOperationType.KIDNAPPING
        and operation.status == CrimeOperationStatus.ACTIVE
        for operation in world.crime_operations.values()
    )
    exposed_citizens = {
        transaction.buyer_id for transaction in transactions
    }
    commodity_sales = Counter(transaction.commodity.value for transaction in transactions)
    commodity_revenue: Counter[str] = Counter()
    for transaction in transactions:
        commodity_revenue[transaction.commodity.value] += transaction.total
    contested = sum(
        1
        for neighborhood_id in world.neighborhoods
        if _territory_contestedness(world, neighborhood_id) >= 45.0
    )
    return {
        "tick": world.tick,
        "metrics": {
            "organizations": sum(organization.active for organization in organizations),
            "factionMembers": sum(len(organization.member_ids) for organization in organizations),
            "criminalMarkets": sum(market.active for market in markets),
            "operations": len(world.crime_operations),
            "organizedCrimesToday": world.organized_crimes_today,
            "activeKidnappings": active_kidnappings,
            "ransomPaidToday": round(world.ransom_paid_today, 2),
            "illegalSalesToday": world.illegal_sales_today,
            "drugSalesToday": world.drug_sales_today,
            "illegalRevenueToday": round(world.illegal_revenue_today, 2),
            "policeSeizuresToday": round(world.police_seizures_today, 2),
            "exposedCitizens": len(exposed_citizens),
            "dependentCitizens": sum(
                citizen.addiction_level >= 35.0 for citizen in world.citizens.values()
            ),
            "highRiskCitizens": sum(
                citizen.addiction_level >= 65.0 for citizen in world.citizens.values()
            ),
            "contestedNeighborhoods": contested,
            "detectedTransactions": sum(transaction.detected for transaction in transactions),
        },
        "organizations": [_organization_summary(world, organization.id) for organization in organizations],
        "markets": [_market_summary(world, market.id) for market in markets],
        "transactions": [
            _transaction_summary(world, transaction.id)
            for transaction in sorted(transactions, key=lambda item: item.id, reverse=True)[:150]
        ],
        "operations": [
            {
                "id": operation.id,
                "organizationId": operation.organization_id,
                "organizationName": world.crime_organizations[operation.organization_id].name,
                "type": operation.operation_type.value,
                "status": operation.status.value,
                "perpetratorIds": operation.perpetrator_ids,
                "victimIds": operation.victim_ids,
                "buildingId": operation.building_id,
                "neighborhoodId": operation.neighborhood_id,
                "commodity": operation.commodity.value if operation.commodity else None,
                "quantity": round(operation.quantity, 2),
                "amount": round(operation.amount, 2),
                "detected": operation.detected,
                "incidentId": operation.incident_id,
                "startedTick": operation.started_tick,
                "resolvedTick": operation.resolved_tick,
                "outcome": operation.outcome,
            }
            for operation in sorted(
                world.crime_operations.values(), key=lambda item: item.id, reverse=True
            )[:120]
        ],
        "relations": [
            _relation_summary(world, first_id, second_id)
            for first_id, second_id in sorted(world.crime_relations)
        ],
        "territories": [
            {
                "neighborhoodId": neighborhood_id,
                "neighborhoodName": world.neighborhoods[neighborhood_id].name,
                "contestedness": _territory_contestedness(world, neighborhood_id),
                "factions": sorted(
                    [
                        {
                            "organizationId": organization.id,
                            "name": organization.name,
                            "influence": round(
                                organization.influence_by_neighborhood.get(neighborhood_id, 0.0),
                                1,
                            ),
                        }
                        for organization in organizations
                    ],
                    key=lambda item: item["influence"],
                    reverse=True,
                ),
            }
            for neighborhood_id in sorted(world.neighborhoods)
        ],
        "history": list(world.crime_history),
        "commodities": [
            {
                "commodity": commodity,
                "transactions": commodity_sales[commodity],
                "revenue": round(commodity_revenue[commodity], 2),
                "supply": round(
                    sum(
                        market.supply
                        for market in markets
                        if market.commodity.value == commodity
                    ),
                    2,
                ),
            }
            for commodity in sorted(
                {market.commodity.value for market in markets}
                | set(commodity_sales)
            )
        ],
    }


def crime_faction_detail(world: World, organization_id: int) -> dict[str, object]:
    organization = world.crime_organizations[organization_id]
    summary = _organization_summary(world, organization_id)
    return {
        "kind": "crime_faction",
        **summary,
        "members": [
            {
                "id": citizen_id,
                "name": world.citizens[citizen_id].full_name,
                "role": organization.role_by_member[citizen_id].value,
                "criminalIncomeToday": round(
                    world.citizens[citizen_id].criminal_income_today, 2
                ),
                "offenses": world.citizens[citizen_id].offenses_committed,
                "arrests": world.citizens[citizen_id].arrests,
                "detained": world.citizens[citizen_id].detained_until_tick is not None,
            }
            for citizen_id in organization.member_ids
            if citizen_id in world.citizens
        ],
        "markets": [
            _market_summary(world, market.id)
            for market in world.criminal_markets.values()
            if market.organization_id == organization_id
        ],
        "operations": [
            operation
            for operation in crime_overview(world)["operations"]
            if operation["organizationId"] == organization_id
        ][:80],
        "transactions": [
            _transaction_summary(world, transaction.id)
            for transaction in sorted(
                world.illegal_transactions.values(), key=lambda item: item.id, reverse=True
            )
            if transaction.organization_id == organization_id
        ][:100],
        "relations": [
            _relation_summary(world, *key)
            for key in sorted(world.crime_relations)
            if organization_id in key
        ],
    }


def _organization_summary(world: World, organization_id: int) -> dict[str, object]:
    organization = world.crime_organizations[organization_id]
    markets = [
        market
        for market in world.criminal_markets.values()
        if market.organization_id == organization_id
    ]
    return {
        "id": organization.id,
        "name": organization.name,
        "factionType": organization.faction_type.value,
        "leaderId": organization.leader_id,
        "leaderName": world.citizens[organization.leader_id].full_name,
        "memberCount": len(organization.member_ids),
        "territoryId": organization.territory_id,
        "territoryIds": organization.territory_ids,
        "treasury": round(organization.treasury, 2),
        "revenueToday": round(organization.revenue_today, 2),
        "expensesToday": round(organization.expenses_today, 2),
        "notoriety": round(organization.notoriety, 1),
        "policeHeat": round(organization.police_heat, 1),
        "cohesion": round(organization.cohesion, 1),
        "violence": round(organization.violence, 1),
        "sophistication": round(organization.sophistication, 1),
        "recruitmentPressure": round(organization.recruitment_pressure, 1),
        "membersRecruited": organization.members_recruited,
        "specialties": [commodity.value for commodity in organization.specialties],
        "inventory": {
            commodity: round(quantity, 2)
            for commodity, quantity in organization.inventory.items()
        },
        "rivalIds": organization.rival_ids,
        "allyIds": organization.ally_ids,
        "marketCount": len(markets),
        "customers": len(
            {
                transaction.buyer_id
                for transaction in world.illegal_transactions.values()
                if transaction.organization_id == organization_id
            }
        ),
        "active": organization.active,
    }


def _market_summary(world: World, market_id: int) -> dict[str, object]:
    market = world.criminal_markets[market_id]
    organization = world.crime_organizations[market.organization_id]
    return {
        "id": market.id,
        "organizationId": organization.id,
        "organizationName": organization.name,
        "neighborhoodId": market.neighborhood_id,
        "neighborhoodName": world.neighborhoods[market.neighborhood_id].name,
        "commodity": market.commodity.value,
        "supply": round(market.supply, 2),
        "demand": round(market.demand, 1),
        "unitPrice": round(market.unit_price, 2),
        "policePressure": round(market.police_pressure, 1),
        "transactionsToday": market.transactions_today,
        "revenueToday": round(market.revenue_today, 2),
        "seizedToday": round(market.seized_today, 2),
        "drugMarket": market.commodity in DRUGS,
        "active": market.active,
    }


def _transaction_summary(world: World, transaction_id: int) -> dict[str, object]:
    transaction = world.illegal_transactions[transaction_id]
    return {
        "id": transaction.id,
        "tick": transaction.tick,
        "organizationId": transaction.organization_id,
        "organizationName": world.crime_organizations[transaction.organization_id].name,
        "marketId": transaction.market_id,
        "seller": {
            "id": transaction.seller_id,
            "name": world.citizens[transaction.seller_id].full_name,
        },
        "buyer": {
            "id": transaction.buyer_id,
            "name": world.citizens[transaction.buyer_id].full_name,
        },
        "commodity": transaction.commodity.value,
        "quantity": round(transaction.quantity, 3),
        "unitPrice": round(transaction.unit_price, 2),
        "total": round(transaction.total, 2),
        "neighborhoodId": transaction.neighborhood_id,
        "buildingId": transaction.building_id,
        "detected": transaction.detected,
        "incidentId": transaction.incident_id,
    }


def _relation_summary(world: World, first_id: int, second_id: int) -> dict[str, object]:
    relation = world.crime_relations[relation_key(first_id, second_id)]
    return {
        "firstId": first_id,
        "firstName": world.crime_organizations[first_id].name,
        "secondId": second_id,
        "secondName": world.crime_organizations[second_id].name,
        "tension": round(relation.tension, 1),
        "trust": round(relation.trust, 1),
        "conflictCount": relation.conflict_count,
        "lastConflictTick": relation.last_conflict_tick,
        "truceUntilTick": relation.truce_until_tick,
        "status": (
            "war"
            if relation.tension >= 72.0
            else "rivalry"
            if relation.tension >= 48.0
            else "cooperation"
            if relation.trust >= 8.0
            else "neutral"
        ),
    }


def _territory_contestedness(world: World, neighborhood_id: int) -> float:
    influences = sorted(
        (
            organization.influence_by_neighborhood.get(neighborhood_id, 0.0)
            for organization in world.crime_organizations.values()
        ),
        reverse=True,
    )
    if len(influences) < 2:
        return 0.0
    return round(min(100.0, influences[1] * 1.35 + max(0.0, 18.0 - (influences[0] - influences[1]))), 1)
