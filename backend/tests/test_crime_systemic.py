from app.simulation.crime import MAX_CRIME_HISTORY_DAYS, MAX_CRIME_OPERATIONS, _prune_operations
from app.simulation.criminal_factions import FACTION_IDENTITIES
from app.simulation.criminal_markets import DRUGS, MAX_ILLEGAL_TRANSACTIONS, _complete_sale
from app.simulation.models import CrimeOperation, CrimeOperationStatus, CrimeOperationType, CrimeRole
from app.simulation.world import World


def test_factions_scale_and_represent_distinct_criminal_models() -> None:
    world = World(seed=13001, citizen_count=2500)

    assert len(world.crime_organizations) == 8
    assert len({organization.faction_type for organization in world.crime_organizations.values()}) >= 6
    assert len(world.crime_relations) == 28
    assert all(organization.territory_ids for organization in world.crime_organizations.values())
    assert all(organization.specialties for organization in world.crime_organizations.values())
    assert all(CrimeRole.BOSS in organization.role_by_member.values() for organization in world.crime_organizations.values())
    assert len(FACTION_IDENTITIES) >= 16


def test_dealer_sale_moves_real_money_and_affects_an_ordinary_citizen() -> None:
    world = World(seed=13002, citizen_count=100)
    market = next(market for market in world.criminal_markets.values() if market.commodity in DRUGS)
    organization = world.crime_organizations[market.organization_id]
    seller_id = next(
        citizen_id for citizen_id, role in organization.role_by_member.items()
        if role in {CrimeRole.DEALER, CrimeRole.LIEUTENANT}
    )
    seller = world.citizens[seller_id]
    buyer = next(
        citizen for citizen in world.citizens.values()
        if citizen.age >= 18 and citizen.crime_organization_id != organization.id
    )
    buyer.money = max(buyer.money, 1000.0)
    funds_before = buyer.money + buyer.bank_balance + buyer.savings_balance
    treasury_before = organization.treasury
    seller_before = seller.money

    _complete_sale(world, market, organization, seller, buyer)

    transaction = next(reversed(world.illegal_transactions.values()))
    assert transaction.buyer_id == buyer.id
    assert transaction.seller_id == seller.id
    assert transaction.total > 0
    assert round(funds_before - (buyer.money + buyer.bank_balance + buyer.savings_balance), 2) == transaction.total
    assert round((organization.treasury - treasury_before) + (seller.money - seller_before), 2) == transaction.total
    assert buyer.illegal_purchase_count == 1
    assert seller.id in buyer.criminal_contact_ids
    assert buyer.addiction_level > 0


def test_illegal_markets_generate_volume_and_monitoring_depth() -> None:
    world = World(seed=13003, citizen_count=250)
    world.run_minutes(15 * 60)
    overview = world.get_crime_overview()

    assert overview["metrics"]["criminalMarkets"] >= len(world.crime_organizations)
    assert overview["metrics"]["illegalSalesToday"] > 0
    assert overview["transactions"]
    assert overview["territories"]
    assert overview["relations"]
    assert overview["commodities"]
    assert any(transaction["buyer"]["id"] != transaction["seller"]["id"] for transaction in overview["transactions"])


def test_crime_state_is_deterministic_and_round_trips() -> None:
    first = World(seed=13004, citizen_count=100)
    second = World(seed=13004, citizen_count=100)
    first.run_minutes(900)
    second.run_minutes(900)

    assert first.get_crime_overview() == second.get_crime_overview()
    restored = World.from_state(first.export_state())
    assert restored.export_state() == first.export_state()
    assert restored.get_crime_overview() == first.get_crime_overview()


def test_crime_histories_are_bounded() -> None:
    world = World(seed=13005, citizen_count=20)
    world.crime_history = [{"day": day} for day in range(MAX_CRIME_HISTORY_DAYS + 5)]
    world._reset_daily_counters()
    assert len(world.crime_history) == MAX_CRIME_HISTORY_DAYS

    organization = next(iter(world.crime_organizations.values()))
    for operation_id in range(1, MAX_CRIME_OPERATIONS + 15):
        world.crime_operations[operation_id] = CrimeOperation(
            id=operation_id,
            organization_id=organization.id,
            operation_type=CrimeOperationType.THEFT,
            status=CrimeOperationStatus.SUCCEEDED,
            planned_tick=0,
            perpetrator_ids=[],
            victim_ids=[],
            building_id=None,
            amount=0.0,
        )
        organization.operation_ids.append(operation_id)
    _prune_operations(world)
    assert len(world.crime_operations) == MAX_CRIME_OPERATIONS
    assert min(world.crime_operations) == 15

    assert MAX_ILLEGAL_TRANSACTIONS == 5000


def test_population_ceiling_world_initializes_with_5000_citizens() -> None:
    world = World(seed=13006, citizen_count=5000)
    assert len(world.citizens) == 5000
    assert len(world.crime_organizations) == 16
    assert len(world.criminal_markets) >= 32
