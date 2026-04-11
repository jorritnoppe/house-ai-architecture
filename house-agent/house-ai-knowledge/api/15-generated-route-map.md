# Generated Route Map

Auto-generated from live route files.

## routes/agent_routes.py

- No Flask route decorators detected automatically.

#### Imports
- `apc_ai.handle_apc_question`
- `config.INFLUX_ORG`
- `extensions.app`
- `extensions.query_api`
- `flask.Blueprint`
- `flask.jsonify`
- `flask.request`
- `os`
- `requests`
- `services.agent_service.handle_agent_question`
- `services.announcement_service.announce_text`
- `services.voice_service.say_text`

#### Calls seen
- `Blueprint`
- `ValueError`
- `_speak_via_audio-node-1`
- `agent_bp.post`
- `announce_text`
- `app.logger.exception`
- `bool`
- `handle_agent_question`
- `handle_apc_question`
- `jsonify`
- `os.getenv`
- `payload.get`
- `request.get_json`
- `requests.post`
- `response.json`
- `response.raise_for_status`
- `result.get`
- `rstrip`
- `say_text`
- `str`
- `strip`

## routes/audio_tool_routes.py

### POST /tools/audio/node_power/<state>
- Handler: `tools_audio_node_power`
- Blueprint: `audio_tools_bp`
- Line: 14

### POST /tools/audio/party/<state>
- Handler: `tools_audio_party`
- Blueprint: `audio_tools_bp`
- Line: 39

### POST /tools/audio/playback/<state>
- Handler: `tools_audio_playback`
- Blueprint: `audio_tools_bp`
- Line: 48

### POST /tools/audio/speaker_route/<state>
- Handler: `tools_audio_speaker_route`
- Blueprint: `audio_tools_bp`
- Line: 26

#### Imports
- `flask.Blueprint`
- `flask.jsonify`
- `flask.request`
- `services.loxone_action_service.audio_node_power`
- `services.loxone_action_service.audio_party`
- `services.loxone_action_service.audio_playback`
- `services.loxone_action_service.audio_speaker_route`

#### Calls seen
- `Blueprint`
- `audio_node_power`
- `audio_party`
- `audio_playback`
- `audio_speaker_route`
- `audio_tools_bp.route`
- `jsonify`
- `request.args.get`
- `result.get`
- `strip`

## routes/health_routes.py

- No Flask route decorators detected automatically.

#### Imports
- `config.INFLUX_BUCKET`
- `extensions.app`
- `extensions.query_api`
- `flask.Blueprint`
- `flask.jsonify`
- `services.influx_helpers.iso_now`

#### Calls seen
- `Blueprint`
- `app.logger.exception`
- `health_bp.get`
- `iso_now`
- `jsonify`
- `query_api.query`

## routes/house_routes.py

- No Flask route decorators detected automatically.

#### Imports
- `flask.Blueprint`
- `flask.jsonify`
- `flask.request`
- `json`
- `os`
- `pathlib.Path`
- `requests`
- `threading`

#### Calls seen
- `Blueprint`
- `CONVERSATION_STORE_FILE.exists`
- `CONVERSATION_STORE_FILE.parent.mkdir`
- `CONVERSATION_STORE_FILE.with_suffix`
- `Path`
- `SPEAKER_DEFAULTS.items`
- `ValueError`
- `_build_speaker_payload`
- `_audio-node-1_request`
- `_load_conversation_store`
- `_local_request`
- `_save_conversation_store`
- `_speaker_or_404`
- `bool`
- `cleaned_targets.append`
- `data.get`
- `float`
- `get_json`
- `get_last_speaker`
- `house_bp.get`
- `house_bp.post`
- `house_diagnostics`
- `info.get`
- `isinstance`
- `items`
- `join`
- `json.dump`
- `json.dumps`
- `json.load`
- `jsonify`
- `lines.append`
- `lower`
- `method.upper`
- `open`
- `os.getenv`
- `payload.get`
- `remember_last_speaker`
- `request.get_json`
- `requests.get`
- `requests.post`
- `resp.json`
- `resp.raise_for_status`
- `results.append`
- `rstrip`
- `str`
- `strip`
- `threading.Lock`
- `tmp_file.replace`

## routes/loxone_routes.py

### GET /ai/audio_resolve_control
- Handler: `audio_resolve_control`
- Blueprint: `loxone_bp`
- Line: 29

### GET /ai/audio_tool_targets
- Handler: `audio_tool_targets`
- Blueprint: `loxone_bp`
- Line: 24

