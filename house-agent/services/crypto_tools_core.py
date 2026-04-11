from __future__ import annotations

from typing import Any, Dict, List, Optional
from influxdb_client import InfluxDBClient
from datetime import datetime, timezone


class CryptoTools:
    def __init__(self, url: str, token: str, org: str, bucket: str = "crypto") -> None:
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
        self.query_api = self.client.query_api()

    def _query(self, flux: str) -> List[Dict[str, Any]]:
        tables = self.query_api.query(query=flux, org=self.org)
        rows: List[Dict[str, Any]] = []

        for table in tables:
            for record in table.records:
                row = {
                    "time": record.get_time().isoformat() if record.get_time() else None,
                    "measurement": record.get_measurement(),
                    "field": record.get_field(),
                    "value": record.get_value(),
                }
                for k, v in record.values.items():
                    if k not in row:
                        row[k] = v
                rows.append(row)

        return rows

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            return float(value)
        except Exception:
            return default

    def _latest_value_rows(self, field_name: str, range_start: str = "-30d") -> List[Dict[str, Any]]:
        flux = f'''
from(bucket: "{self.bucket}")
  |> range(start: {range_start})
  |> filter(fn: (r) => r["_measurement"] == "crypto_portfolio")
  |> filter(fn: (r) => r["_field"] == "{field_name}")
  |> group(columns: ["symbol"])
  |> last()
'''
        return self._query(flux)

    def _window_last_map(self, field_name: str, start: str, stop: Optional[str] = None) -> Dict[str, float]:
        stop_clause = f', stop: {stop}' if stop else ""
        flux = f'''
from(bucket: "{self.bucket}")
  |> range(start: {start}{stop_clause})
  |> filter(fn: (r) => r["_measurement"] == "crypto_portfolio")
  |> filter(fn: (r) => r["_field"] == "{field_name}")
  |> group(columns: ["symbol"])
  |> last()
'''
        rows = self._query(flux)
        return {str(r.get("symbol")): self._safe_float(r.get("value")) for r in rows}

    def _window_last_rows(self, field_name: str, start: str, stop: Optional[str] = None) -> List[Dict[str, Any]]:
        stop_clause = f', stop: {stop}' if stop else ""
        flux = f'''
from(bucket: "{self.bucket}")
  |> range(start: {start}{stop_clause})
  |> filter(fn: (r) => r["_measurement"] == "crypto_portfolio")
  |> filter(fn: (r) => r["_field"] == "{field_name}")
  |> group(columns: ["symbol"])
  |> last()
'''
        return self._query(flux)

    def get_current_portfolio_summary(self) -> Dict[str, Any]:
        rows = self._latest_value_rows("value", "-30d")

        symbols = []
        total_value = 0.0

        for row in rows:
            symbol = str(row.get("symbol"))
            value = self._safe_float(row.get("value"))
            total_value += value
            symbols.append({
                "symbol": symbol,
                "value": round(value, 2),
                "time": row.get("time"),
            })

        symbols.sort(key=lambda x: x["value"], reverse=True)

        return {
            "bucket": self.bucket,
            "measurement": "crypto_portfolio",
            "total_value": round(total_value, 2),
            "coin_count": len(symbols),
            "largest_holding": symbols[0] if symbols else None,
            "symbols": symbols,
        }

    def get_portfolio_composition(self, top_n: int = 5) -> Dict[str, Any]:
        summary = self.get_current_portfolio_summary()
        total_value = self._safe_float(summary.get("total_value"))

        composition = []
        for item in summary["symbols"]:
            pct = (item["value"] / total_value * 100.0) if total_value > 0 else 0.0
            composition.append({
                "symbol": item["symbol"],
                "value": round(item["value"], 2),
                "percentage": round(pct, 2),
                "time": item.get("time"),
            })

        composition.sort(key=lambda x: x["value"], reverse=True)

        top = composition[:top_n]
        rest = composition[top_n:]
        others_value = round(sum(x["value"] for x in rest), 2)
        others_pct = round(sum(x["percentage"] for x in rest), 2)

        return {
            "total_value": round(total_value, 2),
            "top_n": top_n,
            "top_holdings": top,
            "others": {
                "count": len(rest),
                "value": others_value,
                "percentage": others_pct,
            },
            "composition": composition,
        }

    def get_coin_summary(self, symbol: str) -> Dict[str, Any]:
        symbol = symbol.upper()

        flux = f'''
from(bucket: "{self.bucket}")
  |> range(start: -30d)
  |> filter(fn: (r) => r["_measurement"] == "crypto_portfolio")
  |> filter(fn: (r) => r["symbol"] == "{symbol}")
  |> filter(fn: (r) => r["_field"] == "amount" or r["_field"] == "price" or r["_field"] == "value")
  |> group(columns: ["_field"])
  |> last()
'''
        rows = self._query(flux)

        result = {
            "symbol": symbol,
            "amount": None,
            "price": None,
            "value": None,
            "time": None,
        }

        for row in rows:
            field = row.get("field")
            if field in ("amount", "price", "value"):
                result[field] = row.get("value")
                result["time"] = row.get("time")

        return result

    def compare_portfolio_now_vs_24h(self) -> Dict[str, Any]:
        now_map = self._window_last_map("value", "-2h")
        old_map = self._window_last_map("value", "-26h", "-22h")

        current_total = sum(now_map.values())
        old_total = sum(old_map.values())
        delta = current_total - old_total
        delta_pct = (delta / old_total * 100.0) if old_total else None

        return {
            "current_total_value": round(current_total, 2),
            "value_24h_ago": round(old_total, 2),
            "delta": round(delta, 2),
            "delta_pct": round(delta_pct, 2) if delta_pct is not None else None,
        }

    def get_top_movers_24h(self) -> Dict[str, Any]:
        now_map = self._window_last_map("value", "-2h")
        old_map = self._window_last_map("value", "-26h", "-22h")

        all_symbols = sorted(set(now_map.keys()) | set(old_map.keys()))
        movers = []

        for symbol in all_symbols:
            current_value = self._safe_float(now_map.get(symbol))
            old_value = self._safe_float(old_map.get(symbol))
            delta = current_value - old_value
            delta_pct = (delta / old_value * 100.0) if old_value else None

            movers.append({
                "symbol": symbol,
                "current_value": round(current_value, 2),
                "value_24h_ago": round(old_value, 2),
                "delta": round(delta, 2),
                "delta_pct": round(delta_pct, 2) if delta_pct is not None else None,
            })

        by_abs = sorted(movers, key=lambda x: abs(x["delta"]), reverse=True)
        gainers = sorted(movers, key=lambda x: x["delta"], reverse=True)
        losers = sorted(movers, key=lambda x: x["delta"])

        return {
            "top_absolute_movers": by_abs[:5],
            "top_gainers": gainers[:5],
            "top_losers": losers[:5],
            "all_movers": movers,
        }

    def get_contributors_24h(self) -> Dict[str, Any]:
        now_map = self._window_last_map("value", "-2h")
        old_map = self._window_last_map("value", "-26h", "-22h")

        all_symbols = sorted(set(now_map.keys()) | set(old_map.keys()))
        contributors = []

        for symbol in all_symbols:
            now_val = self._safe_float(now_map.get(symbol))
            old_val = self._safe_float(old_map.get(symbol))
            contribution = now_val - old_val
            contributors.append({
                "symbol": symbol,
                "current_value": round(now_val, 2),
                "value_24h_ago": round(old_val, 2),
                "contribution": round(contribution, 2),
            })

        contributors_sorted = sorted(contributors, key=lambda x: x["contribution"], reverse=True)

        return {
            "best_contributors": contributors_sorted[:5],
            "worst_contributors": sorted(contributors, key=lambda x: x["contribution"])[:5],
            "all_contributors": contributors,
        }

    def get_concentration_risk(self) -> Dict[str, Any]:
        composition_data = self.get_portfolio_composition(top_n=5)
        composition = composition_data["composition"]

        top1_pct = round(composition[0]["percentage"], 2) if len(composition) >= 1 else 0.0
        top3_pct = round(sum(x["percentage"] for x in composition[:3]), 2) if len(composition) >= 3 else round(sum(x["percentage"] for x in composition), 2)
        top5_pct = round(sum(x["percentage"] for x in composition[:5]), 2) if len(composition) >= 5 else round(sum(x["percentage"] for x in composition), 2)

        dust_positions = [x for x in composition if x["percentage"] < 0.25]
        above_1pct = [x for x in composition if x["percentage"] >= 1.0]

        hhi = round(sum((x["percentage"] / 100.0) ** 2 for x in composition), 4)

        level = "low"
        if top1_pct >= 50 or top3_pct >= 80:
            level = "high"
        elif top1_pct >= 30 or top3_pct >= 60:
            level = "medium"

        return {
            "largest_holding": composition[0] if composition else None,
            "top1_pct": top1_pct,
            "top3_pct": top3_pct,
            "top5_pct": top5_pct,
            "holdings_over_1pct": len(above_1pct),
            "dust_positions": len(dust_positions),
            "hhi": hhi,
            "risk_level": level,
            "top_holdings": composition[:5],
        }

    def get_stale_data_check(self, stale_hours: int = 12) -> Dict[str, Any]:
        rows = self._latest_value_rows("value", "-30d")
        now = datetime.now(timezone.utc)

        stale = []
        fresh = []

        for row in rows:
            symbol = str(row.get("symbol"))
            value = round(self._safe_float(row.get("value")), 2)
            ts_str = row.get("time")

            if not ts_str:
                stale.append({
                    "symbol": symbol,
                    "value": value,
                    "time": None,
                    "age_hours": None,
                })
                continue

            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            age_hours = (now - ts).total_seconds() / 3600.0

            item = {
                "symbol": symbol,
                "value": value,
                "time": ts_str,
                "age_hours": round(age_hours, 2),
            }

            if age_hours > stale_hours:
                stale.append(item)
            else:
                fresh.append(item)

        stale.sort(key=lambda x: (x["age_hours"] is None, x["age_hours"]), reverse=True)

        return {
            "stale_threshold_hours": stale_hours,
            "stale_count": len(stale),
            "fresh_count": len(fresh),
            "stale_symbols": stale,
            "stale_value_total": round(sum(x["value"] for x in stale), 2),
            "fresh_value_total": round(sum(x["value"] for x in fresh), 2),
            "has_stale_data": len(stale) > 0,
        }

    def get_daily_pnl_summary(self) -> Dict[str, Any]:
        compare = self.compare_portfolio_now_vs_24h()
        contributors = self.get_contributors_24h()

        best = contributors["best_contributors"][0] if contributors["best_contributors"] else None
        worst = contributors["worst_contributors"][0] if contributors["worst_contributors"] else None

        return {
            "current_total_value": compare["current_total_value"],
            "value_24h_ago": compare["value_24h_ago"],
            "delta": compare["delta"],
            "delta_pct": compare["delta_pct"],
            "best_contributor": best,
            "worst_contributor": worst,
        }

    def get_portfolio_health(self) -> Dict[str, Any]:
        summary = self.get_current_portfolio_summary()
        compare = self.compare_portfolio_now_vs_24h()
        concentration = self.get_concentration_risk()
        stale = self.get_stale_data_check()
        contributors = self.get_contributors_24h()

        best = contributors["best_contributors"][0] if contributors["best_contributors"] else None
        worst = contributors["worst_contributors"][0] if contributors["worst_contributors"] else None

        return {
            "total_value": summary["total_value"],
            "coin_count": summary["coin_count"],
            "largest_holding": summary["largest_holding"],
            "delta_24h": compare["delta"],
            "delta_24h_pct": compare["delta_pct"],
            "top3_pct": concentration["top3_pct"],
            "risk_level": concentration["risk_level"],
            "stale_count": stale["stale_count"],
            "stale_value_total": stale["stale_value_total"],
            "best_contributor": best,
            "worst_contributor": worst,
        }

    def get_drawdown_7d(self) -> Dict[str, Any]:
        latest_map = self._window_last_map("value", "-2h")

        flux = f'''
from(bucket: "{self.bucket}")
  |> range(start: -7d)
  |> filter(fn: (r) => r["_measurement"] == "crypto_portfolio")
  |> filter(fn: (r) => r["_field"] == "value")
  |> group(columns: ["symbol"])
  |> max()
'''
        max_rows = self._query(flux)
        max_map = {str(r.get("symbol")): self._safe_float(r.get("value")) for r in max_rows}

        all_symbols = sorted(set(latest_map.keys()) | set(max_map.keys()))
        drawdowns = []

        for symbol in all_symbols:
            current_value = self._safe_float(latest_map.get(symbol))
            peak_value = self._safe_float(max_map.get(symbol))
            drawdown = peak_value - current_value
            drawdown_pct = (drawdown / peak_value * 100.0) if peak_value else None

            drawdowns.append({
                "symbol": symbol,
                "current_value": round(current_value, 2),
                "peak_7d": round(peak_value, 2),
                "drawdown": round(drawdown, 2),
                "drawdown_pct": round(drawdown_pct, 2) if drawdown_pct is not None else None,
            })

        drawdowns_sorted = sorted(drawdowns, key=lambda x: x["drawdown"], reverse=True)

        return {
            "largest_drawdowns": drawdowns_sorted[:5],
            "all_drawdowns": drawdowns,
        }

    def get_compare_7d(self) -> Dict[str, Any]:
        now_map = self._window_last_map("value", "-2h")
        old_map = self._window_last_map("value", "-8d", "-7d")

        current_total = sum(now_map.values())
        old_total = sum(old_map.values())
        delta = current_total - old_total
        delta_pct = (delta / old_total * 100.0) if old_total else None

        return {
            "current_total_value": round(current_total, 2),
            "value_7d_ago": round(old_total, 2),
            "delta": round(delta, 2),
            "delta_pct": round(delta_pct, 2) if delta_pct is not None else None,
        }

    def get_excluding_symbol_summary(self, exclude_symbol: str = "XRP") -> Dict[str, Any]:
        exclude_symbol = exclude_symbol.upper()
        summary = self.get_current_portfolio_summary()
        symbols = [x for x in summary["symbols"] if x["symbol"] != exclude_symbol]

        total_excluding = round(sum(x["value"] for x in symbols), 2)
        largest = max(symbols, key=lambda x: x["value"]) if symbols else None

        return {
            "excluded_symbol": exclude_symbol,
            "total_value_excluding_symbol": total_excluding,
            "coin_count_excluding_symbol": len(symbols),
            "largest_remaining_holding": largest,
            "symbols": symbols,
        }
