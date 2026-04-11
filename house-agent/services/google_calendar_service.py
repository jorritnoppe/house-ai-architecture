from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from dateutil import parser as dtparser
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar"]


@dataclass
class CalendarConfig:
    credentials_file: str
    token_file: str
    timezone_name: str = "Europe/Brussels"


class GoogleCalendarService:
    def __init__(self, config: CalendarConfig):
        self.config = config
        self._service = None

    def _load_credentials(self) -> Credentials:
        creds = None

        if os.path.exists(self.config.token_file):
            creds = Credentials.from_authorized_user_file(
                self.config.token_file,
                SCOPES,
            )

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.config.credentials_file,
                    SCOPES,
                )
                creds = flow.run_local_server(port=8088, open_browser=False)
            with open(self.config.token_file, "w", encoding="utf-8") as f:
                f.write(creds.to_json())

        return creds

    def client(self):
        if self._service is None:
            creds = self._load_credentials()
            self._service = build("calendar", "v3", credentials=creds)
        return self._service

    def list_calendars(self) -> list[dict[str, Any]]:
        svc = self.client()
        result = svc.calendarList().list().execute()
        return result.get("items", [])

    def get_calendar_map(self) -> dict[str, str]:
        calendars = self.list_calendars()
        out: dict[str, str] = {}
        for item in calendars:
            summary = item.get("summary", "").strip()
            cal_id = item.get("id")
            if summary and cal_id:
                out[summary] = cal_id
        return out

    def events_between(
        self,
        calendar_id: str,
        start_dt: datetime,
        end_dt: datetime,
        max_results: int = 100,
    ) -> list[dict[str, Any]]:
        svc = self.client()
        result = (
            svc.events()
            .list(
                calendarId=calendar_id,
                timeMin=start_dt.isoformat(),
                timeMax=end_dt.isoformat(),
                singleEvents=True,
                orderBy="startTime",
                maxResults=max_results,
            )
            .execute()
        )
        return result.get("items", [])

    def get_today(
        self,
        calendar_ids: list[str],
        now_utc: datetime | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        now_utc = now_utc or datetime.now(timezone.utc)

        local_now = now_utc.astimezone()
        start_local = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = start_local + timedelta(days=1)

        out: dict[str, list[dict[str, Any]]] = {}
        for cal_id in calendar_ids:
            out[cal_id] = self.events_between(cal_id, start_local, end_local)
        return out

    def create_event(
        self,
        calendar_id: str,
        summary: str,
        start_dt: datetime,
        end_dt: datetime,
        description: str = "",
    ) -> dict[str, Any]:
        svc = self.client()
        body = {
            "summary": summary,
            "description": description,
            "start": {"dateTime": start_dt.isoformat()},
            "end": {"dateTime": end_dt.isoformat()},
        }
        return svc.events().insert(calendarId=calendar_id, body=body).execute()

    def create_all_day_task(
        self,
        calendar_id: str,
        summary: str,
        day: datetime,
        description: str = "",
    ) -> dict[str, Any]:
        svc = self.client()
        start_date = day.date().isoformat()
        end_date = (day.date() + timedelta(days=1)).isoformat()

        body = {
            "summary": summary,
            "description": description,
            "start": {"date": start_date},
            "end": {"date": end_date},
        }
        return svc.events().insert(calendarId=calendar_id, body=body).execute()

    @staticmethod
    def parse_dt(value: str) -> datetime:
        dt = dtparser.parse(value)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
