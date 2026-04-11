# House AI Voice and Audio System

## Purpose
This file explains the voice and playback system for future AI retrieval.

The audio system is one of the most operationally sensitive parts of the project because it involves:
- user-facing speech output
- room/player routing
- protected speaker handling
- coordination between software playback and house automation

Future AI should read this file before changing anything related to announcements or playback targets.

---

## Main Role of the Audio System
The audio system allows the house AI to:
- speak announcements
- deliver summaries and agenda output
- route speech to specific rooms
- use protected speaker flows where needed
- later support interactive voice behavior

---

## High-Level Playback Flow

```text
AI request
  ->
approved announcement route
  ->
announcement service
  ->
voice service
  ->
player routing / playback target
  ->
room speaker output
