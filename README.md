# GarminSync

GarminSync is a powerful Python application that automatically downloads `.fit` files for all your activities from Garmin Connect. It provides both a command-line interface for manual operations and a daemon mode for automatic background synchronization with a web-based dashboard for monitoring and configuration.

## Features

- **CLI Interface**: List and download activities with flexible filtering options
- **Daemon Mode**: Automatic background synchronization with configurable schedules
- **Web Dashboard**: Real-time monitoring and configuration through a web interface
- **Offline Mode**: Work with cached data without internet connectivity
- **Database Tracking**: SQLite database to track download status and file locations
- **Rate Limiting**: Respects Garmin Connect's servers with built-in rate limiting

## Technology Stack

- **Backend**: Python 3.10 with SQLAlchemy ORM
- **CLI Framework**: Typer for command-line interface
- **Web Framework**: FastAPI with Jinja2 templates
- **Database**: SQLite for local data storage
- **Scheduling**: APScheduler for daemon mode scheduling
- **Containerization**: Docker support for easy deployment

## Installation

### Prerequisites

- Docker (recommended) OR Python 3.10+
- Garmin Connect account credentials

### Using Docker (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/sstent/GarminSync.git
   cd GarminSync
   ```

2. Create a `.env` file with your Garmin credentials:
   ```bash
   echo "GARMIN_EMAIL=your_email@example.com" > .env
   echo "GARMIN_PASSWORD=your_password" >> .env
   ```

3. Build the Docker image:
   ```bash
   docker build -t garminsync .
   ```

### Using Python Directly

1. Clone the repository:
   ```bash
   git clone https://github.com/sstent/GarminSync.git
   cd GarminSync
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your Garmin credentials:
   ```bash
   echo "GARMIN_EMAIL=your_email@example.com" > .env
   echo "GARMIN_PASSWORD=your_password" >> .env
   ```

## Usage

### CLI Commands

List all activities:
```bash
# Using Docker
docker run -it --env-file .env -v $(pwd)/data:/app/data garminsync list --all

# Using Python directly
python -m garminsync.cli list --all
```

List missing activities:
```bash
# Using Docker
docker run -it --env-file .env -v $(pwd)/data:/app/data garminsync list --missing

# Using Python directly
python -m garminsync.cli list --missing
```

List downloaded activities:
```bash
# Using Docker
docker run -it --env-file .env -v $(pwd)/data:/app/data garminsync list --downloaded

# Using Python directly
python -m garminsync.cli list --downloaded
```

Download missing activities:
```bash
# Using Docker
docker run -it --env-file .env -v $(pwd)/data:/app/data garminsync download --missing

# Using Python directly
python -m garminsync.cli download --missing
```

Work offline (without syncing with Garmin Connect):
```bash
# Using Docker
docker run -it --env-file .env -v $(pwd)/data:/app/data garminsync list --missing --offline

# Using Python directly
python -m garminsync.cli list --missing --offline
```

### Daemon Mode

Start the daemon with web UI:
```bash
# Using Docker (expose port 8080 for web UI)
docker run -it --env-file .env -v $(pwd)/data:/app/data -p 8080:8080 garminsync daemon --start

# Using Python directly
python -m garminsync.cli daemon --start
```

Access the web dashboard at `http://localhost:8080`

### Web Interface

The web interface provides real-time monitoring and configuration capabilities:

1. **Dashboard**: View activity statistics, daemon status, and recent logs
2. **Activities**: Browse all activities with detailed information in a sortable table
3. **Logs**: Filter and browse synchronization logs with pagination
4. **Configuration**: Manage daemon settings and scheduling

## Configuration

### Environment Variables

Create a `.env` file in the project root with your Garmin Connect credentials:

```env
GARMIN_EMAIL=your_email@example.com
GARMIN_PASSWORD=your_password
```

### Daemon Scheduling

The daemon uses cron-style scheduling. Configure the schedule through the web UI or by modifying the database directly. Default schedule is every 6 hours (`0 */6 * * *`).

### Data Storage

Downloaded `.fit` files and the SQLite database are stored in the `data/` directory by default. When using Docker, this directory is mounted as a volume to persist data between container runs.

## Web API Endpoints

The web interface provides RESTful API endpoints for programmatic access:

- `GET /api/status` - Get daemon status and recent logs
- `GET /api/activities/stats` - Get activity statistics
- `GET /api/activities` - Get paginated activities with filtering
- `GET /api/activities/{activity_id}` - Get detailed activity information
- `GET /api/dashboard/stats` - Get comprehensive dashboard statistics
- `GET /api/logs` - Get filtered and paginated logs
- `POST /api/sync/trigger` - Manually trigger synchronization
- `POST /api/schedule` - Update daemon schedule configuration
- `POST /api/daemon/start` - Start the daemon
- `POST /api/daemon/stop` - Stop the daemon
- `DELETE /api/logs` - Clear all logs

## Development

### Project Structure

```
garminsync/
├── garminsync/              # Main application package
│   ├── cli.py              # Command-line interface
│   ├── config.py           # Configuration management
│   ├── database.py         # Database models and operations
│   ├── garmin.py           # Garmin Connect client wrapper
│   ├── daemon.py           # Daemon mode implementation
│   └── web/                # Web interface components
│       ├── app.py          # FastAPI application setup
│       ├── routes.py       # API endpoints
│       ├── static/         # CSS, JavaScript files
│       └── templates/      # HTML templates
├── data/                   # Downloaded files and database
├── .env                    # Environment variables (gitignored)
├── Dockerfile              # Docker configuration
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

### Running Tests

(Add test instructions when tests are implemented)

## Known Limitations

- No support for two-factor authentication (2FA)
- Limited automatic retry logic for failed downloads
- No support for selective activity date range downloads

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and feature requests, please use the GitHub issue tracker.
