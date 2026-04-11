def build_crypto_direct_response(intents, tool_data, is_crypto_question, is_power_question):
    if is_crypto_question and not is_power_question:
        intents = [
            i
            for i in intents
            if i
            not in {
                "power_last_24h_summary",
                "energy_summary",
                "power_now",
                "energy_today",
                "energy_yesterday",
                "energy_compare_today_yesterday",
            }
        ]
        tool_data.pop("power_last_24h_summary", None)
        tool_data.pop("energy_summary", None)
        tool_data.pop("power_now", None)
        tool_data.pop("energy_today", None)
        tool_data.pop("energy_yesterday", None)
        tool_data.pop("energy_compare_today_yesterday", None)

    if "crypto_coin_summary" in intents and "crypto_coin_summary" in tool_data:
        c = tool_data["crypto_coin_summary"]
        symbol_name = c.get("symbol", "unknown")
        amount = c.get("amount")
        price = c.get("price")
        value = c.get("value")

        amount_txt = f"{amount:.8f}".rstrip("0").rstrip(".") if amount is not None else "unknown"
        price_txt = f"{price:.5f}".rstrip("0").rstrip(".") if price is not None else "unknown"
        value_txt = f"{value:.2f}" if value is not None else "unknown"

        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["crypto_coin_summary"],
            "tool_data": {"crypto_coin_summary": c},
            "answer": (
                f"You hold {amount_txt} {symbol_name}. "
                f"Current price is {price_txt}, for a position value of {value_txt}."
            ),
        }

    if "crypto_portfolio_summary" in intents and "crypto_portfolio_summary" in tool_data:
        s = tool_data["crypto_portfolio_summary"]
        total_value = s.get("total_value", 0.0)
        coin_count = s.get("coin_count", 0)
        largest = s.get("largest_holding") or {}
        largest_symbol = largest.get("symbol", "unknown")
        largest_value = largest.get("value", 0.0)

        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["crypto_portfolio_summary"],
            "tool_data": {"crypto_portfolio_summary": s},
            "answer": (
                f"Your crypto portfolio is worth {total_value:.2f} across {coin_count} holdings. "
                f"The largest holding is {largest_symbol} at {largest_value:.2f}."
            ),
        }

    if "crypto_portfolio_composition" in intents and "crypto_portfolio_composition" in tool_data:
        c = tool_data["crypto_portfolio_composition"]
        total_value = c.get("total_value", 0.0)
        top_holdings = c.get("top_holdings", [])
        others = c.get("others", {})

        lines = [f"Your crypto portfolio is worth {total_value:.2f}.", "", "Top holdings:"]

        for item in top_holdings:
            lines.append(f"- {item['symbol']}: {item['value']:.2f} ({item['percentage']:.2f}%)")

        if others:
            lines.append(
                f"- All others: {others.get('value', 0.0):.2f} "
                f"({others.get('percentage', 0.0):.2f}%) across "
                f"{others.get('count', 0)} holdings"
            )

        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["crypto_portfolio_composition"],
            "tool_data": {"crypto_portfolio_composition": c},
            "answer": "\n".join(lines),
        }

    if "crypto_compare_now_vs_24h" in intents and "crypto_compare_now_vs_24h" in tool_data:
        d = tool_data["crypto_compare_now_vs_24h"]
        current_total = d.get("current_total_value", 0.0)
        old_total = d.get("value_24h_ago", 0.0)
        delta = d.get("delta", 0.0)
        delta_pct = d.get("delta_pct")

        delta_pct_txt = f"{delta_pct:.2f}%" if delta_pct is not None else "unknown"
        direction = "up" if delta >= 0 else "down"

        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["crypto_compare_now_vs_24h"],
            "tool_data": {"crypto_compare_now_vs_24h": d},
            "answer": (
                f"Your crypto portfolio is currently worth {current_total:.2f}. "
                f"24 hours ago it was {old_total:.2f}. "
                f"That is {abs(delta):.2f} {direction} over 24h ({delta_pct_txt})."
            ),
        }

    if "crypto_top_movers_24h" in intents and "crypto_top_movers_24h" in tool_data:
        m = tool_data["crypto_top_movers_24h"]
        gainers = m.get("top_gainers", [])[:3]
        losers = m.get("top_losers", [])[:3]

        gain_lines = []
        for item in gainers:
            pct = item.get("delta_pct")
            pct_txt = f" ({pct:.2f}%)" if pct is not None else ""
            gain_lines.append(f"- {item['symbol']}: +{item['delta']:.2f}{pct_txt}")

        lose_lines = []
        for item in losers:
            pct = item.get("delta_pct")
            pct_txt = f" ({pct:.2f}%)" if pct is not None else ""
            lose_lines.append(f"- {item['symbol']}: {item['delta']:.2f}{pct_txt}")

        answer_parts = []
        if gain_lines:
            answer_parts.append("Top gainers in the last 24h:\n" + "\n".join(gain_lines))
        if lose_lines:
            answer_parts.append("Top losers in the last 24h:\n" + "\n".join(lose_lines))

        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["crypto_top_movers_24h"],
            "tool_data": {"crypto_top_movers_24h": m},
            "answer": "\n\n".join(answer_parts),
        }

    if "crypto_concentration_risk" in intents and "crypto_concentration_risk" in tool_data:
        c = tool_data["crypto_concentration_risk"]
        largest = c.get("largest_holding") or {}
        largest_symbol = largest.get("symbol", "unknown")
        largest_pct = c.get("top1_pct", 0.0)
        top3_pct = c.get("top3_pct", 0.0)
        top5_pct = c.get("top5_pct", 0.0)
        risk_level = c.get("risk_level", "unknown")

        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["crypto_concentration_risk"],
            "tool_data": {"crypto_concentration_risk": c},
            "answer": (
                f"Your crypto portfolio concentration is {risk_level}. "
                f"The largest holding is {largest_symbol} at {largest_pct:.2f}% of the portfolio. "
                f"The top 3 holdings make up {top3_pct:.2f}%, and the top 5 holdings make up {top5_pct:.2f}%."
            ),
        }

    if "crypto_stale_data_check" in intents and "crypto_stale_data_check" in tool_data:
        s = tool_data["crypto_stale_data_check"]
        stale_count = s.get("stale_count", 0)
        stale_value_total = s.get("stale_value_total", 0.0)
        stale_symbols = s.get("stale_symbols", [])

        if stale_count == 0:
            answer = "No stale crypto data was detected."
        else:
            names = ", ".join(item["symbol"] for item in stale_symbols[:5])
            answer = (
                f"Stale crypto data detected for {stale_count} symbol(s): {names}. "
                f"Total stale value is {stale_value_total:.2f}."
            )

        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["crypto_stale_data_check"],
            "tool_data": {"crypto_stale_data_check": s},
            "answer": answer,
        }

    if "crypto_daily_pnl_summary" in intents and "crypto_daily_pnl_summary" in tool_data:
        d = tool_data["crypto_daily_pnl_summary"]

        current_total = d.get("current_total_value", 0.0)
        old_total = d.get("value_24h_ago", 0.0)
        delta = d.get("delta", 0.0)
        delta_pct = d.get("delta_pct")
        best = d.get("best_contributor") or {}
        worst = d.get("worst_contributor") or {}

        delta_pct_txt = f"{delta_pct:.2f}%" if delta_pct is not None else "unknown"

        answer = (
            f"Your crypto portfolio is currently worth {current_total:.2f}. "
            f"24 hours ago it was {old_total:.2f}. "
            f"The 24h change is {delta:+.2f} ({delta_pct_txt})."
        )

        if best:
            answer += (
                f" Best contributor: {best.get('symbol', 'unknown')} "
                f"({best.get('contribution', 0.0):+.2f})."
            )

        if worst:
            answer += (
                f" Worst contributor: {worst.get('symbol', 'unknown')} "
                f"({worst.get('contribution', 0.0):+.2f})."
            )

        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["crypto_daily_pnl_summary"],
            "tool_data": {"crypto_daily_pnl_summary": d},
            "answer": answer,
        }

    if "crypto_contributors_24h" in intents and "crypto_contributors_24h" in tool_data:
        c = tool_data["crypto_contributors_24h"]
        best = c.get("best_contributors", [])[:3]
        worst = c.get("worst_contributors", [])[:3]

        best_lines = []
        for item in best:
            best_lines.append(f"- {item['symbol']}: {item['contribution']:+.2f}")

        worst_lines = []
        for item in worst:
            worst_lines.append(f"- {item['symbol']}: {item['contribution']:+.2f}")

        parts = []
        if best_lines:
            parts.append("Top positive contributors in the last 24h:\n" + "\n".join(best_lines))
        if worst_lines:
            parts.append("Top negative contributors in the last 24h:\n" + "\n".join(worst_lines))

        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["crypto_contributors_24h"],
            "tool_data": {"crypto_contributors_24h": c},
            "answer": "\n\n".join(parts),
        }

    if "crypto_portfolio_health" in intents and "crypto_portfolio_health" in tool_data:
        h = tool_data["crypto_portfolio_health"]

        total_value = h.get("total_value", 0.0)
        delta_24h = h.get("delta_24h", 0.0)
        delta_24h_pct = h.get("delta_24h_pct")
        coin_count = h.get("coin_count", 0)
        top3_pct = h.get("top3_pct", 0.0)
        risk_level = h.get("risk_level", "unknown")
        stale_count = h.get("stale_count", 0)

        largest = h.get("largest_holding") or {}
        largest_symbol = largest.get("symbol", "unknown")
        largest_value = largest.get("value", 0.0)

        best = h.get("best_contributor") or {}
        worst = h.get("worst_contributor") or {}

        delta_pct_txt = f"{delta_24h_pct:.2f}%" if delta_24h_pct is not None else "unknown"

        answer = (
            f"Your crypto portfolio is worth {total_value:.2f} across {coin_count} holdings. "
            f"The 24h change is {delta_24h:+.2f} ({delta_pct_txt}). "
            f"The largest holding is {largest_symbol} at {largest_value:.2f}. "
            f"Top 3 concentration is {top3_pct:.2f}% and risk level is {risk_level}. "
            f"Stale symbols: {stale_count}."
        )

        if best and worst:
            answer += (
                f" Best contributor: {best.get('symbol', 'unknown')} "
                f"({best.get('contribution', 0.0):+.2f}). "
                f"Worst contributor: {worst.get('symbol', 'unknown')} "
                f"({worst.get('contribution', 0.0):+.2f})."
            )

        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["crypto_portfolio_health"],
            "tool_data": {"crypto_portfolio_health": h},
            "answer": answer,
        }

    if "crypto_compare_7d" in intents and "crypto_compare_7d" in tool_data:
        d = tool_data["crypto_compare_7d"]
        current_total = d.get("current_total_value", 0.0)
        old_total = d.get("value_7d_ago", 0.0)
        delta = d.get("delta", 0.0)
        delta_pct = d.get("delta_pct")

        delta_pct_txt = f"{delta_pct:.2f}%" if delta_pct is not None else "unknown"
        direction = "up" if delta >= 0 else "down"

        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["crypto_compare_7d"],
            "tool_data": {"crypto_compare_7d": d},
            "answer": (
                f"Your crypto portfolio is currently worth {current_total:.2f}. "
                f"7 days ago it was {old_total:.2f}. "
                f"That is {abs(delta):.2f} {direction} over 7 days ({delta_pct_txt})."
            ),
        }

    if "crypto_drawdown_7d" in intents and "crypto_drawdown_7d" in tool_data:
        d = tool_data["crypto_drawdown_7d"]
        items = d.get("largest_drawdowns", [])[:5]

        if not items:
            answer = "No 7-day drawdown data is available."
        else:
            lines = ["Largest 7-day drawdowns:"]
            for item in items:
                pct = item.get("drawdown_pct")
                pct_txt = f" ({pct:.2f}%)" if pct is not None else ""
                lines.append(
                    f"- {item['symbol']}: -{item['drawdown']:.2f}{pct_txt} from a 7d peak of {item['peak_7d']:.2f}"
                )
            answer = "\n".join(lines)

        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["crypto_drawdown_7d"],
            "tool_data": {"crypto_drawdown_7d": d},
            "answer": answer,
        }

    if "crypto_excluding_symbol_summary" in intents and "crypto_excluding_symbol_summary" in tool_data:
        e = tool_data["crypto_excluding_symbol_summary"]
        excluded = e.get("excluded_symbol", "XRP")
        total_ex = e.get("total_value_excluding_symbol", 0.0)
        count_ex = e.get("coin_count_excluding_symbol", 0)
        largest = e.get("largest_remaining_holding") or {}
        largest_symbol = largest.get("symbol", "unknown")
        largest_value = largest.get("value", 0.0)

        return {
            "status": "ok",
            "mode": "direct_tool",
            "intents": intents,
            "used_tools": ["crypto_excluding_symbol_summary"],
            "tool_data": {"crypto_excluding_symbol_summary": e},
            "answer": (
                f"Excluding {excluded}, your remaining crypto portfolio is worth {total_ex:.2f} "
                f"across {count_ex} holdings. "
                f"The largest remaining holding is {largest_symbol} at {largest_value:.2f}."
            ),
        }

    return None

