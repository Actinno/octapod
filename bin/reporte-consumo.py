#!/opt/minieliot/bin/python3

import psycopg2
import os
import os.path
import sys
import json
import time
from datetime import datetime
from dateutil import tz

minieliot_config = "/etc/minieliot/config.json"
report_dir = "/var/minieliot/report/consumo"

with open(minieliot_config, "r") as config_file:
    config = json.load(config_file)

#LOCAL_TZ = 'America/Santiago'
LOCAL_TZ = 'UTC'

TRI_PH_POWYS_QUERY = """
    SELECT
        {} AS "UTC Offset (minutes)",
        TO_CHAR(ts at time zone '{}', 'MM-DD-YYYY HH24:MI') AS "Local Time Stamp",
        replace((export_active_energy_t1/1000.0)::text, '.',',') AS "Active energy delivered (kWh)",
        replace((import_active_energy_t1/1000.0)::text, '.',',') AS "Active energy received (kWh)",
        replace((export_reactive_energy_t1/1000.0)::text, '.',',') AS "Reactive energy delivered (kVArh)",
        replace(system_frecuency::text, '.',',') AS "Frequency (Hz)",
        replace(fase_1_current::text, '.',',') AS "Current A (A)",
        replace(fase_2_current::text, '.',',') AS "Current B (A)",
        replace(fase_3_current::text, '.',',') AS "Current C (A)",
        replace(total_current::text, '.',',') AS "Current N (A)",
        replace(fase_1_voltage_ln::text, '.',',') AS "Voltage A-N (V)",
        replace(fase_2_voltage_ln::text, '.',',') AS "Voltage B-N (V)",
        replace(fase_3_voltage_ln::text, '.',',') AS "Voltage C-N (V)",
        replace(average_voltage_ln::text, '.',',') AS "Voltage L-N Avg (V)",
        replace((fase_1_active_power/1000.0)::text, '.',',') AS "Active Power A (kW)",
        replace((fase_2_active_power/1000.0)::text, '.',',') AS "Active Power B (kW)",
        replace((fase_3_active_power/1000.0)::text, '.',',') AS "Active Power C (kW)",
        replace((total_active_power/1000.0)::text, '.',',') AS "Active Power (kW)",
        replace((fase_1_reactive_power/1000.0)::text, '.',',') AS "Reactive Power A (kVAr)",
        replace((fase_2_reactive_power/1000.0)::text, '.',',') AS "Reactive Power B (kVAr)",
        replace((fase_3_reactive_power/1000.0)::text, '.',',') AS "Reactive Power C (kVAr)",
        replace((total_reactive_power/1000.0)::text, '.',',') AS "Reactive Power (kVAr)"
    FROM "{}"
    WHERE
        unique_id = {}
    AND
        ts >= DATE_TRUNC('HOUR', NOW() - INTERVAL '1 HOUR')
    AND
        ts < DATE_TRUNC('HOUR', NOW())
"""

MONO_PH_POWYS_QUERY = """
    SELECT
        {} AS "UTC Offset (minutes)",
        TO_CHAR(ts at time zone '{}', 'MM-DD-YYYY HH24:MI') AS "Local Time Stamp",
        replace((export_active_energy/1000.0)::text, '.',',') AS "Active energy delivered (kWh)",
        replace((import_active_energy/1000.0)::text, '.',',') AS "Active energy received (kWh)",
        replace((export_reactive_energy/1000.0)::text, '.',',') AS "Reactive energy delivered (kVArh)",
        replace(frequency::text, '.',',') AS "Frequency (Hz)",
        replace(current::text, '.',',') AS "Current A (A)",
        replace(current::text, '.',',') AS "Current N (A)",
        replace(voltage::text, '.',',') AS "Voltage A-N (V)",
        replace(voltage::text, '.',',') AS "Voltage L-N (V)",
        replace((active_power/1000.0)::text, '.',',') AS "Active Power A (kW)",
        replace((active_power/1000.0)::text, '.',',') AS "Active Power (kW)",
        replace((reactive_power/1000.0)::text, '.',',') AS "Reactive Power A (kVAr)",
        replace((reactive_power/1000.0)::text, '.',',') AS "Reactive Power (kVAr)"
    FROM {}
    WHERE
        unique_id = {}
    AND
        ts >= DATE_TRUNC('HOUR', NOW() - INTERVAL '1 HOUR')
    AND
        ts < DATE_TRUNC('HOUR', NOW())
"""

MAC_DICT = {
    '192.168.20.10': 'C4:29:1D:00:29:83',
    '192.168.20.11': 'C4:29:1D:00:29:91',
    '192.168.20.12': 'C4:29:1D:00:29:99',
    '192.168.20.13': 'C4:29:1D:00:29:84',
    '192.168.20.14': 'C4:29:1D:00:29:C2',
    '192.168.20.15': 'C4:29:1D:00:29:C8',
    '192.168.20.16': 'C4:29:1D:00:29:98',
    '192.168.20.17': 'c4:29:1d:00:29:cb',
}

POWYS_DEV_TYPE = {
    'eliot.drivers.klemsan.Powys1120': '606352',
    'eliot.drivers.klemsan.Powys3122': '606303'
}

