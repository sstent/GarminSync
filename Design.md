# **GarminSync Application Design (Python Version)**

## **Basic Info**

**App Name:** GarminSync  
**What it does:** A CLI application that downloads `.fit` files for every activity in Garmin Connect.

-----

## **Core Features**

### **CLI Mode (Current)**
1. List all activities (`garminsync list --all`)
2. List activities that have not been downloaded (`garminsync list --missing`)
3. List activities that have been downloaded (`garminsync list --downloaded`)
4. Download all missing activities (`garminsync download --missing`)

### **Enhanced Features (New)**
5. **Offline Mode**: List activities without polling Garmin Connect (`garminsync list --missing --offline`)
6. **Daemon Mode**: Run as background service with scheduled downloads (`garminsync daemon --start`)
7. **Web UI**: Browser-based interface for daemon monitoring and configuration (`http://localhost:8080`)

-----

## **Tech Stack 🐍**

* **Frontend:** CLI (**Python**)
* **Backend:** **Python**
* **Database:** SQLite (`garmin.db`)
* **Hosting:** Docker container
* **Key Libraries:**
    * **`python-garminconnect`**: The library for Garmin Connect API communication.
    * **`typer`**: A modern and easy-to-use CLI framework (built on `click`).
    * **`python-dotenv`**: For loading credentials from a `.env` file.
    * **`sqlalchemy`**: A robust ORM for database interaction and schema management.
    * **`tqdm`**: For creating user-friendly progress bars.
    * **`fastapi`**: Modern web framework for the daemon web UI.
    * **`uvicorn`**: ASGI server for running the FastAPI web interface.
    * **`apscheduler`**: Advanced Python Scheduler for daemon mode scheduling.
    * **`pydantic`**: Data validation and settings management for configuration.
    * **`jinja2`**: Template engine for web UI rendering.

-----

## **Data Structure**

The application uses SQLAlchemy ORM with expanded models for daemon functionality:

**SQLAlchemy Models (`database.py`):**

```python
class Activity(Base):
    __tablename__ = 'activities'
    
    activity_id = Column(Integer, primary_key=True)
    start_time = Column(String, nullable=False)
    filename = Column(String, unique=True, nullable=True)
    downloaded = Column(Boolean, default=False, nullable=False)
    created_at = Column(String, nullable=False)  # When record was added
    last_sync = Column(String, nullable=True)    # Last successful sync

class DaemonConfig(Base):
    __tablename__ = 'daemon_config'
    
    id = Column(Integer, primary_key=True, default=1)
    enabled = Column(Boolean, default=True, nullable=False)
    schedule_cron = Column(String, default="0 */6 * * *", nullable=False)  # Every 6 hours
    last_run = Column(String, nullable=True)
    next_run = Column(String, nullable=True)
    status = Column(String, default="stopped", nullable=False)  # stopped, running, error

class SyncLog(Base):
    __tablename__ = 'sync_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(String, nullable=False)
    operation = Column(String, nullable=False)  # sync, download, daemon_start, daemon_stop
    status = Column(String, nullable=False)     # success, error, partial
    message = Column(String, nullable=True)
    activities_processed = Column(Integer, default=0, nullable=False)
    activities_downloaded = Column(Integer, default=0, nullable=False)
```

-----

## **User Flow**

### **CLI Mode (Existing)**
1. User sets up credentials in `.env` file with `GARMIN_EMAIL` and `GARMIN_PASSWORD`
2. User launches the container: `docker run -it --env-file .env -v $(pwd)/data:/app/data garminsync`
3. User runs commands like `garminsync download --missing`
4. Application syncs with Garmin Connect, shows progress bars, and downloads activities

### **Offline Mode (New)**
1. User runs `garminsync list --missing --offline` to view cached data without API calls
2. Application queries local database only, showing last known state
3. Useful for checking status without network connectivity or API rate limits