### GET /ai/loxone_audio_action_map
- Handler: `loxone_audio_action_map`
- Blueprint: `loxone_bp`
- Line: 57

### GET /ai/loxone_audio_behavior_map
- Handler: `loxone_audio_behavior_map`
- Blueprint: `loxone_bp`
- Line: 45

### GET /ai/loxone_audio_control_candidates
- Handler: `loxone_audio_control_candidates`
- Blueprint: `loxone_bp`
- Line: 81

### GET /ai/loxone_audio_controls_by_room
- Handler: `loxone_audio_controls_by_room`
- Blueprint: `loxone_bp`
- Line: 93

### GET /ai/loxone_controls_by_category
- Handler: `loxone_controls_by_category`
- Blueprint: `loxone_bp`
- Line: 135

### GET /ai/loxone_controls_by_room
- Handler: `loxone_controls_by_room`
- Blueprint: `loxone_bp`
- Line: 124

### GET /ai/loxone_lighting_controls_by_room
- Handler: `loxone_lighting_controls_by_room`
- Blueprint: `loxone_bp`
- Line: 70

### GET /ai/loxone_room_summary
- Handler: `loxone_room_summary`
- Blueprint: `loxone_bp`
- Line: 105

### GET /ai/loxone_room_temperature
- Handler: `loxone_room_temperature`
- Blueprint: `loxone_bp`
- Line: 146

### GET /ai/loxone_structure_summary
- Handler: `loxone_structure_summary`
- Blueprint: `loxone_bp`
- Line: 119

#### Imports
- `flask.Blueprint`
- `flask.jsonify`
- `flask.request`
- `services.loxone_service.find_control_by_name`
- `services.loxone_service.get_audio_action_map`
- `services.loxone_service.get_audio_behavior_map`
- `services.loxone_service.get_audio_controls_by_room`
- `services.loxone_service.get_audio_tool_targets`
- `services.loxone_service.get_best_audio_control_candidates`
- `services.loxone_service.get_controls_by_category`
- `services.loxone_service.get_controls_by_room`
- `services.loxone_service.get_lighting_controls_by_room`
- `services.loxone_service.get_loxone_structure_summary`
- `services.loxone_service.get_room_summary`
- `services.loxone_service.get_room_temperature`

#### Calls seen
- `Blueprint`
- `find_control_by_name`
- `get_audio_action_map`
- `get_audio_behavior_map`
- `get_audio_controls_by_room`
- `get_audio_tool_targets`
- `get_best_audio_control_candidates`
- `get_controls_by_category`
- `get_controls_by_room`
- `get_lighting_controls_by_room`
- `get_loxone_structure_summary`
- `get_room_summary`
- `get_room_temperature`
- `jsonify`
- `loxone_bp.route`
- `request.args.get`
- `strip`

## routes/openai_routes.py

### POST /v1/chat/completions
- Handler: `openai_chat_completions`
- Blueprint: `openai_bp`
- Line: 28

### GET /v1/models
- Handler: `openai_models`
- Blueprint: `openai_bp`
- Line: 13

#### Imports
- `flask.Blueprint`
- `flask.jsonify`
- `flask.request`
- `services.agent_service.handle_agent_question`
- `services.experimental_approval_service.execute_experimental_approval`
- `services.experimental_approval_service.parse_experimental_approval_question`

#### Calls seen
- `Blueprint`
- `approval.get`
- `body.get`
- `execute_experimental_approval`
- `execution.get`
- `handle_agent_question`
- `jsonify`
- `msg.get`
- `openai_bp.route`
- `parse_experimental_approval_question`
- `payload.get`
- `request.get_json`
- `result.get`
- `reversed`
- `str`
- `strip`

## routes/pdata_routes.py

- No Flask route decorators detected automatically.

#### Imports
- `flask.Blueprint`
- `flask.jsonify`
- `services.influx_helpers.iso_now`
- `services.pdata_service.get_pdata_all_fields_data`
- `services.pdata_service.get_pdata_compare_energy_data`
- `services.pdata_service.get_pdata_energy_summary_data`
- `services.pdata_service.get_pdata_full_overview_data`
- `services.pdata_service.get_pdata_gas_summary_data`

#### Calls seen
- `Blueprint`
- `get_pdata_all_fields_data`
- `get_pdata_compare_energy_data`
- `get_pdata_energy_summary_data`
- `get_pdata_full_overview_data`
- `get_pdata_gas_summary_data`
- `iso_now`
- `jsonify`
- `pdata_bp.get`

