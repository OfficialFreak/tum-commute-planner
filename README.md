# TUM Commute Planner
Creates Google Calendar Events with a recommended route from your home to University.
<div style="display: flex; flex-direction: row;">
   <img src="https://github.com/OfficialFreak/tum-commute-planner/assets/36410565/df6a7e26-2d68-4e02-8aea-d09c1a02694c" alt="Preview of events in Google Calendar" style="height: 20rem;" />
   <img src="https://github.com/OfficialFreak/tum-commute-planner/assets/36410565/883ae5f5-e93c-45af-8b82-2832f6a569e8" alt="Preview of route description" style="height: 20rem;" />
</div>


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
  * The current day's events are checked every 5mins (and will only recalculate the route if the events changed)
    * If there's a route within 30 minutes, the script will renew the Route using a Routing API every minute, even if the event's haven't changed
  * The current week's events are checked every 10 minutes
  * The following weeks' events are checked every 30 minutes
* You can opt in a Main-Calendar event for route-planning by adding `route_relevant` to the metadata and adding a location in the location field
  * to mark the location as a TUM Location, prefix it with `tum:`
  * to mark the location as a TUM Location / Room ID, prefix it with `tum_id:`
  * to mark the location as raw latitude and longitude (in the form of lat, lon), prefix it with `latlon:`
  * if the location isn't prefixed, it's evaluated by the MVG API
* To set a new home for the day, add an event with `home_override` in the tags and a set location
* To disable the routes from / to home for the day, add an event with `disable_home` in the tags
* You can also mark TUM Events as "cancelled" by creating an event in your main calendar at exactly the same start- and ending-time with the title "Ausfall". You can further specify which event you want cancelled by adding a space and a string that's unique to the title of that event (e.g. "Ausfall Diskrete Strukturen")
* By default, routes between events are planned directly after the first of the two events is finished. To change this behaviour, add `route_arrive` to the metadata of the second event
* To override the default Before- and After-Margin for an event, simply add `margin_before=<new_margin>` and `margin_after=<new_margin>` (e.g. `margin_before=0` or `margin_before=5.5`) to the event's metadata
* To use the DB Routing API instead of MVG Routing for an event, add `db_routing` to the metadata (this can be combined with `latlon:` in the location as the MVG API doesn't know about stations outside of Munich)

## Contributing
Issues and Pull-Requests are very welcome. I will also continue to work on this project.

Planned features include:
* Correctly parsing Exams / Add option to specify correct location (as currently there's an event for every exam location)
* Some sort of integration of the Mensa (e.g. by using the [eat-api](https://eat-api.tum.sexy)) to:
  * calculate a route to the nearest Mensa at the "optimal time" (figuring out an optimal time is the reason why this is not implemented at the moment) and 
  * display its menu inside the calendar