from datetime import datetime, date, timedelta
import requests
from dataclasses import dataclass

from client import CalendarClient
import settings

USER_AGENT = "tum-commute-planer/1.0"

def remove_streams(events):
    return list(filter(lambda event : "Videoübertragung aus" not in event.get("description", ""), events))

def get_location(event):
    location_field = event.get("location", None)
    if location_field is None:
        # TODO: Implement Fallback (e.g. to an env variable)
        return None
    return location_field.split("(")[-1][:-1] # Gets content in last braces

def get_events_on_day(calendar_id: str, day: date):
    calendar_client = CalendarClient()

    time_min = datetime.combine(day, datetime.min.time())
    time_max = datetime.combine(day, datetime.max.time())

    events_result = (
        calendar_client.service.events()
        .list(
            calendarId=calendar_id,
            timeMin=time_min.isoformat() + "Z",
            timeMax=time_max.isoformat() + "Z",
            singleEvents=True,
            orderBy="startTime"
        )
        .execute()
    )

    return remove_streams(events_result.get("items", []))

def get_location_data(location: str):
    API_URL = "https://nav.tum.de"
    response = requests.get(
        f"{API_URL}/api/get/{location}",
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json"
        }
    )
    response_json = response.json()
    coords = response_json.get("coords", None)
    return {
        "coords": (coords["lat"], coords["lon"]),
        "link": f'{API_URL}{response_json.get("redirect_url", "")}'
    }

MOVEMENT_TYPES = {
    "SCHIFF": "Schiff",
    "RUFTAXI": "Ruftaxi",
    "BAHN": "Bahn",
    "UBAHN": "U-Bahn",
    "TRAM": "Tram",
    "SBAHN": "S-Bahn",
    "BUS": "Bus",
    "REGIONAL_BUS": "Regional Bus"
}

@dataclass
class Location():
    name: str
    place: str
    coordinates: tuple

    def __str__(self):
        return f"{self.name}, {self.place}"

@dataclass
class Movement():
    movement_type: str
    name: str
    destination: str

    def __str__(self):
        return f"{MOVEMENT_TYPES[self.movement_type]} {self.name} -> {self.destination}"

@dataclass
class RoutePart():
    departure: datetime
    arrival: datetime
    start: Location
    end: Location
    movement: Movement

class Route():
    parts = None
    def __init__(self, route_data):
        self.parts = []

        for part in route_data["parts"]:
            self.parts.append(RoutePart(
                datetime.fromisoformat(part["from"]["plannedDeparture"]),
                datetime.fromisoformat(part["to"]["plannedDeparture"]) + timedelta(minutes=int(part["to"].get("arrivalDelayInMinutes", 0))),
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

    def getDeparture(self):
        return self.parts[0].departure

    def getArrival(self):
        return self.parts[-1].arrival

    def getDuration(self):
        return self.getArrival() - self.getDeparture()

def get_routes(origin, destination, arrival_time):
    response_json = requests.get("https://www.mvg.de/api/fib/v2/connection", params={
        "originLatitude": origin[0],
        "originLongitude": origin[1],
        "destinationLatitude": destination[0],
        "destinationLongitude": destination[1],
        "routingDateTime": (arrival_time - timedelta(hours=1)).isoformat() + "Z",
        "routingDateTimeIsArrival": True,
        "transportTypes": "SCHIFF,RUFTAXI,BAHN,UBAHN,TRAM,SBAHN,BUS,REGIONAL_BUS"
    }, headers={"User-Agent": USER_AGENT}).json()
    return [Route(route) for route in response_json]

def main():
    #todays_date = date.today() + timedelta(days=3)
    #todays_events = get_events_on_day(settings.TUM_CALENDAR_ID, todays_date)

    #locations = [get_location(event) for event in todays_events]
    #print(locations)
    #location_data = get_location_data(locations[0])
    #print(location_data)

    # get route for given arrival time
    routes = get_routes((0, 0), (0, 0), datetime.now())
    print(routes)

if __name__ == "__main__":
    main()