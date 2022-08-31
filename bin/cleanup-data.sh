#!/bin/bash

DATA_DIR='/var/minieliot/data'
DAYS=30
DATEFMT='+%Y-%m-%d %H:%M:%S'

echo "[$(date "${DATEFMT}")] Data files cleanup job"
echo "[$(date "${DATEFMT}")] Deleting files (list may be empty):"
find ${DATA_DIR} -type f -name '*.log' -mtime ${DAYS} | xargs -i rm -v {}
echo "[$(date "${DATEFMT}")] Job completed"

