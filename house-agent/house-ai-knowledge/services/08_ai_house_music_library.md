# AI House Music Library

## Purpose
This service manages the local AI-house music folder and builds the enabled LMS playlist.

It is intentionally split into two layers:

1. Safe AI playback routes
- `/tools/music/play_ai_house`
- `/tools/music/stop_room`

2. Manual admin library routes
- `/ai-server/music`
- `/ai-server/music/api/library`
- `/ai-server/music/api/refresh`
- `/ai-server/music/api/toggle`
- `/ai-server/music/api/delete`

The admin routes are not autonomous AI routes.
They are manual operator tools because they can change playlist composition and delete files.

## Storage
Root music folder:
- `/mnt/aihousemusicfolder/ai-house`

Metadata:
- `/mnt/aihousemusicfolder/ai-house/meta/track_status.csv`
- `/mnt/aihousemusicfolder/ai-house/meta/enabled_playlist.m3u`

LMS playlist load target:
- `/mnt/Trueshare/Music/ai-house/meta/enabled_playlist.m3u`

## Refresh behavior
The refresh flow:
1. scan the AI-house music folder
2. ignore the `meta/` folder
3. detect audio files
4. preserve existing enabled flags by `relative_path`
5. add new files with enabled default `1`
6. remove stale missing files from metadata
7. rebuild `enabled_playlist.m3u`

## Operational rule
- AI may safely play or stop the AI-house playlist
- AI may not autonomously delete tracks
- AI may not autonomously change library membership unless policy is explicitly changed later

## Roadmap note
Phase 2 music intelligence remains deferred:
- no automatic room binding yet
- no strongest-node room inference yet
- no multi-node music origin inference yet

That work should only begin after multi-node capture is mature.
