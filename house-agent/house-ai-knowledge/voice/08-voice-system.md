> Detail doc: this file expands on the canonical root docs listed in `INDEX.md` and should be read after the numbered root files.

# Voice System (Detailed)

## Routes
- routes/voice_routes.py
- routes/voice_input_routes.py

## Services
- services/voice_service.py
- services/stt_service.py
- services/announcement_service.py
- services/monitor_ups_voice.py

## State files
- data/announcement_log.jsonl
- data/announcement_state.json
- data/conversation_last_speaker.json
- data/ups_voice_state.json

## Notes
- Voice supports playback + announcements
- Tracks last speaker
- Uses upload + processing flow

## TODO
- Document endpoints + audio routing
