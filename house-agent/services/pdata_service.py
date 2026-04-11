from extensions import pdata_tools
from services.power_service import get_energy_summary_data


def get_pdata_energy_summary_data():
    return pdata_tools.get_energy_summary()


def get_pdata_compare_energy_data():
    local = get_energy_summary_data()
    return pdata_tools.compare_with_local_meter(local)


def get_pdata_all_fields_data():
    return pdata_tools.decode_all_fields()


def get_pdata_full_overview_data():
    return pdata_tools.get_full_overview()


def get_pdata_gas_summary_data():
    return pdata_tools.get_gas_summary()
