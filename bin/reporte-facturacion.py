#!/opt/minieliot/bin/python3

import json

power_analyzers = [
    "eliot.drivers.klemsan.Powys1120",
    "eliot.drivers.klemsan.Powys3122"
]

def carga_matriz_calculo():
    pass

def calcula_consumo_kwh(unique_id):
    return 0.0

def calcula_facturacion(consumo_kwh):
    matriz = carga_matriz_calculo()
    return 0

def factura(gateways_config, periodo):
    records = list()
    records.append("Edificio;Unidad;Periodo;Consumo kWh;Monto CLP")
    for gw_name in gateways_config.keys():
        gw_cfg = gateways_config[gw_name]
        for dev in gw_cfg['devices']:
            if dev['enable']:
                if dev['driver'] in power_analyzers:
                    addr = dev['modbus_addr']
                    unique_id = dev['unique_id']
                    (edificio, unidad, device_model) = dev['description'].split("-")
                    consumo_kwh = calcula_consumo_kwh(unique_id)
                    monto = calcula_facturacion(consumo_kwh)
                    records.append(f"{edificio};{unidad};{periodo};{consumo_kwh};{monto}\n")
    return records

def emite_csv(records, periodo):
    csv_filename = f"/var/minieliot/report/facturacion/reporte_{periodo}.csv"
    with open(csv_filename, "w") as csv_file:
        for record in records:
            csv_file.write(record)
        csv_file.close()

def main():
    with open("/etc/minieliot/config.json", "r") as config_data:
        config = json.load(config_data)

    # XXX: Período se tendría que pasar por argumento, en caso 
    #      contrario calcular el período del mes actual
    periodo = '2021-04'

    records = factura(config['gateways'], periodo)
    emite_csv(records, periodo)

if __name__ == "__main__":
    main()

