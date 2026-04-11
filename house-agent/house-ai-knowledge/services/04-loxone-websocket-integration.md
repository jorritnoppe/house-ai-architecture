> Detail doc: this file expands on the canonical root docs listed in `INDEX.md` and should be read after the numbered root files.

# Loxone WebSocket Integration (Critical Fix - 2026-03-25)

## Summary
We migrated Loxone state reading from HTTP polling to a **WebSocket-driven cache system**, fixing:
- 404 errors on `/dev/sps/io/...`
- Slow or failing climate reads
- Inconsistent sensor availability

This is now the **primary data source for all live house state**.

---

## 🔥 Core Problem (Before)
- Climate controller states (tempActual, humidity, etc.) returned **404**
- HTTP polling does NOT work for these UUIDs
- Result:
  - `/ai/loxone_room_climate` broken
  - `/ai/loxone_live_room` unreliable
  - House AI blind to real sensor data

---

## ✅ Solution Implemented

### 1. WebSocket Client (loxwebsocket)
File:
