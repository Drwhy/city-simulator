from __future__ import annotations

from typing import TYPE_CHECKING

from .banking import available_funds, deposit, withdraw
from .economy import record_purchase, record_salary_payment, record_work_minute
from .models import Activity, BuildingType, BusinessStatus, CareStatus, Citizen, PoliceMeasure, TravelStage, VehicleStatus, VehicleType

if TYPE_CHECKING:
    from .world import World


def weekday(world: "World") -> int:
    """Jour de semaine simulé, 1=lundi et 7=dimanche."""
    return ((world.day - 1) % 7) + 1


def scheduled_today(world: "World", citizen: Citizen) -> bool:
    medically_available = (
        (citizen.medical_leave_until_tick is None or world.tick >= citizen.medical_leave_until_tick)
        and (citizen.incapacity_until_tick is None or world.tick >= citizen.incapacity_until_tick)
        and citizen.care_status in {CareStatus.NONE, CareStatus.RECOVERING}
    )
    return medically_available and citizen.workplace_id is not None and weekday(world) in citizen.work_days


def shift_bounds(citizen: Citizen) -> tuple[int, int]:
    return citizen.work_start_hour * 60, citizen.work_end_hour * 60


def shift_active(world: "World", citizen: Citizen) -> bool:
    if not scheduled_today(world, citizen):
        return False
    now = world.hour * 60 + world.minute
    start, end = shift_bounds(citizen)
    return start <= now < end


def shift_commute_window(world: "World", citizen: Citizen) -> bool:
    if not scheduled_today(world, citizen):
        return False
    now = world.hour * 60 + world.minute
    start, end = shift_bounds(citizen)
    return max(0, start - 50) <= now < end


def is_on_duty(world: "World", citizen: Citizen) -> bool:
    return (
        shift_active(world, citizen)
        and citizen.workplace_id is not None
        and citizen.destination_building_id == citizen.workplace_id
        and citizen.travel_stage == TravelStage.IDLE
        and citizen.activity == Activity.WORKING
        and (citizen.x, citizen.y) == world.buildings[citizen.workplace_id].entrance
        and not (citizen.detained_until_tick is not None and world.tick < citizen.detained_until_tick)
    )


def staff_count(world: "World", building_id: int) -> int:
    return sum(
        1 for citizen in world.citizens.values()
        if citizen.workplace_id == building_id and is_on_duty(world, citizen)
    )


def building_operational(world: "World", building_id: int) -> bool:
    building = world.buildings[building_id]
    if building.business_status == BusinessStatus.CLOSED:
        return False
    if building.building_type in {BuildingType.HOME, BuildingType.PARK}:
        return True
    return staff_count(world, building_id) >= building.employees_required


def needs_shopping(citizen: Citizen) -> bool:
    return citizen.food_units < 2.2 or citizen.goods_units < 0.75


