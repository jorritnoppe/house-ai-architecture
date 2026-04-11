# House Grafana Dashboard Inventory

Dashboard path:
`/var/lib/grafana/dashboards/house`

## Current dashboards
- 01 House AI - Core Ops
- 02 AI Stack
- 03 Network Devices
- 04 Energy Placeholder
- 05 Energy Live
- 06 Heating Utilities
- 07 Loxone Room Map
- 08 Network Presence Map
- 09 House Overview
- 10 Eastron Meter Deep Dive
- 11 Water And Utilities
- 12 House Wallboard
- 13 Loxone Inventory
- 14 Unifi Room Presence
- 15 Energy Flow Corrected
- 16 Power Price And Run Windows
- 17 Solar Vs House Correlation
- 18 Occupancy And Access
- 19 Service Health Matrix
- 20 UniFi Gateway Deep Dive
- 21 Buderus Efficiency And Cycles
- 22 Eastron Power Quality
- 23 UniFi Client Inventory
- 24 Loxone Sensor Inventory
- 25 Energy Price Vs Solar

## Datasources in use
- Prometheus
- InfluxDB

## Provisioning status
Dashboards are provisioned from:
`/var/lib/grafana/dashboards/house`

Grafana provisioning validated with:
- JSON validation OK
- ownership corrected to grafana:grafana
- grafana-server restart OK
- provisioning.dashboard start/finish messages OK
- no failed dashboard load messages

## Current focus
The dashboard stack now covers:
- service health
- AI stack health
- network health
- energy
- heating
- Loxone state visibility
- UniFi room presence
- overview / wallboard views
- price-aware energy windows
- occupancy / access monitoring
- Buderus analysis
- Eastron power quality
- UniFi client inventory
- Loxone inventory discovery
- energy price vs solar logic

## Recommended next dashboards
- 26 Room Climate Overview
- 27 APC UPS Overview
- 28 Loxone Security And Access
- 29 Automation Activity
- 30 Solar And Heating Correlation
