# Generated Service Map

Auto-generated from live service files.

## services/agent_crypto.py

### Functions
- `build_crypto_direct_response(intents, tool_data, is_crypto_question, is_power_question)`

### Calls seen
- `abs`
- `answer_parts.append`
- `best.get`
- `best_lines.append`
- `c.get`
- `d.get`
- `e.get`
- `gain_lines.append`
- `h.get`
- `item.get`
- `join`
- `largest.get`
- `lines.append`
- `lose_lines.append`
- `m.get`
- `others.get`
- `parts.append`
- `rstrip`
- `s.get`
- `tool_data.pop`
- `worst.get`
- `worst_lines.append`

## services/agent_house.py

### Functions
- `_loxone_make_response(intent_name, tool_key, tool_data, answer)`
- `_join_top(items, limit)`
- `build_loxone_direct_response(intents, tool_data)`
- `build_house_direct_response(question, intents, tool_data)`

### Imports
- `config.PRICE_INFLUX_BUCKET`
- `config.PRICE_INFLUX_FIELD`
- `config.PRICE_INFLUX_MEASUREMENT`
- `requests`
- `services.compare_service.parse_compare_periods_question`
- `services.pdata_service.get_pdata_all_fields_data`
- `services.pdata_service.get_pdata_compare_energy_data`
- `services.pdata_service.get_pdata_energy_summary_data`
- `services.pdata_service.get_pdata_full_overview_data`
- `services.pdata_service.get_pdata_gas_summary_data`
- `services.price_service.get_cheapest_hours_today`
- `services.price_service.get_electricity_cost_last_24h`
- `services.price_service.get_electricity_cost_today`
- `services.price_service.query_latest_price`
- `services.sma_service.get_sma_production_overview_data`
- `services.sma_service.get_sma_summary_data`
- `services.water_service.get_salt_tank_level`
- `services.water_service.get_water_temperature_summary`

### Calls seen
- `_join_top`
- `_loxone_make_response`
- `abs`
- `build_loxone_direct_response`
- `data.get`
- `fmt`
- `get`
- `get_cheapest_hours_today`
- `get_electricity_cost_last_24h`
- `get_electricity_cost_today`
- `get_pdata_all_fields_data`
- `get_pdata_compare_energy_data`
- `get_pdata_energy_summary_data`
- `get_pdata_full_overview_data`
- `get_pdata_gas_summary_data`
- `get_salt_tank_level`
- `get_sma_production_overview_data`
- `get_sma_summary_data`
- `get_water_temperature_summary`
- `item.get`
- `join`
- `json`
- `len`
- `max`
- `names.append`
- `parse_compare_periods_question`
- `pq.get`
- `query_latest_price`
- `requests.post`
- `s.get`
- `salt.get`
- `set`
- `sorted`
- `str`
- `temps.get`

## services/agent_service.py

### Functions
- `_has_production_tool(tool_name)`
- `_has_experimental_tool(tool_name)`
- `get_local_energy_summary_data()`
- `handle_agent_question(question)`

### Imports
- `config.PRICE_INFLUX_BUCKET`
- `config.PRICE_INFLUX_FIELD`
- `config.PRICE_INFLUX_MEASUREMENT`
- `extensions.crypto_tools`
- `extensions.experimental_tool_registry`
- `extensions.tool_registry`
- `ollama_client.ask_ollama`
- `re`
- `requests`
- `router_logic.gather_house_data`
- `services.agent_crypto.build_crypto_direct_response`
- `services.agent_house.build_house_direct_response`
- `services.compare_service.parse_compare_periods_question`
- `services.experimental_approval_service.execute_experimental_approval`
- `services.experimental_approval_service.parse_experimental_approval_question`
- `services.experimental_tool_matcher.find_best_experimental_tool_match`
- `services.influx_helpers.iso_now`
- `services.influx_helpers.query_latest_for_fields`
- `services.intent_detection.enrich_intents`
- `services.price_service.get_cheapest_hours_today`
- `services.price_service.get_electricity_cost_last_24h`
- `services.price_service.get_electricity_cost_today`
- `services.price_service.query_latest_price`
- `services.sma_service.get_sma_summary_data`
- `services.water_service.get_salt_tank_level`
- `services.water_service.get_water_temperature_summary`