### **Daemon Mode (New)**
1. User starts daemon: `garminsync daemon --start`
2. Daemon runs in background, scheduling automatic sync/download operations
3. User accesses web UI at `http://localhost:8080` for monitoring and configuration
4. Web UI provides real-time status, logs, and schedule management
5. Daemon can be stopped with `garminsync daemon --stop` or through web UI

-----

## **File Structure**

```
/garminsync
├── garminsync/              # Main application package
│   ├── __init__.py         # Empty package file
│   ├── cli.py             # Typer CLI commands and main entrypoint
│   ├── config.py          # Configuration and environment variable loading
│   ├── database.py        # SQLAlchemy models and database operations
│   ├── garmin.py          # Garmin Connect client wrapper with robust download logic
│   ├── daemon.py          # Daemon mode implementation with APScheduler
│   ├── web/               # Web UI components
│   │   ├── __init__.py
│   │   ├── app.py         # FastAPI application setup
│   │   ├── routes.py      # API endpoints for web UI
│   │   ├── static/        # CSS, JavaScript, images
│   │   │   ├── style.css
│   │   │   └── app.js
│   │   └── templates/     # Jinja2 HTML templates
│   │       ├── base.html
│   │       ├── dashboard.html
│   │       └── config.html
│   └── utils.py           # Shared utilities and helpers
├── data/                    # Directory for downloaded .fit files and SQLite DB
├── .env                     # Stores GARMIN_EMAIL/GARMIN_PASSWORD (gitignored)
├── .gitignore              # Excludes .env file
├── Dockerfile              # Production-ready container configuration
├── Design.md               # This design document
└── requirements.txt        # Pinned Python dependencies (updated)
```

-----

## **Technical Implementation Details**

### **Architecture**
- **CLI Framework**: Uses Typer with proper type hints and validation
- **Module Separation**: Clear separation between CLI commands, database operations, and Garmin API interactions
- **Error Handling**: Comprehensive exception handling with user-friendly error messages
- **Session Management**: Proper SQLAlchemy session management with cleanup

### **Authentication & Configuration**
- Credentials loaded via `python-dotenv` from environment variables
- Configuration validation ensures required credentials are present
- Garmin client handles authentication automatically with session persistence

### **Database Operations**
- SQLite database with SQLAlchemy ORM for type safety
- Database initialization creates tables automatically
- Sync functionality reconciles local database with Garmin Connect activities
- Proper transaction management with rollback on errors

### **File Management**
- Files named with pattern: `activity_{activity_id}_{timestamp}.fit`
- Timestamp sanitized for filesystem compatibility (colons and spaces replaced)
- Downloads saved to configurable data directory
- Database tracks both download status and file paths

### **API Integration**
- **Rate Limiting**: 2-second delays between API requests to respect Garmin's servers
- **Robust Downloads**: Multiple fallback methods for downloading FIT files:
  1. Default download method
  2. Explicit 'fit' format parameter
  3. Alternative parameter names and formats
  4. Graceful fallback with detailed error reporting
- **Activity Fetching**: Configurable batch sizes (currently 1000 activities per sync)

### **User Experience**
- **Progress Indicators**: tqdm progress bars for all long-running operations
- **Informative Output**: Clear status messages and operation summaries
- **Input Validation**: Prevents invalid command combinations
- **Exit Codes**: Proper exit codes for script integration

-----

## **Development Status ✅**

### **✅ Completed Features**

#### **Phase 1: Core Infrastructure**
- [x] **Dockerfile**: Production-ready Python 3.10 container with proper layer caching
- [x] **Environment Configuration**: `python-dotenv` integration with validation
- [x] **CLI Framework**: Complete Typer implementation with type hints and help text
- [x] **Garmin Integration**: Robust `python-garminconnect` wrapper with authentication

