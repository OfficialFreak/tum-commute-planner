# TUM Commute Planner
Creates Google Calendar Events with a recommended route from your home to University.

## Getting started
1. ⬇ Install the requirements `pip3 install -r requirements.txt`
2. 🔑 Follow the instructions to get the `credentials.json`: https://developers.google.com/calendar/api/quickstart/python?hl=en
3. Copy `.env.example` and rename it to `.env` and enter the required variables
    * You can get your calendar IDs from https://developers.google.com/calendar/api/v3/reference/calendarList/list?hl=en 
        * `TUM_CALENDAR_ID` is the TUM Calendar directly imported into Google Calendar
        * `MAIN_CALENDAR_ID` is your main Calendar, which all of your normal events are in. By default, all events are ignored for the route-planning.
        * `ROUTE_CALENDAR_ID` is the Calendar you want tum-commute-planner to create events in
        * `HOME_LATITUDE` and `HOME_LONGITUDE` are the coordinates, the script calculates a route to before the first and after the last event
        * `TIME_MARGIN_BEFORE_IN_MINUTES` and `TIME_MARGIN_AFTER_IN_MINUTES` are responsible for the time margin the planner leaves between the start / end of an event and a route
        * `MIN_ROUTE_DISTANCE_IN_KM` is the minimum distance two events have to be, so the route planner plans a route between them
4. Start the script by running `python -m commute_planner.main`

## Usage
* metadata must be put at the top of the description, separated by a comma and a space: ", "
* When setup correctly, the script will continuously update the routes in your calendar
  * The current day's events in the calendar will be checked every 5 minutes (and will only recalculate the route if the events changed)
    * If there's a route within 30 minutes of the current time, the script will update the route with data from MVG every minute, even if the event's haven't changed
  * The current week's events in the calendar will be checked every 10 minutes (and will only recalculate the route if the events changed)
  * The following weeks' events will be checked every 30 minutes for changes (and will only recalculate the route if the events changed)
* You can opt in a Main-Calendar event for route-planning by adding `route_relevant` to the metadata and adding a location in the location field
  * to mark the location as a TUM Location, prefix it with `tum:`
  * to mark the location as a TUM Location / Room ID, prefix it with `tum_id:`
  * if the location isn't prefixed, it's evaluated by the MVG API
* You can also mark TUM Events as "cancelled" by creating an event in your main calendar at exactly the same start- and ending-time with the title "Ausfall". You can further specify which event you want cancelled by adding a space and a string that's unique to the title of that event (e.g. "Ausfall Diskrete Strukturen")
* By default, routes between events are planned directly after the first of the two events is finished. To change this behaviour, add `route_arrive` to the metadata of the second event
* To override the default Before- and After-Margin for an event, simply add `margin_before=<new_margin>` and `margin_after=<new_margin>` (e.g. `margin_before=0` or `margin_before=5.5`) to the event's metadata