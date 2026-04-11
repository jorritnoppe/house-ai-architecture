# Automation Rules

## Purpose
Defines how automation should behave safely and predictably.

---

## Core Rules

### 1. No Direct Device Control
All actions must go through:
- routes
- services

---

### 2. Trigger-Based Behavior
Some systems use triggers instead of states.

Examples:
- music ON commands
- short pulses

AI must not assume persistent state.

---

### 3. Living Room Audio Rule

- enable speaker first
- respect delay
- release after use

---

### 4. No Rapid Repetition

Avoid:
- rapid toggling
- repeated triggers
- loops

---

### 5. Announcements

- should not overlap
- should respect priority
- should not spam

---

### 6. Safe Expansion

New automation must:
1. have a route
2. have a service
3. be documented
4. be validated

---

## Philosophy

Automation should be:
- predictable
- safe
- observable
- controlled
