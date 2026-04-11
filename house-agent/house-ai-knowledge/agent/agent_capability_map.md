# Agent Capability Map

This file maps user intents to routes, services, tools, and safety policy.

## Routes detected

- `POST /agent/query` -> `routes/agent_routes.py::agent_query` [write_action / medium]
- `POST /house/speak/living` -> `routes/agent_routes.py::house_speak_living` [write_action / medium]
- `POST /house/speak/wc` -> `routes/agent_routes.py::house_speak_wc` [write_action / medium]
- `POST /tools/audio/node_power/<state>` -> `routes/audio_tool_routes.py::tools_audio_node_power` [write_action / high]
- `POST /tools/audio/party/<state>` -> `routes/audio_tool_routes.py::tools_audio_party` [write_action / high]
- `POST /tools/audio/playback/<state>` -> `routes/audio_tool_routes.py::tools_audio_playback` [write_action / high]
- `POST /tools/audio/speaker_route/<state>` -> `routes/audio_tool_routes.py::tools_audio_speaker_route` [write_action / high]
- `GET /health` -> `routes/health_routes.py::health` [read_only / low]
- `GET /house/conversation/<conversation_id>/speaker` -> `routes/house_routes.py::house_conversation_last_speaker` [read_only / medium]
- `GET /house/diagnostics` -> `routes/house_routes.py::house_diagnostics` [read_only / medium]
- `GET /house/diagnostics/text` -> `routes/house_routes.py::house_diagnostics_text` [read_only / medium]
- `GET /house/help` -> `routes/house_routes.py::house_help` [read_only / medium]
- `GET /house/help/text` -> `routes/house_routes.py::house_help_text` [read_only / medium]
- `POST /house/speak/<speaker>` -> `routes/house_routes.py::house_speak_named` [write_action / medium]
- `POST /house/speak/all` -> `routes/house_routes.py::house_speak_all` [write_action / medium]
- `POST /house/speak/default` -> `routes/house_routes.py::house_speak_default` [write_action / medium]
- `POST /house/speak/last` -> `routes/house_routes.py::house_speak_last` [write_action / medium]
- `GET /house/speaker/<speaker>/status` -> `routes/house_routes.py::house_speaker_status` [read_only / medium]
- `POST /house/speaker/<speaker>/test` -> `routes/house_routes.py::house_speaker_test` [write_action / medium]
- `GET /house/status` -> `routes/house_routes.py::house_status` [read_only / medium]
- `GET /ai/audio_resolve_control` -> `routes/loxone_routes.py::audio_resolve_control` [read_only / low]
- `GET /ai/audio_tool_targets` -> `routes/loxone_routes.py::audio_tool_targets` [read_only / low]
- `GET /ai/loxone_audio_action_map` -> `routes/loxone_routes.py::loxone_audio_action_map` [read_only / high]
- `GET /ai/loxone_audio_behavior_map` -> `routes/loxone_routes.py::loxone_audio_behavior_map` [read_only / high]
- `GET /ai/loxone_audio_control_candidates` -> `routes/loxone_routes.py::loxone_audio_control_candidates` [read_only / high]
- `GET /ai/loxone_audio_controls_by_room` -> `routes/loxone_routes.py::loxone_audio_controls_by_room` [read_only / high]
- `GET /ai/loxone_controls_by_category` -> `routes/loxone_routes.py::loxone_controls_by_category` [read_only / high]
- `GET /ai/loxone_controls_by_room` -> `routes/loxone_routes.py::loxone_controls_by_room` [read_only / high]
- `GET /ai/loxone_lighting_controls_by_room` -> `routes/loxone_routes.py::loxone_lighting_controls_by_room` [read_only / high]
- `GET /ai/loxone_room_summary` -> `routes/loxone_routes.py::loxone_room_summary` [read_only / high]
- `GET /ai/loxone_room_temperature` -> `routes/loxone_routes.py::loxone_room_temperature` [read_only / high]
- `GET /ai/loxone_structure_summary` -> `routes/loxone_routes.py::loxone_structure_summary` [read_only / high]
- `POST /v1/chat/completions` -> `routes/openai_routes.py::openai_chat_completions` [write_action / low]
- `GET /v1/models` -> `routes/openai_routes.py::openai_models` [read_only / low]
- `GET /ai/pdata_all_fields` -> `routes/pdata_routes.py::ai_pdata_all_fields` [read_only / low]
- `GET /ai/pdata_compare_energy` -> `routes/pdata_routes.py::ai_pdata_compare_energy` [read_only / low]
- `GET /ai/pdata_energy_summary` -> `routes/pdata_routes.py::ai_pdata_energy_summary` [read_only / low]
- `GET /ai/pdata_full_overview` -> `routes/pdata_routes.py::ai_pdata_full_overview` [read_only / low]
- `GET /ai/pdata_gas_summary` -> `routes/pdata_routes.py::ai_pdata_gas_summary` [read_only / low]
- `GET /ai/energy_summary` -> `routes/power_routes.py::ai_energy_summary` [read_only / low]
- `GET /ai/energy_today` -> `routes/power_routes.py::ai_energy_today` [read_only / low]
- `GET /ai/phase_overview` -> `routes/power_routes.py::ai_phase_overview` [read_only / low]
- `GET /ai/power_now` -> `routes/power_routes.py::ai_power_now` [read_only / low]
- `GET /ai/cheapest_hours_today` -> `routes/price_routes.py::ai_cheapest_hours_today` [read_only / low]
- `GET /ai/electricity_cost_last_24h` -> `routes/price_routes.py::ai_electricity_cost_last_24h` [read_only / low]
- `GET /ai/electricity_cost_today` -> `routes/price_routes.py::ai_electricity_cost_today` [read_only / low]
- `GET /ai/electricity_price_now` -> `routes/price_routes.py::ai_electricity_price_now` [read_only / low]
- `GET /ai/sma_production_overview` -> `routes/sma_routes.py::ai_sma_production_overview` [read_only / low]
- `GET /ai/sma_summary` -> `routes/sma_routes.py::ai_sma_summary` [read_only / low]
- `POST /status/announce` -> `routes/status.py::status_announce` [write_action / low]
- `GET /status/full` -> `routes/status.py::status_full` [read_only / low]
- `GET /tools/ping` -> `routes/status.py::tools_ping` [read_only / low]
- `GET /experimental-tools` -> `routes/tool_routes.py::list_experimental_tools` [read_only / low]
- `POST /experimental-tools/execute` -> `routes/tool_routes.py::execute_experimental_tool` [write_action / low]
- `GET /proposed-tools` -> `routes/tool_routes.py::list_proposed` [read_only / low]
- `GET /proposed-tools/<proposal_id>` -> `routes/tool_routes.py::get_proposed` [read_only / low]
- `POST /proposed-tools/<proposal_id>/approve` -> `routes/tool_routes.py::approve_proposed` [write_action / low]
- `POST /proposed-tools/<proposal_id>/install-missing-packages` -> `routes/tool_routes.py::install_missing_packages_for_proposal` [write_action / low]
- `POST /proposed-tools/<proposal_id>/preflight` -> `routes/tool_routes.py::preflight_proposed_tool` [write_action / low]
- `POST /proposed-tools/<proposal_id>/promote` -> `routes/tool_routes.py::promote_proposed` [write_action / low]
- `POST /proposed-tools/<proposal_id>/promote-to-production` -> `routes/tool_routes.py::promote_to_production` [write_action / low]
- `POST /proposed-tools/<proposal_id>/reject` -> `routes/tool_routes.py::reject_proposed` [write_action / low]
- `POST /proposed-tools/<proposal_id>/validate` -> `routes/tool_routes.py::validate_proposed_tool` [write_action / low]
- `POST /proposed-tools/analyze-dependencies` -> `routes/tool_routes.py::analyze_proposed_dependencies` [write_action / low]
- `POST /proposed-tools/generate` -> `routes/tool_routes.py::generate_proposed_tool` [write_action / low]
- `POST /proposed-tools/install-package` -> `routes/tool_routes.py::install_proposed_package` [write_action / low]
- `POST /proposed-tools/install-plan` -> `routes/tool_routes.py::proposed_tool_install_plan` [write_action / low]
- `GET /proposed-tools/promotion-audit` -> `routes/tool_routes.py::get_promotion_audit` [read_only / low]
- `POST /proposed-tools/save` -> `routes/tool_routes.py::save_proposed` [write_action / low]
- `GET /tools` -> `routes/tool_routes.py::list_tools` [read_only / low]
- `POST /tools/execute` -> `routes/tool_routes.py::execute_tool` [write_action / low]
- `GET /voice/input/status` -> `routes/voice_input_routes.py::voice_input_status` [read_only / low]
- `POST /voice/process-last` -> `routes/voice_input_routes.py::voice_process_last` [write_action / low]
- `POST /voice/query-last` -> `routes/voice_input_routes.py::voice_query_last` [write_action / low]
- `POST /voice/transcribe-last` -> `routes/voice_input_routes.py::voice_transcribe_last` [write_action / low]
- `POST /voice/upload` -> `routes/voice_input_routes.py::voice_upload` [write_action / low]
- `POST /voice/announce` -> `routes/voice_routes.py::voice_announce` [write_action / low]
- `POST /voice/announce_once` -> `routes/voice_routes.py::voice_announce_once` [write_action / low]
- `GET /voice/files/<path:filename>` -> `routes/voice_routes.py::voice_file` [read_only / low]
- `GET /voice/logs` -> `routes/voice_routes.py::voice_logs` [read_only / low]
- `POST /voice/player_action` -> `routes/voice_routes.py::voice_player_action` [write_action / low]
- `GET /voice/player_status/<player_key>` -> `routes/voice_routes.py::voice_player_status` [read_only / low]
- `GET /voice/players` -> `routes/voice_routes.py::voice_players` [read_only / low]
- `POST /voice/say` -> `routes/voice_routes.py::voice_say` [write_action / low]
- `GET /voice/status` -> `routes/voice_routes.py::voice_status` [read_only / low]
- `POST /voice/stop` -> `routes/voice_routes.py::voice_stop` [write_action / low]
- `POST /voice/volume` -> `routes/voice_routes.py::voice_volume` [write_action / low]
- `GET /ai/salt_tank_level` -> `routes/water_routes.py::ai_salt_tank_level` [read_only / low]
- `GET /ai/water_softener_overview` -> `routes/water_routes.py::ai_water_softener_overview` [read_only / low]
- `GET /ai/water_temperatures` -> `routes/water_routes.py::ai_water_temperatures` [read_only / low]