#### **Phase 2: Activity Listing**
- [x] **Database Schema**: SQLAlchemy models with proper relationships
- [x] **Database Operations**: Session management, initialization, and sync functionality
- [x] **List Commands**: All filter options (`--all`, `--missing`, `--downloaded`) implemented
- [x] **Progress Display**: tqdm integration for user feedback during operations

#### **Phase 3: Download Pipeline**
- [x] **FIT File Downloads**: Multi-method download approach with fallback strategies
- [x] **Idempotent Operations**: Prevents re-downloading existing files
- [x] **Database Updates**: Proper status tracking and file path storage
- [x] **File Management**: Safe filename generation and directory creation

#### **Phase 4: Polish**
- [x] **Progress Bars**: Comprehensive tqdm implementation across all operations
- [x] **Error Handling**: Graceful error handling with informative messages
- [x] **Container Optimization**: Efficient Docker build with proper dependency management

### **🚧 New Features Implementation Guide**

#### **Feature 1: Offline Mode**

**Implementation Steps:**
1. **CLI Enhancement** (`cli.py`):
   ```python
   @app.command("list")
   def list_activities(
       all_activities: bool = False,
       missing: bool = False,
       downloaded: bool = False,
       offline: Annotated[bool, typer.Option("--offline", help="Work offline without syncing")] = False
   ):
       if not offline:
           # Existing sync logic
           sync_database(client)
       else:
           typer.echo("Working in offline mode - using cached data")
       
       # Rest of listing logic remains the same
   ```

2. **Database Enhancements** (`database.py`):
   - Add `last_sync` column to Activity table
   - Add utility functions for offline status checking
   ```python
   def get_offline_stats():
       """Return statistics about cached data without API calls"""
       session = get_session()
       total = session.query(Activity).count()
       downloaded = session.query(Activity).filter_by(downloaded=True).count()
       missing = total - downloaded
       last_sync = session.query(Activity).order_by(Activity.last_sync.desc()).first()
       return {
           'total': total,
           'downloaded': downloaded, 
           'missing': missing,
           'last_sync': last_sync.last_sync if last_sync else 'Never'
       }
   ```

#### **Feature 2: Daemon Mode**

**Implementation Steps:**
1. **New Daemon Module** (`daemon.py`):
   ```python
   from apscheduler.schedulers.background import BackgroundScheduler
   from apscheduler.triggers.cron import CronTrigger
   import signal
   import sys
   import time
   import threading
   from datetime import datetime
   
   class GarminSyncDaemon:
       def __init__(self):
           self.scheduler = BackgroundScheduler()
           self.running = False
           self.web_server = None
           
       def start(self, web_port=8080):
           """Start daemon with scheduler and web UI"""
           # Load configuration from database
           config = self.load_config()
           
           # Setup scheduled job
           if config.enabled:
               self.scheduler.add_job(
                   func=self.sync_and_download,
                   trigger=CronTrigger.from_crontab(config.schedule_cron),
                   id='sync_job',
                   replace_existing=True
               )
           
           # Start scheduler
           self.scheduler.start()
           self.running = True
           
           # Start web UI in separate thread
           self.start_web_ui(web_port)
           
           # Setup signal handlers for graceful shutdown
           signal.signal(signal.SIGINT, self.signal_handler)
           signal.signal(signal.SIGTERM, self.signal_handler)
           
           print(f"Daemon started. Web UI available at http://localhost:{web_port}")
           
           # Keep daemon running
           try:
               while self.running:
                   time.sleep(1)
           except KeyboardInterrupt:
               self.stop()
               
       def sync_and_download(self):
           """Scheduled job function"""
           try:
               self.log_operation("sync", "started")
               
               # Perform sync and download
               from .garmin import GarminClient
               from .database import sync_database
               
               client = GarminClient()
               activities_before = self.count_missing()
               
               sync_database(client)
               
               # Download missing activities
               downloaded_count = self.download_missing_activities(client)
               
               self.log_operation("sync", "success", 
                   f"Downloaded {downloaded_count} new activities")
               
           except Exception as e:
               self.log_operation("sync", "error", str(e))
               
       def load_config(self):
           """Load daemon configuration from database"""
           session = get_session()
           config = session.query(DaemonConfig).first()
           if not config:
               # Create default configuration
               config = DaemonConfig()
               session.add(config)
               session.commit()
           session.close()
           return config
   ```