### Calls seen
- `_has_production_tool`
- `any`
- `approval_request.get`
- `approval_result.get`
- `ask_ollama`
- `build_crypto_direct_response`
- `build_house_direct_response`
- `cidr_match.group`
- `crypto_tools.compare_portfolio_now_vs_24h`
- `crypto_tools.get_coin_summary`
- `crypto_tools.get_compare_7d`
- `crypto_tools.get_concentration_risk`
- `crypto_tools.get_contributors_24h`
- `crypto_tools.get_current_portfolio_summary`
- `crypto_tools.get_daily_pnl_summary`
- `crypto_tools.get_drawdown_7d`
- `crypto_tools.get_excluding_symbol_summary`
- `crypto_tools.get_portfolio_composition`
- `crypto_tools.get_portfolio_health`
- `crypto_tools.get_stale_data_check`
- `crypto_tools.get_top_movers_24h`
- `data.get`
- `enrich_intents`
- `execute_experimental_approval`
- `experimental_tool_registry.get`
- `find_best_experimental_tool_match`
- `gather_house_data`
- `get_sma_summary_data`
- `host.get`
- `intents.append`
- `ip_match.group`
- `iso_now`
- `join`
- `len`
- `list`
- `locals`
- `parse_experimental_approval_question`
- `payload.get`
- `preview.append`
- `query_latest_for_fields`
- `question.lower`
- `re.search`
- `result.get`
- `str`
- `sym.lower`
- `tool_data.keys`
- `tool_registry.execute`
- `tool_registry.get`

## services/ai_tool_generator.py

### Functions
- `_sanitize_tool_name(name)`
- `_default_stub_code(name, description)`
- `generate_proposed_tool_file(name, description, code)`

### Imports
- `re`
- `services.proposed_tool_service.add_proposed_tool`

### Calls seen
- `ValueError`
- `_default_stub_code`
- `_sanitize_tool_name`
- `add_proposed_tool`
- `lower`
- `re.sub`
- `replace`
- `strip`
- `value.replace`

## services/announce_service.py

### Functions
- `announce_text(text)`
  - Sends text to the local voice pipeline.
Tries several common payload formats/endpoints so it works in more setups.

### Imports
- `os`
- `requests`

### Calls seen
- `os.getenv`
- `requests.post`
- `rstrip`

## services/announcement_log_service.py

### Functions
- `log_announcement(level, text, player_id, volume)`

### Imports
- `datetime.datetime`
- `datetime.timezone`
- `json`
- `pathlib.Path`

### Calls seen
- `LOG_FILE.open`
- `LOG_FILE.parent.mkdir`
- `Path`
- `datetime.now`
- `f.write`
- `isoformat`
- `json.dumps`

## services/announcement_service.py

### Functions
- `_get_announcement_voice()`
- `_syn_config_for_level(level)`
- `_generate_chime(level, sr)`
- `_read_wav_mono_16(path)`
- `_write_wav_stereo_left_only(path, mono, sr)`
- `_synthesize_announcement_wav(text, level)`
- `_is_quiet_hours(now_hour)`
- `_resolve_announcement_volume(level, requested_volume, default_volume)`
- `announce_text(text, level, player_id, volume)`
- `announce_house_event(message, level, player_id, volume)`

### Imports
- `datetime.datetime`
- `math`
- `os`
- `pathlib.Path`
- `piper.PiperVoice`
- `piper.config.SynthesisConfig`
- `services.announcement_log_service.log_announcement`
- `services.voice_service.PUBLIC_BASE_URL`
- `services.voice_service.VOICE_DIR`
- `services.voice_service.play_url_on_player`
- `struct`
- `uuid`
- `wave`

### Calls seen
- `LEVELS.get`
- `PiperVoice.load`
- `RuntimeError`
- `SynthesisConfig`
- `_generate_chime`
- `_get_announcement_voice`
- `_is_quiet_hours`
- `_read_wav_mono_16`
- `_resolve_announcement_volume`
- `_syn_config_for_level`
- `_synthesize_announcement_wav`
- `_write_wav_stereo_left_only`
- `announce_text`
- `cfg.get`
- `combined.extend`
- `datetime.now`
- `float`
- `int`
- `interleaved.append`
- `join`
- `len`
- `list`
- `log_announcement`
- `lower`
- `math.sin`
- `max`
- `min`
- `os.getenv`
- `out.append`
- `out.extend`
- `play_url_on_player`
- `range`
- `silence`
- `speech_path.unlink`
- `str`
- `strip`
- `struct.pack`
- `struct.unpack`
- `text.strip`
- `tone`
- `uuid.uuid4`
- `voice.synthesize_wav`
- `wave.open`
- `wf.getframerate`
- `wf.getnchannels`
- `wf.getnframes`
- `wf.getsampwidth`
- `wf.readframes`
- `wf.setframerate`
- `wf.setnchannels`

## services/announcement_state_service.py

### Functions
- `_load_state()`
- `_save_state(state)`
- `should_announce(key, cooldown_seconds)`
- `clear_announce_key(key)`

### Imports
- `json`
- `pathlib.Path`
- `time`

### Calls seen
- `Path`
- `STATE_FILE.exists`
- `STATE_FILE.parent.mkdir`
- `STATE_FILE.read_text`
- `STATE_FILE.write_text`
- `_load_state`
- `_save_state`
- `json.dumps`
- `json.loads`
- `state.get`
- `time.time`

