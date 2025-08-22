#!/bin/bash

# Run database migrations
echo "Running database migrations..."
export ALEMBIC_CONFIG=./migrations/alembic.ini
export ALEMBIC_SCRIPT_LOCATION=./migrations/versions
alembic upgrade head
if [ $? -ne 0 ]; then
    echo "Migration failed!" >&2
    exit 1
fi

# Start the application
echo "Starting application..."
exec python -m garminsync.cli daemon --start
sleep infinity