2. **CLI Integration** (`cli.py`):
   ```python
   @app.command("daemon")
   def daemon_mode(
       start: Annotated[bool, typer.Option("--start", help="Start daemon")] = False,
       stop: Annotated[bool, typer.Option("--stop", help="Stop daemon")] = False,
       status: Annotated[bool, typer.Option("--status", help="Show daemon status")] = False,
       port: Annotated[int, typer.Option("--port", help="Web UI port")] = 8080
   ):
       """Daemon mode operations"""
       from .daemon import GarminSyncDaemon
       
       if start:
           daemon = GarminSyncDaemon()
           daemon.start(web_port=port)
       elif stop:
           # Implementation for stopping daemon (PID file or signal)
           pass
       elif status:
           # Show current daemon status
           pass
   ```

#### **Feature 3: Web UI**

**Implementation Steps:**
1. **FastAPI Application** (`web/app.py`):
   ```python
   from fastapi import FastAPI, Request
   from fastapi.staticfiles import StaticFiles
   from fastapi.templating import Jinja2Templates
   from .routes import router
   
   app = FastAPI(title="GarminSync Dashboard")
   
   # Mount static files and templates
   app.mount("/static", StaticFiles(directory="garminsync/web/static"), name="static")
   templates = Jinja2Templates(directory="garminsync/web/templates")
   
   # Include API routes
   app.include_router(router)
   
   @app.get("/")
   async def dashboard(request: Request):
       # Get current statistics
       from ..database import get_offline_stats
       stats = get_offline_stats()
       
       return templates.TemplateResponse("dashboard.html", {
           "request": request,
           "stats": stats
       })
   ```

2. **API Routes** (`web/routes.py`):
   ```python
   from fastapi import APIRouter, HTTPException
   from pydantic import BaseModel
   from ..database import get_session, DaemonConfig, SyncLog
   
   router = APIRouter(prefix="/api")
   
   class ScheduleConfig(BaseModel):
       enabled: bool
       cron_schedule: str
   
   @router.get("/status")
   async def get_status():
       """Get current daemon status"""
       session = get_session()
       config = session.query(DaemonConfig).first()
       
       # Get recent logs
       logs = session.query(SyncLog).order_by(SyncLog.timestamp.desc()).limit(10).all()
       
       return {
           "daemon": {
               "running": config.status == "running" if config else False,
               "next_run": config.next_run if config else None,
               "schedule": config.schedule_cron if config else None
           },
           "recent_logs": [
               {
                   "timestamp": log.timestamp,
                   "operation": log.operation,
                   "status": log.status,
                   "message": log.message
               } for log in logs
           ]
       }
   
   @router.post("/schedule")
   async def update_schedule(config: ScheduleConfig):
       """Update daemon schedule configuration"""
       session = get_session()
       daemon_config = session.query(DaemonConfig).first()
       
       if not daemon_config:
           daemon_config = DaemonConfig()
           session.add(daemon_config)
       
       daemon_config.enabled = config.enabled
       daemon_config.schedule_cron = config.cron_schedule
       session.commit()
       
       return {"message": "Configuration updated successfully"}
   
   @router.post("/sync/trigger")
   async def trigger_sync():
       """Manually trigger a sync operation"""
       # Implementation to trigger immediate sync
       pass
   ```

