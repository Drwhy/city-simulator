from __future__ import annotations

from statistics import median
from typing import TYPE_CHECKING

from .models import (
    Activity,
    Building,
    BuildingType,
    BusinessFinancialRecord,
    BusinessStatus,
    Citizen,
    EmploymentRecord,
    HouseholdFinancialRecord,
    JobApplication,
    JobApplicationStatus,
    TravelStage,
)

if TYPE_CHECKING:
    from .world import World


EMPLOYER_TYPES = {
    BuildingType.OFFICE,
    BuildingType.FACTORY,
    BuildingType.SHOP,
    BuildingType.CAFE,
    BuildingType.PUBLIC,
    BuildingType.POLICE,
    BuildingType.HOSPITAL,
    BuildingType.COURT,
    BuildingType.DETENTION_CENTER,
    BuildingType.BANK,
    BuildingType.SHELTER,
}
PUBLIC_EMPLOYER_TYPES = {BuildingType.PUBLIC, BuildingType.POLICE, BuildingType.HOSPITAL, BuildingType.COURT, BuildingType.DETENTION_CENTER, BuildingType.SHELTER}
MIN_JOB_CHANGE_MINUTES = 7 * 24 * 60
MAX_APPLICATION_HISTORY = 40
MAX_FINANCIAL_HISTORY = 30
MAX_EMPLOYMENT_HISTORY = 40

JOB_PROFILES: dict[BuildingType, tuple[str, float]] = {
    BuildingType.OFFICE: ("Employé de bureau", 96.0),
    BuildingType.FACTORY: ("Ouvrier", 88.0),
    BuildingType.SHOP: ("Employé de commerce", 82.0),
    BuildingType.CAFE: ("Serveur", 78.0),
    BuildingType.PUBLIC: ("Agent municipal", 92.0),
    BuildingType.POLICE: ("Policier municipal", 108.0),
    BuildingType.HOSPITAL: ("Infirmier", 118.0),
    BuildingType.COURT: ("Greffier", 112.0),
    BuildingType.DETENTION_CENTER: ("Surveillant", 106.0),
    BuildingType.BANK: ("Conseiller bancaire", 116.0),
    BuildingType.SHELTER: ("Travailleur social", 98.0),
}


def is_employer(building: Building) -> bool:
    return building.building_type in EMPLOYER_TYPES


def is_public_employer(building: Building) -> bool:
    return building.building_type in PUBLIC_EMPLOYER_TYPES


def assigned_staff_count(world: World, building_id: int) -> int:
    return sum(1 for citizen in world.citizens.values() if citizen.workplace_id == building_id)


def job_offer(building: Building, employee_index: int = 0) -> tuple[str, float, int, int, tuple[int, ...]]:
    title, salary = JOB_PROFILES[building.building_type]
    variants = {
        BuildingType.OFFICE: ["Analyste", "Comptable", "Développeur", "Assistant administratif", "Architecte"],
        BuildingType.FACTORY: ["Ouvrier", "Technicien", "Mécanicien", "Logisticien", "Contrôleur qualité"],
        BuildingType.SHOP: ["Vendeur", "Caissier", "Responsable de rayon", "Préparateur de commandes"],
        BuildingType.CAFE: ["Serveur", "Cuisinier", "Barista", "Responsable de salle"],
        BuildingType.PUBLIC: ["Agent municipal", "Urbaniste", "Bibliothécaire", "Jardinier municipal"],
        BuildingType.BANK: ["Conseiller bancaire", "Analyste crédit", "Caissier bancaire", "Responsable conformité"],
        BuildingType.SHELTER: ["Travailleur social", "Éducateur", "Agent d’accueil"],
    }.get(building.building_type)
    if variants:
        title = variants[employee_index % len(variants)]
        salary += (employee_index % len(variants)) * 3.0
    if building.building_type in {BuildingType.POLICE, BuildingType.HOSPITAL, BuildingType.DETENTION_CENTER}:
        start_hour, end_hour = ((6, 14) if employee_index % 2 == 0 else (14, 22))
        work_days = (1, 2, 3, 4, 5, 6, 7)
    elif building.building_type == BuildingType.FACTORY:
        start_hour, end_hour = ((6, 14) if employee_index % 2 == 0 else (14, 22))
        work_days = (1, 2, 3, 4, 5)
    elif building.building_type == BuildingType.SHOP:
        start_hour, end_hour, work_days = 8, 19, (1, 2, 3, 4, 5, 6)
    elif building.building_type == BuildingType.CAFE:
        start_hour, end_hour, work_days = 11, 23, (2, 3, 4, 5, 6, 7)
    else:
        start_hour, end_hour, work_days = 8, 17, (1, 2, 3, 4, 5)
    return title, salary, start_hour, end_hour, work_days


