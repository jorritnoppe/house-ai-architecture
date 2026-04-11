import os
from dotenv import load_dotenv

load_dotenv()
EXPERIMENTAL_APPROVAL_PASSWORD_HASH = os.getenv("EXPERIMENTAL_APPROVAL_PASSWORD_HASH", "")


INFLUX_URL = os.getenv("INFLUX_URL", "http://influx.local:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "CHANGE_ME")
INFLUX_ORG = os.getenv("INFLUX_ORG", "home")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "eastron630")
INFLUX_MEASUREMENT = os.getenv("INFLUX_MEASUREMENT", INFLUX_BUCKET)

PRICE_INFLUX_BUCKET = os.getenv("PRICE_INFLUX_BUCKET", "Eleprice")
PRICE_INFLUX_MEASUREMENT = os.getenv("PRICE_INFLUX_MEASUREMENT", "solarpulse")
PRICE_INFLUX_FIELD = os.getenv("PRICE_INFLUX_FIELD", "value")
PRICE_WINDOW = os.getenv("PRICE_WINDOW", "30m")

SALT_INFLUX_BUCKET = os.getenv("SALT_INFLUX_BUCKET", "Housedata")
SALT_INFLUX_MEASUREMENT = os.getenv("SALT_INFLUX_MEASUREMENT", "water_sensor")
SALT_INFLUX_FIELD = os.getenv("SALT_INFLUX_FIELD", "distance_cm")

SALT_FULL_CM = float(os.getenv("SALT_FULL_CM", "5"))
SALT_EMPTY_CM = float(os.getenv("SALT_EMPTY_CM", "37"))

WATER_TEMP_BUCKET = os.getenv("WATER_TEMP_BUCKET", "Housedata")
WATER_TEMP_MEASUREMENT = os.getenv("WATER_TEMP_MEASUREMENT", "water_sensor")
WATER_TEMP1_FIELD = os.getenv("WATER_TEMP1_FIELD", "temp1_c")
WATER_TEMP2_FIELD = os.getenv("WATER_TEMP2_FIELD", "temp2_c")
WATER_TEMP1_DIVISOR = float(os.getenv("WATER_TEMP1_DIVISOR", "2"))

SMA_INFLUX_BUCKET = os.getenv("SMA_INFLUX_BUCKET", "sma_inverter")
SMA_INFLUX_MEASUREMENT = os.getenv("SMA_INFLUX_MEASUREMENT", "sma_inverter")

SMA_AC_POWER_FIELD = os.getenv("SMA_AC_POWER_FIELD", "ac_power")
SMA_DAILY_ENERGY_FIELD = os.getenv("SMA_DAILY_ENERGY_FIELD", "daily_energy")
SMA_GRID_VOLTAGE_FIELD = os.getenv("SMA_GRID_VOLTAGE_FIELD", "grid_current")
SMA_INVERTER_TEMP_FIELD = os.getenv("SMA_INVERTER_TEMP_FIELD", "inverter_temp")
SMA_PV_CURRENT_FIELD = os.getenv("SMA_PV_CURRENT_FIELD", "pv_current")
SMA_PV_VOLTAGE_FIELD = os.getenv("SMA_PV_VOLTAGE_FIELD", "pv_voltage")
SMA_TOTAL_ENERGY_FIELD = os.getenv("SMA_TOTAL_ENERGY_FIELD", "total_energy")

SMA_DAILY_ENERGY_DIVISOR = float(os.getenv("SMA_DAILY_ENERGY_DIVISOR", "1000"))
SMA_TOTAL_ENERGY_DIVISOR = float(os.getenv("SMA_TOTAL_ENERGY_DIVISOR", "1000"))
SMA_PV_VOLTAGE_DIVISOR = float(os.getenv("SMA_PV_VOLTAGE_DIVISOR", "10"))
SMA_INVERTER_TEMP_DIVISOR = float(os.getenv("SMA_INVERTER_TEMP_DIVISOR", "100"))

POWER_FIELDS_DEFAULT = [
    "frequency",
    "max_power_demand",
    "power_demand",
    "total_pf",
    "total_power",
    "total_va",
    "total_var",
]

LOXONE_HOST = os.getenv("LOXONE_HOST", "loxone.local")
LOXONE_USER = os.getenv("LOXONE_USER", "aiuser")
LOXONE_PASSWORD = os.getenv("LOXONE_PASSWORD", "")



LOXONE_HISTORY_BUCKET = os.getenv("LOXONE_HISTORY_BUCKET", "loxone_history")
LOXONE_HISTORY_MEASUREMENT = os.getenv("LOXONE_HISTORY_MEASUREMENT", "loxone_state")
LOXONE_HISTORY_ENABLED = os.getenv("LOXONE_HISTORY_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
LOXONE_HISTORY_HEARTBEAT_SECONDS = int(os.getenv("LOXONE_HISTORY_HEARTBEAT_SECONDS", "900"))
