from __future__ import annotations

import random

from .models import (
    Building,
    BuildingType,
    Citizen,
    Needs,
    Vehicle,
    VehicleStatus,
    VehicleType,
)

FIRST_NAMES = [
    "Alice", "Karim", "Sophie", "Lucas", "Camille", "Malik", "Léa", "Hugo",
    "Nina", "Arthur", "Sarah", "Mehdi", "Emma", "Jules", "Chloé", "Rayan",
    "Inès", "Thomas", "Manon", "Gabriel",
]

LAST_NAMES = [
    "Martin", "Bernard", "Dubois", "Thomas", "Robert", "Richard", "Petit",
    "Durand", "Leroy", "Moreau", "Simon", "Laurent", "Michel", "Garcia",
    "David", "Bertrand", "Roux", "Vincent", "Fournier", "Morel",
]


def generate_buildings() -> dict[int, Building]:
    buildings: dict[int, Building] = {}
    next_id = 1

    home_positions = [
        (2, 2), (6, 2), (10, 2), (14, 2), (18, 2),
        (2, 7), (6, 7), (10, 7), (14, 7), (18, 7),
        (2, 17), (6, 17), (10, 17), (14, 17), (18, 17),
        (24, 2), (28, 2), (32, 2), (36, 2),
        (24, 17), (28, 17), (32, 17), (36, 17),
    ]
    for index, (x, y) in enumerate(home_positions, start=1):
        buildings[next_id] = Building(
            id=next_id,
            name=f"Résidence {index}",
            building_type=BuildingType.HOME,
            x=x,
            y=y,
            capacity=6,
        )
        next_id += 1

    workplaces = [
        ("Bureaux Horizon", BuildingType.OFFICE, 24, 7, 24),
        ("Ateliers du Sud", BuildingType.FACTORY, 30, 11, 30),
        ("Marché Central", BuildingType.SHOP, 18, 11, 16),
        ("Café Central", BuildingType.CAFE, 22, 11, 14),
        ("Parc des Tilleuls", BuildingType.PARK, 10, 11, 40),
        ("Mairie", BuildingType.PUBLIC, 26, 15, 12),
        ("Commissariat central", BuildingType.POLICE, 34, 15, 12),
    ]
    for name, building_type, x, y, capacity in workplaces:
        building = Building(
            id=next_id,
            name=name,
            building_type=building_type,
            x=x,
            y=y,
            width=3 if building_type != BuildingType.PARK else 5,
            height=2 if building_type != BuildingType.PARK else 3,
            capacity=capacity,
            employees_required={
                BuildingType.OFFICE: 4,
                BuildingType.FACTORY: 5,
                BuildingType.SHOP: 2,
                BuildingType.CAFE: 1,
                BuildingType.PUBLIC: 2,
                BuildingType.POLICE: 2,
                BuildingType.PARK: 0,
            }.get(building_type, 1),
            food_stock=420.0 if building_type == BuildingType.SHOP else 0.0,
            goods_stock=220.0 if building_type == BuildingType.SHOP else 0.0,
        )
        buildings[next_id] = building
        next_id += 1

    return buildings