def initialize_economy(world: World) -> None:
    for building in world.buildings.values():
        if not is_employer(building):
            continue
        building.employee_capacity = max(building.employees_required, building.employee_capacity or building.capacity)
        building.target_employees = max(
            building.employees_required,
            min(building.employee_capacity, building.target_employees or building.employee_capacity),
        )
        if building.cash == 0.0:
            building.cash = 8_000.0 if is_public_employer(building) else 6_000.0
        if building.fixed_cost_daily == 0.0:
            building.fixed_cost_daily = 160.0

    for citizen in world.citizens.values():
        if citizen.job_title:
            citizen.experience_by_job.setdefault(citizen.job_title, 20.0 + citizen.age * 0.35)
        else:
            citizen.job_search_active = True
            citizen.job_search_since_tick = world.tick

    for household in world.households.values():
        member_count = max(1, len(household.member_ids))
        household.overdraft_limit = max(household.overdraft_limit, member_count * 80.0)
        household.food_budget_daily = max(household.food_budget_daily, member_count * 8.0)
        household.goods_budget_daily = max(household.goods_budget_daily, member_count * 3.0)

    refresh_open_positions(world, emit=False)


def record_work_minute(world: World, citizen: Citizen) -> None:
    if citizen.workplace_id is None:
        return
    building = world.buildings[citizen.workplace_id]
    building.productive_minutes_today += 1
    if citizen.job_title:
        citizen.experience_by_job[citizen.job_title] = min(
            10_000.0,
            citizen.experience_by_job.get(citizen.job_title, 0.0) + 1.0 / 480.0,
        )


def record_salary_payment(world: World, citizen: Citizen, pay: float) -> None:
    citizen.income_today = round(citizen.income_today + pay, 2)
    if citizen.workplace_id is not None:
        employer = world.buildings[citizen.workplace_id]
        employer.payroll_today = round(employer.payroll_today + pay, 2)
        employer.cash = round(employer.cash - pay, 2)
    household = world.households.get(citizen.household_id) if citizen.household_id else None
    if household is not None:
        household.income_today = round(household.income_today + pay, 2)
        household.total_income = round(household.total_income + pay, 2)


def record_purchase(
    world: World,
    citizen: Citizen,
    *,
    food_cost: float,
    goods_cost: float,
) -> None:
    total = round(food_cost + goods_cost, 2)
    citizen.expenses_today = round(citizen.expenses_today + total, 2)
    household = world.households.get(citizen.household_id) if citizen.household_id else None
    if household is None:
        return
    household.food_expenses_today = round(household.food_expenses_today + food_cost, 2)
    household.goods_expenses_today = round(household.goods_expenses_today + goods_cost, 2)
    household.total_expenses = round(household.total_expenses + total, 2)


def update_economy(world: World) -> None:
    labor_slot = world.day
    if world.hour == 6 and world.minute == 5 and labor_slot != world._last_labor_market_day:
        world._last_labor_market_day = labor_slot
        run_labor_market(world)