def update_work_and_consumption(world: "World") -> None:
    market = next(
        (building for building in world.buildings.values() if building.building_type == BuildingType.SHOP),
        None,
    )

    for citizen in world.citizens.values():
        citizen.intoxication = max(0.0, citizen.intoxication - 0.035)
        current_building = world.buildings.get(citizen.destination_building_id)
        if (
            current_building is not None
            and current_building.building_type == BuildingType.CAFE
            and citizen.activity in {Activity.EATING, Activity.RELAXING}
            and world.hour >= 18
            and world.minute == citizen.id % 30
            and world.rng.random() < 0.42
        ):
            citizen.intoxication = min(100.0, citizen.intoxication + world.rng.uniform(8.0, 18.0))
            citizen.needs.stress = max(0.0, citizen.needs.stress - 2.0)

        if is_on_duty(world, citizen):
            citizen.minutes_worked_today += 1
            if citizen.needs.stress < 75:
                citizen.job_performance = min(100.0, citizen.job_performance + 0.002)
            else:
                citizen.job_performance = max(0.0, citizen.job_performance - 0.006)
            record_work_minute(world, citizen)

        # Un repas à domicile consomme le stock du foyer. Un cooldown évite les achats/repas répétés.
        if (
            citizen.activity in {Activity.AT_HOME, Activity.EATING}
            and citizen.destination_building_id == citizen.home_id
            and citizen.travel_stage == TravelStage.IDLE
            and citizen.needs.hunger >= 48
            and citizen.food_units >= 0.75
            and (citizen.last_meal_tick is None or world.tick - citizen.last_meal_tick >= 180)
        ):
            citizen.food_units = max(0.0, citizen.food_units - 0.75)
            citizen.needs.hunger = max(0.0, citizen.needs.hunger - 47.0)
            citizen.last_meal_tick = world.tick
            world._emit(
                "home_meal",
                f"{citizen.full_name} prépare un repas avec les provisions du foyer.",
                citizen_ids=(citizen.id,),
                building_id=citizen.home_id,
            )

        # Les biens courants s'usent lentement, sans simulation article par article.
        if world.minute == citizen.id % 60 and world.hour == 20 and citizen.goods_units > 0:
            citizen.goods_units = max(0.0, citizen.goods_units - 0.035)

        if (
            market is not None
            and citizen.activity == Activity.SHOPPING
            and citizen.destination_building_id == market.id
            and citizen.travel_stage == TravelStage.IDLE
            and (citizen.last_shopping_tick is None or world.tick - citizen.last_shopping_tick >= 120)
        ):
            if not building_operational(world, market.id):
                citizen.needs.stress = min(100.0, citizen.needs.stress + 3.0)
                citizen.last_decision_reason = "Le commerce manque de personnel et ne peut pas servir correctement."
                continue
            household = world.households.get(citizen.household_id) if citizen.household_id else None
            food_wanted = max(0.0, 8.0 - citizen.food_units)
            goods_wanted = max(0.0, 3.0 - citizen.goods_units)
            food_budget = max(
                0.0,
                (household.food_budget_daily - household.food_expenses_today) if household else 28.0,
            )
            goods_budget = max(
                0.0,
                (household.goods_budget_daily - household.goods_expenses_today) if household else 12.0,
            )
            if citizen.financial_stress >= 55.0 or citizen.workplace_id is None:
                goods_budget *= 0.35
                goods_wanted *= 0.5
            available_credit = available_funds(citizen, allow_credit=True)
            food_bought = min(food_wanted, market.food_stock, available_credit / 3.2, food_budget / 3.2)
            food_cost = round(food_bought * 3.2, 2)
            remaining_credit = max(0.0, available_credit - food_cost)
            goods_bought = min(goods_wanted, market.goods_stock, remaining_credit / 7.5, goods_budget / 7.5)
            goods_cost = round(goods_bought * 7.5, 2)
            cost = round(food_cost + goods_cost, 2)
            if cost <= 0:
                citizen.needs.stress = min(100.0, citizen.needs.stress + 2.0)
                continue
            paid = withdraw(world, citizen, cost, label=f"Achats à {market.name}", transaction_type="purchase", counterparty_id=market.id, allow_credit=True)
            if paid + 0.01 < cost:
                continue
            record_purchase(world, citizen, food_cost=food_cost, goods_cost=goods_cost)
            citizen.food_units += food_bought
            citizen.goods_units += goods_bought
            citizen.last_shopping_tick = world.tick
            citizen.shopping_visits += 1
            market.food_stock -= food_bought
            market.goods_stock -= goods_bought
            market.revenue_today = round(market.revenue_today + cost, 2)
            world.shop_sales_today = round(world.shop_sales_today + cost, 2)
            world.shopping_trips_today += 1
            world._emit(
                "shopping_completed",
                f"{citizen.full_name} achète des provisions et biens courants pour {cost:.2f} €.",
                citizen_ids=(citizen.id,),
                building_id=market.id,
            )

        # Paie en fin de shift, selon la présence effective.
        if citizen.workplace_id is None or citizen.last_paid_day == world.day:
            continue
        _, end = shift_bounds(citizen)
        now = world.hour * 60 + world.minute
        if not scheduled_today(world, citizen) or now < end:
            continue
        scheduled_minutes = max(1, (citizen.work_end_hour - citizen.work_start_hour) * 60)
        ratio = min(1.0, citizen.minutes_worked_today / scheduled_minutes)
        if ratio >= 0.45:
            pay = round(citizen.salary_daily * ratio, 2)
            deposit(world, citizen, pay, label=f"Salaire — {world.buildings[citizen.workplace_id].name}", transaction_type="salary", counterparty_id=citizen.workplace_id, cash_share=0.15)
            record_salary_payment(world, citizen, pay)
            if ratio >= 0.82:
                citizen.shifts_completed += 1
                citizen.job_satisfaction = min(100.0, citizen.job_satisfaction + 0.12)
            else:
                citizen.missed_shifts += 1
                citizen.job_performance = max(0.0, citizen.job_performance - 0.8)
            world._emit(
                "salary_paid",
                f"{citizen.full_name} reçoit {pay:.2f} € pour {citizen.minutes_worked_today} minutes travaillées.",
                citizen_ids=(citizen.id,),
                building_id=citizen.workplace_id,
            )
        else:
            citizen.missed_shifts += 1
            citizen.job_performance = max(0.0, citizen.job_performance - 2.0)
            citizen.job_satisfaction = max(0.0, citizen.job_satisfaction - 0.8)
        citizen.last_paid_day = world.day