def generate_citizens(
    buildings: dict[int, Building],
    *,
    count: int = 100,
    seed: int = 12345,
) -> dict[int, Citizen]:
    rng = random.Random(seed)
    homes = [b for b in buildings.values() if b.building_type == BuildingType.HOME]
    police_station = next(b for b in buildings.values() if b.building_type == BuildingType.POLICE)
    ordinary_workplaces = [
        b for b in buildings.values()
        if b.building_type in {
            BuildingType.OFFICE,
            BuildingType.FACTORY,
            BuildingType.SHOP,
            BuildingType.CAFE,
            BuildingType.PUBLIC,
        }
    ]

    job_by_type = {
        BuildingType.OFFICE: ("Employé de bureau", 96.0),
        BuildingType.FACTORY: ("Ouvrier", 88.0),
        BuildingType.SHOP: ("Employé de commerce", 82.0),
        BuildingType.CAFE: ("Serveur", 78.0),
        BuildingType.PUBLIC: ("Agent municipal", 92.0),
        BuildingType.POLICE: ("Policier municipal", 108.0),
    }

    citizens: dict[int, Citizen] = {}
    home_load = {home.id: 0 for home in homes}
    work_load = {work.id: 0 for work in [*ordinary_workplaces, police_station]}
    police_target = min(police_station.capacity, max(4, round(count * 0.08)))

    for citizen_id in range(1, count + 1):
        available_homes = [h for h in homes if home_load[h.id] < h.capacity]
        home = rng.choice(available_homes)
        home_load[home.id] += 1

        if citizen_id <= police_target:
            workplace = police_station
        else:
            available_workplaces = [
                w for w in ordinary_workplaces if work_load[w.id] < w.capacity
            ]
            workplace = rng.choice(available_workplaces) if available_workplaces else None
        if workplace:
            work_load[workplace.id] += 1
            job_title, salary = job_by_type[workplace.building_type]
        else:
            job_title, salary = None, 0.0

        if workplace is None:
            start_hour, end_hour, work_days = 0, 0, ()
        elif workplace.building_type == BuildingType.POLICE:
            # Deux équipes donnent une couverture réelle sans transformer les agents en robots.
            shift = (work_load[workplace.id] - 1) % 2
            start_hour, end_hour = ((6, 14) if shift == 0 else (14, 22))
            work_days = (1, 2, 3, 4, 5, 6, 7)
        elif workplace.building_type == BuildingType.FACTORY:
            shift = citizen_id % 2
            start_hour, end_hour = ((6, 14) if shift == 0 else (14, 22))
            work_days = (1, 2, 3, 4, 5)
        elif workplace.building_type == BuildingType.SHOP:
            start_hour, end_hour, work_days = 8, 19, (1, 2, 3, 4, 5, 6)
        elif workplace.building_type == BuildingType.CAFE:
            start_hour, end_hour, work_days = 11, 23, (2, 3, 4, 5, 6, 7)
        else:
            start_hour, end_hour, work_days = 8, 17, (1, 2, 3, 4, 5)

        x, y = home.entrance
        citizens[citizen_id] = Citizen(
            id=citizen_id,
            first_name=rng.choice(FIRST_NAMES),
            last_name=rng.choice(LAST_NAMES),
            age=rng.randint(18, 67),
            home_id=home.id,
            workplace_id=workplace.id if workplace else None,
            job_title=job_title,
            salary_daily=salary,
            x=x,
            y=y,
            money=round(rng.uniform(150.0, 1200.0), 2),
            needs=Needs(
                hunger=rng.uniform(5.0, 20.0),
                fatigue=rng.uniform(5.0, 20.0),
                stress=rng.uniform(0.0, 15.0),
                social=rng.uniform(5.0, 30.0),
            ),
            work_start_hour=start_hour,
            work_end_hour=end_hour,
            work_days=work_days,
            job_performance=rng.uniform(48.0, 86.0),
            job_satisfaction=rng.uniform(38.0, 82.0),
            food_units=rng.uniform(2.0, 8.0),
            goods_units=rng.uniform(0.5, 3.5),
        )
        home.occupants.add(citizen_id)

    return citizens


def generate_vehicles(
    citizens: dict[int, Citizen],
    buildings: dict[int, Building],
    bus_route: list[tuple[int, int]],
    *,
    seed: int,
) -> dict[int, Vehicle]:
    rng = random.Random(seed ^ 0xC17C0DE)
    vehicles: dict[int, Vehicle] = {}
    next_id = 1

    # Un taux volontairement modéré afin que marche et bus restent visibles.
    for citizen in citizens.values():
        ownership_probability = 0.46 if citizen.age >= 25 else 0.22
        if rng.random() >= ownership_probability:
            continue
        home = buildings[citizen.home_id]
        x, y = home.entrance
        vehicle = Vehicle(
            id=next_id,
            vehicle_type=VehicleType.CAR,
            owner_id=citizen.id,
            x=x,
            y=y,
            capacity=4,
            status=VehicleStatus.PARKED,
            current_building_id=home.id,
        )
        vehicles[vehicle.id] = vehicle
        citizen.owned_vehicle_id = vehicle.id
        next_id += 1

    if not bus_route:
        return vehicles

    for index in range(2):
        route_index = (index * len(bus_route)) // 2
        x, y = bus_route[route_index]
        bus = Vehicle(
            id=next_id,
            vehicle_type=VehicleType.BUS,
            x=x,
            y=y,
            capacity=18,
            status=VehicleStatus.IN_SERVICE,
            line_id=1,
            route=list(bus_route),
            route_index=route_index,
        )
        vehicles[bus.id] = bus
        next_id += 1

    police_station = next(
        (building for building in buildings.values() if building.building_type == BuildingType.POLICE),
        None,
    )
    if police_station is not None:
        for _ in range(2):
            x, y = police_station.entrance
            patrol = Vehicle(
                id=next_id,
                vehicle_type=VehicleType.POLICE,
                x=x,
                y=y,
                capacity=2,
                status=VehicleStatus.PARKED,
                current_building_id=police_station.id,
            )
            vehicles[patrol.id] = patrol
            next_id += 1

    return vehicles


