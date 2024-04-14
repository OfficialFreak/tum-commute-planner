# This is an example of how to use the upcoming events callback

from geopy.distance import distance
from phue import Bridge

from commute_planer.main import *
from commute_planer.settings import HOME_POS, MIN_ROUTE_DISTANCE


def update_lamps(route):
    global b
    # check if start is at home (if not, triggering the lamps would be kinda dumb)
    start_coordinates = route["description"].split("\n")[0].split(" | ")[0].split(", ")
    start_coordinates = (float(start_coordinates[0]), float(start_coordinates[1]))
    if distance(start_coordinates, HOME_POS).kilometers > MIN_ROUTE_DISTANCE:
        return
    # decide which color to set
    departure_delta = datetime.fromisoformat(route["start"]["dateTime"]).replace(tzinfo=None) - datetime.now()

    # cyan -> purple -> magenta -> color changing -> off

    if departure_delta > timedelta(minutes=10):
        # Set to cyan
        b.set_light([1, 2, 3], {
            "on": True,
            'bri': 254, 'hue': 39675, 'sat': 240
        })
    elif departure_delta < timedelta(minutes=1.5):
        b.set_light([1, 2, 3], "on", False)
    elif departure_delta < timedelta(minutes=3):
        # Set to color changing
        b.set_light([1, 2, 3], {
            "on": True,
            "effect": "colorloop"
        })
    elif departure_delta < timedelta(minutes=5):
        # set to magenta
        b.set_light([1, 2, 3], {
            "on": True,
            'bri': 254,
            'hue': 55844,
            'sat': 254
        })
    elif departure_delta < timedelta(minutes=10):
        # set to purple
        b.set_light([1, 2, 3], {
            "on": True,
            'bri': 254, 'hue': 49962, 'sat': 254
        })


b: Bridge
BRIDGE_IP = "192.168.0.186"  # Enter the ip of your Bridge here


async def main():
    global b

    b = Bridge(BRIDGE_IP)
    b.connect()

    await asyncio.gather(
        update_today_loop(update_lamps),
        update_week_except_today_loop(),
        update_following_weeks()
    )


if __name__ == "__main__":
    asyncio.run(main())
