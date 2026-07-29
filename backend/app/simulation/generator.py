from __future__ import annotations

import random
import math

from .models import (
    Building,
    BuildingType,
    Citizen,
    Needs,
    Neighborhood,
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


def generate_neighborhoods() -> dict[int, Neighborhood]:
    return {
        1: Neighborhood(1, "Rives Nord-Ouest", 0, 0, 19, 11, 62.0, 68.0, 60.0),
        2: Neighborhood(2, "Centre Nord-Est", 20, 0, 39, 11, 78.0, 73.0, 72.0),
        3: Neighborhood(3, "Faubourgs Sud-Ouest", 0, 12, 19, 23, 48.0, 57.0, 48.0),
        4: Neighborhood(4, "Cité des Services", 20, 12, 39, 23, 72.0, 76.0, 67.0),
    }


def generate_buildings(citizen_count: int = 100) -> dict[int, Building]:
    buildings: dict[int, Building] = {}
    next_id = 1

    # Îlots résidentiels irréguliers, accrochés aux axes et espacés des pôles de service.
    home_positions = [
        (1, 1), (5, 2), (9, 1), (13, 2), (17, 1), (21, 2), (27, 1), (31, 2), (35, 1),
        (1, 6), (5, 7), (9, 6), (13, 7), (17, 6), (21, 6), (27, 6), (31, 6),
        (1, 15), (9, 15), (13, 15), (17, 15), (21, 15), (39, 15),
        (1, 20), (5, 20), (9, 20), (13, 20), (17, 20), (21, 20), (29, 20), (38, 20),
    ]
    for index, (x, y) in enumerate(home_positions, start=1):
        buildings[next_id] = Building(
            id=next_id,
            name=f"Résidence {index}",
            building_type=BuildingType.HOME,
            x=x,
            y=y,
            capacity=max(6, math.ceil(citizen_count / max(1, len(home_positions) - 5))) + (index % 3),
            rent_monthly=round(330.0 + (index % 7) * 58.0 + (20 - min(20, abs(x - 20))) * 4.0, 2),
            housing_condition=round(55.0 + (index * 17 % 40), 1),
            comfort=round(45.0 + (index * 13 % 43), 1),
            owner_type="municipal" if index % 6 == 0 else "private",
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
        ("Centre médical Saint-Roch", BuildingType.HOSPITAL, 36, 7, 16),
        ("Tribunal municipal", BuildingType.COURT, 26, 19, 12),
        ("Centre de détention", BuildingType.DETENTION_CENTER, 34, 19, 14),
        ("Banque des Quatre Quartiers", BuildingType.BANK, 6, 11, 18),
        ("Accueil municipal de nuit", BuildingType.SHELTER, 6, 15, 24),
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
                BuildingType.HOSPITAL: 3,
                BuildingType.COURT: 2,
                BuildingType.DETENTION_CENTER: 2,
                BuildingType.BANK: 3,
                BuildingType.SHELTER: 2,
                BuildingType.PARK: 0,
            }.get(building_type, 1),
            employee_capacity=max(4, (capacity - 4 if building_type in {BuildingType.OFFICE, BuildingType.FACTORY} else capacity) * max(1, math.ceil(citizen_count / 100))) if building_type not in {BuildingType.PARK, BuildingType.SHELTER} else (max(4, math.ceil(citizen_count / 120)) if building_type == BuildingType.SHELTER else 0),
            target_employees=max(4, (capacity - 4 if building_type in {BuildingType.OFFICE, BuildingType.FACTORY} else capacity) * max(1, math.ceil(citizen_count / 100))) if building_type not in {BuildingType.PARK, BuildingType.SHELTER} else (max(4, math.ceil(citizen_count / 120)) if building_type == BuildingType.SHELTER else 0),
            cash={
                BuildingType.OFFICE: 14_000.0,
                BuildingType.FACTORY: 12_000.0,
                BuildingType.SHOP: 8_000.0,
                BuildingType.CAFE: 6_000.0,
                BuildingType.PUBLIC: 20_000.0,
                BuildingType.POLICE: 25_000.0,
                BuildingType.HOSPITAL: 24_000.0,
                BuildingType.COURT: 18_000.0,
                BuildingType.DETENTION_CENTER: 20_000.0,
                BuildingType.BANK: 45_000.0,
                BuildingType.SHELTER: 16_000.0,
                BuildingType.PARK: 0.0,
            }.get(building_type, 6_000.0),
            fixed_cost_daily={
                BuildingType.OFFICE: 420.0,
                BuildingType.FACTORY: 360.0,
                BuildingType.SHOP: 220.0,
                BuildingType.CAFE: 160.0,
                BuildingType.PUBLIC: 260.0,
                BuildingType.POLICE: 340.0,
                BuildingType.HOSPITAL: 420.0,
                BuildingType.COURT: 300.0,
                BuildingType.DETENTION_CENTER: 360.0,
                BuildingType.BANK: 320.0,
                BuildingType.SHELTER: 280.0,
                BuildingType.PARK: 0.0,
            }.get(building_type, 160.0),
            food_stock=420.0 if building_type == BuildingType.SHOP else 0.0,
            goods_stock=220.0 if building_type == BuildingType.SHOP else 0.0,
            medical_beds=8 if building_type == BuildingType.HOSPITAL else 0,
            bank_reserves=120_000.0 if building_type == BuildingType.BANK else 0.0,
        )
        if building_type != BuildingType.PARK:
            building.target_employees = max(building.employees_required, round(building.employee_capacity * 0.55))
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
    # Réserve structurelle pour que le marché résidentiel puisse réellement fonctionner.
    initial_homes = homes[:-5] if len(homes) > 5 and sum(home.capacity for home in homes[:-5]) >= count else homes
    police_station = next(b for b in buildings.values() if b.building_type == BuildingType.POLICE)
    medical_center = next(b for b in buildings.values() if b.building_type == BuildingType.HOSPITAL)
    court = next(b for b in buildings.values() if b.building_type == BuildingType.COURT)
    detention_center = next(b for b in buildings.values() if b.building_type == BuildingType.DETENTION_CENTER)
    ordinary_workplaces = [
        b for b in buildings.values()
        if b.building_type in {
            BuildingType.OFFICE,
            BuildingType.FACTORY,
            BuildingType.SHOP,
            BuildingType.CAFE,
            BuildingType.PUBLIC,
            BuildingType.BANK,
            BuildingType.SHELTER,
        }
    ]

    job_by_type = {
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

    citizens: dict[int, Citizen] = {}
    home_load = {home.id: 0 for home in initial_homes}
    work_load = {work.id: 0 for work in [*ordinary_workplaces, police_station, medical_center, court, detention_center]}
    police_target = min(police_station.capacity, max(4, round(count * 0.08)))
    medical_target = min(8, max(4, round(count * 0.08)))
    court_target = min(4, max(2, round(count * 0.03)))
    detention_target = min(4, max(2, round(count * 0.03)))

    for citizen_id in range(1, count + 1):
        available_homes = [h for h in initial_homes if home_load[h.id] < h.capacity]
        home = rng.choice(available_homes)
        home_load[home.id] += 1

        if citizen_id <= police_target:
            workplace = police_station
        elif citizen_id <= police_target + medical_target:
            rng.choice(ordinary_workplaces)
            workplace = medical_center
        elif citizen_id <= police_target + medical_target + court_target:
            workplace = court
        elif citizen_id <= police_target + medical_target + court_target + detention_target:
            workplace = detention_center
        else:
            available_workplaces = [
                w for w in ordinary_workplaces if work_load[w.id] < w.employee_capacity
            ]
            workplace = rng.choice(available_workplaces) if available_workplaces else None
        if workplace:
            work_load[workplace.id] += 1
            job_title, salary = job_by_type[workplace.building_type]
            variants = {
                BuildingType.OFFICE: ["Analyste", "Comptable", "Développeur", "Assistant administratif", "Architecte"],
                BuildingType.FACTORY: ["Ouvrier", "Technicien", "Mécanicien", "Logisticien", "Contrôleur qualité"],
                BuildingType.SHOP: ["Vendeur", "Caissier", "Responsable de rayon", "Préparateur de commandes"],
                BuildingType.CAFE: ["Serveur", "Cuisinier", "Barista", "Responsable de salle"],
                BuildingType.PUBLIC: ["Agent municipal", "Urbaniste", "Bibliothécaire", "Jardinier municipal"],
                BuildingType.BANK: ["Conseiller bancaire", "Analyste crédit", "Caissier bancaire", "Responsable conformité"],
                BuildingType.SHELTER: ["Travailleur social", "Éducateur", "Agent d’accueil"],
            }.get(workplace.building_type)
            if variants:
                job_title = variants[(work_load[workplace.id] - 1) % len(variants)]
                salary += ((work_load[workplace.id] - 1) % len(variants)) * 3.0
            if workplace.building_type == BuildingType.HOSPITAL and work_load[workplace.id] % 3 == 1:
                job_title, salary = "Médecin", 145.0
            elif workplace.building_type == BuildingType.COURT and work_load[workplace.id] == 1:
                job_title, salary = "Juge", 148.0
        else:
            job_title, salary = None, 0.0

        if workplace is None:
            start_hour, end_hour, work_days = 0, 0, ()
        elif workplace.building_type == BuildingType.POLICE:
            # Deux équipes donnent une couverture réelle sans transformer les agents en robots.
            shift = (work_load[workplace.id] - 1) % 2
            start_hour, end_hour = ((6, 14) if shift == 0 else (14, 22))
            work_days = (1, 2, 3, 4, 5, 6, 7)
        elif workplace.building_type == BuildingType.HOSPITAL:
            shift = (work_load[workplace.id] - 1) % 2
            start_hour, end_hour = ((6, 14) if shift == 0 else (14, 22))
            work_days = (1, 2, 3, 4, 5, 6, 7)
        elif workplace.building_type == BuildingType.DETENTION_CENTER:
            shift = (work_load[workplace.id] - 1) % 2
            start_hour, end_hour = ((6, 14) if shift == 0 else (14, 22))
            work_days = (1, 2, 3, 4, 5, 6, 7)
        elif workplace.building_type == BuildingType.COURT:
            start_hour, end_hour, work_days = 8, 17, (1, 2, 3, 4, 5)
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

    medical_center = next((building for building in buildings.values() if building.building_type == BuildingType.HOSPITAL), None)
    if medical_center is not None:
        for _ in range(2):
            x, y = medical_center.entrance
            ambulance = Vehicle(
                id=next_id, vehicle_type=VehicleType.AMBULANCE, x=x, y=y, capacity=4,
                status=VehicleStatus.PARKED, current_building_id=medical_center.id,
            )
            vehicles[ambulance.id] = ambulance
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
