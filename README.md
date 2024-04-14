# TUM Commute Planner
Creates Google Calendar Events with a recommended route from your home to University.
<div style="display: flex; flex-direction: row;">
   <img src="https://github.com/OfficialFreak/tum-commute-planner/assets/36410565/df6a7e26-2d68-4e02-8aea-d09c1a02694c" alt="Preview of events in Google Calendar" style="height: 20rem;" />
   <img src="https://github.com/OfficialFreak/tum-commute-planner/assets/36410565/883ae5f5-e93c-45af-8b82-2832f6a569e8" alt="Preview of route description" style="height: 20rem;" />
</div>


## Getting started
1. Create a virtual environment using `python -m venv .venv` and activate it
2. ⬇ Install the requirements `pip3 install -r requirements.txt`
3. 🔑 Follow the instructions to get the `credentials.json`: https://developers.google.com/calendar/api/quickstart/python?hl=en
4. Copy `.env.example` and rename it to `.env` and enter the required variables
    * You can get your calendar IDs from https://developers.google.com/calendar/api/v3/reference/calendarList/list?hl=en 
        * `TUM_CALENDAR_ID` is the TUM Calendar directly imported into Google Calendar
        * `MAIN_CALENDAR_ID` is your main Calendar, which all of your normal events are in. By default, all events are ignored for the route-planning.
        * `ROUTE_CALENDAR_ID` is the Calendar you want tum-commute-planner to create events in
        * `HOME_LATITUDE` and `HOME_LONGITUDE` are the coordinates, the script calculates a route to before the first and after the last event
        * `TIME_MARGIN_BEFORE_IN_MINUTES` and `TIME_MARGIN_AFTER_IN_MINUTES` are responsible for the time margin the planner leaves between the start / end of an event and a route
        * `MIN_ROUTE_DISTANCE_IN_KM` is the minimum distance two events have to be, so the route planner plans a route between them
5. Start the script by running `python -m commute_planer.main`

## Usage
* When setup correctly, the script will continuously update the routes in your calendar
  * The current day's events are checked every 5mins (and will only recalculate the route if the events changed)
    * If there's a route within 30 minutes, the script will renew the Route using a Routing API every minute, even if the event's haven't changed
  * The current week's events are checked every 10 minutes
  * The following weeks' events are checked every 30 minutes
### Event Metadata
* Metadata must be put at the top of the description, each separated by a comma and a space: ", "
* `route_relevant`: opt in a Main-Calendar event for route-planning (Location required)
* Marking TUM Events as "cancelled": Creating an event in your main calendar at exactly the same start- and ending-time with the title `Ausfall`
  * You can further specify which event you want cancelled by adding a space and a string that's unique to the title of that event (e.g. "Ausfall Diskrete Strukturen")
* `arrive`: Plan the route to arrive at the beginning of this event (By default, routes between events are planned directly after the first of the two events is finished)
* `margin_before=<new_margin>`, `margin_after=<new_margin>`: override the default Before- and After-Margin for an event (e.g. `margin_before=0` or `margin_before=5.5`)
* `db_routing`: use the DB Routing API instead of MVG Routing for all routes regarding an event 
  * this can be combined with `latlon:` in the location as the MVG API doesn't know about stations outside of Munich
* `home_override`: set a new home for the day (Location required)
* `home_disabled`: disable the routes from / to home for the day
* `no_route`: prevent a route from being planned from or to this event (e.g. in an event "Commuting by car")

### Location Field
* The route planner can accept several forms of Locations:
  * `tum:`: to mark the location as a TUM Location (e.g. `tum:MI Cafeteria`) 
  * `tum_id:`: to mark the location as a TUM Location ID (e.g. `tum_id:5610.EG.021`)
  * `latlon:`: to mark the location as raw latitude and longitude (`latlon:<lat>, <lon>`) 
* If the location isn't prefixed, it's evaluated by the MVG API

## Contributing
Issues and Pull-Requests are very welcome. I will also continue to work on this project.

Planned features include:
* Some sort of integration of the Mensa (e.g. by using the [eat-api](https://eat-api.tum.sexy)) to:
  * calculate a route to the nearest Mensa at the "optimal time" (figuring out an optimal time is the reason why this is not implemented at the moment) and 
  * display its menu inside the calendar
* Creating Routing API parsers / users for more cities
* Think about reducing the waiting time if an event has changed (user is currently planning and would like more frequent updates) to e.g. a minute of 10s updates