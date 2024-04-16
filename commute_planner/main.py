import asyncio
import socket
from datetime import datetime, date, timedelta, UTC
from typing import Optional

import pytz
import requests

from .calendar_client import CalendarClient, bold, underlined
from .route_api import get_route, Route
from . import settings


class TerminalStyles:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def remove_streams(events):
    return [event for event in events if "Videoübertragung" not in event.get("description", "")]


def get_location(event):
    location_field = event.get("location", None)
    if location_field is None:
        # TODO: Implement Fallback (e.g. to an env variable)
        return None

    # Search for exact ID (TUM Calendar Format)
    if location_field.find("(") != -1:
        return get_tum_id_location(location_field.split("(")[-1][:-1])

    # Search for exact ID
    if location_field.startswith("tum_id:"):
        return get_tum_id_location(location_field[7:])

    # Try to interpret Location using nav.tum.de Search
    if location_field.startswith("tum:"):
        return get_tum_location(location_field[4:])

    if location_field.startswith("latlon:"):
        return [float(elem) for elem in location_field[7:].split(", ")]

    # Try to interpret Location using MVG API
    try:
        response = requests.get("https://www.mvg.de/api/fib/v2/location", params={
            "query": location_field
        }, headers={"User-Agent": settings.USER_AGENT})

        response_json = response.json()
    except Exception as ex:
        print(ex)
        return None

    if (len(response_json) == 0 or
            response_json[0].get("latitude", None) is None is response_json[0].get("longitude", None)):
        return None

    return response_json[0]["latitude"], response_json[0]["longitude"]


def get_tum_location(query: str):
    response = requests.get(
        f"{settings.TUM_API_URL}/api/search",
        headers={
            "User-Agent": settings.USER_AGENT,
            "Accept": "application/json"
        },
        params={
            "q": query,
            "limit_all": 1,
            "post_highlight": "",
            "pre_highlight": ""
        }
    )
    response_json = response.json()
    try:
        tum_id = response_json.get("sections", [{}])[0].get("entries", [{}])[0].get("id", None)
    except IndexError:
        try:
            tum_id = response_json.get("sections", [{}])[1].get("entries", [{}])[0].get("id", None)
        except IndexError:
            tum_id = None
    if tum_id is None:
        return None
    return get_tum_id_location(tum_id)


def get_tum_id_location(location_id: str):
    try:
        response = requests.get(
            f"{settings.TUM_API_URL}/api/get/{location_id}",
            headers={
                "User-Agent": settings.USER_AGENT,
                "Accept": "application/json"
            }
        )
        response_json = response.json()
    except Exception as ex:
        print(ex)
        return None
    coords = response_json.get("coords", None)
    if coords is None:
        return None
    return coords["lat"], coords["lon"]


def get_events_on_day(day: date):
    events_today = get_events_from_calendar(settings.TUM_CALENDAR_ID, day)
    main_calendar_events = get_events_from_calendar(settings.MAIN_CALENDAR_ID, day)
    home_override = {}

    for main_calendar_event in main_calendar_events:
        if "Ausfall" in main_calendar_event.get("summary", ""):
            events_today = [tum_event for tum_event in events_today if not (
                    (main_calendar_event["start"]["dateTime"] == tum_event["start"]["dateTime"]) and
                    (main_calendar_event["end"]["dateTime"] == tum_event["end"]["dateTime"]) and
                    ((len(main_calendar_event) < 8) or (
                            main_calendar_event["summary"][8:] in tum_event.get("summary", "")))
            )]
        if "home_override" in main_calendar_event.get("description", ""):
            home_override["location"] = get_location(main_calendar_event)
        if "home_disabled" in main_calendar_event.get("description", ""):
            home_override["disabled"] = True

    events_today.extend([main_calendar_event for main_calendar_event in main_calendar_events if
                         not ("Ausfall" in main_calendar_event.get("summary", ""))
                         and not ("home_override" in main_calendar_event.get("description", ""))
                         and not ("home_disabled" in main_calendar_event.get("description", ""))])

    events_today.sort(key=lambda x: datetime.fromisoformat(x["start"]["dateTime"]))

    return events_today, home_override


def get_events_from_calendar(calendar_id: str, day: date):
    tum_calendar = calendar_id == settings.TUM_CALENDAR_ID
    main_calendar = calendar_id == settings.MAIN_CALENDAR_ID
    calendar_client = CalendarClient()

    time_min = datetime.combine(day, datetime.min.time())
    time_max = datetime.combine(day, datetime.max.time())

    try:
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
    except socket.gaierror:
        return get_events_from_calendar(calendar_id, day)

    events = events_result.get("items", [])
    if tum_calendar:
        events = remove_streams(events_result.get("items", []))
    elif main_calendar:
        events = [event for event in events_result.get("items", []) if
                  "route_relevant" in event.get("description", "") or
                  "home_override" in event.get("description", "") or
                  "home_disabled" in event.get("description", "") or
                  "no_route" in event.get("description", "") or
                  "Ausfall" in event.get("summary", "")]

    for event in events:
        event["created"] = datetime.fromisoformat(event["created"]).astimezone(pytz.utc).isoformat()
        event["updated"] = datetime.fromisoformat(event["updated"]).astimezone(pytz.utc).isoformat()
        event["start"]["dateTime"] = datetime.fromisoformat(event["start"]["dateTime"]).astimezone(pytz.utc).isoformat()
        event["end"]["dateTime"] = datetime.fromisoformat(event["end"]["dateTime"]).astimezone(pytz.utc).isoformat()
    return events