## Production tools detected

- `apc_battery_health` -> `tools/apc_battery_health.py`
- `apc_highest_load` -> `tools/apc_highest_load.py`
- `apc_lowest_runtime` -> `tools/apc_lowest_runtime.py`
- `apc_on_battery_status` -> `tools/apc_on_battery_status.py`
- `apc_summary` -> `tools/apc_summary.py`
- `buderus_boiler_health_summary` -> `tools/buderus_boiler_health_summary.py`
- `buderus_current_status` -> `tools/buderus_current_status.py`
- `buderus_diagnostics` -> `tools/buderus_diagnostics.py`
- `buderus_heating_status` -> `tools/buderus_heating_status.py`
- `buderus_hot_water_status` -> `tools/buderus_hot_water_status.py`
- `buderus_pressure_analysis` -> `tools/buderus_pressure_analysis.py`
- `cheapest_hours_today` -> `tools/cheapest_hours_today.py`
- `crypto_coin_summary` -> `tools/crypto_coin_summary.py`
- `crypto_compare_7d` -> `tools/crypto_compare_7d.py`
- `crypto_compare_now_vs_24h` -> `tools/crypto_compare_now_vs_24h.py`
- `crypto_concentration_risk` -> `tools/crypto_concentration_risk.py`
- `crypto_contributors_24h` -> `tools/crypto_contributors_24h.py`
- `crypto_daily_pnl_summary` -> `tools/crypto_daily_pnl_summary.py`
- `crypto_drawdown_7d` -> `tools/crypto_drawdown_7d.py`
- `crypto_excluding_symbol_summary` -> `tools/crypto_excluding_symbol_summary.py`
- `crypto_portfolio_health` -> `tools/crypto_portfolio_health.py`
- `crypto_portfolio_summary` -> `tools/crypto_portfolio_summary.py`
- `crypto_stale_data_check` -> `tools/crypto_stale_data_check.py`
- `crypto_top_movers_24h` -> `tools/crypto_top_movers_24h.py`
- `electricity_cost_last_24h` -> `tools/electricity_cost_last_24h.py`
- `electricity_cost_today` -> `tools/electricity_cost_today.py`
- `latest_price` -> `tools/latest_price.py`
- `network_scan` -> `tools/network_scan.py`
- `pdata_all_fields` -> `tools/pdata_all_fields.py`
- `pdata_compare_energy` -> `tools/pdata_compare_energy.py`
- `pdata_energy_summary` -> `tools/pdata_energy_summary.py`
- `pdata_full_overview` -> `tools/pdata_full_overview.py`
- `pdata_gas_summary` -> `tools/pdata_gas_summary.py`
- `salt_tank_level` -> `tools/salt_tank_level.py`
- `sma` -> `tools/sma.py`
- `valid_test_tool` -> `tools/valid_test_tool.py`
- `water_softener_overview` -> `tools/water_softener_overview.py`
- `water_temperature_summary` -> `tools/water_temperature_summary.py`