## services/apc_service.py

### Functions
- `_run_apc_question(question)`
- `get_apc_summary_data()`
- `get_apc_on_battery_status_data()`
- `get_apc_highest_load_data()`
- `get_apc_battery_health_data()`
- `get_apc_lowest_runtime_data()`

### Imports
- `apc_ai.APC_BUCKET_DEFAULT`
- `apc_ai.APC_MEASUREMENTS_DEFAULT`
- `apc_ai.handle_apc_question`
- `config.INFLUX_ORG`
- `extensions.query_api`

### Calls seen
- `_run_apc_question`
- `handle_apc_question`
- `result.get`

## services/buderus_service.py

### Functions
- `_env(name, default)`
- `_service()`
- `_wrap(intent, data, answer)`
- `get_buderus_current_status_data()`
- `get_buderus_heating_status_data()`
- `get_buderus_hot_water_status_data()`
- `get_buderus_pressure_analysis_data()`
- `get_buderus_diagnostics_data()`
- `get_buderus_boiler_health_summary_data()`

### Imports
- `buderus_module.BuderusService`
- `extensions.app`
- `os`

### Calls seen
- `BuderusService`
- `RuntimeError`
- `_env`
- `_service`
- `_wrap`
- `app.extensions.get`
- `os.getenv`
- `svc.boiler_health_summary`
- `svc.build_natural_answer`
- `svc.current_summary`
- `svc.dhw_summary`
- `svc.diagnostics_summary`
- `svc.heating_summary`
- `svc.pressure_analysis`

## services/compare_service.py

### Functions
- `period_stats_for_field(field, start_iso, stop_iso)`
- `compare_period_stats(a, b)`
- `parse_compare_periods_question(question)`

### Imports
- `datetime.datetime`
- `datetime.timezone`
- `re`
- `services.influx_helpers.iso_z`
- `services.influx_helpers.read_flux_values_for_field`

### Calls seen
- `abs`
- `datetime.strptime`
- `iso_z`
- `len`
- `lower`
- `match.group`
- `max`
- `metric_map.get`
- `min`
- `parse_local`
- `pattern.search`
- `question.strip`
- `re.compile`
- `read_flux_values_for_field`
- `replace`
- `strip`
- `sum`

## services/experimental_approval_service.py

### Functions
- `_extract_text_from_content(content)`
- `_find_last_assistant_message(messages)`
- `_looks_like_password_only_message(question)`
- `_extract_tool_name_from_assistant_text(text)`
- `_extract_args_from_assistant_text(text)`
- `parse_experimental_approval_question(question, messages)`
- `execute_experimental_approval(tool_name, args, admin_password)`

### Imports
- `os`
- `re`
- `requests`
- `typing.Any`
- `typing.Dict`
- `typing.Optional`

### Calls seen
- `_extract_args_from_assistant_text`
- `_extract_text_from_content`
- `_extract_tool_name_from_assistant_text`
- `_find_last_assistant_message`
- `_looks_like_password_only_message`
- `content.strip`
- `isinstance`
- `item.get`
- `join`
- `len`
- `m.group`
- `message_match.group`
- `msg.get`
- `msg_match.group`
- `parts.append`
- `password_match.group`
- `payload.get`
- `q.lower`
- `q.strip`
- `q_lower.startswith`
- `r.json`
- `re.match`
- `re.search`
- `requests.post`
- `reversed`
- `str`
- `strip`
- `tool_match.group`

## services/experimental_security.py

### Functions
- `utc_now_iso()`
- `write_experimental_audit(event, tool_name, args, source, status, details)`
- `_load_cooldowns()`
- `_save_cooldowns(data)`
- `check_experimental_cooldown(tool_name, cooldown_seconds)`
- `mark_experimental_cooldown(tool_name)`
- `write_package_install_audit(package_name, status, details, source)`

### Imports
- `datetime.datetime`
- `datetime.timezone`
- `json`
- `os`
- `time`

### Calls seen
- `_load_cooldowns`
- `_save_cooldowns`
- `datetime.now`
- `f.write`
- `float`
- `int`
- `isoformat`
- `json.dump`
- `json.dumps`
- `json.load`
- `max`
- `open`
- `os.makedirs`
- `os.path.dirname`
- `os.path.exists`
- `replace`
- `round`
- `state.get`
- `time.time`
- `utc_now_iso`
- `write_experimental_audit`

## services/experimental_tool_matcher.py

### Functions
- `_tokenize(text)`
- `find_best_experimental_tool_match(question, experimental_tool_registry)`

### Imports
- `re`
- `typing.Any`