def get_metadata(event):
    split_flags = event.get("description", "").split("<br>")[0].split(", ")
    metadata = {}
    for data in split_flags:
        res = data.split("=")
        key = res[0]
        value = True
        if len(res) > 1:
            value = res[1]
        metadata[key] = value
    return metadata


def get_routes_for_events(events_today, home_override):
    routes = []
    if len(events_today) == 0:
        return []

    home_pos = home_override.get("location", None) if home_override.get("location", None) is not None \
        else settings.HOME_POS

    if not home_override.get("disabled", False):
        # From home to first event
        event_metadata = get_metadata(events_today[0])
        if not event_metadata.get("no_route", False):
            margin_before = float(event_metadata.get("margin_before", settings.TIME_MARGIN_BEFORE))
            arrival_time = (datetime.fromisoformat(events_today[0]["start"]["dateTime"]) -
                            timedelta(minutes=margin_before))
            location_data = get_location(events_today[0])
            if location_data is not None:
                route = get_route(home_pos, location_data, arrival_time,
                                  api_="DB" if event_metadata.get("db_routing", False) else "MVG")
                if route is not None:
                    routes.append(route)
            else:
                print(f"[{arrival_time.strftime('%Y-%m-%d')}] Skipping route relevant event, because location data is missing")

        # From last event to home
        event_metadata = get_metadata(events_today[-1])
        if not event_metadata.get("no_route", False):
            margin_after = float(event_metadata.get("margin_after", settings.TIME_MARGIN_AFTER))
            departure_time = (datetime.fromisoformat(events_today[-1]["end"]["dateTime"]) +
                              timedelta(minutes=margin_after))
            location_data = get_location(events_today[-1])
            if location_data is not None:
                route = get_route(location_data, home_pos, departure_time, type_="DEPARTURE",
                                  api_="DB" if event_metadata.get("db_routing", False) else "MVG")
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
    if event1_location is None:
        return None
    event2_location = get_location(event2)
    if event2_location is None:
        return None

    event1_metadata = get_metadata(event1)
    event2_metadata = get_metadata(event2)

    if event1_metadata.get("no_route", False) or event2_metadata.get("no_route", False):
        return None

    if event2_metadata.get("arrive", False):
        margin_before = float(event2_metadata.get("margin_before", settings.TIME_MARGIN_BEFORE))
        arrival_time = datetime.fromisoformat(event2["start"]["dateTime"]) - timedelta(minutes=margin_before)

        return get_route(event1_location, event2_location, arrival_time, type_="ARRIVAL",
                         api_="DB" if event1_metadata.get("db_routing", False) or
                                      event2_metadata.get("db_routing", False) else "MVG")

    margin_after = float(event1_metadata.get("margin_after", settings.TIME_MARGIN_AFTER))
    departure_time = datetime.fromisoformat(event1["end"]["dateTime"]) + timedelta(minutes=margin_after)
    return get_route(event1_location, event2_location, departure_time, type_="DEPARTURE",
                     api_="DB" if event1_metadata.get("db_routing", False) or
                                  event2_metadata.get("db_routing", False) else "MVG")


