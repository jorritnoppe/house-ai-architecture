from __future__ import annotations

from datetime import datetime, timedelta, timezone

import requests

BASE_URL = "http://127.0.0.1:8000"


def create_cleaning_task(summary: str, day: str, description: str = "source: house-agent"):
    return requests.post(
        f"{BASE_URL}/agenda/task/cleaning",
        json={
            "summary": summary,
            "day": day,
            "description": description,
        },
        timeout=15,
    ).json()


def create_plants_task(summary: str, day: str, description: str = "source: house-agent"):
    return requests.post(
        f"{BASE_URL}/agenda/task/plants",
        json={
            "summary": summary,
            "day": day,
            "description": description,
        },
        timeout=15,
    ).json()


def create_maintenance_task(summary: str, day: str, description: str = "source: house-agent"):
    return requests.post(
        f"{BASE_URL}/agenda/task/maintenance",
        json={
            "summary": summary,
            "day": day,
            "description": description,
        },
        timeout=15,
    ).json()


def create_laundry_task(
    summary: str,
    start: str,
    end: str,
    description: str = "source: house-agent",
):
    return requests.post(
        f"{BASE_URL}/agenda/task/laundry",
        json={
            "summary": summary,
            "start": start,
            "end": end,
            "description": description,
        },
        timeout=15,
    ).json()


def get_spoken_agenda():
    return requests.get(
        f"{BASE_URL}/agenda/spoken",
        timeout=15,
    ).json()
