# Deployment

## Purpose
Describes how the house-agent runs in production.

---

## Environment

- Ubuntu server
- RTX 3060
- Python virtual environment
- Flask backend
- Ollama for AI

---

## Components

### house-agent
- Flask API
- main control layer

### Ollama
- local AI model

### InfluxDB
- time-series database

---

## Running

Typical usage:

curl -X POST http://127.0.0.1:8000/agent/query

---

## Folder Structure

- routes/ → API endpoints
- services/ → logic
- tools/ → helpers
- data/ → runtime state
- house-ai-knowledge/ → docs

---

## Backups

- stored in /mnt/aiserver-backups
- sanitized before export

---

## Rules

- system must be restart-safe
- avoid breaking working flows