def generate_households(
    citizens: dict[int, Citizen],
    buildings: dict[int, Building],
    *,
    seed: int,
):
    from .models import Household, Relationship

    rng = random.Random(seed ^ 0x50C1A1)
    households: dict[int, Household] = {}
    residents_by_home: dict[int, list[int]] = {}
    for citizen in citizens.values():
        residents_by_home.setdefault(citizen.home_id, []).append(citizen.id)

    next_id = 1
    for home_id, member_ids in sorted(residents_by_home.items()):
        member_ids.sort()
        household = Household(
            id=next_id,
            home_id=home_id,
            member_ids=member_ids,
            cohesion=rng.uniform(48.0, 76.0),
        )
        households[household.id] = household
        for citizen_id in member_ids:
            citizen = citizens[citizen_id]
            citizen.household_id = household.id
            citizen.sociability = rng.uniform(25.0, 85.0)
            citizen.agreeableness = rng.uniform(25.0, 85.0)
            citizen.spontaneity = rng.uniform(20.0, 90.0)
            # La majorité de la population reste peu conflictuelle, mais une minorité
            # possède un tempérament nettement plus volatil et peut accélérer une escalade.
            citizen.aggression = rng.triangular(4.0, 72.0, 22.0)
            citizen.impulsivity = rng.triangular(8.0, 88.0, 34.0)
            citizen.grudge_tendency = rng.triangular(5.0, 82.0, 28.0)
            if rng.random() < 0.12:
                citizen.aggression = rng.uniform(68.0, 94.0)
                citizen.impulsivity = rng.uniform(62.0, 96.0)
                citizen.grudge_tendency = rng.uniform(52.0, 91.0)
                citizen.agreeableness = min(citizen.agreeableness, rng.uniform(12.0, 42.0))

        # Les membres d'un même foyer commencent avec un lien réel, mais pas uniforme.
        for index, citizen_a_id in enumerate(member_ids):
            for citizen_b_id in member_ids[index + 1:]:
                affection = rng.uniform(18.0, 58.0)
                trust = rng.uniform(22.0, 62.0)
                familiarity = rng.uniform(55.0, 92.0)
                citizens[citizen_a_id].relationships.setdefault(
                    citizen_b_id,
                    Relationship(
                        other_id=citizen_b_id,
                        familiarity=familiarity,
                        affection=affection,
                        trust=trust,
                    ),
                )
                citizens[citizen_b_id].relationships.setdefault(
                    citizen_a_id,
                    Relationship(
                        other_id=citizen_a_id,
                        familiarity=familiarity,
                        affection=affection,
                        trust=trust,
                    ),
                )
        next_id += 1

    # Quelques liens professionnels préexistants rendent la ville sociale dès le premier jour.
    workers_by_place: dict[int, list[int]] = {}
    for citizen in citizens.values():
        if citizen.workplace_id is not None:
            workers_by_place.setdefault(citizen.workplace_id, []).append(citizen.id)
    for worker_ids in workers_by_place.values():
        worker_ids.sort()
        for citizen_id in worker_ids:
            candidates = [other_id for other_id in worker_ids if other_id != citizen_id]
            rng.shuffle(candidates)
            for other_id in candidates[:2]:
                if other_id in citizens[citizen_id].relationships:
                    continue
                familiarity = rng.uniform(18.0, 42.0)
                tense = rng.random() < 0.12
                affection = rng.uniform(-22.0, -10.0) if tense else rng.uniform(-2.0, 24.0)
                trust = rng.uniform(-8.0, 6.0) if tense else rng.uniform(8.0, 28.0)
                negative_interactions = 2 if tense else 0
                citizens[citizen_id].relationships[other_id] = Relationship(
                    other_id=other_id,
                    familiarity=familiarity,
                    affection=affection,
                    trust=trust,
                    negative_interactions=negative_interactions,
                )
                citizens[other_id].relationships.setdefault(
                    citizen_id,
                    Relationship(
                        other_id=citizen_id,
                        familiarity=familiarity,
                        affection=affection,
                        trust=trust,
                        negative_interactions=negative_interactions,
                    ),
                )

    return households
