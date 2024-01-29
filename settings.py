import os
from os.path import join, dirname
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

TUM_CALENDAR_ID = os.environ.get("TUM_CALENDAR_ID")