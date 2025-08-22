build:
    docker build -t garminsync .

run_server:
    just build
    docker run -d --rm --env-file .env -v $(pwd)/data:/app/data -p 8888:8080 --name garminsync garminsync daemon --start

run_server_live:
    just build
    docker run --rm --env-file .env -v $(pwd)/data:/app/data -p 8888:8080 --name garminsync garminsync daemon --start

stop_server:
    docker stop garminsync
    docker rm garminsync