from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from .models import BusLine, BusStop

MAP_WIDTH = 42
MAP_HEIGHT = 24
HORIZONTAL_ROADS = (4, 9, 13, 14, 17, 19)
VERTICAL_ROADS = (3, 7, 11, 15, 19, 25, 29, 33, 37)


def generate_road_cells() -> set[tuple[int, int]]:
    return {
        (x, y)
        for x in range(MAP_WIDTH)
        for y in range(MAP_HEIGHT)
        if y in HORIZONTAL_ROADS or x in VERTICAL_ROADS
    }


def manhattan_path(
    start: tuple[int, int],
    end: tuple[int, int],
    *,
    horizontal_first: bool = True,
) -> list[tuple[int, int]]:
    if start == end:
        return []
    x, y = start
    target_x, target_y = end
    path: list[tuple[int, int]] = []

    def move_x() -> None:
        nonlocal x
        while x != target_x:
            x += 1 if x < target_x else -1
            path.append((x, y))

    def move_y() -> None:
        nonlocal y
        while y != target_y:
            y += 1 if y < target_y else -1
            path.append((x, y))

    if horizontal_first:
        move_x()
        move_y()
    else:
        move_y()
        move_x()
    return path


def nearest_cell(position: tuple[int, int], cells: Iterable[tuple[int, int]]) -> tuple[int, int]:
    x, y = position
    return min(cells, key=lambda cell: (abs(cell[0] - x) + abs(cell[1] - y), cell[1], cell[0]))


def road_path(
    start: tuple[int, int],
    end: tuple[int, int],
    road_cells: set[tuple[int, int]],
) -> list[tuple[int, int]]:
    if start == end:
        return []

    start_road = nearest_cell(start, road_cells)
    end_road = nearest_cell(end, road_cells)
    prefix = manhattan_path(start, start_road)
    suffix = manhattan_path(end_road, end)

    queue: deque[tuple[int, int]] = deque([start_road])
    previous: dict[tuple[int, int], tuple[int, int] | None] = {start_road: None}
    while queue:
        current = queue.popleft()
        if current == end_road:
            break
        x, y = current
        for neighbor in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if neighbor not in road_cells or neighbor in previous:
                continue
            previous[neighbor] = current
            queue.append(neighbor)

    if end_road not in previous:
        return manhattan_path(start, end)

    middle: list[tuple[int, int]] = []
    cursor = end_road
    while cursor != start_road:
        middle.append(cursor)
        parent = previous[cursor]
        if parent is None:
            break
        cursor = parent
    middle.reverse()
    return _deduplicate_path(prefix + middle + suffix)


def generate_bus_network(road_cells: set[tuple[int, int]]) -> tuple[dict[int, BusStop], dict[int, BusLine]]:
    stop_rows = [
        (1, "Nord-Ouest", 3, 4),
        (2, "Nord-Centre", 19, 4),
        (3, "Nord-Est", 37, 4),
        (4, "Quartier des bureaux", 25, 9),
        (5, "Centre-ville", 19, 13),
        (6, "Ateliers", 31, 13),
        (7, "Mairie", 27, 17),
        (8, "Sud-Est", 37, 19),
        (9, "Sud-Centre", 19, 19),
        (10, "Sud-Ouest", 3, 19),
    ]
    stops = {
        stop_id: BusStop(
            id=stop_id,
            name=name,
            x=x,
            y=y,
            line_id=1,
            sequence=index,
        )
        for index, (stop_id, name, x, y) in enumerate(stop_rows)
    }

    ordered = [stops[index] for index in sorted(stops)]
    route: list[tuple[int, int]] = [ordered[0].position]
    for current, following in zip(ordered, ordered[1:] + ordered[:1]):
        route.extend(road_path(current.position, following.position, road_cells))
    route = _deduplicate_path(route)
    if len(route) > 1 and route[-1] == route[0]:
        route.pop()

    line = BusLine(
        id=1,
        name="Ligne circulaire C1",
        stop_ids=[stop.id for stop in ordered],
        route=route,
        fare=2.0,
    )
    return stops, {line.id: line}


def forward_route_distance(route: list[tuple[int, int]], start: tuple[int, int], end: tuple[int, int]) -> int:
    start_indexes = [index for index, cell in enumerate(route) if cell == start]
    end_indexes = [index for index, cell in enumerate(route) if cell == end]
    if not start_indexes or not end_indexes:
        return len(route)
    return min((end_index - start_index) % len(route) for start_index in start_indexes for end_index in end_indexes)


def _deduplicate_path(path: list[tuple[int, int]]) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    for cell in path:
        if not result or result[-1] != cell:
            result.append(cell)
    return result
