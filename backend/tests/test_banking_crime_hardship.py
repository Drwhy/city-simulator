from app.simulation.banking import deposit, request_loan, withdraw
from app.simulation.crime import _execute_operation
from app.simulation.housing import become_homeless
from app.simulation.justice import attempt_contact_violation
from app.simulation.models import (
    BuildingType,
    CrimeOperationType,
    JudicialSentence,
    SentenceStatus,
    SentenceType,
)
from app.simulation.world import World


def test_city_supports_one_thousand_citizens_with_housing_and_job_variety() -> None:
    world = World(seed=12001, citizen_count=1000)
    homes = [building for building in world.buildings.values() if building.building_type == BuildingType.HOME]
    titles = {citizen.job_title for citizen in world.citizens.values() if citizen.job_title}
    assert len(world.citizens) == 1000
    assert sum(home.capacity for home in homes) >= 1000
    assert len(titles) >= 25
    assert all(citizen.workplace_id is None or citizen.workplace_id in world.buildings for citizen in world.citizens.values())
    buildings = list(world.buildings.values())
    assert not [(first.id, second.id) for index, first in enumerate(buildings) for second in buildings[index + 1:] if first.x < second.x + second.width and second.x < first.x + first.width and first.y < second.y + second.height and second.y < first.y + first.height]


def test_bank_ledger_covers_income_payments_credit_and_round_trip() -> None:
    world = World(seed=12002, citizen_count=30)
    citizen = world.citizens[1]
    starting = citizen.money + citizen.bank_balance
    deposit(world, citizen, 100, label="Test de salaire", transaction_type="salary")
    assert withdraw(world, citizen, 45, label="Test de paiement") == 45
    citizen.credit_score = 90
    loan = request_loan(world, citizen, 200, reason="dépense indispensable")
    assert loan == 200
    assert citizen.bank_debt == 200
    assert round(citizen.money + citizen.bank_balance, 2) == round(starting + 255, 2)
    restored = World.from_state(world.export_state())
    assert restored.citizens[1].bank_balance == citizen.bank_balance
    assert restored.citizens[1].bank_debt == citizen.bank_debt
    assert restored.citizens[1].banking_history == citizen.banking_history


def test_household_without_resources_becomes_homeless_at_the_shelter() -> None:
    world = World(seed=12003, citizen_count=30)
    household = next(iter(world.households.values()))
    previous_home = household.home_id
    become_homeless(world, household, "test de précarité")
    assert household.housing_status == "homeless"
    assert world.buildings[household.home_id].building_type in {BuildingType.SHELTER, BuildingType.PARK}
    assert all(world.citizens[citizen_id].is_homeless for citizen_id in household.member_ids)
    assert all(world.citizens[citizen_id].previous_home_id == previous_home for citizen_id in household.member_ids)


def test_mafia_can_generate_all_major_operation_families() -> None:
    world = World(seed=12004, citizen_count=250)
    organization = next(iter(world.crime_organizations.values()))
    for _ in range(80):
        _execute_operation(world, organization)
    operation_types = {operation.operation_type for operation in world.crime_operations.values()}
    assert operation_types >= {
        CrimeOperationType.THEFT,
        CrimeOperationType.ROBBERY,
        CrimeOperationType.EXTORTION,
        CrimeOperationType.KIDNAPPING,
    }
    assert any(operation.incident_id is not None for operation in world.crime_operations.values())


def test_restrained_citizen_can_attempt_and_trigger_a_violation() -> None:
    world = World(seed=12005, citizen_count=20)
    offender, victim = world.citizens[1], world.citizens[2]
    offender.impulsivity = offender.aggression = 100
    sentence = JudicialSentence(
        id=1,
        case_id=1,
        citizen_id=offender.id,
        sentence_type=SentenceType.RESTRAINING_ORDER,
        label="Interdiction de communication",
        status=SentenceStatus.ACTIVE,
        start_tick=world.tick,
        beneficiary_id=victim.id,
    )
    world.sentences[sentence.id] = sentence
    assert any(attempt_contact_violation(world, offender.id, victim.id) for _ in range(20))
    assert sentence.status == SentenceStatus.VIOLATED
    assert sentence.violation_count >= 1
    assert any(incident.incident_type == "restraining_order_violation" for incident in world.incidents.values())