def close_economic_day(world: World, completed_day: int) -> None:
    _close_household_finances(world, completed_day)
    for building in sorted(world.buildings.values(), key=lambda item: item.id):
        if not is_employer(building) or building.business_status == BusinessStatus.CLOSED:
            continue
        _close_business_finances(world, building, completed_day)

    for citizen in world.citizens.values():
        citizen.income_today = 0.0
        citizen.expenses_today = 0.0
    for building in world.buildings.values():
        building.revenue_today = 0.0
        building.payroll_today = 0.0
        building.fixed_costs_today = 0.0
        building.productive_minutes_today = 0
    for household in world.households.values():
        household.income_today = 0.0
        household.recurring_expenses_today = 0.0
        household.food_expenses_today = 0.0
        household.goods_expenses_today = 0.0

    _charge_recurring_household_expenses(world)
    refresh_open_positions(world)


def _close_business_finances(world: World, building: Building, completed_day: int) -> None:
    generated_revenue = _generated_revenue(building)
    building.revenue_today = round(building.revenue_today + generated_revenue, 2)
    if is_public_employer(building):
        public_funding = round(building.payroll_today + building.fixed_cost_daily + 120.0, 2)
        building.revenue_today = round(building.revenue_today + public_funding, 2)
        world.public_spending_total = round(world.public_spending_total + public_funding, 2)

    building.fixed_costs_today = round(building.fixed_cost_daily, 2)
    building.result_today = round(
        building.revenue_today - building.payroll_today - building.fixed_costs_today,
        2,
    )
    building.cash = round(building.cash + building.revenue_today - building.fixed_costs_today, 2)
    building.total_revenue = round(building.total_revenue + building.revenue_today, 2)
    expected_minutes = max(1, building.target_employees * 480)
    building.service_level = round(min(100.0, building.productive_minutes_today / expected_minutes * 100.0), 1)

    if building.result_today < -max(30.0, building.fixed_cost_daily * 0.2):
        building.deficit_days += 1
        building.business_status = BusinessStatus.DEFICIT
    elif building.cash < building.fixed_cost_daily * 5 or building.result_today < 0:
        building.deficit_days = max(0, building.deficit_days - 1)
        building.business_status = BusinessStatus.FRAGILE
    else:
        building.deficit_days = 0
        building.business_status = BusinessStatus.HEALTHY

    building.financial_history.append(
        BusinessFinancialRecord(
            day=completed_day,
            revenue=building.revenue_today,
            payroll=building.payroll_today,
            fixed_costs=building.fixed_costs_today,
            result=building.result_today,
            cash=building.cash,
            service_level=building.service_level,
            status=building.business_status,
        )
    )
    building.financial_history[:] = building.financial_history[-MAX_FINANCIAL_HISTORY:]

    employee_count = assigned_staff_count(world, building.id)
    if (
        not is_public_employer(building)
        and building.deficit_days >= 2
        and employee_count > building.employees_required
    ):
        _lay_off_one_employee(world, building, "Réduction d'effectif après plusieurs journées déficitaires.")
    if (
        not is_public_employer(building)
        and building.deficit_days >= 5
        and building.cash < 0
    ):
        close_business(world, building, "Trésorerie épuisée après une période déficitaire prolongée.")


def _generated_revenue(building: Building) -> float:
    worker_days = building.productive_minutes_today / 480.0
    rate = {
        BuildingType.OFFICE: 138.0,
        BuildingType.FACTORY: 126.0,
        BuildingType.SHOP: 12.0,
        BuildingType.CAFE: 72.0,
    }.get(building.building_type, 0.0)
    return round(worker_days * rate, 2)


