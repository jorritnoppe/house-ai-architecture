> Detail doc: this file expands on the canonical root docs listed in `INDEX.md` and should be read after the numbered root files.

# Runtime Data and State

## Purpose
Document runtime state files without treating them as source-of-truth architecture.

## Observed runtime/state files
- data/announcement_log.jsonl
- data/announcement_state.json
- data/conversation_last_speaker.json
- data/proposed_promotion_audit.json
- data/proposed_tools.json
- data/proposed_tools.backup.json
- data/ups_voice_state.json

## Volatile content
These files may change often and should not be blindly uploaded as permanent knowledge.
Instead, document:
- what each file stores
- who writes it
- retention expectations
- whether it is audit-critical

## Exclude from knowledge ingestion
- raw wav files in data/voice_uploads/
- transient runtime logs
