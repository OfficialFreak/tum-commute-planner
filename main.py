from dataclasses import dataclass
from datetime import datetime, date, timedelta
import requests

from calendar_client import CalendarClient
from route_api import get_route
import settings

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
            "User-Agent": settings.USER_AGENT,
            "Accept": "application/json"
        }
    )
    response_json = response.json()
    coords = response_json.get("coords", None)
    return ((coords["lat"], coords["lon"]), f'{API_URL}{response_json.get("redirect_url", "")}')

def get_routes_for_day(day: datetime):
    # Implemented as array because I'm thinking about adding routes between events as well
    routes = []
    # TODO: Option to filter events
    todays_events = get_events_on_day(settings.TUM_CALENDAR_ID, day)
    print(todays_events)

    # From home to first event
    arrival_time = datetime.fromisoformat(todays_events[0]["start"]["dateTime"]).replace(tzinfo=None) - timedelta(minutes=settings.TIME_MARGIN_BEFORE)
    location_data = get_location_data(get_location(todays_events[0]))

    routes.append(get_route(settings.HOME, location_data[0], arrival_time))

    # From last event to home
    departure_time = datetime.fromisoformat(todays_events[-1]["end"]["dateTime"]).replace(tzinfo=None) + timedelta(minutes=settings.TIME_MARGIN_AFTER)
    location_data = get_location_data(get_location(todays_events[-1]))

    routes.append(get_route(location_data[0], settings.HOME, departure_time, type="DEPARTURE"))

    return routes

@dataclass
class Event:
    calendar_id: str
    event_id: str
    start: datetime
    end: datetime
    reminders: dict
    sendUpdates: str # all, externalOnly, none

    def save():
        pass

def main():
    todays_date = date.today() + timedelta(days=1)
    print('\n\n'.join([str(route) for route in get_routes_for_day(todays_date)]))

if __name__ == "__main__":
    main()