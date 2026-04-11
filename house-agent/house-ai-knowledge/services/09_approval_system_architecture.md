# 09 - Approval System Architecture

## Components

### 1. Pending Approval Service
services/pending_approval_service.py

Stores:
- token
- action
- expiry
- status

### 2. Approval Signal Processor
services/approval_signal_processor_service.py

Handles:
- approve signals
- signal normalization
- state transitions

### 3. WebSocket Bridge
services/approval_signal_bridge_service.py

Maps:
UUID → approval signal

Handles:
- rising edge detection
- filtering duplicate signals

### 4. Execution Layer
services/approved_action_executor_service.py
services/approved_action_executor_service_helpers.py

Executes:
- approved actions via Flask context

### 5. Routes
/ai/approvals/*
/ai/approved-actions/*

## Final Flow

Agent → creates approval  
↓  
Pending queue  
↓  
NFC scan  
↓  
WebSocket update  
↓  
Bridge detects rising edge  
↓  
Processor approves  
↓  
Executor runs action  
↓  
Audio plays / action executes  

## Key Fixes Done
- Removed token-based execution confusion
- Unified execution path
- Fixed Flask context issues
- Ensured auto execution after approval

## Result
Fully working physical authorization system