def _close_household_finances(world: World, completed_day: int) -> None:
    for household in world.households.values():
        members = [world.citizens[citizen_id] for citizen_id in household.member_ids]
        household.debt = round(sum(max(0.0, -citizen.money) for citizen in members) + household.rent_arrears, 2)
        expenses = (
            household.recurring_expenses_today
            + household.food_expenses_today
            + household.goods_expenses_today
        )
        unemployed = sum(1 for citizen in members if citizen.workplace_id is None)
        pressure = (
            household.debt / max(1.0, household.overdraft_limit) * 45.0
            + max(0.0, expenses - household.income_today) / max(15.0, expenses) * 35.0
            + unemployed / max(1, len(members)) * 28.0
        )
        household.financial_stress = round(
            max(0.0, min(100.0, household.financial_stress * 0.72 + pressure * 0.28)),
            1,
        )
        household.financial_history.append(
            HouseholdFinancialRecord(
                day=completed_day,
                income=household.income_today,
                recurring_expenses=household.recurring_expenses_today,
                food_expenses=household.food_expenses_today,
                goods_expenses=household.goods_expenses_today,
                debt=household.debt,
                financial_stress=household.financial_stress,
            )
        )
        household.financial_history[:] = household.financial_history[-MAX_FINANCIAL_HISTORY:]
        for citizen in members:
            citizen.financial_stress = household.financial_stress
            citizen.needs.stress = min(100.0, citizen.needs.stress + household.financial_stress * 0.035)


def _charge_recurring_household_expenses(world: World) -> None:
    from .banking import available_funds, withdraw
    from .housing import charge_daily_rent
    for household in world.households.values():
        members = [world.citizens[citizen_id] for citizen_id in household.member_ids]
        rent_paid = charge_daily_rent(world, household)
        charge = round(8.0 + len(members) * 5.5, 2)
        remaining = charge
        for citizen in sorted(members, key=lambda item: available_funds(item, allow_credit=True), reverse=True):
            paid = withdraw(world, citizen, remaining, label="Charges courantes du foyer", transaction_type="household_charge", allow_credit=True)
            citizen.expenses_today = round(citizen.expenses_today + paid, 2)
            remaining = round(remaining - paid, 2)
            if remaining <= 0:
                break
        household.recurring_expenses_today = round(rent_paid + charge - remaining, 2)
        household.total_expenses = round(household.total_expenses + rent_paid + charge - remaining, 2)
        if remaining > 0:
            household.debt = round(household.debt + remaining, 2)


def refresh_open_positions(world: World, *, emit: bool = True) -> None:
    for building in sorted(world.buildings.values(), key=lambda item: item.id):
        if not is_employer(building):
            continue
        previous = building.open_positions
        if building.business_status == BusinessStatus.CLOSED:
            building.open_positions = 0
            continue
        desired = building.target_employees
        if building.business_status == BusinessStatus.DEFICIT and not is_public_employer(building):
            desired = building.employees_required
        building.open_positions = max(0, min(building.employee_capacity, desired) - assigned_staff_count(world, building.id))
        if emit and building.open_positions > previous:
            _record_building_event(
                building,
                EmploymentRecord(
                    tick=world.tick,
                    event_type="vacancy_opened",
                    label="Postes ouverts",
                    building_id=building.id,
                    job_title=JOB_PROFILES[building.building_type][0],
                    salary_daily=JOB_PROFILES[building.building_type][1],
                    reason="Effectif inférieur au besoin cible de l'employeur.",
                ),
            )
            world._emit(
                "vacancy_opened",
                f"{building.name} ouvre {building.open_positions} poste(s).",
                building_id=building.id,
            )


