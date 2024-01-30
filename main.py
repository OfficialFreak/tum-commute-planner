from datetime import datetime, date, timedelta
import requests

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

def main():
    #todays_date = date.today() + timedelta(days=3)
    #todays_events = get_events_on_day(settings.TUM_CALENDAR_ID, todays_date)

    #locations = [get_location(event) for event in todays_events]
    #print(locations)
    #location_data = get_location_data(locations[0])
    #print(location_data)
    
    arrival_time = datetime.now() + timedelta(hours=2) - timedelta(hours=1) # idk why but mvg does it as well
    print(arrival_time.isoformat() + "Z")
    # get route for given arrival time
    response_json = requests.get("https://www.mvg.de/api/fib/v2/connection", params={
        "originLatitude": 0,
        "originLongitude": 0,
        "destinationLatitude": 0,
        "destinationLongitude": 0,
        "routingDateTime": arrival_time.isoformat() + "Z",
        "routingDateTimeIsArrival": True,
        "transportTypes": "SCHIFF,RUFTAXI,BAHN,UBAHN,TRAM,SBAHN,BUS,REGIONAL_BUS"
    }, headers={"User-Agent": USER_AGENT}).json()
    print(response_json)
    # TODO: Parsing a single Route to something like
    # [{"departure": from.plannedDeparture, "arrival": to.plannedDeparture, "from": f"{from.name}, {from.place}", "to": f"{to.name}, {to.place}", "transportationName": f"{line.transportType} {line.label} {line.transportType}"}, ...]

if __name__ == "__main__":
    main()