3. **HTML Templates** (`web/templates/dashboard.html`):
   ```html
   {% extends "base.html" %}
   
   {% block content %}
   <div class="container">
       <h1>GarminSync Dashboard</h1>
       
       <div class="row">
           <div class="col-md-4">
               <div class="card">
                   <div class="card-header">Statistics</div>
                   <div class="card-body">
                       <p>Total Activities: {{ stats.total }}</p>
                       <p>Downloaded: {{ stats.downloaded }}</p>
                       <p>Missing: {{ stats.missing }}</p>
                       <p>Last Sync: {{ stats.last_sync }}</p>
                   </div>
               </div>
           </div>
           
           <div class="col-md-4">
               <div class="card">
                   <div class="card-header">Daemon Status</div>
                   <div class="card-body" id="daemon-status">
                       <!-- Populated by JavaScript -->
                   </div>
               </div>
           </div>
           
           <div class="col-md-4">
               <div class="card">
                   <div class="card-header">Quick Actions</div>
                   <div class="card-body">
                       <button class="btn btn-primary" onclick="triggerSync()">
                           Sync Now
                       </button>
                       <button class="btn btn-secondary" onclick="toggleDaemon()">
                           Toggle Daemon
                       </button>
                   </div>
               </div>
           </div>
       </div>
       
       <div class="row mt-4">
           <div class="col-12">
               <div class="card">
                   <div class="card-header">Recent Activity</div>
                   <div class="card-body" id="recent-logs">
                       <!-- Populated by JavaScript -->
                   </div>
               </div>
           </div>
       </div>
       
       <div class="row mt-4">
           <div class="col-12">
               <div class="card">
                   <div class="card-header">Schedule Configuration</div>
                   <div class="card-body">
                       <form id="schedule-form">
                           <div class="form-group">
                               <label for="schedule-enabled">Enable Scheduled Sync</label>
                               <input type="checkbox" id="schedule-enabled">
                           </div>
                           <div class="form-group">
                               <label for="cron-schedule">Cron Schedule</label>
                               <input type="text" class="form-control" id="cron-schedule" 
                                      placeholder="0 */6 * * *" title="Every 6 hours">
                           </div>
                           <button type="submit" class="btn btn-primary">
                               Update Schedule
                           </button>
                       </form>
                   </div>
               </div>
           </div>
       </div>
   </div>
   {% endblock %}
   ```

4. **JavaScript for Interactivity** (`web/static/app.js`):
   ```javascript
   // Auto-refresh dashboard data
   setInterval(updateStatus, 30000); // Every 30 seconds
   
   async function updateStatus() {
       try {
           const response = await fetch('/api/status');
           const data = await response.json();
           
           // Update daemon status
           document.getElementById('daemon-status').innerHTML = `
               <p>Status: <span class="badge ${data.daemon.running ? 'badge-success' : 'badge-danger'}">
                   ${data.daemon.running ? 'Running' : 'Stopped'}
               </span></p>
               <p>Next Run: ${data.daemon.next_run || 'Not scheduled'}</p>
               <p>Schedule: ${data.daemon.schedule || 'Not configured'}</p>
           `;
           
           // Update recent logs
           const logsHtml = data.recent_logs.map(log => `
               <div class="log-entry">
                   <small class="text-muted">${log.timestamp}</small>
                   <span class="badge badge-${log.status === 'success' ? 'success' : 'danger'}">
                       ${log.status}
                   </span>
                   ${log.operation}: ${log.message || ''}
               </div>
           `).join('');
           
           document.getElementById('recent-logs').innerHTML = logsHtml;
           
       } catch (error) {
           console.error('Failed to update status:', error);
       }
   }
   
   async function triggerSync() {
       try {
           await fetch('/api/sync/trigger', { method: 'POST' });
           alert('Sync triggered successfully');
           updateStatus();
       } catch (error) {
           alert('Failed to trigger sync');
       }
   }
   
   // Initialize on page load
   document.addEventListener('DOMContentLoaded', updateStatus);
   ```