def run_labor_market(world: World) -> None:
    refresh_open_positions(world)
    open_buildings = [
        building for building in world.buildings.values()
        if is_employer(building)
        and building.business_status != BusinessStatus.CLOSED
        and building.open_positions > 0
    ]
    for citizen in sorted(world.citizens.values(), key=lambda item: item.id):
        if not _should_search_for_job(world, citizen) or _has_pending_application(world, citizen):
            continue
        citizen.job_search_active = True
        if citizen.job_search_since_tick is None:
            citizen.job_search_since_tick = world.tick
        offers = [
            (_application_score(world, citizen, building), building)
            for building in open_buildings
            if building.id != citizen.workplace_id
        ]
        if not offers:
            continue
        score, building = max(offers, key=lambda item: (item[0], -item[1].id))
        _submit_application(world, citizen, building, score)

    for building in sorted(open_buildings, key=lambda item: item.id):
        pending = sorted(
            (
                application for application in world.job_applications.values()
                if application.building_id == building.id
                and application.status == JobApplicationStatus.PENDING
            ),
            key=lambda item: (-item.score, item.submitted_tick, item.citizen_id),
        )
        hires_allowed = min(2, building.open_positions)
        for application in pending[:hires_allowed]:
            citizen = world.citizens[application.citizen_id]
            assign_employment(world, citizen, building, application)
        for application in pending[hires_allowed:]:
            application.status = JobApplicationStatus.REJECTED
            application.resolved_tick = world.tick
            application.reason = "Un autre profil correspondait mieux au poste disponible."
    refresh_open_positions(world, emit=False)


def _should_search_for_job(world: World, citizen: Citizen) -> bool:
    if citizen.detained_until_tick is not None and world.tick < citizen.detained_until_tick:
        return False
    if citizen.workplace_id is None:
        return True
    if world.buildings[citizen.workplace_id].building_type == BuildingType.POLICE:
        return False
    if world.tick - citizen.last_job_change_tick < MIN_JOB_CHANGE_MINUTES:
        return False
    return citizen.job_satisfaction < 34.0 or citizen.financial_stress > 78.0


def _has_pending_application(world: World, citizen: Citizen) -> bool:
    return any(
        application_id in world.job_applications
        and world.job_applications[application_id].status == JobApplicationStatus.PENDING
        for application_id in citizen.application_ids
    )


def _application_score(world: World, citizen: Citizen, building: Building) -> float:
    title, salary, start_hour, end_hour, _ = job_offer(building, assigned_staff_count(world, building.id))
    experience = citizen.experience_by_job.get(title, 0.0)
    distance = abs(citizen.x - building.entrance[0]) + abs(citizen.y - building.entrance[1])
    schedule_fit = 8.0 if 6 <= start_hour <= 9 and end_hour <= 19 else 2.0
    current_salary = max(1.0, citizen.salary_daily)
    salary_gain = (salary - current_salary) / current_salary * 18.0 if citizen.workplace_id else salary / 12.0
    criminal_record_penalty = min(18.0, citizen.criminal_record_count * 4.0 + citizen.probation_violations * 6.0)
    if building.building_type in {BuildingType.POLICE, BuildingType.COURT, BuildingType.DETENTION_CENTER}:
        criminal_record_penalty *= 1.4
    return round(
        experience * 0.65
        + citizen.job_performance * 0.34
        + citizen.agreeableness * 0.08
        + schedule_fit
        + salary_gain
        - distance * 0.55
        - criminal_record_penalty
        + world.rng.uniform(-2.0, 2.0),
        2,
    )


def _submit_application(world: World, citizen: Citizen, building: Building, score: float) -> JobApplication:
    title, salary, _, _, _ = job_offer(building, assigned_staff_count(world, building.id))
    application = JobApplication(
        id=world._next_job_application_id,
        citizen_id=citizen.id,
        building_id=building.id,
        job_title=title,
        salary_daily=salary,
        submitted_tick=world.tick,
        score=score,
    )
    world._next_job_application_id += 1
    world.job_applications[application.id] = application
    citizen.application_ids.append(application.id)
    if len(citizen.application_ids) > MAX_APPLICATION_HISTORY:
        removed_id = citizen.application_ids.pop(0)
        world.job_applications.pop(removed_id, None)
    world._emit(
        "job_application_submitted",
        f"{citizen.full_name} candidate auprès de {building.name}.",
        citizen_ids=(citizen.id,),
        building_id=building.id,
    )
    return application


