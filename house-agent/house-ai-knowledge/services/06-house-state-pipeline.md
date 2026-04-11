> Detail doc: this file expands on the canonical root docs listed in `INDEX.md` and should be read after the numbered root files.

# Loxone Live System (WebSocket Architecture)

## Purpose
Provide **real-time access to all Loxone sensor data** for the house AI using a stable, fast, and reliable system.

This replaces ALL direct HTTP polling for live values.

---

## 🚨 Core Rule (DO NOT BREAK)
- NEVER rely on `/dev/sps/io/...` HTTP polling for live values
- ALWAYS use WebSocket cache
- DO NOT modify UUID handling unless absolutely necessary
- This system is **critical infrastructure**

---

## 🧠 Architecture
