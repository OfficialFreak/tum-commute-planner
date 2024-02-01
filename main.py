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

def get_start(event):
    return datetime.now()

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

def main():
    # TODO: Routes from Home to first event and from last event to HOME (maybe from event to event as well)
    todays_date = date.today()
    origin = settings.HOME

    todays_events = get_events_on_day(settings.TUM_CALENDAR_ID, todays_date)
    # TODO: Option to filter events
    times_locations = [(get_start(event), get_location(event)) for event in todays_events]
    location_data = get_location_data(times_locations[0][1])
    arrival_time = times_locations[0][0] - timedelta(minutes=settings.TIME_MARGIN)
    print(get_route(origin, location_data[0], arrival_time))

if __name__ == "__main__":
    main()