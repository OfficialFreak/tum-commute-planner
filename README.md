🚧 Still under construction! 🚧

# tum-commute-planer
Creates Google Calendar Events with a recommended route from your home to University.

## Getting started
1. ⬇ Install the requirements `pip3 install -r requirements.txt`
2. 🔑 Follow the instructions to get the `credentials.json`: https://developers.google.com/calendar/api/quickstart/python?hl=en
3. Copy `.env.example` and rename it to `.env` and enter the required variables
    * You can get your calendar IDs from https://developers.google.com/calendar/api/v3/reference/calendarList/list?hl=en 
        * `TUM_CALENDAR_ID` is the TUM Calendar directly imported into Google Calendar
        * `MAIN_CALENDAR_ID` is your main Calendar, which all of your normal events are in. By default, all events are ignored for the route-planning. 
            * You can opt-in an event for route-planning by adding "route_relevant" in the description and adding a location in the location field (text is evaluated by the mvg text to location api)
            * You can also mark TUM Events as "cancelled" by creating an event in your main calendar at exactly the same start- and ending-time with the title "Ausfall". You can further specify which event you want cancelled by adding a space and a string that's unique to the title of that event (e.g. "Ausfall Diskrete Strukturen")
        * `ROUTE_CALENDAR_ID` is the Calendar you want tum-commute-planner to create events in
        * `TIME_MARGIN_BEFORE_IN_MINUTES` and `TIME_MARGIN_AFTER_IN_MINUTES` are responsible for the time margin the planner leaves between the start / end of an event and a route
        * `MIN_ROUTE_DISTANCE_IN_KM` is the minimum distance two events have to be, so the route planner plans a route between them