def refresh_police_crews(world: "World") -> None:
    station = next(
        (building for building in world.buildings.values() if building.building_type == BuildingType.POLICE),
        None,
    )
    if station is None:
        return
    available_officers = [
        citizen for citizen in world.citizens.values()
        if citizen.workplace_id == station.id
        and is_on_duty(world, citizen)
        and citizen.active_vehicle_id is None
    ]
    available_ids = {citizen.id for citizen in available_officers}
    units = sorted(
        (vehicle for vehicle in world.vehicles.values() if vehicle.vehicle_type == VehicleType.POLICE),
        key=lambda vehicle: vehicle.id,
    )
    reserved: set[int] = set()
    for unit in units:
        if unit.status != VehicleStatus.PARKED:
            reserved.update(unit.crew_ids)
            continue
        valid = {citizen_id for citizen_id in unit.crew_ids if citizen_id in available_ids}
        unit.crew_ids = valid
        reserved.update(valid)
        for officer in available_officers:
            if len(unit.crew_ids) >= unit.capacity:
                break
            if officer.id in reserved:
                continue
            unit.crew_ids.add(officer.id)
            reserved.add(officer.id)


def apply_police_measure(
    world: "World",
    citizen: Citizen,
    incident_id: int,
    measure_type: str,
    duration_minutes: int,
    reason: str,
    officer_ids: tuple[int, ...],
) -> PoliceMeasure:
    labels = {
        "warning": "Rappel à la loi",
        "temporary_cell": "Mise en cellule",
        "sobering_cell": "Cellule de dégrisement",
        "custody": "Garde à vue",
        "medical_exam": "Examen médical préalable",
    }
    measure = PoliceMeasure(
        tick=world.tick,
        incident_id=incident_id,
        measure_type=measure_type,
        label=labels[measure_type],
        duration_minutes=duration_minutes,
        reason=reason,
        officer_ids=officer_ids,
    )
    citizen.police_history.append(measure)
    citizen.police_history[:] = citizen.police_history[-40:]
    if duration_minutes > 0:
        citizen.detained_until_tick = max(citizen.detained_until_tick or 0, world.tick + duration_minutes)
        citizen.current_detention_type = measure_type
        citizen.destination_building_id = next(
            building.id for building in world.buildings.values() if building.building_type == BuildingType.POLICE
        )
        citizen.planned_activity = Activity.DETAINED
    return measure
