# 10 - Loxone NFC / Keypad Limitations

## Observations

### HTTP API
- Many NFC states return:
  Code 500 or empty
- Some states return 404
- Not all states are directly readable

### WebSocket
- Provides real-time values
- Works reliably for:
  - historyDate
  - codeDate
  - keyPadAuthType
  - custom outputs

## Key Finding
WebSocket is REQUIRED for NFC logic  
HTTP polling is insufficient

## Keypad Issues
- Code input not reliably visible
- History endpoint returns empty
- Needs further Loxone config investigation

## Working Solution
- Use RFID tag instead of keypad
- Use pushbutton outputs from NFC block

## Future Work
- investigate keypad event configuration
- possibly use history parsing
- or alternative Loxone blocks
