"""
Simple MVP route matching to prevent fake bus-location sharing.

The idea
--------
Each bus runs along a fixed corridor described by a list of
(latitude, longitude) points. When a passenger POSTs their GPS for a bus, we
measure how far they are from the *nearest* point on that bus's route:

  * within MAX_DISTANCE_METERS  -> accept and save the location
  * farther than that           -> reject with HTTP 400

This is intentionally simple (straight-line "great-circle" distance to each
point, no road snapping or map-matching) so it is easy to read and extend.

------------------------------------------------------------------------------
WHERE TO ADD ROUTE PATH DATA  (this is the part you edit)
------------------------------------------------------------------------------
Edit the ROUTE_PATHS dictionary below.

  * Key   = the bus's UUID as a string, exactly as it appears in
            Bus-Management-System-fronted/data/timeTable.json and in
            seed_timetable_buses.py.
  * Value = a list of (latitude, longitude) points along that bus's route.

Add as many points as you like along the roads the bus drives. More points =
better coverage. With the 1000 m radius below, points spaced roughly every
1-2 km give continuous coverage of the corridor.

If a bus_id is NOT listed in ROUTE_PATHS, the check is skipped and the location
is accepted (so buses without route data keep working). Set ALLOW_IF_NO_PATH
to False if you would rather reject buses that have no configured route.
"""

from __future__ import annotations

import math
import uuid

# A user is "on the route" if they are within this many metres of any point
# on the bus's path.
MAX_DISTANCE_METERS = 1000.0

# What to do when a bus has no route path configured (see note above).
ALLOW_IF_NO_PATH = True

# ---------------------------------------------------------------------------
# Route path data
# ---------------------------------------------------------------------------
# All current timetable buses run the Umlazi <-> Westmead corridor (Durban).
# These are approximate waypoints along that corridor — replace/extend them
# with the real road points for your routes.
UMLAZI_WESTMEAD_CORRIDOR: list[tuple[float, float]] = [
    (-29.9620, 30.8890),  # Umlazi side
    (-29.9447, 30.8842),
    (-29.9274, 30.8795),
    (-29.9100, 30.8747),
    (-29.8927, 30.8699),
    (-29.8753, 30.8652),
    (-29.8580, 30.8604),
    (-29.8407, 30.8556),
    (-29.8233, 30.8509),
    (-29.8060, 30.8460),  # Westmead side
]

# Real points collected for the Umlazi-2 -> Westmead bus.
UMLAZI_2_TO_WESTMEAD: list[tuple[float, float]] = [
    (-29.951854341036775, 30.858685294199038),
    (-29.954734135334903, 30.85866938522101),
    (-29.97089032009606, 30.872596354247854),
    (-29.968974956605848, 30.899924724412088),
    (-29.96918525161641, 30.900167502877498),
]

# bus_id (string) -> list of (latitude, longitude) points.
# The AM and PM buses share the same physical corridor (distance to the
# nearest point does not depend on travel direction), so they all map to the
# same path here. Give a bus its own list if its route differs.
ROUTE_PATHS: dict[str, list[tuple[float, float]]] = {
    "5e1c3169-a012-44d9-a18c-561f0fff3a10": UMLAZI_WESTMEAD_CORRIDOR,
    "cb02bb3f-97f2-4ef5-8c17-338e61e4fd7d": UMLAZI_WESTMEAD_CORRIDOR,
    "8f0358df-68a1-49bb-a9f9-6079c91324e7": UMLAZI_WESTMEAD_CORRIDOR,
    "b6f7e2c4-7d3a-4f9b-8e1c-5d6f7a8b9c20": UMLAZI_2_TO_WESTMEAD,  # Umlazi-2 -> Westmead
    "c9c4b6d8-2f3a-4b5c-8d9e-1a2b3c4d5e30": UMLAZI_WESTMEAD_CORRIDOR,
    "d3a7b8c9-1e2f-4a5b-9c8d-7e6f5a4b3c40": UMLAZI_WESTMEAD_CORRIDOR,
    "e6d5e4f3-2b1c-4d5e-9f8a-7b6c5d4e3f50": UMLAZI_WESTMEAD_CORRIDOR,
    "f1b2c3d4-5f6a-4b7c-8d9e-0f1a2b3c4d60": UMLAZI_WESTMEAD_CORRIDOR,
}


def haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two GPS points, in metres."""
    earth_radius_m = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_m * c


def distance_to_route_meters(
    bus_id: uuid.UUID | str,
    latitude: float,
    longitude: float,
) -> float | None:
    """Distance (metres) to the closest point on the bus's route.

    Returns None when the bus has no configured route path.
    """
    path = ROUTE_PATHS.get(str(bus_id))
    if not path:
        return None
    return min(
        haversine_meters(latitude, longitude, point_lat, point_lng)
        for point_lat, point_lng in path
    )


def is_location_on_route(
    bus_id: uuid.UUID | str,
    latitude: float,
    longitude: float,
) -> bool:
    """True if the GPS point is close enough to the bus's route to be accepted."""
    nearest = distance_to_route_meters(bus_id, latitude, longitude)
    if nearest is None:
        return ALLOW_IF_NO_PATH
    return nearest <= MAX_DISTANCE_METERS