## Intent map

### house_status
- Keywords: house status, overview, what is going on in the house, status summary
- Preferred routes: /house/diagnostics, /status, /health
- Preferred services: services.status_service, services.agent_house, services.agent_service
- Safety: safe_read

### power_current
- Keywords: power now, current power, house consumption, import export, grid power
- Preferred routes: /power, /status
- Preferred services: services.power_service, router_logic.gather_house_data
- Preferred tools: pdata_energy_summary, pdata_full_overview, sma
- Safety: safe_read

### sma_solar
- Keywords: solar, inverter, pv production, sma
- Preferred routes: /sma
- Preferred services: services.sma_service
- Preferred tools: sma
- Safety: safe_read

### water_status
- Keywords: water softener, salt level, water temperature
- Preferred routes: /water
- Preferred services: services.water_service
- Preferred tools: salt_tank_level, water_temperature_summary, water_softener_overview
- Safety: safe_read

### price_status
- Keywords: price now, electricity price, cheapest hours, cost today
- Preferred routes: /price
- Preferred services: services.price_service
- Preferred tools: latest_price, cheapest_hours_today, electricity_cost_today, electricity_cost_last_24h
- Safety: safe_read

### pdata_queries
- Keywords: pdata, gas summary, all fields, compare energy
- Preferred routes: /pdata
- Preferred services: services.pdata_service
- Preferred tools: pdata_all_fields, pdata_compare_energy, pdata_energy_summary, pdata_full_overview, pdata_gas_summary
- Safety: safe_read

