from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .housing import common_budget, home_summary, household_summary as housing_household_summary
from .justice import COURT_DAILY_CAPACITY, sentence_summary
from .models import BuildingType, VehicleType
from .social import conflict_label, conflict_propensity, relationship_label, temperament_label
from .work import building_operational, is_on_duty, staff_count

if TYPE_CHECKING:
    from .world import World


def building_detail(world: World, building_id: int) -> dict[str, Any]:
    building = world.buildings[building_id]
    employees = sorted(
        (citizen for citizen in world.citizens.values() if citizen.workplace_id == building.id),
        key=lambda citizen: (not is_on_duty(world, citizen), citizen.full_name),
    )
    occupants = [
        world.citizens[citizen_id]
        for citizen_id in sorted(building.occupants)
        if citizen_id in world.citizens
    ]
    return {
        "kind": "building",
        **world._building_to_dict(building),
        "employees": [
            {
                "id": employee.id,
                "name": employee.full_name,
                "jobTitle": employee.job_title,
                "onDuty": is_on_duty(world, employee),
                "shift": f"{employee.work_start_hour:02d}:00–{employee.work_end_hour:02d}:00",
                "performance": round(employee.job_performance, 1),
                "satisfaction": round(employee.job_satisfaction, 1),
            }
            for employee in employees
        ],
        "occupants": [
            {"id": occupant.id, "name": occupant.full_name} for occupant in occupants[:40]
        ],
        "housing": (
            home_detail(world, building_id)
            if building.building_type == BuildingType.HOME
            else None
        ),
        "healthcare": _healthcare_detail(world, building_id),
        "justice": _justice_detail(world, building_id),
        "services": {
            "operational": building_operational(world, building.id),
            "staffOnDuty": staff_count(world, building.id),
            "employeesRequired": building.employees_required,
            "foodStock": round(building.food_stock, 1),
            "goodsStock": round(building.goods_stock, 1),
            "revenueToday": round(building.revenue_today, 2),
        },
        "finance": {
            "status": building.business_status.value,
            "cash": round(building.cash, 2),
            "totalRevenue": round(building.total_revenue, 2),
            "payrollToday": round(building.payroll_today, 2),
            "fixedCostsToday": round(building.fixed_costs_today, 2),
            "resultToday": round(building.result_today, 2),
            "serviceLevel": round(building.service_level, 1),
            "employeeCapacity": building.employee_capacity,
            "targetEmployees": building.target_employees,
            "openPositions": building.open_positions,
            "financialHistory": [
                world._business_financial_to_dict(record)
                for record in reversed(building.financial_history)
            ][:14],
            "employmentHistory": [
                world._employment_record_to_dict(record)
                for record in reversed(building.employment_events)
            ][:20],
        },
    }


def _healthcare_detail(world: World, building_id: int) -> dict[str, Any] | None:
    building = world.buildings[building_id]
    if building.building_type != BuildingType.HOSPITAL:
        return None
    return {
        "beds": building.medical_beds,
        "queue": [
            world._health_case_summary(case_id)
            for case_id in building.medical_queue
            if case_id in world.health_cases
        ],
        "hospitalized": [
            world._citizen_ref(citizen_id) for citizen_id in sorted(building.hospitalized_ids)
        ],
        "patientsTreatedToday": building.patients_treated_today,
        "ambulances": [
            world._vehicle_summary(vehicle)
            for vehicle in world.vehicles.values()
            if vehicle.vehicle_type == VehicleType.AMBULANCE
        ],
    }



