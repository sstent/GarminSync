#!/bin/bash

# Conditionally run database migrations
if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    echo "$(date) - Starting database migrations..."
    echo "ALEMBIC_CONFIG: ${ALEMBIC_CONFIG:-/app/migrations/alembic.ini}"
    echo "ALEMBIC_SCRIPT_LOCATION: ${ALEMBIC_SCRIPT_LOCATION:-/app/migrations/versions}"
    
    # Run migrations with timing
    start_time=$(date +%s)
    export ALEMBIC_CONFIG=${ALEMBIC_CONFIG:-/app/migrations/alembic.ini}
    export ALEMBIC_SCRIPT_LOCATION=${ALEMBIC_SCRIPT_LOCATION:-/app/migrations/versions}
    alembic upgrade head
    migration_status=$?
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    if [ $migration_status -ne 0 ]; then
        echo "$(date) - Migration failed after ${duration} seconds!" >&2
        exit 1
    else
        echo "$(date) - Migrations completed successfully in ${duration} seconds"
    fi
else
    echo "$(date) - Skipping database migrations (RUN_MIGRATIONS=${RUN_MIGRATIONS})"
fi

# Start the application
echo "$(date) - Starting application..."
exec python -m garminsync.cli daemon --start --port 8888
sleep infinity
