#!/bin/bash

# Always run database migrations with retries
echo "$(date) - Starting database migrations..."
echo "ALEMBIC_CONFIG: ${ALEMBIC_CONFIG:-/app/migrations/alembic.ini}"
echo "ALEMBIC_SCRIPT_LOCATION: ${ALEMBIC_SCRIPT_LOCATION:-/app/migrations/versions}"

max_retries=5
retry_count=0
migration_status=1

export ALEMBIC_CONFIG=${ALEMBIC_CONFIG:-/app/migrations/alembic.ini}
export ALEMBIC_SCRIPT_LOCATION=${ALEMBIC_SCRIPT_LOCATION:-/app/migrations/versions}

while [ $retry_count -lt $max_retries ] && [ $migration_status -ne 0 ]; do
    echo "Attempt $((retry_count+1))/$max_retries: Running migrations..."
    start_time=$(date +%s)
    alembic upgrade head
    migration_status=$?
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    if [ $migration_status -ne 0 ]; then
        echo "$(date) - Migration attempt failed after ${duration} seconds! Retrying..."
        retry_count=$((retry_count+1))
        sleep 2
    else
        echo "$(date) - Migrations completed successfully in ${duration} seconds"
    fi
done

if [ $migration_status -ne 0 ]; then
    echo "$(date) - Migration failed after $max_retries attempts!" >&2
    exit 1
fi

# Start the application
echo "$(date) - Starting application..."
exec python -m garminsync.cli daemon --start --port 8888
