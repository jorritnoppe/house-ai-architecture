INFLUX_SOURCE_MAP = {
    "main_power": {
        "bucket": "eastron630",
        "measurement": "eastron630",
        "description": "Main house power meter",
    },
    "smart_meter": {
        "bucket": "Pdata",
        "measurement": "Pdata",
        "description": "Second meter / smart meter source",
    },
    "solar_inverter": {
        "bucket": "sma_inverter",
        "measurement": "sma_inverter",
        "description": "SunnyBoy inverter data",
    },
    "water_softener": {
        "bucket": "Housedata",
        "measurement": "water_sensor",
        "fields": ["distance_cm", "flow_lpm", "temp1_c", "temp2_c"],
        "description": "Water softener salt, temperature, and flow data",
    },
    "loxone_history": {
        "bucket": "loxone_history",
        "measurement": "loxone_state",
        "description": "Historical Loxone state changes",
    },
    "ups": {
        "bucket": "apcdata",
        "measurements": ["apc_ups", "apc_ups2"],
        "description": "UPS telemetry",
    },
    "prices": {
        "bucket": "Eleprice",
        "measurement": "solarpulse",
        "field": "value",
        "description": "Electricity price timeline",
    },
    "boiler": {
        "bucket": "Buderus",
        "measurement": "Buderus",
        "description": "Boiler / EMS telemetry",
    },
    "crypto": {
        "bucket": "crypto",
        "measurement": "crypto_portfolio",
        "description": "Crypto portfolio snapshots",
    },
    "unifi": {
        "bucket": "unifi_log_ai",
        "description": "UniFi device and client logging",
    },
    "automation_logs": {
        "bucket": "home_automation",
        "measurement": "voice_requests",
        "description": "Voice / automation interaction logs",
    },
}