### Calls seen
- `_tokenize`
- `experimental_tool_registry.list_tool_specs`
- `len`
- `list`
- `module_name.replace`
- `name.replace`
- `re.findall`
- `set`
- `sorted`
- `spec.get`
- `text.lower`

## services/influx_helpers.py

### Functions
- `iso_now()`
- `iso_z(dt)`
- `build_field_filter(fields)`
- `query_latest_for_fields(fields, range_window)`
- `read_flux_values_for_field(field, start_iso, stop_iso)`

### Imports
- `config.INFLUX_BUCKET`
- `config.INFLUX_MEASUREMENT`
- `datetime.datetime`
- `datetime.timezone`
- `extensions.query_api`

### Calls seen
- `build_field_filter`
- `datetime.now`
- `dt.astimezone`
- `float`
- `isinstance`
- `isoformat`
- `join`
- `query_api.query`
- `record.get_field`
- `record.get_measurement`
- `record.get_time`
- `record.get_value`
- `record.values.items`
- `replace`
- `str`
- `time_.isoformat`
- `values.append`

## services/intent_detection.py

### Functions
- `detect_symbol(question)`
- `enrich_intents(question, intents, tool_data)`

### Imports
- `re`

### Calls seen
- `any`
- `detect_symbol`
- `intents.append`
- `question.lower`
- `re.findall`
- `symbol.upper`
- `tool_data.pop`

## services/loxone_action_service.py

### Functions
- `_auth()`
- `trigger_pushbutton(uuid)`
- `set_switch(uuid, value)`
- `execute_control(control, desired_state)`
- `audio_node_power(room, state)`
- `audio_speaker_route(target, state)`
- `audio_party(state)`
- `audio_playback(room, state)`

### Imports
- `config.LOXONE_HOST`
- `config.LOXONE_PASSWORD`
- `config.LOXONE_USER`
- `requests`
- `requests.auth.HTTPBasicAuth`
- `services.loxone_service.find_control_by_name`
- `services.loxone_service.get_audio_action_map`
- `services.loxone_service.get_audio_tool_targets`

### Calls seen
- `HTTPBasicAuth`
- `ValueError`
- `_auth`
- `action_map.get`
- `control.get`
- `ctrl.get`
- `execute_control`
- `find_control_by_name`
- `get`
- `get_audio_action_map`
- `get_audio_tool_targets`
- `lower`
- `node_power.get`
- `paired.get`
- `r.raise_for_status`
- `r.text.strip`
- `requests.get`
- `resolved.get`
- `room.lower`
- `room_data.get`
- `set_switch`
- `str`
- `target.lower`
- `targets.items`
- `trigger_pushbutton`

## services/loxone_music_controls.py

### Functions
- `build_plaintext_payload()`
- `set_music_state(command_key, value)`
- `ai_music_controls_feed()`
- `music_living_on()`
- `music_living_off()`
- `music_toilet_on()`
- `music_toilet_off()`
- `music_party_on()`
- `music_party_off()`
- `music_reset()`
- `music_status()`

### Imports
- `flask.Blueprint`
- `flask.jsonify`

### Calls seen
- `Blueprint`
- `MUSIC_STATE.copy`
- `MUSIC_STATE.items`
- `MUSIC_STATE.keys`
- `build_plaintext_payload`
- `int`
- `join`
- `jsonify`
- `list`
- `music_controls_bp.route`
- `set_music_state`

## services/loxone_routes.py

### Functions
- `loxone_structure_summary()`
- `loxone_controls()`
- `loxone_controls_by_room()`
- `loxone_controls_by_category()`

### Imports
- `flask.Blueprint`
- `flask.jsonify`
- `flask.request`
- `services.loxone_service.get_all_controls`
- `services.loxone_service.get_controls_by_category`
- `services.loxone_service.get_controls_by_room`
- `services.loxone_service.get_loxone_structure_summary`

### Calls seen
- `Blueprint`
- `get_all_controls`
- `get_controls_by_category`
- `get_controls_by_room`
- `get_loxone_structure_summary`
- `jsonify`
- `loxone_bp.route`
- `request.args.get`
- `strip`

## services/loxone_service.py

### Functions
- `_auth()`
- `get_audio_tool_targets()`
- `find_control_by_name(room_name, control_name)`
- `get_lighting_controls_by_room(room_name)`
- `get_audio_action_map(room_name)`
- `get_audio_behavior_map(room_name)`
- `get_best_audio_control_candidates(room_name)`
- `resolve_room_name(room_name)`
- `get_audio_controls_by_room(room_name)`
- `fetch_loxapp3()`
- `fetch_loxone_state_value(uuid)`
- `extract_loxone_value(raw_text)`
- `get_loxone_structure_summary()`
- `get_all_controls()`
- `get_controls_by_room(room_name)`
- `get_controls_by_category(category_name)`
- `get_temperature_controls_by_room(room_name)`
- `get_control_state_uuid(control, preferred_keys)`
- `get_room_temperature(room_name)`
- `get_room_summary(room_name)`

