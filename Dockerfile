# GarminSync Dockerfile - Pure Go Implementation
FROM golang:1.22.0-alpine3.19 AS builder

# Create working directory
WORKDIR /app

# Set Go module permissions and install Git
RUN mkdir -p /go/pkg/mod && \
    chown -R 1000:1000 /go && \
    chmod -R 777 /go/pkg/mod && \
    apk add --no-cache git

# Copy entire project
COPY . .

# Generate checksums and download dependencies
RUN go mod tidy && go mod download

# Build the Go application
RUN CGO_ENABLED=0 go build -o /garminsync main.go

# Final stage
FROM alpine:3.19

# Create non-root user (UID 1000:1000)
RUN addgroup -S -g 1000 garminsync && \
    adduser -S -u 1000 -G garminsync garminsync

# Create data directory for FIT files and set permissions
RUN mkdir -p /data && chown garminsync:garminsync /data

# Copy the built Go binary from the builder stage
COPY --from=builder /garminsync /garminsync

# Set the working directory
WORKDIR /data

# Switch to non-root user
USER garminsync

# Set the entrypoint to the binary
ENTRYPOINT ["/garminsync"]
# Default command (can be overridden)
CMD ["--help"]
