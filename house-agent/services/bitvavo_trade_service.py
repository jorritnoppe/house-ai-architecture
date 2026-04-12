from __future__ import annotations

import os
from typing import Any, Dict

import requests


BITVAVO_BRIDGE_BASE_URL = os.getenv("BITVAVO_BRIDGE_BASE_URL", "http://192.168.1.185:5001").rstrip("/")
BITVAVO_BRIDGE_SHARED_SECRET = os.getenv("BITVAVO_BRIDGE_SHARED_SECRET", "")


class BitvavoTradeService:
    def __init__(self) -> None:
        self.base_url = BITVAVO_BRIDGE_BASE_URL
        self.shared_secret = BITVAVO_BRIDGE_SHARED_SECRET

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }
        if self.shared_secret:
            headers["X-House-Trade-Secret"] = self.shared_secret
        return headers

    def _check_config(self) -> None:
        if not self.base_url:
            raise RuntimeError("BITVAVO_BRIDGE_BASE_URL is not configured")
        if not self.shared_secret:
            raise RuntimeError("BITVAVO_BRIDGE_SHARED_SECRET is not configured")

    def get_markets(self) -> Dict[str, Any]:
        self._check_config()
        r = requests.get(
            f"{self.base_url}/trade/markets",
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

    def get_balance(self) -> Dict[str, Any]:
        self._check_config()
        r = requests.get(
            f"{self.base_url}/trade/balance",
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

    def get_marketsxml(self) -> str:
        self._check_config()
        r = requests.get(
            f"{self.base_url}/marketsxml",
            headers=self._headers(),
            timeout=20,
        )
        r.raise_for_status()
        return r.text

    def preview_trade(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._check_config()
        r = requests.post(
            f"{self.base_url}/trade/preview",
            headers=self._headers(),
            json=payload,
            timeout=25,
        )
        try:
            data = r.json()
        except Exception:
            data = {"status": "error", "error": r.text}

        if r.status_code >= 400:
            return {
                "status": "error",
                "http_status": r.status_code,
                "bridge_response": data,
            }
        return data

    def execute_trade(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self._check_config()
        r = requests.post(
            f"{self.base_url}/trade/execute",
            headers=self._headers(),
            json=payload,
            timeout=30,
        )
        try:
            data = r.json()
        except Exception:
            data = {"status": "error", "error": r.text}

        if r.status_code >= 400:
            return {
                "status": "error",
                "http_status": r.status_code,
                "bridge_response": data,
            }
        return data


bitvavo_trade_service = BitvavoTradeService()