### Imports
- `config.LOXONE_HOST`
- `config.LOXONE_PASSWORD`
- `config.LOXONE_USER`
- `re`
- `requests`
- `requests.auth.HTTPBasicAuth`

### Calls seen
- `HTTPBasicAuth`
- `_auth`
- `append`
- `bucket.sort`
- `c.get`
- `candidate.get`
- `cats.get`
- `cats.values`
- `control.get`
- `controller_candidates.append`
- `controls.items`
- `controls_result.get`
- `ctrl.get`
- `data.get`
- `direct_candidates.append`
- `extract_loxone_value`
- `fallback_candidates.append`
- `fetch_loxapp3`
- `fetch_loxone_state_value`
- `float`
- `get`
- `get_all_controls`
- `get_audio_controls_by_room`
- `get_control_state_uuid`
- `get_controls_by_room`
- `get_temperature_controls_by_room`
- `isinstance`
- `item.get`
- `items.append`
- `len`
- `ll.get`
- `lower`
- `m.group`
- `name.lower`
- `name_l.endswith`
- `name_l.startswith`
- `other.append`
- `playback_off.append`
- `playback_on.append`
- `power_off.append`
- `power_on.append`
- `r.get`
- `r.json`
- `r.raise_for_status`
- `raw.lower`
- `re.search`
- `replace`
- `requests.get`
- `resolve_room_name`
- `response.json`

## services/monitor_ups_voice.py

### Functions
- `load_state()`
- `save_state(state)`
- `query_ups_on_battery()`
- `announce(text, level, key, cooldown_seconds)`
- `main()`

### Imports
- `json`
- `pathlib.Path`
- `requests`
- `services.announcement_state_service.clear_announce_key`
- `sys`
- `time`

### Calls seen
- `Path`
- `STATE_FILE.exists`
- `STATE_FILE.parent.mkdir`
- `STATE_FILE.read_text`
- `STATE_FILE.write_text`
- `announce`
- `clear_announce_key`
- `data.get`
- `device.get`
- `join`
- `json.dumps`
- `json.loads`
- `load_state`
- `lower`
- `main`
- `print`
- `query_ups_on_battery`
- `requests.post`
- `response.json`
- `response.raise_for_status`
- `save_state`
- `state.get`
- `status_flags.get`
- `str`
- `sys.path.insert`
- `time.sleep`
- `tool_data.get`
- `ups.get`

## services/package_batch_install_service.py

### Functions
- `install_missing_packages_batch(missing_packages, admin_password)`

### Imports
- `services.package_install_executor.install_python_package`
- `typing.Any`

### Calls seen
- `install_python_package`
- `item.get`
- `result.get`
- `results.append`
- `seen.add`
- `set`
- `strip`

## services/package_install_executor.py

### Functions
- `_check_admin_password(admin_password)`
- `install_python_package(package_name, admin_password)`

### Imports
- `hashlib`
- `os`
- `subprocess`
- `sys`
- `typing.Any`

### Calls seen
- `_check_admin_password`
- `encode`
- `hashlib.sha256`
- `hexdigest`
- `join`
- `os.getenv`
- `strip`
- `subprocess.run`

## services/package_install_service.py

### Functions
- `build_install_plan(dependency_analysis)`

### Imports
- `typing.Any`

### Calls seen
- `dependency_analysis.get`
- `item.get`
- `len`
- `packages.append`

## services/pdata_service.py

### Functions
- `get_pdata_energy_summary_data()`
- `get_pdata_compare_energy_data()`
- `get_pdata_all_fields_data()`
- `get_pdata_full_overview_data()`
- `get_pdata_gas_summary_data()`

### Imports
- `extensions.pdata_tools`
- `services.power_service.get_energy_summary_data`

### Calls seen
- `get_energy_summary_data`
- `pdata_tools.compare_with_local_meter`
- `pdata_tools.decode_all_fields`
- `pdata_tools.get_energy_summary`
- `pdata_tools.get_full_overview`
- `pdata_tools.get_gas_summary`

## services/power_service.py

### Functions
- `get_power_now_data()`
- `get_energy_summary_data()`
- `get_phase_overview_data()`
- `get_energy_today_data()`

### Imports
- `config.INFLUX_BUCKET`
- `extensions.query_api`
- `services.influx_helpers.iso_now`
- `services.influx_helpers.query_latest_for_fields`

### Calls seen
- `data.get`
- `float`
- `iso_now`
- `latest.get`
- `query_api.query`
- `query_latest_for_fields`
- `record.get_field`
- `record.get_value`
- `start_values.get`

## services/price_service.py