def add_route_to_calendar(route: Route):
    event = {
        'summary': f"{route.calendar_summary}",
        'location': str(route.parts[-1].end),
        'description': f"{
            route.start.coordinates[0] if route.start.coordinates is not None else 0}, {
            route.start.coordinates[1] if route.start.coordinates is not None else 0} | {
            route.end.coordinates[0] if route.end.coordinates is not None else 0}, {
            route.end.coordinates[1] if route.end.coordinates is not None else 0}\n{
            underlined(bold('Routenbeschreibung'))}\n\n{route.calendar_description}",
        'start': {
            'dateTime': route.departure.isoformat(),
        },
        'end': {
            'dateTime': route.arrival.isoformat(),
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
    return start_time_check and end_time_check and summary_check


def refresh_day(day, known_events, known_home_override):
    current_routes = get_events_from_calendar(settings.ROUTE_CALENDAR_ID, day)
    events_today, home_override = get_events_on_day(day)

    upcoming_route = None
    for route in current_routes:
        if (datetime.fromisoformat(route["start"]["dateTime"]) > datetime.now(UTC) and
                (datetime.fromisoformat(route["start"]["dateTime"]) - datetime.now(UTC)) < timedelta(
                    minutes=30)):
            upcoming_route = route
            break

    if events_today == known_events and home_override == known_home_override and not upcoming_route:
        return events_today, upcoming_route, home_override

    target_routes = get_routes_for_events(events_today, home_override)

    events_to_remove = [event for event in current_routes if
                        not any(event_equals_route(event, route) for route in target_routes)]
    routes_to_add = [route for route in target_routes if
                     not any(event_equals_route(event, route) for event in current_routes)]

    for event in events_to_remove:
        CalendarClient().service.events().delete(calendarId=settings.ROUTE_CALENDAR_ID, eventId=event['id']).execute()
        print(f"[{day}] {TerminalStyles.HEADER}Removed event {event['id']}{TerminalStyles.ENDC}")
    for route in routes_to_add:
        route_event = add_route_to_calendar(route)
        # Check for new upcoming route
        if (datetime.fromisoformat(route_event["start"]["dateTime"]) > datetime.now(UTC) and
           (datetime.fromisoformat(route_event["start"]["dateTime"]) - datetime.now(UTC)) < timedelta(minutes=30)):
            upcoming_route = route_event
        print(f"[{day}] {TerminalStyles.OKGREEN}Created new event {route.calendar_summary}{TerminalStyles.ENDC}")

    return events_today, upcoming_route, home_override


def refresh_week(day_of_week: date, known_events, known_home_overrides):
    new_events = {}
    new_known_home_overrides = {}
    monday = day_of_week - timedelta(days=day_of_week.weekday())
    for day in range(0, 7):
        current_day = monday + timedelta(days=day)
        if current_day <= date.today():
            print(f"[{current_day}] is in the past or today, skipping")
            continue
        print(f"[{current_day}] Refreshing...")
        new_events[day], _, new_known_home_overrides[day] = refresh_day(
            current_day, known_events[day], known_home_overrides[day])

    return new_events, new_known_home_overrides


async def update_week_except_today_loop():
    known_events: dict[int, list | None] = {i: None for i in range(7)}
    known_home_overrides = {i: None for i in range(7)}
    known_events_monday = date.today() - timedelta(days=date.today().weekday())

    while 1:
        print(f"[{known_events_monday}] {TerminalStyles.UNDERLINE}Starting Update All Loop{TerminalStyles.ENDC}")
        if date.today() - timedelta(days=date.today().weekday()) != known_events_monday:
            known_events = {i: None for i in range(7)}
            known_home_overrides = {i: None for i in range(7)}
            known_events_monday = date.today() - timedelta(days=date.today().weekday())

        known_events, known_home_overrides = refresh_week(date.today(), known_events, known_home_overrides)
        print(f"[{known_events_monday}] {TerminalStyles.OKGREEN}Finished Update All Loop{TerminalStyles.ENDC}")
        await asyncio.sleep(10 * 60)


async def update_following_weeks():
    def get_default_known_events():
        return {i: {j: None for j in range(7)} for i in range(settings.PRE_CALC_WEEK_COUNT)}

    known_events = get_default_known_events()
    known_home_overrides = {i: {j: None for j in range(7)} for i in range(settings.PRE_CALC_WEEK_COUNT)}
    known_events_monday = date.today() - timedelta(days=date.today().weekday() - 7)

    while 1:
        print(
            f"[{known_events_monday}] {
                TerminalStyles.UNDERLINE}Starting Update Following Weeks Loop{TerminalStyles.ENDC}")
        if date.today() - timedelta(days=date.today().weekday() - 7) != known_events_monday:
            known_events = get_default_known_events()
            known_home_overrides = {i: {j: None for j in range(7)} for i in range(settings.PRE_CALC_WEEK_COUNT)}
            known_events_monday = date.today() - timedelta(days=date.today().weekday() - 7)

        for week in range(settings.PRE_CALC_WEEK_COUNT):
            date_today = date.today() + timedelta(days=7 * (week + 1))
            known_events[week], known_home_overrides[week] = refresh_week(
                date_today, known_events[week], known_home_overrides[week])
        print(
            f"[{known_events_monday}] {
                TerminalStyles.OKGREEN}Finished Update Following Weeks Loop{TerminalStyles.ENDC}")
        await asyncio.sleep(30 * 60)


async def update_today_loop(upcoming_route_callback=lambda route: None):
    known_events: None | list = None
    known_home_override = None
    known_events_day = date.today()

    while 1:
        print(f"[{known_events_day}] {TerminalStyles.UNDERLINE}Starting Update Today Loop{TerminalStyles.ENDC}")
        if date.today() != known_events_day:
            known_events = None
            known_home_override = None
            known_events_day = date.today()

        known_events, upcoming_route, known_home_override = refresh_day(
            date.today(), known_events, known_home_override)
        print(f"[{known_events_day}] {TerminalStyles.OKGREEN}Finished Update Today Loop{TerminalStyles.ENDC}")
        if upcoming_route:
            print(
                f"[{known_events_day}] {TerminalStyles.WARNING}Has upcoming route, 1min waiting times...{
                    TerminalStyles.ENDC}")
            upcoming_route_callback(upcoming_route)
            await asyncio.sleep(1 * 60)
        else:
            print(f"[{known_events_day}] No upcoming route, 5min waiting time")
            await asyncio.sleep(5 * 60)


async def main():
    await asyncio.gather(
        update_today_loop(),
        update_week_except_today_loop(),
        update_following_weeks()
    )


if __name__ == "__main__":
    asyncio.run(main())
