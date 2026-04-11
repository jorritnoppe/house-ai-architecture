# System Architecture

## Purpose
This document describes the public-facing architecture of the House AI system.

## Core flow
Input
-> local AI reasoning
-> intent routing
-> safety validation
-> service execution
-> telemetry and response

## Main subsystems
- route layer
- service layer
- tool layer
- voice pipeline
- telemetry and analytics
- automation control

## Design goals
- local-first AI execution
- safe action boundaries
- modular deployment
- future context-awareness