def assign_employment(
    world: World,
    citizen: Citizen,
    building: Building,
    application: JobApplication | None = None,
) -> None:
    previous_building = world.buildings.get(citizen.workplace_id) if citizen.workplace_id else None
    if previous_building is not None:
        terminate_employment(
            world,
            citizen,
            "resignation",
            f"Changement vers une offre jugée plus adaptée chez {building.name}.",
        )
        world.resignations_today += 1

    employee_index = assigned_staff_count(world, building.id)
    title, salary, start_hour, end_hour, work_days = job_offer(building, employee_index)
    citizen.workplace_id = building.id
    citizen.job_title = title
    citizen.salary_daily = salary
    citizen.work_start_hour = start_hour
    citizen.work_end_hour = end_hour
    citizen.work_days = work_days
    citizen.employed_since_tick = world.tick
    citizen.last_job_change_tick = world.tick
    citizen.job_search_active = False
    citizen.job_search_since_tick = None
    citizen.job_satisfaction = max(42.0, citizen.job_satisfaction)
    citizen.experience_by_job.setdefault(title, 0.0)
    record = EmploymentRecord(
        tick=world.tick,
        event_type="hired",
        label="Recrutement",
        building_id=building.id,
        job_title=title,
        salary_daily=salary,
        reason="Candidature retenue selon l'expérience, le profil, le salaire, les horaires et la distance.",
    )
    _record_citizen_employment(citizen, record)
    _record_building_event(building, record)
    if application is not None:
        application.status = JobApplicationStatus.ACCEPTED
        application.resolved_tick = world.tick
        application.reason = "Candidature retenue."
    for other_id in citizen.application_ids:
        other = world.job_applications.get(other_id)
        if other is not None and other.id != (application.id if application else -1) and other.status == JobApplicationStatus.PENDING:
            other.status = JobApplicationStatus.WITHDRAWN
            other.resolved_tick = world.tick
            other.reason = "Retirée automatiquement : le citoyen possède déjà un emploi."
    world.hires_today += 1
    world._emit(
        "employee_hired",
        f"{citizen.full_name} est recruté par {building.name} comme {title}.",
        citizen_ids=(citizen.id,),
        building_id=building.id,
    )


def terminate_employment(world: World, citizen: Citizen, event_type: str, reason: str) -> None:
    if citizen.workplace_id is None:
        return
    building = world.buildings[citizen.workplace_id]
    record = EmploymentRecord(
        tick=world.tick,
        event_type=event_type,
        label="Licenciement" if event_type == "dismissed" else "Démission",
        building_id=building.id,
        job_title=citizen.job_title,
        salary_daily=citizen.salary_daily,
        reason=reason,
    )
    _record_citizen_employment(citizen, record)
    _record_building_event(building, record)
    if citizen.destination_building_id == building.id:
        world._cancel_active_trip(citizen)
        citizen.destination_building_id = citizen.home_id
        citizen.planned_activity = Activity.AT_HOME
        citizen.activity = Activity.AT_HOME
        citizen.travel_stage = TravelStage.IDLE
    citizen.workplace_id = None
    citizen.job_title = None
    citizen.salary_daily = 0.0
    citizen.work_start_hour = 0
    citizen.work_end_hour = 0
    citizen.work_days = ()
    citizen.job_search_active = True
    citizen.job_search_since_tick = world.tick
    citizen.last_job_change_tick = world.tick


def _lay_off_one_employee(world: World, building: Building, reason: str) -> None:
    employees = [citizen for citizen in world.citizens.values() if citizen.workplace_id == building.id]
    if len(employees) <= building.employees_required:
        return
    citizen = min(
        employees,
        key=lambda item: (item.job_performance * 0.7 + item.job_satisfaction * 0.3, item.id),
    )
    terminate_employment(world, citizen, "dismissed", reason)
    world.layoffs_today += 1
    world._emit(
        "employee_dismissed",
        f"{citizen.full_name} est licencié par {building.name} : {reason}",
        citizen_ids=(citizen.id,),
        building_id=building.id,
        severity="warning",
    )