### Functions
- `query_latest_price(range_window)`
- `read_price_series(start_iso, stop_iso, window)`
- `read_import_counter_series(start_iso, stop_iso, window)`
- `calculate_cost_from_counters(start_iso, stop_iso, window)`
- `get_electricity_cost_today()`
- `get_electricity_cost_last_24h()`
- `get_cheapest_hours_today(limit)`

### Imports
- `config.INFLUX_BUCKET`
- `config.INFLUX_MEASUREMENT`
- `config.PRICE_INFLUX_BUCKET`
- `config.PRICE_INFLUX_FIELD`
- `config.PRICE_INFLUX_MEASUREMENT`
- `config.PRICE_WINDOW`
- `datetime.datetime`
- `datetime.timedelta`
- `datetime.timezone`
- `extensions.query_api`
- `services.influx_helpers.iso_z`

### Calls seen
- `breakdown.append`
- `calculate_cost_from_counters`
- `datetime.now`
- `float`
- `isinstance`
- `iso_z`
- `isoformat`
- `len`
- `now.replace`
- `query_api.query`
- `read_import_counter_series`
- `read_price_series`
- `record.get_field`
- `record.get_measurement`
- `record.get_time`
- `record.get_value`
- `round`
- `rows.append`
- `sorted`
- `str`
- `time_.isoformat`
- `timedelta`

## services/proposal_promotion_service.py

### Functions
- `_safe_filename(filename)`
- `promote_proposed_tool_to_experimental(proposal_id)`

### Imports
- `importlib`
- `os`
- `re`
- `services.proposed_tool_service.mark_proposed_tool_promoted`
- `services.proposed_tool_service.read_proposed_tool`

### Calls seen
- `RuntimeError`
- `ValueError`
- `_safe_filename`
- `code.strip`
- `f.write`
- `filename.endswith`
- `importlib.import_module`
- `importlib.invalidate_caches`
- `mark_proposed_tool_promoted`
- `open`
- `os.makedirs`
- `os.path.exists`
- `os.path.join`
- `proposal.get`
- `re.fullmatch`
- `read_proposed_tool`
- `strip`

## services/proposed_dependency_service.py

### Functions
- `_stdlib_modules()`
- `_extract_imports_from_code(code)`
- `_local_project_modules()`
- `_is_installed_module(module_name)`
- `analyze_python_dependencies(code)`

### Imports
- `ast`
- `importlib.util`
- `os`
- `typing.Any`

### Calls seen
- `PACKAGE_NAME_MAP.get`
- `__import__`
- `_extract_imports_from_code`
- `_is_installed_module`
- `_local_project_modules`
- `_stdlib_modules`
- `alias.name.split`
- `ast.parse`
- `ast.walk`
- `entry.endswith`
- `getattr`
- `importlib.util.find_spec`
- `imports.add`
- `installed_packages.append`
- `isinstance`
- `len`
- `local_imports.append`
- `missing_packages.append`
- `names.add`
- `node.module.split`
- `os.listdir`
- `os.path.isdir`
- `os.path.join`
- `set`
- `sorted`
- `stdlib_imports.append`
- `third_party_imports.append`

## services/proposed_promotion_audit_service.py

### Functions
- `_utc_now_iso()`
- `_ensure_parent_dir()`
- `_load_all()`
- `_save_all(items)`
- `list_promotion_audit()`
- `add_promotion_audit_record(proposal_id, target, proposal_status, target_path, allow_overwrite, validation, preflight, dependency_analysis, actor)`

### Imports
- `datetime.datetime`
- `datetime.timezone`
- `json`
- `os`
- `typing.Any`

### Calls seen
- `_ensure_parent_dir`
- `_load_all`
- `_save_all`
- `_utc_now_iso`
- `datetime.now`
- `int`
- `isinstance`
- `isoformat`
- `items.append`
- `json.dump`
- `json.load`
- `open`
- `os.makedirs`
- `os.path.dirname`
- `os.path.exists`
- `timestamp`

## services/proposed_promotion_guard_service.py

### Functions
- `_safe_target_path(base_dir, filename)`
- `_compile_code_in_tempfile(code)`
- `_tool_name_collision(tool_name, target)`
- `preflight_promotion_check(proposal, target, allow_overwrite)`

### Imports
- `extensions.experimental_tool_registry`
- `extensions.tool_registry`
- `os`
- `py_compile`
- `services.proposed_tool_validation_service.validate_proposal_record`
- `tempfile`
- `typing.Any`

