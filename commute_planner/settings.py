import os

from dotenv import load_dotenv

load_dotenv()

TUM_API_URL = "https://nav.tum.de"
USER_AGENT = os.environ.get("USER_AGENT")
TUM_CALENDAR_ID = os.environ.get("TUM_CALENDAR_ID")
MAIN_CALENDAR_ID = os.environ.get("MAIN_CALENDAR_ID")
ROUTE_CALENDAR_ID = os.environ.get("ROUTE_CALENDAR_ID")
TIME_MARGIN_BEFORE = int(os.environ.get("TIME_MARGIN_BEFORE_IN_MINUTES"))
TIME_MARGIN_AFTER = int(os.environ.get("TIME_MARGIN_AFTER_IN_MINUTES"))
HOME_POS = (float(os.environ.get("HOME_LATITUDE")), float(os.environ.get("HOME_LONGITUDE")))
MIN_ROUTE_DISTANCE = float(os.environ.get("MIN_ROUTE_DISTANCE_IN_KM"))