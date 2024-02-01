import os
from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

USER_AGENT = os.environ.get("USER_AGENT")
TUM_CALENDAR_ID = os.environ.get("TUM_CALENDAR_ID")
TIME_MARGIN = int(os.environ.get("TIME_MARGIN_IN_MINUTES"))
HOME = (float(os.environ.get("HOME_LATITUDE")), float(os.environ.get("HOME_LONGITUDE")))