### Calls seen
- `_compile_code_in_tempfile`
- `_safe_target_path`
- `_tool_name_collision`
- `checks.append`
- `experimental_tool_registry.get`
- `f.write`
- `filename.endswith`
- `full_path.startswith`
- `get`
- `locals`
- `os.path.abspath`
- `os.path.basename`
- `os.path.exists`
- `os.path.join`
- `os.unlink`
- `proposal.get`
- `py_compile.compile`
- `strip`
- `tempfile.NamedTemporaryFile`
- `tool_registry.get`
- `validate_proposal_record`
- `validation.get`

## services/proposed_tool_service.py

### Functions
- `_utc_now_iso()`
- `_ensure_parent_dir()`
- `_load_all()`
- `_save_all(items)`
- `list_proposed_tools()`
- `get_proposed_tool(proposal_id)`
- `read_proposed_tool(proposal_id)`
- `save_proposed_tool(proposal)`
- `find_existing_pending_by_name(name)`
- `add_proposed_tool(name, description, filename, code, requested_by, notes)`
- `approve_proposed_tool(proposal_id, approved_by)`
- `mark_proposed_tool_installed(proposal_id, status, promoted_by, target)`
- `reject_proposed_tool(proposal_id, rejected_by)`
- `update_proposed_tool(proposal_id)`

### Imports
- `datetime.datetime`
- `datetime.timezone`
- `json`
- `os`

### Calls seen
- `FileNotFoundError`
- `ValueError`
- `_ensure_parent_dir`
- `_load_all`
- `_save_all`
- `_utc_now_iso`
- `code.strip`
- `datetime.now`
- `enumerate`
- `find_existing_pending_by_name`
- `get_proposed_tool`
- `int`
- `isinstance`
- `isoformat`
- `item.get`
- `items.append`
- `json.dump`
- `json.load`
- `lower`
- `open`
- `os.makedirs`
- `os.path.dirname`
- `os.path.exists`
- `proposal.get`
- `proposal.update`
- `save_proposed_tool`
- `str`
- `strip`
- `timestamp`

## services/proposed_tool_validation_service.py

### Functions
- `validate_proposed_tool_code(code)`
- `validate_proposal_record(proposal)`

### Imports
- `ast`
- `os`
- `tempfile`
- `traceback`
- `typing.Any`

### Calls seen
- `ast.parse`
- `callable`
- `checks.append`
- `code.strip`
- `exec`
- `isinstance`
- `namespace.get`
- `proposal.get`
- `tool_spec.get`
- `traceback.format_exc`
- `validate_proposed_tool_code`

## services/sma_service.py

### Functions
- `get_sma_summary_data()`
- `get_sma_production_overview_data()`

### Imports
- `extensions.sma_tools`

### Calls seen
- `sma_tools.get_production_overview`
- `sma_tools.get_summary`

## services/status_service.py

### Functions
- `utc_now()`
- `ping_check(host)`
- `tcp_check(host, port, timeout)`
- `check_device(name, host, port)`
- `http_check(name, url, severity_if_fail)`
- `ollama_check()`
- `influx_check()`
- `build_speech_summary(checks)`
- `build_status_report()`

### Imports
- `datetime.datetime`
- `datetime.timezone`
- `os`
- `requests`
- `socket`
- `subprocess`
- `time`

### Calls seen
- `build_speech_summary`
- `check_device`
- `checks.items`
- `checks.values`
- `core_fail.append`
- `data.get`
- `datetime.now`
- `http_check`
- `influx_check`
- `isoformat`
- `join`
- `len`
- `name.replace`
- `offline.append`
- `ollama_check`
- `os.getenv`
- `parts.append`
- `ping_check`
- `requests.get`
- `resp.json`
- `resp.raise_for_status`
- `round`
- `socket.create_connection`
- `subprocess.run`
- `sum`
- `tcp_check`
- `time.time`
- `utc_now`
- `warnings.append`

## services/stt_service.py

### Functions
- `get_model()`
- `convert_to_mono_16k(src, dst)`
- `transcribe_wav(path, language)`

### Imports
- `faster_whisper.WhisperModel`
- `pathlib.Path`
- `subprocess`

### Calls seen
- `Path`
- `WhisperModel`
- `convert_to_mono_16k`
- `get_model`
- `getattr`
- `join`
- `model.transcribe`
- `seg.text.strip`
- `str`
- `strip`
- `subprocess.run`
- `text_parts.append`

## services/tool_promoter.py

### Functions
- `_ensure_dirs()`
- `promote_proposed_to_experimental(proposal_id)`
- `promote_experimental_to_production(proposal_id)`

### Imports
- `os`
- `services.proposed_tool_service.mark_proposed_tool_installed`
- `services.proposed_tool_service.read_proposed_tool`
- `shutil`

### Calls seen
- `FileNotFoundError`
- `ValueError`
- `_ensure_dirs`
- `f.write`
- `mark_proposed_tool_installed`
- `open`
- `os.makedirs`
- `os.path.exists`
- `os.path.join`
- `os.path.splitext`
- `proposal.get`
- `read_proposed_tool`
- `shutil.copy2`

