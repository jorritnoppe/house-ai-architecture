> Detail doc: this file expands on the canonical root docs listed in `INDEX.md` and should be read after the numbered root files.

# Repo Notes and Exclusions

## Exclude from knowledge upload
- .env
- secrets
- tokens
- private keys
- backups/
- __pycache__/
- data/voice_uploads/
- raw logs unless specifically summarized
- generated binary/cache artifacts

## Keep summarized instead
- backup strategy
- state files
- audit files
- generated tools lifecycle

## Current repo-specific note
This repo contains many `.save`, `.known-good`, and backup variants.
These are useful for local recovery, but should not all be ingested into the AI knowledge base.
Prefer summarizing the currently active files first.
