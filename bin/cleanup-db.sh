#!/bin/bash

CONFIG='/opt/minieliot/etc/config.json'
RETENTION_UNIT='month'
RETENTION_PERIOD=3
TABLES="easio_hr powys_1120_hr powys_3122_hr"
DATEFMT='+%Y-%m-%d %H:%M:%S'

PSQL=$(jq '["psql -h ", .db_config.host, " -p ", .db_config.port, " -U ", .db_config.user, .db_config.db] | join(" ")' < ${CONFIG} | sed 's/"//g')

echo "[$(date "${DATEFMT}")] DB Cleanup job"
for TABLE in ${TABLES}
do
    DELETE_QUERY="DELETE FROM ${TABLE} WHERE ts < DATE_TRUNC('${RETENTION_UNIT}', NOW() - INTERVAL '${RETENTION_PERIOD} ${RETENTION_UNIT}s');"
    echo "[$(date "${DATEFMT}")] Executing query: ${DELETE_QUERY}"
    echo "${DELETE_QUERY}" | PGPASSWORD=$(jq '.db_config.pass' < ${CONFIG} | sed 's/"//g') ${PSQL}
done

