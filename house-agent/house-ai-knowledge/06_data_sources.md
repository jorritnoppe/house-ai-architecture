# House AI Data Sources

## Purpose
This file explains where the house-agent gets its information from.

Future AI should use this file to understand:
- which systems provide data
- which sources are real-time versus historical
- how those sources are typically used
- which data sources are important for summaries and automation decisions

---

## Main Data Model
The project combines data from multiple sources instead of relying on one monolithic system.

Broadly, the data comes from:
- live house systems
- stored time-series history
- device-specific integrations
- future context systems such as scheduling or email

---

## InfluxDB

### Purpose
InfluxDB is the primary historical data store for time-series information.

### Typical uses
- recent power history
- historical telemetry
- room temperature and humidity history
- trend and comparison summaries
- state persistence for some systems or tools

### Why it matters
A future AI should understand that many good answers are not based on a single current value. InfluxDB provides context over time.

Examples of question types that likely depend on InfluxDB:
- how much power have we been using recently
- which rooms have been warmest today
- what was the humidity trend
- did usage spike around a certain time

### Operational note
Future AI should prefer wrapped service queries over raw direct database logic unless explicitly asked to work at the database level.

---

## Loxone

### Purpose
Loxone acts as a real-time house automation and state source.

### Typical uses
- current sensor values
- real-time house states
- control points
- relay and automation logic
- room/device state information

### Why it matters
Loxone is both a data source and a control platform. Future AI should distinguish carefully between:
- reading from Loxone
- writing to Loxone

These are not equally safe operations.

---

## SMA Inverter

### Purpose
The SMA integration provides inverter and solar-related information.

### Typical uses
- solar production data
- inverter metrics
- power and energy context
- house energy summaries

### Why it matters
Energy awareness is one of the major themes of the project. Future AI should treat inverter data as part of the house intelligence model, not as an isolated extra.

---

## Metering and Utility Data

Depending on active files and enabled integrations, the project may include data from:
- SDM630 or similar power meters
- APC UPS systems
- Buderus systems
- water-related sources
- price-related feeds
- crypto/state-tracking systems from older project work

Future AI should inspect code and documentation before assuming a source is inactive.

---

## Real-Time vs Historical

### Real-Time Sources
Usually include:
- Loxone live values
- direct device routes
- active integration endpoints

### Historical Sources
Usually include:
- InfluxDB queries
- recent summaries across minutes/hours/days
- trend calculations
- persistence-backed status recovery

Future AI should understand that the answer to "what is happening now" may come from a different source than the answer to "what has been happening."

---

## Practical Guidance for Future AI
When answering questions:
1. use real-time sources for current state
2. use historical sources for trends and summaries
3. prefer structured endpoints over raw source access
4. document any newly discovered measurement or source so future sessions do not have to rediscover it
