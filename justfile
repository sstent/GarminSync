# GarminSync project tasks

# Build container image
build:
    docker build -t garminsync .

# Run server in development mode with live reload (container-based)
dev:
    just build
    docker run -it --rm --env-file .env -v $(pwd)/garminsync:/app/garminsync -v $(pwd)/data:/app/data -p 8888:8888 --name garminsync-dev garminsync uvicorn garminsync.web.app:app --reload --host 0.0.0.0 --port 8080

# Run database migrations with enhanced logging (container-based)
migrate:
    just build
    docker run --rm --env-file .env -v $(pwd)/data:/app/data --entrypoint "python" garminsync -m garminsync.cli migrate
# Run validation tests (container-based)
test:
    just build
    docker run --rm --env-file .env -v $(pwd)/tests:/app/tests -v $(pwd)/data:/app/data --entrypoint "pytest" garminsync /app/tests

# View logs of running container
logs:
    docker logs garminsync

# Access container shell
shell:
    docker exec -it garminsync /bin/bash

# Run linter (container-based)
lint:
    just build
    docker run --rm -v $(pwd)/garminsync:/app/garminsync --entrypoint "pylint" garminsync garminsync/

# Run formatter (container-based)
format:
    black garminsync/
    isort garminsync/
    just build

# Start production server
run_server:
    cd ~/GarminSync/docker
    docker compose up --build

# Stop production server
stop_server:
    docker stop garminsync

# Run server in live mode for debugging
run_server_live:
    just build
    docker run -it --rm --env-file .env -e RUN_MIGRATIONS=1 -v $(pwd)/data:/app/data -p 8888:8888 --name garminsync garminsync daemon --start

# Clean up any existing container
cleanup:
    docker stop garminsync
    docker rm garminsync
