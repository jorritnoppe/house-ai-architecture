# House AI Architecture

## Purpose
This file explains how the house-agent is structured so future AI sessions understand the intended control flow and do not bypass safe layers.

The architecture is designed around a clear rule:

**AI reasoning should be separated from hardware execution.**

That means the AI can interpret requests, but execution should happen through approved backend layers.

---

## High-Level Request Flow

```text
User request
  ->
AI / agent layer
  ->
intent selection or safe executor decision
  ->
approved route
  ->
service layer
  ->
device integration or data source
  ->
structured result
  ->
AI-friendly answer
