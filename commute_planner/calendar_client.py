from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import os


def singleton(cls):
    instances = {}

    def _singleton(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return _singleton


@singleton
class CalendarClient:
    """ Class for simplifying the calendar client setup """
    SCOPES = ["https://www.googleapis.com/auth/calendar"]  # Full Access to all calendars
    creds: Credentials = None
    service = None

    def __init__(self) -> None:
        self.creds = self._get_creds()
        self.service = build("calendar", "v3", credentials=self.creds)

    def _get_creds(self) -> Credentials:
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", self.SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open("token.json", "w") as f:
                f.write(creds.to_json())

        return creds


def bold(text: str) -> str:
    return f"\u003cb\u003e{text}\u003c/b\u003e"


def italic(text: str) -> str:
    return f"\u003ci\u003e{text}\u003c/i\u003e"


def underlined(text: str) -> str:
    return f"\u003cu\u003e{text}\u003c/u\u003e"
