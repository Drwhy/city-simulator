from collections import Counter

from app.simulation.economy import (
    close_business,
    close_economic_day,
    refresh_open_positions,
    terminate_employment,
)
from app.simulation.models import BuildingType, BusinessStatus, JobApplicationStatus
from app.simulation.world import World


def test_unemployed_citizen_really_applies_and_is_hired() -> None:
    world = World(seed=7001, citizen_count=100)
    office = next(building for building in world.buildings.values() if building.building_type == BuildingType.OFFICE)
    candidate = next(
        citizen for citizen in world.citizens.values()
        if citizen.workplace_id not in {None, office.id}
        and world.buildings[citizen.workplace_id].building_type != BuildingType.POLICE
    )
    terminate_employment(world, candidate, "dismissed", "Fin de contrat de test.")
    current_staff = sum(1 for citizen in world.citizens.values() if citizen.workplace_id == office.id)
    office.employee_capacity = max(office.employee_capacity, current_staff + 1)
    office.target_employees = current_staff + 1
    refresh_open_positions(world, emit=False)

    world.hour = 6
    world.minute = 4
    world._last_labor_market_day = 0
    world.advance_one_minute()

    applications = [world.job_applications[application_id] for application_id in candidate.application_ids]
    assert applications
    assert applications[-1].status == JobApplicationStatus.ACCEPTED
    assert candidate.workplace_id == applications[-1].building_id
    assert candidate.job_search_active is False


def test_understaffed_business_opens_positions() -> None:
    world = World(seed=7002, citizen_count=100)
    factory = next(building for building in world.buildings.values() if building.building_type == BuildingType.FACTORY)
    current_staff = sum(1 for citizen in world.citizens.values() if citizen.workplace_id == factory.id)
    factory.employee_capacity = current_staff + 3
    factory.target_employees = current_staff + 3
    factory.business_status = BusinessStatus.HEALTHY
    refresh_open_positions(world, emit=False)
    assert factory.open_positions == 3


def test_deficit_business_reduces_staff() -> None:
    world = World(seed=7003, citizen_count=100)
    cafe = next(building for building in world.buildings.values() if building.building_type == BuildingType.CAFE)
    before = sum(1 for citizen in world.citizens.values() if citizen.workplace_id == cafe.id)
    assert before > cafe.employees_required
    cafe.deficit_days = 1
    cafe.payroll_today = 5_000.0
    cafe.revenue_today = 0.0
    cafe.productive_minutes_today = 0

    close_economic_day(world, completed_day=1)

    after = sum(1 for citizen in world.citizens.values() if citizen.workplace_id == cafe.id)
    assert after == before - 1
    assert cafe.business_status == BusinessStatus.DEFICIT
    assert any(event.event_type == "dismissed" for event in cafe.employment_events)


def test_unemployment_increases_financial_stress_and_limits_debt() -> None:
    world = World(seed=7004, citizen_count=30)
    household = next(iter(world.households.values()))
    members = [world.citizens[citizen_id] for citizen_id in household.member_ids]
    initial_stress = household.financial_stress
    for citizen in members:
        citizen.workplace_id = None
        citizen.job_title = None
        citizen.salary_daily = 0.0
        citizen.money = -citizen.overdraft_limit * 0.75
    household.recurring_expenses_today = 80.0

    close_economic_day(world, completed_day=1)

    assert household.financial_stress > initial_stress
    assert household.debt > 0
    assert all(citizen.money >= -citizen.overdraft_limit for citizen in members)
    assert all(citizen.financial_stress == household.financial_stress for citizen in members)


def test_private_business_can_close_but_public_employer_cannot() -> None:
    world = World(seed=7005, citizen_count=100)
    market = next(building for building in world.buildings.values() if building.building_type == BuildingType.SHOP)
    city_hall = next(building for building in world.buildings.values() if building.building_type == BuildingType.PUBLIC)

    close_business(world, market, "Trésorerie épuisée.")
    close_business(world, city_hall, "Test de fermeture publique.")

    assert market.business_status == BusinessStatus.CLOSED
    assert all(citizen.workplace_id != market.id for citizen in world.citizens.values())
    assert city_hall.business_status != BusinessStatus.CLOSED
    assert any(citizen.workplace_id == city_hall.id for citizen in world.citizens.values())


def test_no_employee_receives_two_salaries_for_the_same_day() -> None:
    world = World(seed=7006, citizen_count=100)
    world.run_minutes(7 * 24 * 60)
    salary_events = [event for event in world.events if event.event_type == "salary_paid"]
    payments = Counter((event.citizen_ids[0], event.day) for event in salary_events)
    assert salary_events
    assert max(payments.values()) == 1


def test_economy_save_resume_is_deterministic() -> None:
    world = World(seed=7007, citizen_count=100)
    world.run_minutes(5 * 24 * 60)
    restored = World.from_state(world.export_state())
    assert restored.snapshot() == world.snapshot()
    assert restored.export_state() == world.export_state()

    restored.run_minutes(24 * 60)
    world.run_minutes(24 * 60)
    assert restored.snapshot() == world.snapshot()
    assert restored.export_state() == world.export_state()


def test_thirty_day_economy_changes_jobs_without_stuck_workers() -> None:
    world = World(seed=12345, citizen_count=100)
    world.run_minutes(30 * 24 * 60)
    snapshot = world.snapshot()
    statuses = Counter(application.status for application in world.job_applications.values())
    employment_events = Counter(
        event.event_type
        for citizen in world.citizens.values()
        for event in citizen.employment_history
    )

    assert statuses[JobApplicationStatus.ACCEPTED] > 0
    assert employment_events["hired"] > 0
    assert employment_events["dismissed"] > 0
    assert 0 < snapshot["stats"]["unemploymentRate"] < 40
    assert all(len(building.financial_history) <= 30 for building in world.buildings.values())
    assert all(len(citizen.application_ids) <= 40 for citizen in world.citizens.values())

    station = next(building for building in world.buildings.values() if building.building_type == BuildingType.POLICE)
    officers = [citizen for citizen in world.citizens.values() if citizen.workplace_id == station.id]
    assert len(officers) >= station.employees_required
    assert all(citizen.job_title == "Policier municipal" for citizen in officers)
    assert all(
        citizen.trip_started_tick is None or world.tick - citizen.trip_started_tick < 12 * 60
        for citizen in world.citizens.values()
    )