## routes/power_routes.py

- No Flask route decorators detected automatically.

#### Imports
- `flask.Blueprint`
- `flask.jsonify`
- `services.power_service.get_energy_summary_data`
- `services.power_service.get_energy_today_data`
- `services.power_service.get_phase_overview_data`
- `services.power_service.get_power_now_data`

#### Calls seen
- `Blueprint`
- `get_energy_summary_data`
- `get_energy_today_data`
- `get_phase_overview_data`
- `get_power_now_data`
- `jsonify`
- `power_bp.get`

## routes/price_routes.py

- No Flask route decorators detected automatically.

#### Imports
- `config.PRICE_INFLUX_BUCKET`
- `config.PRICE_INFLUX_FIELD`
- `config.PRICE_INFLUX_MEASUREMENT`
- `flask.Blueprint`
- `flask.jsonify`
- `services.influx_helpers.iso_now`
- `services.price_service.get_cheapest_hours_today`
- `services.price_service.get_electricity_cost_last_24h`
- `services.price_service.get_electricity_cost_today`
- `services.price_service.query_latest_price`

#### Calls seen
- `Blueprint`
- `get_cheapest_hours_today`
- `get_electricity_cost_last_24h`
- `get_electricity_cost_today`
- `iso_now`
- `jsonify`
- `price_bp.get`
- `query_latest_price`

## routes/sma_routes.py

- No Flask route decorators detected automatically.

#### Imports
- `flask.Blueprint`
- `flask.jsonify`
- `services.sma_service.get_sma_production_overview_data`
- `services.sma_service.get_sma_summary_data`

#### Calls seen
- `Blueprint`
- `get_sma_production_overview_data`
- `get_sma_summary_data`
- `jsonify`
- `sma_bp.get`

## routes/status.py

- No Flask route decorators detected automatically.

#### Imports
- `flask.Blueprint`
- `flask.jsonify`
- `services.announce_service.announce_text`
- `services.status_service.build_status_report`

#### Calls seen
- `Blueprint`
- `announce_result.get`
- `announce_text`
- `build_status_report`
- `jsonify`
- `status_bp.get`
- `status_bp.post`

## routes/tool_routes.py

- No Flask route decorators detected automatically.

#### Imports
- `extensions.experimental_tool_registry`
- `extensions.tool_registry`
- `flask.Blueprint`
- `flask.jsonify`
- `flask.request`
- `hashlib`
- `os`
- `services.ai_tool_generator.generate_proposed_tool_file`
- `services.experimental_security.check_experimental_cooldown`
- `services.experimental_security.mark_experimental_cooldown`
- `services.experimental_security.write_experimental_audit`
- `services.experimental_security.write_package_install_audit`
- `services.package_batch_install_service.install_missing_packages_batch`
- `services.package_install_executor.install_python_package`
- `services.package_install_service.build_install_plan`
- `services.proposed_dependency_service.analyze_python_dependencies`
- `services.proposed_promotion_audit_service.add_promotion_audit_record`
- `services.proposed_promotion_audit_service.list_promotion_audit`
- `services.proposed_promotion_guard_service.preflight_promotion_check`
- `services.proposed_tool_service.approve_proposed_tool`
- `services.proposed_tool_service.list_proposed_tools`
- `services.proposed_tool_service.read_proposed_tool`
- `services.proposed_tool_service.reject_proposed_tool`
- `services.proposed_tool_service.save_proposed_tool`
- `services.proposed_tool_validation_service.validate_proposal_record`
- `services.tool_promoter.promote_experimental_to_production`
- `services.tool_promoter.promote_proposed_to_experimental`

#### Calls seen
- `Blueprint`
- `add_promotion_audit_record`
- `admin_password.encode`
- `analyze_python_dependencies`
- `approve_proposed_tool`
- `batch_result.get`
- `body.get`
- `bool`
- `build_install_plan`
- `check_experimental_cooldown`
- `code.strip`
- `dependency_analysis.get`
- `experimental_tool_registry.execute`
- `experimental_tool_registry.list_tool_specs`
- `generate_proposed_tool_file`
- `hashlib.sha256`
- `hexdigest`
- `install_missing_packages_batch`
- `install_python_package`
- `item.get`
- `jsonify`
- `len`
- `list_promotion_audit`
- `list_proposed_tools`
- `mark_experimental_cooldown`
- `next`
- `os.getenv`
- `preflight.get`
- `preflight_promotion_check`
- `promote_experimental_to_production`
- `promote_proposed_to_experimental`
- `proposal.get`
- `read_proposed_tool`
- `reject_proposed_tool`
- `request.get_json`
- `result.get`
- `save_proposed_tool`
- `str`
- `strip`
- `tool.get`
- `tool_registry.execute`
- `tool_registry.list_tool_specs`
- `tools_bp.get`
- `tools_bp.post`
- `validate_proposal_record`
- `write_experimental_audit`
- `write_package_install_audit`

