# House AI Architecture Overview

This document describes how the House AI system is structured, how the two repositories relate to each other, how runtime flows work on the AI server, and what engineering workflow must be followed for safe development.

---

# 1. System purpose

The House AI system is a local-first home intelligence stack built around:

- Ubuntu AI server
- RTX 3060
- Ollama
- Open WebUI
- Flask house-agent API
- InfluxDB
- Loxone / PLC / Raspberry Pi integrations
- PiCore / LMS multi-room audio
- safe API execution only

The design goal is:

- one canonical natural-language routing path
- truthful structured house-state answers
- safe execution only for actions
- live runtime truth kept private
- only sanitized reviewed code mirrored to public repo

---

# 2. Core repo model

There are two repositories on the AI server.

## 2.1 Live runtime repo

Path:

```bash
~/house-agent
