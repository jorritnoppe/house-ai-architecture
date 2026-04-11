# 08 - NFC Approval Integration

## Summary
Physical NFC (RFID tag) is now used to approve AI actions.

## Flow
1. AI requests action → approval required
2. Approval stored in pending queue
3. User scans NFC tag
4. Loxone triggers pushbutton
5. WebSocket detects UUID change
6. Approval bridge processes signal
7. Action is approved AND executed

## Working Signal
masterbedroom approve pulse

UUID:
2073f2a7-03d6-f7f1-05ff5d6294eb1538

## Important Behavior
- Uses rising edge detection
- Pulse length increased to ~3 seconds for reliability
- Auto-reset handled in software

## Result
- Reliable physical approval
- No polling required
- Real-time via websocket

## Current Scope
- ONLY "approve" is active
- RFID tag used as trigger

## Future
- multi-user tags
- room-based approvals
- deny / identity signals
