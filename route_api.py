from datetime import datetime, timedelta
import requests
from dataclasses import dataclass
from typing import List
from pytz import utc

import settings

MOVEMENT_TYPES = {
    "SCHIFF": "Schiff",
    "RUFTAXI": "Ruftaxi",
    "BAHN": "Bahn",
    "UBAHN": "U-Bahn",
    "TRAM": "Tram",
    "SBAHN": "S-Bahn",
    "BUS": "Bus",
    "REGIONAL_BUS": "Regional Bus",
    "PEDESTRIAN": "Fussweg"
}

@dataclass
class Location():
    name: str
    place: str
    coordinates: tuple

    def __str__(self) -> str:
        return f"{self.name}, {self.place}"

@dataclass
class Movement():
    movement_type: str
    name: str
    destination: str

    def __str__(self) -> str:
        return f"{
                f'{self.name}'
            }{
                f' ({self.destination})' if self.destination else ''
            }"
        """
        # Also displays the Movement Type (Such as Bus, Subway, etc.)
        return f"{
                MOVEMENT_TYPES.get(self.movement_type, self.movement_type)
            }{
                f' {self.name}'
            }{
                f' Richtung {self.destination}' if self.destination else ''
            }"
        """

@dataclass
class RoutePart():
    departure: datetime
    arrival: datetime
    start: Location
    end: Location
    movement: Movement

    def __str__(self) -> str:
        return f"{self.departure.strftime('%H:%M')} - {self.arrival.strftime('%H:%M')} | {self.movement} -> {self.end.name}"

class Route():
    parts = None
    def __init__(self, route_data):
        self.parts = []
        
        for part in route_data["parts"]:
            self.parts.append(RoutePart(
                datetime.fromisoformat(part["from"]["plannedDeparture"]).replace(tzinfo=utc),
                (datetime.fromisoformat(part["to"]["plannedDeparture"]) + timedelta(minutes=int(part["to"].get("arrivalDelayInMinutes", 0)))).replace(tzinfo=utc),
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
                Movement(
                    part["line"]["transportType"],
                    part["line"]["label"],
                    part["line"]["destination"]
                )
            ))
    
    def __str__(self) -> str:
        return '\n'.join([str(route_part) for route_part in self.parts])

    def getDeparture(self):
        return self.parts[0].departure

    def getArrival(self):
        return self.parts[-1].arrival

    def getDuration(self):
        return self.getArrival() - self.getDeparture()

def get_routes(origin, destination, arrival_time, type):
    try:
        response = requests.get("https://www.mvg.de/api/fib/v2/connection", params={
            "originLatitude": origin[0],
            "originLongitude": origin[1],
            "destinationLatitude": destination[0],
            "destinationLongitude": destination[1],
            "routingDateTime": (arrival_time - timedelta(hours=1)).isoformat() + "Z",
            "routingDateTimeIsArrival": type == "ARRIVAL",
            "transportTypes": "SCHIFF,RUFTAXI,BAHN,UBAHN,TRAM,SBAHN,BUS,REGIONAL_BUS"
        }, headers={"User-Agent": settings.USER_AGENT})
        response_json = response.json()
    except Exception as ex:
        print(ex)
        print(response.status_code, response.headers, response.content)
        raise Exception("Invalid MVG API Response")
    return [Route(route) for route in response_json]

def get_best_route(routes: List[Route], time: datetime, type: str) -> Route:
    if(type == "ARRIVAL"):
        filtered_routes = filter(lambda route: route.getArrival() <= time.replace(tzinfo=utc), routes)
        return max(filtered_routes, key=lambda route: route.getDeparture())
    
    filtered_routes = filter(lambda route: route.getDeparture() >= time.replace(tzinfo=utc), routes)
    return min(filtered_routes, key=lambda route: route.getArrival())

def get_route(origin, destination, time, type="ARRIVAL"):
    best_route = get_best_route(get_routes(origin, destination, time, type), time, type)
    if(best_route is None): # If no route could be found, check 30mins earlier/later
        if(type == "ARRIVAL"):
            return get_route(origin, destination, time - timedelta(minutes=30), type)
        return get_route(origin, destination, time + timedelta(minutes=30), type)
    return best_route