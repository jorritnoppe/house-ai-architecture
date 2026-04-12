from __future__ import annotations

import time
from typing import Any

from services.energy_service import energy_service
from services.automation_energy_state_store import automation_energy_state_store


LOW_ON_KW = 0.5
MEDIUM_ON_KW = 1.5
HIGH_ON_KW = 3.0

LOW_OFF_KW = 0.3
MEDIUM_OFF_KW = 1.0
HIGH_OFF_KW = 2.5

LOW_MIN_STABLE_SECONDS = 5 * 60
MEDIUM_MIN_STABLE_SECONDS = 3 * 60
HIGH_MIN_STABLE_SECONDS = 2 * 60

COOLDOWN_SECONDS = 3 * 60


class AutomationEnergyService:
    """
    Reusable anti-flapping automation readiness layer for excess solar energy.

    This service sits on top of energy_service.get_power_flow_summary()
    and decides whether the house currently has stable, automation-safe
    excess energy available.

    State is persisted in SQLite so all Gunicorn workers share one
    authoritative readiness timeline.
    """

    def _now(self) -> float:
        return time.time()

    def _required_stable_seconds(self, level: str) -> int:
        if level == "high":
            return HIGH_MIN_STABLE_SECONDS
        if level == "medium":
            return MEDIUM_MIN_STABLE_SECONDS
        if level == "low":
            return LOW_MIN_STABLE_SECONDS
        return 0

    def _determine_level_with_hysteresis(self, available_kw: float, previous_level: str) -> str:
        if previous_level == "high":
            if available_kw >= HIGH_OFF_KW:
                return "high"
        elif previous_level == "medium":
            if available_kw >= HIGH_ON_KW:
                return "high"
            if available_kw >= MEDIUM_OFF_KW:
                return "medium"
        elif previous_level == "low":
            if available_kw >= HIGH_ON_KW:
                return "high"
            if available_kw >= MEDIUM_ON_KW:
                return "medium"
            if available_kw >= LOW_OFF_KW:
                return "low"

        if available_kw >= HIGH_ON_KW:
            return "high"
        if available_kw >= MEDIUM_ON_KW:
            return "medium"
        if available_kw >= LOW_ON_KW:
            return "low"
        return "none"

    def _is_cooldown_active(self, now: float, cooldown_until_ts: float | None) -> tuple[bool, int]:
        if cooldown_until_ts is None:
            return False, 0
        if now >= float(cooldown_until_ts):
            return False, 0
        return True, max(0, int(float(cooldown_until_ts) - now))

    def _build_reason(
        self,
        *,
        ready: bool,
        level: str,
        available_kw: float,
        stable_for_seconds: int,
        required_stable_seconds: int,
        cooldown_active: bool,
        cooldown_remaining_seconds: int,
    ) -> str:
        if cooldown_active:
            return (
                f"Excess energy recently dropped out. Cooldown is active for another "
                f"{cooldown_remaining_seconds} seconds. Current available excess is "
                f"{available_kw:.2f} kilowatts."
            )

        if level == "none":
            return (
                f"No automation-safe excess energy is currently available. "
                f"Available excess is {available_kw:.2f} kilowatts."
            )

        if not ready:
            remaining = max(0, required_stable_seconds - stable_for_seconds)
            return (
                f"Excess energy is currently {level.upper()} at {available_kw:.2f} kilowatts, "
                f"but it has only been stable for {stable_for_seconds} seconds. "
                f"It needs {required_stable_seconds} stable seconds before it becomes ready "
                f"for automation. {remaining} seconds remaining."
            )

        return (
            f"Excess energy is stable and ready for automation. "
            f"Level is {level.upper()} with {available_kw:.2f} kilowatts available."
        )

    def get_excess_energy_ready(self) -> dict[str, Any]:
        now = self._now()

        summary = energy_service.get_power_flow_summary()
        available_kw = float(summary.get("excess_energy_available_kw") or 0.0)

        state = automation_energy_state_store.get_state()
        previous_level = str(state.get("current_level") or "none")
        stable_since_ts = state.get("stable_since_ts")
        last_state_change_ts = state.get("last_state_change_ts")
        cooldown_until_ts = state.get("cooldown_until_ts")

        new_level = self._determine_level_with_hysteresis(available_kw, previous_level)

        if stable_since_ts is None:
            stable_since_ts = now

        if new_level != previous_level:
            stable_since_ts = now
            last_state_change_ts = now

            if new_level == "none" and previous_level != "none":
                cooldown_until_ts = now + COOLDOWN_SECONDS

        automation_energy_state_store.set_state(
            current_level=new_level,
            stable_since_ts=stable_since_ts,
            last_state_change_ts=last_state_change_ts,
            cooldown_until_ts=cooldown_until_ts,
        )

        stable_for_seconds = max(0, int(now - float(stable_since_ts or now)))
        required_stable_seconds = self._required_stable_seconds(new_level)

        cooldown_active, cooldown_remaining_seconds = self._is_cooldown_active(now, cooldown_until_ts)

        ready = (
            new_level != "none"
            and not cooldown_active
            and stable_for_seconds >= required_stable_seconds
        )

        safe_to_use = ready

        return {
            "status": summary.get("status", "unknown"),
            "timestamp": summary.get("timestamp"),
            "ready": ready,
            "safe_to_use": safe_to_use,
            "level": new_level,
            "available_kw": round(available_kw, 3),
            "reason": self._build_reason(
                ready=ready,
                level=new_level,
                available_kw=available_kw,
                stable_for_seconds=stable_for_seconds,
                required_stable_seconds=required_stable_seconds,
                cooldown_active=cooldown_active,
                cooldown_remaining_seconds=cooldown_remaining_seconds,
            ),
            "state": {
                "stable_for_seconds": stable_for_seconds,
                "required_stable_seconds": required_stable_seconds,
                "cooldown_active": cooldown_active,
                "cooldown_remaining_seconds": cooldown_remaining_seconds,
                "last_state_change_ts": last_state_change_ts,
                "current_level": new_level,
                "backend": "sqlite",
            },
            "energy": {
                "solar_power_kw": summary.get("solar_power_kw"),
                "grid_import_kw": summary.get("grid_import_kw"),
                "grid_export_kw": summary.get("grid_export_kw"),
                "estimated_house_load_kw": summary.get("estimated_house_load_kw"),
                "self_consumed_solar_kw": summary.get("self_consumed_solar_kw"),
                "excess_energy_available_kw": summary.get("excess_energy_available_kw"),
                "excess_energy_state": summary.get("excess_energy_state"),
                "excess_energy_reason": summary.get("excess_energy_reason"),
                "export_reserve_kw": summary.get("export_reserve_kw"),
                "source_status": summary.get("source_status"),
            },
        }


automation_energy_service = AutomationEnergyService()