### crypto_summary
- Keywords: portfolio, crypto status, pnl, top movers
- Preferred services: services.agent_crypto, services.agent_service
- Preferred tools: crypto_coin_summary, crypto_compare_7d, crypto_compare_now_vs_24h, crypto_concentration_risk, crypto_contributors_24h, crypto_daily_pnl_summary, crypto_drawdown_7d, crypto_excluding_symbol_summary, crypto_portfolio_health, crypto_portfolio_summary, crypto_stale_data_check, crypto_top_movers_24h
- Safety: safe_read

### audio_control
- Keywords: turn on speakers, audio route, party mode, playback on, music on
- Preferred routes: /tools/audio/node_power/<state>, /tools/audio/speaker_route/<state>, /tools/audio/party/<state>, /tools/audio/playback/<state>
- Preferred services: services.loxone_action_service, services.loxone_music_controls
- Safety: confirmation_or_policy

### voice_output
- Keywords: say this, announce, speak through speakers
- Preferred routes: /agent, /voice
- Preferred services: services.voice_service, services.announcement_service
- Safety: safe_write_limited

### network_scan
- Keywords: scan network, find hosts, nmap sweep
- Preferred services: services.experimental_tool_matcher, services.experimental_approval_service
- Preferred tools: network_scan
- Safety: approval_required

## Global safety rules

- LLM must prefer read-only routes by default.
- Write actions require allowlisting and often confirmation.
- Loxone/audio actions are high risk compared with pure sensor reads.
- Experimental and scanning tools require approval flow.
- Do not expose secrets or raw credentials to the model.