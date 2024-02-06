from datetime import datetime, date, timedelta
from typing import Optional
import requests

from .calendar_client import CalendarClient
from .route_api import get_route, Route
from . import settings
from .utils import *


def remove_streams(events):
    return [event for event in events if "Videoübertragung aus" not in event.get("description", "")]


def get_location(event):
    location_field = event.get("location", None)
    if location_field is None:
        # TODO: Implement Fallback (e.g. to an env variable)
        return None
    if location_field.find("(") != -1:
        return get_tum_location(location_field.split("(")[-1][:-1])
    
    # Try to interpret Location using MVG API
    response = requests.get("https://www.mvg.de/api/fib/v2/location", params={
        "query": location_field
    }, headers={"User-Agent": settings.USER_AGENT})
    
    try:
        response_json = response.json()
    except Exception as ex:
        print(ex)
        print(response.status_code, response.headers, response.content)
        raise Exception("Invalid MVG API Response") from ex

    return (response_json[0]["latitude"], response_json[0]["longitude"])

def get_events_on_day(day: date):
    todays_events = get_events_from_calendar(settings.TUM_CALENDAR_ID, day)
    main_calendar_events = get_events_from_calendar(settings.MAIN_CALENDAR_ID, day)
    
    for main_calendar_event in main_calendar_events:
        if "Ausfall" in main_calendar_event.get("summary", ""):
            todays_events = [tum_event for tum_event in todays_events if not (
                (main_calendar_event["start"]["dateTime"] == tum_event["start"]["dateTime"]) and
                (main_calendar_event["end"]["dateTime"] == tum_event["end"]["dateTime"]) and
                ((len(main_calendar_event) < 8) or (main_calendar_event["summary"][8:] in tum_event.get("summary", "")))
            )]

    todays_events.extend([main_calendar_event for main_calendar_event in main_calendar_events if not ("Ausfall" in main_calendar_event.get("summary", ""))])

    todays_events.sort(key=lambda x: datetime.fromisoformat(x["start"]["dateTime"]))

    return todays_events

def get_events_from_calendar(calendar_id: str, day: date):
    tum_calendar = calendar_id == settings.TUM_CALENDAR_ID
    main_calendar = calendar_id == settings.MAIN_CALENDAR_ID
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
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])
    if tum_calendar:
        events = remove_streams(events_result.get("items", []))
    elif main_calendar:
        events = [event for event in events_result.get("items", []) if "route_relevant" in event.get("description", "") or "Ausfall" in event.get("summary", "")]
    
    return events

def get_tum_location(location: str):
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
    return (coords["lat"], coords["lon"])


def get_routes_for_day(day: date):
    routes = []
    todays_events = get_events_on_day(day)
    if(len(todays_events) == 0):
        return []

    # From home to first event
    arrival_time = datetime.fromisoformat(todays_events[0]["start"]["dateTime"]).replace(tzinfo=None) - timedelta(
        minutes=settings.TIME_MARGIN_BEFORE)
    location_data = get_location(todays_events[0])
    route = get_route(settings.HOME_POS, location_data, arrival_time)
    if route is not None:
        routes.append(route)

    # From last event to home
    departure_time = datetime.fromisoformat(todays_events[-1]["end"]["dateTime"]).replace(tzinfo=None) + timedelta(
        minutes=settings.TIME_MARGIN_AFTER)
    location_data = get_location(todays_events[-1])
    route = get_route(location_data, settings.HOME_POS, departure_time, type_="DEPARTURE")
    if route is not None:
        routes.append(route)

    # Routes between events
    if len(todays_events) == 1:
        return routes
    
    for i in range(0, len(todays_events)-1): # -1 because the last event doesn't have one after
        route = route_between_events(todays_events[i], todays_events[i+1])
        if route is not None:
            routes.append(route)

    return routes

def route_between_events(event1, event2) -> Optional[Route]:
    event1_location = get_location(event1)
    event2_location = get_location(event2)
    departure_time = datetime.fromisoformat(event1["end"]["dateTime"]).replace(tzinfo=None) + timedelta(
        minutes=settings.TIME_MARGIN_AFTER)
    return get_route(event1_location, event2_location, departure_time, type_="DEPARTURE")

def add_route_to_calendar(route: Route):
    event = {
        'summary': f"{route.calendar_summary}",
        'location': str(route.parts[-1].end),
        'description': f"{underlined(bold('Routenbeschreibung'))}\n\n{route.calendar_description}",
        'start': {
            'dateTime': (route.departure - timedelta(hours=1)).isoformat(),
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': (route.arrival - timedelta(hours=1)).isoformat(),
            'timeZone': 'UTC',
        },
        'sendUpdates': "all"
    }

    event = CalendarClient().service.events().insert(calendarId=settings.ROUTE_CALENDAR_ID, body=event).execute()
    return event

def event_equals_route(event, route: Route) -> bool:
    # Check start and end-time
    start_time_check = datetime.fromisoformat(event["start"]["dateTime"]) == route.departure
    end_time_check = datetime.fromisoformat(event["end"]["dateTime"]) == route.arrival
    # Compare Summary
    summary_check = event.get("summary", "") == route.calendar_summary
    print(event, route)
    return start_time_check and end_time_check and summary_check

def refresh_day(day):
    route_calendar_events = get_events_from_calendar(settings.ROUTE_CALENDAR_ID, day)
    tmp_routes = get_routes_for_day(day)
    print(event_equals_route(route_calendar_events[0], tmp_routes[0]))
    #for

def main():
    todays_date = date.today() + timedelta(days=1)
    #for route in get_routes_for_day(todays_date):
    #    add_route_to_calendar(route)
    #    print("Added route to calendar")
    print(refresh_day(todays_date))


if __name__ == "__main__":
    main()