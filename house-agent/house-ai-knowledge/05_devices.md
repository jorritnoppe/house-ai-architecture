# Devices and Integrations

## Purpose
This file describes all physical and logical devices connected to the house-agent.

It helps future AI understand:
- what hardware exists
- how it is accessed
- which devices require special handling

---

## Core Systems

### Loxone
Main house automation system.

Responsibilities:
- relays
- switches
- automation logic

Access:
- via loxone_service
- via safe API routes

Important:
Never bypass Loxone with raw calls.

---

### Audio System (PiCore / LMS)

Handles:
- music playback
- speech output

Controlled via:
- voice_service
- announcement_service

---

### Living Room Speaker (SPECIAL CASE)

This is a protected resource.

Rules:
- must enable speaker module before playback
- must release after playback
- shared with normal music system

AI must NOT treat this as a normal speaker.

---

### SMA Inverter

Provides:
- solar production data
- energy metrics

---

### SDM630 Power Meter

Provides:
- electrical measurements
- power monitoring

---

### APC UPS

Provides:
- power backup status
- system health info

---

### Buderus (if active)

Heating system integration.

---

## Device Rules

- always go through services
- never assume behavior
- check for special logic
- preserve working flows

---

## Future Expansion

Expected:
- more sensors
- more rooms
- microphone arrays
- additional automation devices
