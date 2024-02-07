import asyncio
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

    return response_json[0]["latitude"], response_json[0]["longitude"]


def get_events_on_day(day: date):
    todays_events = get_events_from_calendar(settings.TUM_CALENDAR_ID, day)
    main_calendar_events = get_events_from_calendar(settings.MAIN_CALENDAR_ID, day)

    for main_calendar_event in main_calendar_events:
        if "Ausfall" in main_calendar_event.get("summary", ""):
            todays_events = [tum_event for tum_event in todays_events if not (
                (main_calendar_event["start"]["dateTime"] == tum_event["start"]["dateTime"]) and
                (main_calendar_event["end"]["dateTime"] == tum_event["end"]["dateTime"]) and
                ((len(main_calendar_event) < 8) or (
                    main_calendar_event["summary"][8:] in tum_event.get("summary", "")))
            )]

    todays_events.extend([main_calendar_event for main_calendar_event in main_calendar_events if
                          not ("Ausfall" in main_calendar_event.get("summary", ""))])

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
        events = [event for event in events_result.get("items", []) if
                  "route_relevant" in event.get("description", "") or "Ausfall" in event.get("summary", "")]

    return events


def get_tum_location(location: str):
    api_url = "https://nav.tum.de"
    response = requests.get(
        f"{api_url}/api/get/{location}",
        headers={
            "User-Agent": settings.USER_AGENT,
            "Accept": "application/json"
        }
    )
    response_json = response.json()
    coords = response_json.get("coords", None)
    return coords["lat"], coords["lon"]


def get_routes_for_events(events_today):
    routes = []
    if len(events_today) == 0:
        return []

    # From home to first event
    # event_metadata = events_today[0][""]
    arrival_time = datetime.fromisoformat(events_today[0]["start"]["dateTime"]).replace(tzinfo=None) - timedelta(
        minutes=settings.TIME_MARGIN_BEFORE)
    location_data = get_location(events_today[0])
    route = get_route(settings.HOME_POS, location_data, arrival_time)
    if route is not None:
        routes.append(route)

    # From last event to home
    departure_time = datetime.fromisoformat(events_today[-1]["end"]["dateTime"]).replace(tzinfo=None) + timedelta(
        minutes=settings.TIME_MARGIN_AFTER)
    location_data = get_location(events_today[-1])
    route = get_route(location_data, settings.HOME_POS, departure_time, type_="DEPARTURE")
    if route is not None:
        routes.append(route)

    # Routes between events
    if len(events_today) == 1:
        return routes

    for i in range(0, len(events_today) - 1):  # -1 because the last event doesn't have one after
        route = route_between_events(events_today[i], events_today[i + 1])
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
    start_time_check = datetime.fromisoformat(event["start"]["dateTime"]).replace(
        tzinfo=None) == route.departure.replace(tzinfo=None)
    end_time_check = datetime.fromisoformat(event["end"]["dateTime"]).replace(tzinfo=None) == route.arrival.replace(
        tzinfo=None)
    # Compare Summary
    summary_check = event.get("summary", "") == route.calendar_summary
    return start_time_check and end_time_check and summary_check


def refresh_day(day, known_events):
    existing_events = get_events_from_calendar(settings.ROUTE_CALENDAR_ID, day)
    events_today = get_events_on_day(day)
    print(events_today, known_events)
    if events_today == known_events:
        print("No events changed, skipping route recalculation")
        return events_today

    target_routes = get_routes_for_events(events_today)

    has_upcoming_route = False
    for route in target_routes:
        if route.departure.replace(tzinfo=None) - datetime.now() < timedelta(minutes=30):
            has_upcoming_route = True
            break

    events_to_remove = [event for event in existing_events if not any(event_equals_route(event, route) for route in target_routes)]
    routes_to_add = [route for route in target_routes if not any(event_equals_route(event, route) for event in existing_events)]

    for event in events_to_remove:
        CalendarClient().service.events().delete(calendarId=settings.ROUTE_CALENDAR_ID, eventId=event['id']).execute()
        print(f"Removed event {event['id']}")
    for route in routes_to_add:
        add_route_to_calendar(route)
        print(f"Created new event {route.calendar_summary}")

    return events_today, has_upcoming_route


def refresh_week(day_of_week: date, known_events) -> dict[int, list | None]:
    new_events = {}
    monday = day_of_week - timedelta(days=day_of_week.weekday())
    for day in range(0, 7):
        current_day = monday + timedelta(days=day)
        if current_day <= date.today():
            print(current_day, "is in the past or today, skipping")
            continue
        print(f"Refreshing {current_day}")
        new_events[day] = refresh_day(current_day, known_events[day])

    return new_events


async def update_all_but_today_loop():
    known_events: dict[int, list | None] = {i: None for i in range(7)}

    while 1:
        date_today = date.today() + timedelta(days=0)
        known_events = refresh_week(date_today, known_events)
        await asyncio.sleep(10 * 60)
        print("Finished a week cycle")


async def update_today_loop():
    known_events: None | list = None

    while 1:
        known_events, today_has_upcoming_route = refresh_day(date.today(), known_events)
        if today_has_upcoming_route:
            await asyncio.sleep(5 * 60)
        else:
            await asyncio.sleep(10 * 60)


async def main():
    await asyncio.gather(
        update_today_loop(),
        update_all_but_today_loop()
    )

if __name__ == "__main__":
    asyncio.run(main())
