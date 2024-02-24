import asyncio
from typing import Optional, Literal
from datetime import datetime, timedelta
import requests
from dataclasses import dataclass

from pytz import utc
from geopy import distance

from .calendar_client import bold, italic

from . import settings

MOVEMENT_TYPES = {
    "PEDESTRIAN": "🚶‍",
    "RUFTAXI": "🚕",
    "BUS": "🚌",
    "REGIONAL_BUS": "🚏",
    "BAHN": "🚝",
    "UBAHN": "🚇",
    "TRAM": "🚋",
    "SBAHN": "🚈",
    "ICE": "🚆",
    "EC_IC": "🚅",
    "IR": "🚅",
    "REGIONAL": "🚈",
    "SCHIFF": "🛥️",
    "UNKNOWN": "🐎"
}


@dataclass
class Location:
    name: str
    place: str
    coordinates: tuple

    @classmethod
    def coords_from_part(cls, part, type_: Literal["FROM", "TO"]):
        index = 0 if type_ == "FROM" else -1

        stations = part["halte"]
        if len(stations) == 0:
            return None
        return Location.coords_from_db_id(stations[index]["id"])

    @classmethod
    def coords_from_db_id(cls, db_id):
        if db_id is None:
            return None
        split_id = db_id.split("@")
        lat = -1
        lon = -1
        for elem in split_id:
            if elem[:1] == "Y":
                lat = elem[2:]
            elif elem[:1] == "X":
                lon = elem[2:]
        return int(lat) / 1e6, int(lon) / 1e6

    def __str__(self) -> str:
        return str(self.name) + f", {self.place}" if self.place else ""


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
        return f"{self.departure.strftime('%H:%M')} {bold(str(self.movement_type))} ➜ {self.end.name}"


@dataclass
class Route:
    parts: list

    @classmethod
    def from_mvg_data(cls, route_data: dict):
        self = cls([])

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

        return self

    @classmethod
    def from_db_data(cls, route_data: dict):
        self = cls([])

        for part in route_data["verbindungsAbschnitte"]:
            self.parts.append(
                RoutePart(
                    datetime.fromisoformat(part.get("ezAbfahrtsZeitpunkt", part["abfahrtsZeitpunkt"])).replace(
                        tzinfo=utc),
                    datetime.fromisoformat(part.get("ezAnkunftsZeitpunkt", part["ankunftsZeitpunkt"])).replace(
                        tzinfo=utc),
                    Location(
                        part["abfahrtsOrt"],
                        "",
                        Location.coords_from_part(part, type_="FROM")
                    ),
                    Location(
                        part["ankunftsOrt"],
                        "",
                        Location.coords_from_part(part, type_="TO")
                    ),
                    MovementType(
                        "PEDESTRIAN" if part["verkehrsmittel"].get("typ", "") == "WALK"
                        else part["verkehrsmittel"].get("produktGattung", "UNKNOWN"),
                        part["verkehrsmittel"].get("langText", part["verkehrsmittel"]["name"]),
                        part["verkehrsmittel"].get("richtung", "")
                    )
                )
            )

        return self

    def __str__(self) -> str:
        return '\n'.join([str(route_part) for route_part in self.parts])

    @property
    def calendar_description(self) -> str:
        return '\n\n'.join([route_part.calendar_repr for route_part in self.parts]) + f"\n\n{bold('Ankunft:')} " + \
            self.parts[-1].arrival.strftime('%H:%M') + f" Uhr\n" + italic(f"Dauer: {self.duration}")

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

    @property
    def start(self) -> Location:
        return self.parts[0].start

    @property
    def end(self) -> Location:
        return self.parts[-1].end


def get_route_from_db(origin, destination, arrival_time, type_: Literal["ARRIVAL", "DEPARTURE"]):
    response = requests.post("https://www.bahn.de/web/api/angebote/fahrplan", json={
        "abfahrtsHalt": f"@X={
            str(origin[1]).replace('.', '')[:8].ljust(8, '0')
        }@Y={
            str(origin[0]).replace('.', '')[:8].ljust(8, '0')
        }",
        "anfrageZeitpunkt": arrival_time.isoformat(),
        "ankunftsHalt": f"@X={str(destination[1]).replace('.', '')[:8].ljust(8, '0')}@Y={str(destination[0]).replace('.', '')[:8].ljust(8, '0')}",
        "ankunftSuche": "ABFAHRT" if type_ == "DEPARTURE" else "ANKUNFT",
        "klasse": "KLASSE_2",
        "produktgattungen": [
            "ICE",
            "EC_IC",
            "IR",
            "REGIONAL",
            "SBAHN",
            "BUS",
            "SCHIFF",
            "UBAHN",
            "TRAM",
            "ANRUFPFLICHTIG"
        ],
        "reisende": [
            {
                "typ": "ERWACHSENER",
                "ermaessigungen": [
                    {
                        "art": "KEINE_ERMAESSIGUNG",
                        "klasse": "KLASSENLOS"
                    }
                ],
                "alter": [],
                "anzahl": 1
            }
        ],
        "rueckfahrtAnfrageFolgt": False,
        "schnelleVerbindungen": True,
        "sitzplatzOnly": False,
        "bikeCarriage": False,
        "reservierungsKontingenteVorhanden": False
    }, headers={"User-Agent": settings.USER_AGENT})
    try:
        response_json = response.json()
    except Exception as ex:
        print(ex)
        print(response.status_code, response.headers, response.content)
        return get_route_from_db(origin, destination, arrival_time, type_)
        # raise Exception("Invalid DB API Response") from ex

    return [Route.from_db_data(route) for route in response_json.get("verbindungen", [])]


def get_route_from_mvg(origin, destination, arrival_time, type_: Literal["ARRIVAL", "DEPARTURE"]):
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
        return get_route_from_mvg(origin, destination, arrival_time, type_)
        # raise Exception("Invalid MVG API Response") from ex

    return [Route.from_mvg_data(route) for route in response_json]


def get_routes(origin, destination, arrival_time, type_: Literal["ARRIVAL", "DEPARTURE"], api_: Literal["MVG", "DB"]):
    if api_ == "DB":
        return get_route_from_db(origin, destination, arrival_time, type_)
    elif api_ == "MVG":
        return get_route_from_mvg(origin, destination, arrival_time, type_)

    return []


def get_best_route(routes: list[Route], time: datetime, type_: Literal["ARRIVAL", "DEPARTURE"]) -> Route:
    if type_ == "ARRIVAL":
        filtered_routes = filter(lambda route: route.arrival <= time.replace(tzinfo=utc), routes)
        return max(filtered_routes, key=lambda route: route.departure, default=None)

    filtered_routes = filter(lambda route: route.departure >= time.replace(tzinfo=utc), routes)
    return min(filtered_routes, key=lambda route: route.arrival, default=None)


def get_route(origin, destination, time, type_: Literal["ARRIVAL", "DEPARTURE"] = "ARRIVAL",
              api_: Literal["MVG", "DB"] = "mvg", _try=0) -> Optional[Route]:
    if distance.distance(origin, destination).kilometers <= settings.MIN_ROUTE_DISTANCE:
        return None
    best_route = get_best_route(get_routes(origin, destination, time, type_, api_), time, type_)
    if best_route is None and _try < 3:  # If no route could be found, check 30 min earlier/later (max of 5 tries)
        print("No route could be found, checking 30mins offset")
        if type_ == "ARRIVAL":
            return get_route(origin, destination, time - timedelta(minutes=30), type_, api_, _try+1)
        return get_route(origin, destination, time + timedelta(minutes=30), type_, api_, _try+1)
    return best_route