### **Updated Requirements** (`requirements.txt`):
```
typer==0.9.0
click==8.1.7
python-dotenv==1.0.0
garminconnect==0.2.28
sqlalchemy==2.0.23
tqdm==4.66.1
fastapi==0.104.1
uvicorn[standard]==0.24.0
apscheduler==3.10.4
pydantic==2.5.0
jinja2==3.1.2
python-multipart==0.0.6
aiofiles==23.2.1
```

### **Docker Updates**:
```dockerfile
# Expose web UI port
EXPOSE 8080

# Update entrypoint to support daemon mode
ENTRYPOINT ["python", "-m", "garminsync.cli"]
CMD ["--help"]
```

### **Usage Examples**:

**Offline Mode:**
```bash
# List missing activities without network calls
docker run --env-file .env -v $(pwd)/data:/app/data garminsync list --missing --offline
```

**Daemon Mode:**
```bash
# Start daemon with web UI on port 8080
docker run -d --env-file .env -v $(pwd)/data:/app/data -p 8080:8080 garminsync daemon --start

# Access web UI at http://localhost:8080
```

-----

## **Docker Usage**

### **Build the Container**
```bash
docker build -t garminsync .
```

### **Run with Environment File**
```bash
docker run -it --env-file .env -v $(pwd)/data:/app/data garminsync --help
```

### **Example Commands**
```bash
# List all activities
docker run -it --env-file .env -v $(pwd)/data:/app/data garminsync list --all

# Download missing activities
docker run -it --env-file .env -v $(pwd)/data:/app/data garminsync download --missing
```

-----

## **Environment Setup**

Create a `.env` file in the project root:
```
GARMIN_EMAIL=your_email@example.com
GARMIN_PASSWORD=your_password
```

-----

## **Key Implementation Highlights**

### **Robust Download Logic**
The `garmin.py` module implements a sophisticated download strategy that tries multiple methods to handle variations in the Garmin Connect API:

```python
methods_to_try = [
    lambda: self.client.download_activity(activity_id),
    lambda: self.client.download_activity(activity_id, fmt='fit'),
    lambda: self.client.download_activity(activity_id, format='fit'),
    # ... additional fallback methods
]
```

### **Database Synchronization**
The sync process efficiently updates the local database with new activities from Garmin Connect:

```python
def sync_database(garmin_client):
    """Sync local database with Garmin Connect activities"""
    activities = garmin_client.get_activities(0, 1000)
    for activity in activities:
        # Only add new activities, preserve existing download status
        existing = session.query(Activity).filter_by(activity_id=activity_id).first()
        if not existing:
            new_activity = Activity(...)
            session.add(new_activity)
```

### **CLI Integration**
Clean separation between CLI interface and business logic with proper type annotations:

```python
def list_activities(
    all_activities: Annotated[bool, typer.Option("--all", help="List all activities")] = False,
    missing: Annotated[bool, typer.Option("--missing", help="List missing activities")] = False,
    downloaded: Annotated[bool, typer.Option("--downloaded", help="List downloaded activities")] = False
):
```

-----

## **Documentation 📚**

Here are links to the official documentation for the key libraries used:

* **Garmin API:** [python-garminconnect](https://github.com/cyberjunky/python-garminconnect)
* **CLI Framework:** [Typer](https://typer.tiangolo.com/)
* **Environment Variables:** [python-dotenv](https://github.com/theskumar/python-dotenv)
* **Database ORM:** [SQLAlchemy](https://docs.sqlalchemy.org/en/20/)
* **Progress Bars:** [tqdm](https://github.com/tqdm/tqdm)

-----

## **Performance Considerations**

- **Rate Limiting**: 2-second delays between API requests prevent server overload
- **Batch Processing**: Fetches up to 1000 activities per sync operation
- **Efficient Queries**: Database queries optimized for filtering operations
- **Memory Management**: Proper session cleanup and resource management
- **Docker Optimization**: Layer caching and minimal base image for faster builds