POWYS_DEV_MODEL = {
    'eliot.drivers.klemsan.Powys1120': 'Klemsan Powys 1120',
    'eliot.drivers.klemsan.Powys3122': 'Klemsan Powys 3101'
}

TABLES = {
    'eliot.drivers.klemsan.Powys1120': 'powys_1120_hr',
    'eliot.drivers.klemsan.Powys3122': 'powys_3122_hr'
}

def print_now():
    return datetime.now().strftime('[%m/%d/%Y %H:%M]:')

def get_utc_offset(tz_name):
    tzfile = tz.gettz(tz_name)
    utc_now = datetime.now()
    local_now = datetime(utc_now.year, utc_now.month, utc_now.day, utc_now.hour, utc_now.minute, tzinfo=tzfile)
    tdelta = local_now.tzinfo.utcoffset(utc_now)
    utc_diff = int(tdelta.days * 24 * 60 + tdelta.seconds / 60)
    return utc_diff

def do_reports():
    for gw_name in config["gateways"].keys():
        gw_enbled = config['gateways'][gw_name]['enable']
        if gw_enbled:
            gw_addr = config['gateways'][gw_name]['addr']
            gw_sn = ""
            gw_mac = MAC_DICT.get(gw_addr)
            for dev in config['gateways'][gw_name]['devices']:
                device_enabled = dev['enable']
                if device_enabled:
                    device_driver = dev['driver']
                    device_name = dev['description']
                    table = TABLES.get(device_driver)
                    freq = config['minieliot']['read_frequency']
                    unique_id = dev["unique_id"]
        
                    if device_driver in POWYS_DEV_TYPE.keys():
                        dev_header  = "Gateway Name;"
                        dev_header += "Gateway SN;"
                        dev_header += "Gateway IP Address;"
                        dev_header += "Gateway MAC Address;"
                        dev_header += "Device Name;"
                        dev_header += "Device Local ID;"
                        dev_header += "Device Type ID;"
                        dev_header += "Device Type Name;"
                        dev_header += "Logging Interval;"
                        dev_header += "Historical Intervals"
                        dev_header += ";"*13 + "\n"

                        dev_data  = f"{gw_name};"
                        dev_data += ";"
                        dev_data += f"{gw_addr};"
                        dev_data += f"{MAC_DICT[gw_addr]};"
                        dev_data += f"{device_name};"
                        dev_data += f"{dev['modbus_addr']};"
                        dev_data += f"{POWYS_DEV_TYPE.get(device_driver)};"
                        dev_data += f"{POWYS_DEV_MODEL.get(device_driver)};"
                        dev_data += str(freq) + ";"
                        dev_data += str(int(60/freq)) + ";"
                        dev_data += ";"*13 + "\n"
                    else:
                        print(f"{print_now()} Driver {device_driver} no soportado para la generación de reportes")
                        continue
        
                    print(f"{print_now()} Creando reporte para dispositivo {unique_id}")
                    csv_export(config['db_config'], gw_addr, dev_header, dev_data, device_driver, device_name, unique_id, table)

def csv_export(db_config, gw_addr, dev_header, dev_data, device_driver, device_name, unique_id, table):
    utc_offset = get_utc_offset(LOCAL_TZ)
    if device_driver == 'eliot.drivers.klemsan.Powys3122':
        sql_query = TRI_PH_POWYS_QUERY.format(utc_offset, LOCAL_TZ, table, unique_id)
    elif device_driver == 'eliot.drivers.klemsan.Powys1120':
        sql_query = MONO_PH_POWYS_QUERY.format(utc_offset, LOCAL_TZ, table, unique_id)
    else:
        print(f"{print_now()} {model} no es un modelo soportado")
        return False

    # Use the COPY function on the SQL we created above.
    SQL_for_file_output = "COPY ({0}) TO STDOUT WITH CSV HEADER DELIMITER ';'".format(sql_query)

    # Set up a variable to store our file path and name.
    #date_fmt = datetime.now().strftime("%m-%d-%Y-%H%M")
    date_fmt = datetime.now().strftime("%m-%d-%Y_%H")
    output_dir = f"{report_dir}/{gw_addr}"
    t_path_n_file = f"{output_dir}/{device_name}_{date_fmt}.tmp"

    # Trap errors for opening the file
    try:
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)

        print(f"{print_now()} Creando archivo temporal {t_path_n_file}")
        with open(t_path_n_file, 'w') as f_output:
            f_output.write(dev_header)
            f_output.write(dev_data)
            f_output.write((";" * 22 + "\n") * 4)
            db_conn = psycopg2.connect(
                    host=db_config['host'], 
                    port=db_config['port'], 
                    dbname=db_config['db'], 
                    user=db_config['user'], 
                    password=db_config['pass']
                )
            db_cursor = db_conn.cursor()
            db_cursor.copy_expert(SQL_for_file_output, f_output)
            # Clean up: Close the database cursor and connection
            db_cursor.close()
            db_conn.close()
            f_output.close()
            
            path_n_file = t_path_n_file.replace(".tmp", ".csv")
            print(f"{print_now()} Renombrando archivo {t_path_n_file} como {path_n_file}")
            os.rename(t_path_n_file, path_n_file)
    except (psycopg2.Error, OSError) as e:
        print(f"{print_now()} Error generando reporte de hora {date_fmt}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    do_reports()

