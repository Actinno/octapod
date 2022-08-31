#!/opt/minieliot/bin/python3

import re
import json
import pandas as pd
from eliot.util.file import load_json_file

unique_id = 11000

drivers = {
    'powys_3101': 'eliot.drivers.klemsan.Powys3122',
    'powys_3121': 'eliot.drivers.klemsan.Powys3122',
    'powys_3122': 'eliot.drivers.klemsan.Powys3122',
    'powys_1120': 'eliot.drivers.klemsan.Powys1120',
    'easio_1101': 'eliot.drivers.klemsan.Easio'
}

medicion_file = "Medicion-cdaII.csv"
medicion_cols = {
    'Organizacion':                 'location',
    'Descripcion':                  'description',
    'Modelo del dispositivo':       'device_model',
    'Direccion':                    'device_addr',
    'Punto de acceso':              'gateway_name'
    }

gateways_file = "Comunicacion-cdaII.csv"
gateways_cols = {
    'Punto de acceso':  'gateway_name',
    'IP Address':       'gateway_addr',
    #'Puerto':           'gateway_port'
    }

device_df = pd.read_csv(
        medicion_file, 
        header='infer', 
        delimiter=',',
        usecols=list(medicion_cols.keys())
    ).rename(columns=medicion_cols)

gateways_df = pd.read_csv(
        gateways_file,
        header='infer',
        delimiter=',',
        usecols=list(gateways_cols.keys())
    ).rename(columns=gateways_cols)

#joined_data = device_df.join(gateways_df.set_index('gateway_name'), on=['gateway_name'])
#grouped_devices = joined_data.groupby('gateway_name')

base_config = load_json_file("base-config.json")

grouped_devices = device_df.groupby('gateway_name')

gateways = {}

for gw_name, gw_devices_df in grouped_devices:
    gw_df = gateways_df.where(gateways_df.gateway_name == gw_name).dropna()
    gw_addr = gw_df['gateway_addr'].values[0]
    #gw_port = int(gw_df['gateway_port'].values[0])
    gw_port = 502

    gw_devices = []
    for row_id, row in gw_devices_df.iterrows():
        #location = re.sub(r'.*(zenteno|nataniel).*', r'\1', row.location.lower())
        location = re.sub(r'colores del abra ii/piso ', 'cda2_piso', row.location.lower())
        model = re.sub(r'^(easio|powys) ([0-9]{4}).*', r'\1_\2', row.device_model.lower())

        #description = re.sub(r'^local\s', 'L', row.description.lower())
        #if description == row.description:
        #    description = re.sub(r'^', 'D', row.description)
        description = re.sub(r'\s', '_', row.description.lower())

        device_desc = location + "-" + description + "-" + model

        device = {
            'enable': True,
            'description': device_desc,
            'modbus_addr': row.device_addr,
            'unique_id': unique_id,
            'reading': 'read_' + model,
            'driver': drivers[model]
        }
        gw_devices.append(device)
        unique_id += 1

    gateways[gw_name] = {
        'enable': True,
        'addr': gw_addr,
        'port': gw_port,
        'devices': gw_devices
    }

base_config['gateways'] = gateways

print(json.dumps(base_config, indent=2))

