import os

from flask import Flask
from flask_cors import CORS
from influxdb_client import InfluxDBClient

from config import (
    INFLUX_URL,
    INFLUX_TOKEN,
    INFLUX_ORG,
    SMA_INFLUX_BUCKET,
    SMA_INFLUX_MEASUREMENT,
    SMA_AC_POWER_FIELD,
    SMA_DAILY_ENERGY_FIELD,
    SMA_GRID_VOLTAGE_FIELD,
    SMA_INVERTER_TEMP_FIELD,
    SMA_PV_CURRENT_FIELD,
    SMA_PV_VOLTAGE_FIELD,
    SMA_TOTAL_ENERGY_FIELD,
    SMA_DAILY_ENERGY_DIVISOR,
    SMA_TOTAL_ENERGY_DIVISOR,
    SMA_PV_VOLTAGE_DIVISOR,
    SMA_INVERTER_TEMP_DIVISOR,
)

from tools_crypto import CryptoTools
from Pdata import PdataTools
from sma_ai import SMATools

from services.tool_registry import load_tools_from_package
from influxdb_client.client.write_api import SYNCHRONOUS


app = Flask(__name__)
CORS(app)

client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG,
    timeout=10_000,
)

query_api = client.query_api()



write_api = client.write_api(write_options=SYNCHRONOUS)



crypto_tools = CryptoTools(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG,
    bucket="crypto",
)

pdata_tools = PdataTools(query_api=query_api)

sma_tools = SMATools(
    query_api=query_api,
    bucket=SMA_INFLUX_BUCKET,
    measurement=SMA_INFLUX_MEASUREMENT,
    ac_power_field=SMA_AC_POWER_FIELD,
    daily_energy_field=SMA_DAILY_ENERGY_FIELD,
    grid_voltage_field=SMA_GRID_VOLTAGE_FIELD,
    inverter_temp_field=SMA_INVERTER_TEMP_FIELD,
    pv_current_field=SMA_PV_CURRENT_FIELD,
    pv_voltage_field=SMA_PV_VOLTAGE_FIELD,
    total_energy_field=SMA_TOTAL_ENERGY_FIELD,
    daily_energy_divisor=SMA_DAILY_ENERGY_DIVISOR,
    total_energy_divisor=SMA_TOTAL_ENERGY_DIVISOR,
    pv_voltage_divisor=SMA_PV_VOLTAGE_DIVISOR,
    inverter_temp_divisor=SMA_INVERTER_TEMP_DIVISOR,
)

# Share main Influx settings with Buderus module
os.environ.setdefault("BUDERUS_INFLUX_URL", INFLUX_URL)
os.environ.setdefault("BUDERUS_INFLUX_TOKEN", INFLUX_TOKEN)
os.environ.setdefault("BUDERUS_INFLUX_ORG", INFLUX_ORG)
os.environ.setdefault("BUDERUS_INFLUX_BUCKET", "Buderus")
os.environ.setdefault("BUDERUS_MEASUREMENT", "Buderus")

# Production registry: safe auto-runnable tools
tool_registry = load_tools_from_package("tools")

# Experimental registry: discoverable but never auto-run
experimental_tool_registry = load_tools_from_package("experimental_tools")
