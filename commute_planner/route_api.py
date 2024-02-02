from typing import Optional, Literal
from datetime import datetime, timedelta
import requests
from dataclasses import dataclass
from pytz import utc
from geopy import distance

from .utils import bold, italic

from . import settings

MOVEMENT_TYPES = {
    "SCHIFF": "🛥️",
    "RUFTAXI": "🚕",
    "BAHN": "🚝",
    "UBAHN": "🚇",
    "TRAM": "🚋",
    "SBAHN": "🚈",
    "BUS": "🚌",
    "REGIONAL_BUS": "🚏",
    "PEDESTRIAN": "🚶‍♂️"
}


@dataclass
class Location:
    name: str
    place: str
    coordinates: tuple

    def __str__(self) -> str:
        return f"{self.name}, {self.place}"


@dataclass
class MovementType:
    movement_type: str
    name: str
    destination: str

    @property
    def symbol(self) -> str:
        return MOVEMENT_TYPES.get(self.movement_type, self.movement_type)

    def __str__(self) -> str:
        return f"{self.symbol} {self.name}{f' ({self.destination})' if self.destination else ''}"


@dataclass
class RoutePart:
    departure: datetime
    arrival: datetime
    start: Location
    end: Location
    movement_type: MovementType

    def __str__(self) -> str:
        return f"{self.departure.strftime('%H:%M')} - {self.arrival.strftime('%H:%M')} {self.movement_type} ➜ {self.end.name}"
    
    @property
    def calendar_repr(self) -> str:
        return f"{self.departure.strftime('%H:%M')} {bold(self.movement_type)} ➜ {self.end.name}"


class Route:
    def __init__(self, route_data):
        self.parts = []

        for part in route_data["parts"]:
            self.parts.append(
                RoutePart(
                    datetime.fromisoformat(part["from"]["plannedDeparture"]).replace(tzinfo=utc),
                    (datetime.fromisoformat(part["to"]["plannedDeparture"]) + timedelta(
                        minutes=int(part["to"].get("arrivalDelayInMinutes", 0)))).replace(tzinfo=utc),
                    Location(
                        part["from"]["name"],
                        part["from"]["place"],
                        (part["from"]["latitude"], part["from"]["longitude"])
                    ),
                    Location(
                        part["to"]["name"],
                        part["to"]["place"],
                        (part["to"]["latitude"], part["to"]["longitude"])
                    ),
                    MovementType(
                        part["line"]["transportType"],
                        part["line"]["label"],
                        part["line"]["destination"]
                    )
                )
            )

    def __str__(self) -> str:
        return '\n'.join([str(route_part) for route_part in self.parts])
    
    @property
    def calendar_description(self) -> str:
        return '\n'.join([route_part.calendar_repr for route_part in self.parts]) + f"\n\n{bold('Ankunft:')} " + self.parts[-1].arrival.strftime('%H:%M') + f" Uhr\n" + italic(f"Dauer: {self.duration}")
    
    @property
    def calendar_summary(self) -> str:
        movements = [
            f"{part.movement_type.symbol} {part.movement_type.name}" 
            if part.movement_type.movement_type != "PEDESTRIAN"
            else f"{part.movement_type.symbol} {int((part.arrival - part.departure).total_seconds() // 60)}"
            for part in self.parts
        ]
        return ' ➜ '.join(movements)

    @property
    def departure(self) -> datetime:
        return self.parts[0].departure

    @property
    def arrival(self) -> datetime:
        return self.parts[-1].arrival
    
    @property
    def duration(self) -> timedelta:
        return self.arrival - self.departure


def get_routes(origin, destination, arrival_time, type_: Literal["ARRIVAL", "DEPARTURE"]):
    response = requests.get("https://www.mvg.de/api/fib/v2/connection", params={
        "originLatitude": origin[0],
        "originLongitude": origin[1],
        "destinationLatitude": destination[0],
        "destinationLongitude": destination[1],
        "routingDateTime": (arrival_time - timedelta(hours=1)).isoformat() + "Z",
        "routingDateTimeIsArrival": type_ == "ARRIVAL",
        "transportTypes": "SCHIFF,RUFTAXI,BAHN,UBAHN,TRAM,SBAHN,BUS,REGIONAL_BUS"
    }, headers={"User-Agent": settings.USER_AGENT})
    try:
        response_json = response.json()
    except Exception as ex:
        print(ex)
        print(response.status_code, response.headers, response.content)
        raise Exception("Invalid MVG API Response") from ex

    return [Route(route) for route in response_json]


def get_best_route(routes: list[Route], time: datetime, type_: Literal["ARRIVAL", "DEPARTURE"]) -> Route:
    if type_ == "ARRIVAL":
        filtered_routes = filter(lambda route: route.arrival <= time.replace(tzinfo=utc), routes)
        return max(filtered_routes, key=lambda route: route.departure)

    filtered_routes = filter(lambda route: route.departure >= time.replace(tzinfo=utc), routes)
    return min(filtered_routes, key=lambda route: route.arrival)


def get_route(origin, destination, time, type_: Literal["ARRIVAL", "DEPARTURE"] = "ARRIVAL") -> Optional[Route]:
    if(distance.distance(origin, destination).kilometers <= settings.MIN_ROUTE_DISTANCE):
        return None
    best_route = get_best_route(get_routes(origin, destination, time, type_), time, type_)
    if best_route is None:  # If no route could be found, check 30 min earlier/later
        if type_ == "ARRIVAL":
            return get_route(origin, destination, time - timedelta(minutes=30), type_)
        return get_route(origin, destination, time + timedelta(minutes=30), type_)
    return best_route
