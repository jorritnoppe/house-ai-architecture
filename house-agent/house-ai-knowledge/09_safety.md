# House AI Safety Model

## Purpose
This file defines the safety philosophy and practical rules for the house-agent.

This is one of the most important files for future AI retrieval because the project is connected to real devices and real house behavior.

The goal is to keep the AI useful **without** giving it uncontrolled power over the house.

---

## Main Safety Principle
The AI should not directly execute arbitrary device actions.

Instead, the AI should work through:

```text
AI reasoning
  ->
structured decision
  ->
approved route or safe executor
  ->
service layer
  ->
controlled device integration