## services/tool_registry.py

### Functions
- `load_tools_from_package(package_name)`

### Classes
- `Tool`
- `ToolRegistry`
  - Methods: __init__, register, get, list_tools, list_tool_specs, execute

### Imports
- `dataclasses.dataclass`
- `importlib`
- `pkgutil`
- `typing.Any`
- `typing.Callable`

### Calls seen
- `KeyError`
- `Tool`
- `ToolRegistry`
- `ValueError`
- `getattr`
- `importlib.import_module`
- `list`
- `module_info.name.startswith`
- `pkgutil.iter_modules`
- `registry.register`
- `self._tools.get`
- `self._tools.values`
- `self.get`
- `tool.handler`

## services/voice_service.py

### Functions
- `chunk_text(text, max_chars)`
- `stop_player(player_id)`
- `mute_player(player_id)`
- `speech_round_units(text)`
- `normalize_wav_ffmpeg(src_path, dst_path)`
- `expand_tts_abbreviations(text)`
- `speech_cleanup_text(text)`
- `concat_wav_files(wav_paths, output_path)`
- `sanitize_text(text)`
- `resolve_player_id(player_id)`
- `normalize_wav_ffmpeg(src_path, dst_path)`
- `ensure_standard_wav(wav_path)`
- `resolve_volume(volume)`
- `_build_syn_config()`
- `_get_voice()`
- `synthesize_wav(text)`
- `lms_request(player_id, command_parts)`
- `get_players()`
- `mute_player(player_id)`
- `set_player_volume(player_id, volume)`
- `play_url_on_player(player_id, url, volume)`
- `say_text(text, player_id, volume)`
- `announce_text(text, player_id, volume, prefix)`

### Imports
- `os`
- `pathlib.Path`
- `piper.PiperVoice`
- `piper.config.SynthesisConfig`
- `re`
- `requests`
- `subprocess`
- `time`
- `uuid`
- `wave`

### Calls seen
- `FileNotFoundError`
- `PLAYER_ALIASES.get`
- `Path`
- `PiperVoice.load`
- `RuntimeError`
- `SynthesisConfig`
- `VOICE_DIR.mkdir`
- `ValueError`
- `_build_syn_config`
- `_get_voice`
- `chunk_text`
- `chunks.append`
- `concat_wav_files`
- `data.get`
- `ensure_standard_wav`
- `enumerate`
- `expand_tts_abbreviations`
- `filepath.exists`
- `first.getcompname`
- `first.getcomptype`
- `first.getframerate`
- `first.getnchannels`
- `first.getsampwidth`
- `float`
- `get`
- `int`
- `join`
- `len`
- `lms_request`
- `lower`
- `m.group`
- `model_path.exists`
- `normalize_wav_ffmpeg`
- `normalized_paths.append`
- `os.getenv`
- `out.setcomptype`
- `out.setframerate`
- `out.setnchannels`
- `out.setsampwidth`
- `out.writeframes`
- `part_files.append`
- `play_url_on_player`
- `re.split`
- `re.sub`
- `requests.post`
- `resolve_player_id`
- `resolve_volume`
- `response.json`
- `response.raise_for_status`
- `responses.append`

## services/water_service.py

### Functions
- `query_latest_salt_distance(range_window)`
- `salt_level_percent_from_distance(distance_cm)`
- `salt_level_status_from_percent(percent)`
- `get_salt_tank_level()`
- `query_latest_water_temps(range_window)`
- `water_temp_status(temp_c)`
- `get_water_temperature_summary()`
- `get_water_softener_overview()`

### Imports
- `config.SALT_EMPTY_CM`
- `config.SALT_FULL_CM`
- `config.SALT_INFLUX_BUCKET`
- `config.SALT_INFLUX_FIELD`
- `config.SALT_INFLUX_MEASUREMENT`
- `config.WATER_TEMP1_DIVISOR`
- `config.WATER_TEMP1_FIELD`
- `config.WATER_TEMP2_FIELD`
- `config.WATER_TEMP_BUCKET`
- `config.WATER_TEMP_MEASUREMENT`
- `datetime.datetime`
- `extensions.query_api`

### Calls seen
- `ValueError`
- `data.get`
- `float`
- `get_salt_tank_level`
- `get_water_temperature_summary`
- `isinstance`
- `max`
- `min`
- `query_api.query`
- `query_latest_salt_distance`
- `query_latest_water_temps`
- `record.get_field`
- `record.get_measurement`
- `record.get_time`
- `record.get_value`
- `round`
- `salt.get`
- `salt_level_percent_from_distance`
- `salt_level_status_from_percent`
- `str`
- `temps.get`
- `time_.isoformat`
- `water_temp_status`
- `x.get`
