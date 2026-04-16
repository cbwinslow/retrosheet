#!/usr/bin/env bash

# Backup all database objects (procedures, functions, views, materialized views)
# and schema definitions to a timestamped SQL dump. This script is intended to be
# run from the project root after the virtual environment is activated.

set -euo pipefail

# Configuration
DB_NAME=${RETROSHEET_DB:-retrosheet}
BACKUP_DIR=${RETROSHEET_BACKUP_DIR:-"$(pwd)/backups"}
TIMESTAMP=$(date +"%Y%m%dT%H%M%SZ")
FILE="${BACKUP_DIR}/db_objects_${TIMESTAMP}.sql"

mkdir -p "${BACKUP_DIR}"

echo "Backing up database objects from \"${DB_NAME}\" to \"${FILE}\""

# Dump schema objects (functions, procedures, views, materialized views) without data
pg_dump \
  --dbname="${DB_NAME}" \
  --schema-only \
  --no-owner \
  --no-privileges \
  --exclude-table-data='*' \
  --file="${FILE}"

echo "Backup completed successfully."
