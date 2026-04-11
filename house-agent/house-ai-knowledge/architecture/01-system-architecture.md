> Detail doc: this file expands on the canonical root docs listed in `INDEX.md` and should be read after the numbered root files.

# System Architecture (Detailed)

## Flask Entry
- app.py
- extensions.py

## Routing layer
- agent_routes.py
- audio_tool_routes.py
- health_routes.py
- house_routes.py
- loxone_routes.py
- openai_routes.py
- pdata_routes.py
- power_routes.py
- price_routes.py
- __pycache__
- sma_routes.py
- status.py
- tool_routes.py
- tool_routes.py.save
- tool_routes.py.save.1
- voice_input_routes.py
- voice_input_routes.py.save
- voice_input_routes.py.save.1
- voice_routes.py
- water_routes.py

## Service layer
- agent_crypto.py
- agent_house.py
- agent_service.py
- ai_tool_generator.py
- announcement_log_service.py
- announcement_service.py
- announcement_state_service.py
- announce_service.py
- apc_service.py
- buderus_service.py
- compare_service.py
- experimental_approval_service.py
- experimental_audit.log
- experimental_cooldowns.json
- experimental_security.py
- experimental_tool_matcher.py
- influx_helpers.py
- intent_detection.py
- loxone_action_service.py
- loxone_music_controls.py
- loxone_music_controls.py.save
- loxone_music_controls.py.save.1
- loxone_music_controls.py.save.2
- loxone_routes.py
- loxone_service.py
- loxone_service.py.save
- loxone_service.py.save.1
- monitor_ups_voice.py
- package_batch_install_service.py
- package_install_executor.py
- package_install_service.py
- pdata_service.py
- power_service.py
- price_service.py
- proposal_promotion_service.py
- proposed_dependency_service.py
- proposed_promotion_audit_service.py
- proposed_promotion_guard_service.py
- proposed_tool_service.py
- proposed_tool_validation_service.py
- __pycache__
- sma_service.py
- status_service.py
- stt_service.py
- tool_promoter.py
- tool_registry.py
- voice_service.py
- voice_service.py.bak_tts_cleanup
- voice_service.py.save
- water_service.py

## Tool system
- tools/
- experimental_tools/
- proposed_tools/

## Runtime data
- data/announcement_log.jsonl
- data/announcement_state.json
- data/conversation_last_speaker.json
- data/proposed_promotion_audit.json
- data/proposed_tools.backup.json
- data/proposed_tools.json
- data/ups_voice_state.json
- data/voice_uploads

## Key modules
- router_logic.py
- router_tools.py
- config.py
- ollama_client.py
- buderus_module.py
- apc_ai.py
- sma_ai.py

## Notes
- System uses modular Flask blueprints
- Strong separation between routes and services
- Tool lifecycle system is present (proposed → experimental → production)