def close_business(world: World, building: Building, reason: str) -> None:
    if building.business_status == BusinessStatus.CLOSED or is_public_employer(building):
        return
    for citizen in sorted(world.citizens.values(), key=lambda item: item.id):
        if citizen.workplace_id == building.id:
            terminate_employment(world, citizen, "dismissed", reason)
            world.layoffs_today += 1
    building.business_status = BusinessStatus.CLOSED
    building.service_level = 0.0
    building.open_positions = 0
    _record_building_event(
        building,
        EmploymentRecord(
            tick=world.tick,
            event_type="business_closed",
            label="Fermeture",
            building_id=building.id,
            job_title=None,
            salary_daily=0.0,
            reason=reason,
        ),
    )
    world._emit(
        "business_closed",
        f"{building.name} ferme : {reason}",
        building_id=building.id,
        severity="danger",
    )


def _record_citizen_employment(citizen: Citizen, record: EmploymentRecord) -> None:
    citizen.employment_history.append(record)
    citizen.employment_history[:] = citizen.employment_history[-MAX_EMPLOYMENT_HISTORY:]


def _record_building_event(building: Building, record: EmploymentRecord) -> None:
    building.employment_events.append(record)
    building.employment_events[:] = building.employment_events[-MAX_EMPLOYMENT_HISTORY:]


def economy_metrics(world: World) -> dict[str, float | int]:
    employers = [building for building in world.buildings.values() if is_employer(building)]
    employed = [citizen for citizen in world.citizens.values() if citizen.workplace_id is not None]
    unemployed = [citizen for citizen in world.citizens.values() if citizen.workplace_id is None]
    household_incomes = [
        household.income_today
        if household.income_today > 0
        else household.financial_history[-1].income if household.financial_history else 0.0
        for household in world.households.values()
    ]
    return {
        "unemployedCitizens": len(unemployed),
        "unemploymentRate": round(len(unemployed) / max(1, len(world.citizens)) * 100.0, 1),
        "openPositions": sum(building.open_positions for building in employers),
        "deficitBusinesses": sum(
            1 for building in employers if building.business_status == BusinessStatus.DEFICIT
        ),
        "closedBusinesses": sum(
            1 for building in employers if building.business_status == BusinessStatus.CLOSED
        ),
        "medianSalary": round(median([citizen.salary_daily for citizen in employed]), 2) if employed else 0.0,
        "medianHouseholdIncome": round(median(household_incomes), 2) if household_incomes else 0.0,
        "hiresToday": world.hires_today,
        "layoffsToday": world.layoffs_today,
        "resignationsToday": world.resignations_today,
        "publicSpendingTotal": round(world.public_spending_total, 2),
    }


def economy_overview(world: World) -> dict[str, object]:
    return {
        "tick": world.tick,
        "metrics": economy_metrics(world),
        "businesses": [
            {
                "id": building.id,
                "name": building.name,
                "type": building.building_type.value,
                "status": building.business_status.value,
                "cash": round(building.cash, 2),
                "revenueToday": round(building.revenue_today, 2),
                "payrollToday": round(building.payroll_today, 2),
                "fixedCostsToday": round(building.fixed_costs_today, 2),
                "resultToday": round(building.result_today, 2),
                "serviceLevel": round(building.service_level, 1),
                "employees": assigned_staff_count(world, building.id),
                "employeesRequired": building.employees_required,
                "employeeCapacity": building.employee_capacity,
                "openPositions": building.open_positions,
            }
            for building in sorted(world.buildings.values(), key=lambda item: item.id)
            if is_employer(building)
        ],
    }