## routes/voice_input_routes.py

### GET /voice/input/status
- Handler: `voice_input_status`
- Blueprint: `voice_input_bp`
- Line: 140

### POST /voice/process-last
- Handler: `voice_process_last`
- Blueprint: `voice_input_bp`
- Line: 153

### POST /voice/query-last
- Handler: `voice_query_last`
- Blueprint: `voice_input_bp`
- Line: 201

### POST /voice/transcribe-last
- Handler: `voice_transcribe_last`
- Blueprint: `voice_input_bp`
- Line: 178

### POST /voice/upload
- Handler: `voice_upload`
- Blueprint: `voice_input_bp`
- Line: 101

#### Imports
- `__future__.annotations`
- `flask.Blueprint`
- `flask.jsonify`
- `flask.request`
- `pathlib.Path`
- `random`
- `requests`
- `services.stt_service.transcribe_wav`
- `threading`
- `time`
- `uuid`
- `werkzeug.utils.secure_filename`

#### Calls seen
- `Blueprint`
- `Path`
- `ROOM_LOCKS.get`
- `ROOM_LOCKS.pop`
- `VOICE_UPLOAD_DIR.mkdir`
- `_latest_file_for_room`
- `_safe_voice_say`
- `acquire_room_lock`
- `agent_data.get`
- `agent_resp.json`
- `bool`
- `file.save`
- `jsonify`
- `latest_link.exists`
- `latest_link.is_symlink`
- `latest_link.symlink_to`
- `latest_link.unlink`
- `p.stat`
- `payload.get`
- `pick_thinking_phrase`
- `random.choice`
- `refresh_room_lock`
- `release_room_lock`
- `request.args.get`
- `request.form.get`
- `request.get_json`
- `requests.post`
- `resp.json`
- `room_dir.exists`
- `room_dir.glob`
- `room_dir.mkdir`
- `secure_filename`
- `sorted`
- `str`
- `strip`
- `suffix.lower`
- `target.stat`
- `thinking_thread.start`
- `threading.Lock`
- `threading.Thread`
- `time.sleep`
- `time.time`
- `transcribe_wav`
- `uuid.uuid4`
- `voice_input_bp.route`

## routes/voice_routes.py

- No Flask route decorators detected automatically.

#### Imports
- `flask.Blueprint`
- `flask.jsonify`
- `flask.request`
- `flask.send_from_directory`
- `json`
- `pathlib.Path`
- `services.announcement_service.announce_text`
- `services.announcement_state_service.should_announce`
- `services.voice_service.VOICE_DIR`
- `services.voice_service.get_players`
- `services.voice_service.mute_player`
- `services.voice_service.resolve_player_id`
- `services.voice_service.say_text`
- `services.voice_service.set_player_volume`
- `services.voice_service.stop_player`

#### Calls seen
- `Blueprint`
- `Path`
- `announce_text`
- `bool`
- `get_players`
- `int`
- `json.loads`
- `jsonify`
- `len`
- `log_file.exists`
- `log_file.read_text`
- `logs.append`
- `lower`
- `mute_player`
- `payload.get`
- `player.get`
- `request.args.get`
- `request.get_json`
- `resolve_player_id`
- `say_text`
- `send_from_directory`
- `set_player_volume`
- `should_announce`
- `splitlines`
- `stop_player`
- `str`
- `strip`
- `voice_bp.get`
- `voice_bp.post`

## routes/water_routes.py

- No Flask route decorators detected automatically.

#### Imports
- `flask.Blueprint`
- `flask.jsonify`
- `services.influx_helpers.iso_now`
- `services.water_service.get_salt_tank_level`
- `services.water_service.get_water_softener_overview`
- `services.water_service.get_water_temperature_summary`

#### Calls seen
- `Blueprint`
- `data.get`
- `get_salt_tank_level`
- `get_water_softener_overview`
- `get_water_temperature_summary`
- `iso_now`
- `jsonify`
- `water_bp.get`