def _justice_detail(world: World, building_id: int) -> dict[str, Any] | None:
    building = world.buildings[building_id]
    if building.building_type == BuildingType.COURT:
        queue = sorted(
            (case for case in world.judicial_cases.values() if case.status.value == "awaiting_hearing"),
            key=lambda case: (-case.priority, case.hearing_tick, case.id),
        )
        return {
            "institutionType": "court",
            "dailyCapacity": COURT_DAILY_CAPACITY,
            "hearingsToday": world.hearings_today,
            "queue": [world._case_summary(case) for case in queue],
        }
    if building.building_type == BuildingType.DETENTION_CENTER:
        detained = [
            citizen for citizen in world.citizens.values()
            if citizen.current_detention_type == "judicial_detention"
            and citizen.detained_until_tick is not None
            and world.tick < citizen.detained_until_tick
        ]
        active = [
            sentence_summary(world, sentence) for sentence in world.sentences.values()
            if sentence.citizen_id in {citizen.id for citizen in detained}
            and sentence.status.value in {"active", "violated"}
        ]
        return {
            "institutionType": "detention_center",
            "capacity": building.capacity,
            "detained": [world._citizen_ref(citizen.id) for citizen in detained],
            "activeSentences": active,
        }
    return None

def home_detail(world: World, building_id: int) -> dict[str, Any]:
    building = world.buildings[building_id]
    households = [
        household for household in world.households.values() if household.home_id == building.id
    ]
    return {
        **home_summary(world, building),
        "residents": [
            world._citizen_ref(citizen.id)
            for citizen in sorted(world.citizens.values(), key=lambda citizen: citizen.id)
            if citizen.home_id == building.id
        ],
        "households": [
            housing_household_summary(world, household) for household in households
        ],
        "arrears": round(sum(household.rent_arrears for household in households), 2),
        "history": [
            world._housing_record_to_dict(record)
            for record in reversed(building.housing_history)
        ][:30],
    }


def household_detail(world: World, household_id: int) -> dict[str, Any]:
    household = world.households[household_id]
    home = world.buildings[household.home_id]
    return {
        "kind": "household",
        **world._household_summary(household),
        **housing_household_summary(world, household),
        "membersList": [world._citizen_ref(citizen_id) for citizen_id in household.member_ids],
        "expenses": {
            "recurringToday": round(household.recurring_expenses_today, 2),
            "foodToday": round(household.food_expenses_today, 2),
            "goodsToday": round(household.goods_expenses_today, 2),
            "rentDueToday": round(household.rent_due_today, 2),
            "rentPaidToday": round(household.rent_paid_today, 2),
        },
        "reserves": common_budget(world, household),
        "home": home_summary(world, home),
        "financialHistory": [
            world._household_financial_to_dict(record)
            for record in reversed(household.financial_history)
        ][:30],
        "housingHistory": [
            world._housing_record_to_dict(record)
            for record in reversed(household.housing_history)
        ][:30],
        "temporaryHostHouseholdId": household.temporary_host_household_id,
    }


def social_graph(world: World) -> dict[str, Any]:
    edges: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for citizen in world.citizens.values():
        for relationship in citizen.relationships.values():
            pair = tuple(sorted((citizen.id, relationship.other_id)))
            if pair in seen or relationship.familiarity < 8:
                continue
            seen.add(pair)
            edges.append(
                {
                    "source": pair[0],
                    "target": pair[1],
                    "status": relationship_label(relationship),
                    "affection": round(relationship.affection, 1),
                    "trust": round(relationship.trust, 1),
                    "familiarity": round(relationship.familiarity, 1),
                    "conflictLevel": relationship.conflict_level,
                    "conflictLabel": conflict_label(relationship),
                }
            )
    return {
        "tick": world.tick,
        "nodes": [_social_node(citizen) for citizen in world.citizens.values()],
        "edges": edges,
    }


def _social_node(citizen) -> dict[str, Any]:
    return {
        "id": citizen.id,
        "name": citizen.full_name,
        "householdId": citizen.household_id,
        "workplaceId": citizen.workplace_id,
        "friendCount": sum(
            relationship_label(relationship) in {"friend", "close_friend"}
            for relationship in citizen.relationships.values()
        ),
        "rivalCount": sum(
            relationship_label(relationship) == "rival"
            for relationship in citizen.relationships.values()
        ),
        "conflictPropensity": round(conflict_propensity(citizen) * 100, 1),
        "temperament": temperament_label(citizen),
    }