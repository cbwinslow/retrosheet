#!/usr/bin/env bash

# Backup all .sql files from the project's sql directory to a timestamped folder.
# This ensures the full database schema is version‑controlled in Git.

set -euo pipefail

# Directory containing the source SQL files
SQL_SRC_DIR="$(pwd)/sql"
# Destination root for backups (can be overridden via env var)
BACKUP_ROOT="${RETROSHEET_SQL_BACKUP_DIR:-$(pwd)/sql_backups}"
TIMESTAMP=$(date +"%Y%m%dT%H%M%SZ")
DEST_DIR="${BACKUP_ROOT}/${TIMESTAMP}"

mkdir -p "${DEST_DIR}"

echo "Backing up SQL schema files from ${SQL_SRC_DIR} to ${DEST_DIR}"

# Copy all .sql files preserving directory structure
rsync -av --include='*.sql' --exclude='*' "${SQL_SRC_DIR}/" "${DEST_DIR}/"

echo "Backup completed successfully."
