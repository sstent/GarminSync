# **GarminSync Application Design (Python Version)**

## **Basic Info**

**App Name:** GarminSync  
**What it does:** A CLI application that downloads `.fit` files for every activity in Garmin Connect.

-----

## **Core Features**

### **CLI Mode (Implemented)**
1. List all activities (`garminsync list --all`)
2. List activities that have not been downloaded (`garminsync list --missing`)
3. List activities that have been downloaded (`garminsync list --downloaded`)
4. Download all missing activities (`garminsync download --missing`)

### **Enhanced Features (Implemented)**
5. **Offline Mode**: List activities without polling Garmin Connect (`garminsync list --missing --offline`)
6. **Daemon Mode**: Run as background service with scheduled downloads (`garminsync daemon --start`)
7. **Web UI**: Browser-based interface for daemon monitoring and configuration (`http://localhost:8080`)

-----

## **Tech Stack 🐍**

* **Frontend:** CLI (**Python** with Typer) + Web UI (FastAPI + Jinja2)
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

### **CLI Mode (Implemented)**
1. User sets up credentials in `.env` file with `GARMIN_EMAIL` and `GARMIN_PASSWORD`
2. User launches the container: `docker run -it --env-file .env -v $(pwd)/data:/app/data garminsync`
3. User runs commands like `garminsync download --missing`
4. Application syncs with Garmin Connect, shows progress bars, and downloads activities

### **Offline Mode (Implemented)**
1. User runs `garminsync list --missing --offline` to view cached data without API calls
2. Application queries local database only, showing last known state
3. Useful for checking status without network connectivity or API rate limits

### **Daemon Mode (Implemented)**
1. User starts daemon: `garminsync daemon` (runs continuously in foreground)
2. Daemon automatically starts web UI and background scheduler
3. User accesses web UI at `http://localhost:8080` for monitoring and configuration
4. Web UI provides real-time status, logs, and schedule management
5. Daemon can be stopped with `Ctrl+C` or through web UI stop functionality

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
│   ├── utils.py           # Shared utilities and helpers
│   └── web/               # Web UI components
│       ├── __init__.py
│       ├── app.py         # FastAPI application setup
│       ├── routes.py      # API endpoints for web UI
│       ├── static/        # CSS, JavaScript, images
│       │   ├── style.css
│       │   └── app.js
│       └── templates/     # Jinja2 HTML templates
│           ├── base.html
│           ├── dashboard.html
│           └── config.html
├── data/                    # Directory for downloaded .fit files and SQLite DB
├── .env                     # Stores GARMIN_EMAIL/GARMIN_PASSWORD (gitignored)
├── .gitignore              # Excludes .env file and data directory
├── Dockerfile              # Production-ready container configuration
├── Design.md               # This design document
├── plan.md                 # Implementation notes and fixes
└── requirements.txt        # Python dependencies with compatibility fixes
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

#### **Phase 4: Enhanced Features**
- [x] **Offline Mode**: List activities without API calls using cached data
- [x] **Daemon Mode**: Background service with APScheduler for automatic sync
- [x] **Web UI**: FastAPI-based dashboard with real-time monitoring
- [x] **Schedule Configuration**: Configurable cron-based sync schedules
- [x] **Activity Logs**: Comprehensive logging of sync operations

#### **Phase 5: Web Interface**
- [x] **Dashboard**: Real-time statistics and daemon status monitoring
- [x] **API Routes**: RESTful endpoints for configuration and control
- [x] **Templates**: Responsive HTML templates with Bootstrap styling
- [x] **JavaScript Integration**: Auto-refreshing status and interactive controls
- [x] **Configuration Management**: Web-based daemon settings and schedule updates

### **🔧 Recent Fixes and Improvements**

#### **Dependency Management**
- [x] **Pydantic Compatibility**: Fixed version constraints to avoid conflicts with `garth`
- [x] **Requirements Lock**: Updated to `pydantic>=2.0.0,<2.5.0` for stability
- [x] **Package Versions**: Verified compatibility across all dependencies

#### **Code Quality Fixes**
- [x] **Missing Fields**: Added `created_at` field to Activity model and sync operations
- [x] **Import Issues**: Resolved circular import problems in daemon module
- [x] **Error Handling**: Improved exception handling and logging throughout
- [x] **Method Names**: Corrected method calls and parameter names

#### **Web UI Enhancements**
- [x] **Template Safety**: Added fallback handling for missing template files
- [x] **API Error Handling**: Improved error responses and status codes
- [x] **JavaScript Functions**: Added missing daemon control functions
- [x] **Status Updates**: Real-time status updates with proper data formatting

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

# List missing activities offline
docker run -it --env-file .env -v $(pwd)/data:/app/data garminsync list --missing --offline

# Download missing activities
docker run -it --env-file .env -v $(pwd)/data:/app/data garminsync download --missing

# Start daemon with web UI
docker run -it --env-file .env -v $(pwd)/data:/app/data -p 8080:8080 garminsync daemon
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
            new_activity = Activity(
                activity_id=activity_id,
                start_time=start_time,
                downloaded=False,
                created_at=datetime.now().isoformat(),
                last_sync=datetime.now().isoformat()
            )
            session.add(new_activity)
```

### **Daemon Implementation**
The daemon uses APScheduler for reliable background task execution:

```python
class GarminSyncDaemon:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.running = False
        self.web_server = None
        
    def start(self, web_port=8080):
        config_data = self.load_config()
        if config_data['enabled']:
            self.scheduler.add_job(
                func=self.sync_and_download,
                trigger=CronTrigger.from_crontab(config_data['schedule_cron']),
                id='sync_job',
                replace_existing=True
            )
```

### **Web API Integration**
FastAPI provides RESTful endpoints for daemon control and monitoring:

```python
@router.get("/status")
async def get_status():
    """Get current daemon status with logs"""
    config = session.query(DaemonConfig).first()
    logs = session.query(SyncLog).order_by(SyncLog.timestamp.desc()).limit(10).all()
    return {
        "daemon": {"running": config.status == "running"},
        "recent_logs": [{"timestamp": log.timestamp, "status": log.status} for log in logs]
    }
```

-----

## **Known Issues & Limitations**

### **Current Limitations**
1. **Web Interface**: Some components need completion (detailed below)
2. **Error Recovery**: Limited automatic retry logic for failed downloads
3. **Batch Processing**: No support for selective activity date range downloads
4. **Authentication**: No support for two-factor authentication (2FA)

### **Dependency Issues Resolved**
- ✅ **Pydantic Conflicts**: Fixed version constraints to avoid `garth` compatibility issues
- ✅ **Missing Fields**: Added all required database fields
- ✅ **Import Errors**: Resolved circular import problems

-----

## **Performance Considerations**

- **Rate Limiting**: 2-second delays between API requests prevent server overload
- **Batch Processing**: Fetches up to 1000 activities per sync operation
- **Efficient Queries**: Database queries optimized for filtering operations
- **Memory Management**: Proper session cleanup and resource management
- **Docker Optimization**: Layer caching and minimal base image for faster builds
- **Background Processing**: Daemon mode prevents blocking CLI operations

-----

## **Security Considerations**

- **Credential Storage**: Environment variables prevent hardcoded credentials
- **File Permissions**: Docker container runs with appropriate user permissions
- **API Rate Limiting**: Respects Garmin Connect rate limits to prevent account restrictions
- **Error Logging**: Sensitive information excluded from logs and error messages

-----

## **Documentation 📚**

Here are links to the official documentation for the key libraries used:

* **Garmin API:** [python-garminconnect](https://github.com/cyberjunky/python-garminconnect)
* **CLI Framework:** [Typer](https://typer.tiangolo.com/)
* **Environment Variables:** [python-dotenv](https://github.com/theskumar/python-dotenv)
* **Database ORM:** [SQLAlchemy](https://docs.sqlalchemy.org/en/20/)
* **Progress Bars:** [tqdm](https://github.com/tqdm/tqdm)
* **Web Framework:** [FastAPI](https://fastapi.tiangolo.com/)
* **Task Scheduler:** [APScheduler](https://apscheduler.readthedocs.io/)

-----

## **Web Interface Implementation Steps**

### **🎯 Missing Components to Complete**

#### **1. Enhanced Dashboard Components**

**A. Real-time Activity Counter**
- **File:** `garminsync/web/templates/dashboard.html`
- **Implementation:**
  ```html
  <div class="col-md-3">
      <div class="card bg-info text-white">
          <div class="card-body">
              <h4 id="sync-status">Idle</h4>
              <p>Current Operation</p>
          </div>
      </div>
  </div>
  ```
- **JavaScript Update:** Add WebSocket or periodic updates for sync status

**B. Activity Progress Charts**
- **File:** Add Chart.js to `garminsync/web/static/charts.js`
- **Implementation:**
  ```javascript
  // Add to dashboard
  const ctx = document.getElementById('activityChart').getContext('2d');
  const chart = new Chart(ctx, {
      type: 'doughnut',
      data: {
          labels: ['Downloaded', 'Missing'],
          datasets: [{
              data: [downloaded, missing],
              backgroundColor: ['#28a745', '#dc3545']
          }]
      }
  });
  ```

#### **2. Enhanced Configuration Page**

**A. Advanced Schedule Options**
- **File:** `garminsync/web/templates/config.html`
- **Add Preset Schedules:**
  ```html
  <div class="form-group">
      <label>Quick Schedule Presets</label>
      <select id="schedule-presets" class="form-control">
          <option value="">Custom</option>
          <option value="0 */1 * * *">Every Hour</option>
          <option value="0 */6 * * *">Every 6 Hours</option>
          <option value="0 0 * * *">Daily at Midnight</option>
          <option value="0 0 * * 0">Weekly (Sundays)</option>
      </select>
  </div>
  ```

**B. Notification Settings**
- **New Model in `database.py`:**
  ```python
  class NotificationConfig(Base):
      __tablename__ = 'notification_config'
      
      id = Column(Integer, primary_key=True)
      email_enabled = Column(Boolean, default=False)
      email_address = Column(String, nullable=True)
      webhook_enabled = Column(Boolean, default=False)
      webhook_url = Column(String, nullable=True)
      notify_on_success = Column(Boolean, default=True)
      notify_on_error = Column(Boolean, default=True)
  ```

#### **3. Comprehensive Logs Page**

**A. Create Dedicated Logs Page**
- **File:** `garminsync/web/templates/logs.html`
- **Implementation:**
  ```html
  {% extends "base.html" %}
  
  {% block content %}
  <div class="container">
      <div class="d-flex justify-content-between align-items-center mb-4">
          <h1>Sync Logs</h1>
          <div>
              <button class="btn btn-secondary" onclick="refreshLogs()">Refresh</button>
              <button class="btn btn-warning" onclick="clearLogs()">Clear Logs</button>
          </div>
      </div>
      
      <!-- Filters -->
      <div class="card mb-4">
          <div class="card-header">Filters</div>
          <div class="card-body">
              <div class="row">
                  <div class="col-md-3">
                      <select id="status-filter" class="form-control">
                          <option value="">All Statuses</option>
                          <option value="success">Success</option>
                          <option value="error">Error</option>
                          <option value="partial">Partial</option>
                      </select>
                  </div>
                  <div class="col-md-3">
                      <select id="operation-filter" class="form-control">
                          <option value="">All Operations</option>
                          <option value="sync">Sync</option>
                          <option value="download">Download</option>
                          <option value="daemon">Daemon</option>
                      </select>
                  </div>
                  <div class="col-md-3">
                      <input type="date" id="date-filter" class="form-control">
                  </div>
                  <div class="col-md-3">
                      <button class="btn btn-primary" onclick="applyFilters()">Apply</button>
                  </div>
              </div>
          </div>
      </div>
      
      <!-- Logs Table -->
      <div class="card">
          <div class="card-header">Log Entries</div>
          <div class="card-body">
              <div class="table-responsive">
                  <table class="table table-striped" id="logs-table">
                      <thead>
                          <tr>
                              <th>Timestamp</th>
                              <th>Operation</th>
                              <th>Status</th>
                              <th>Message</th>
                              <th>Activities</th>
                          </tr>
                      </thead>
                      <tbody id="logs-tbody">
                          <!-- Populated by JavaScript -->
                      </tbody>
                  </table>
              </div>
              
              <!-- Pagination -->
              <nav>
                  <ul class="pagination justify-content-center" id="pagination">
                      <!-- Populated by JavaScript -->
                  </ul>
              </nav>
          </div>
      </div>
  </div>
  {% endblock %}
  ```

**B. Enhanced Logs API**
- **File:** `garminsync/web/routes.py`
- **Add Filtering and Pagination:**
  ```python
  @router.get("/logs")
  async def get_logs(
      limit: int = 50,
      offset: int = 0,
      status: str = None,
      operation: str = None,
      date: str = None
  ):
      """Get logs with filtering and pagination"""
      session = get_session()
      try:
          query = session.query(SyncLog)
          
          # Apply filters
          if status:
              query = query.filter(SyncLog.status == status)
          if operation:
              query = query.filter(SyncLog.operation == operation)
          if date:
              # Filter by date (assuming ISO format)
              query = query.filter(SyncLog.timestamp.like(f"{date}%"))
          
          # Get total count for pagination
          total = query.count()
          
          # Apply pagination
          logs = query.order_by(SyncLog.timestamp.desc()).offset(offset).limit(limit).all()
          
          return {
              "logs": [log_to_dict(log) for log in logs],
              "total": total,
              "limit": limit,
              "offset": offset
          }
      finally:
          session.close()
  
  def log_to_dict(log):
      return {
          "id": log.id,
          "timestamp": log.timestamp,
          "operation": log.operation,
          "status": log.status,
          "message": log.message,
          "activities_processed": log.activities_processed,
          "activities_downloaded": log.activities_downloaded
      }
  ```

#### **4. Activity Management Page**

**A. Create Activities Page**
- **File:** `garminsync/web/templates/activities.html`
- **Features:**
  - List all activities with status
  - Filter by date range, status, activity type
  - Bulk download options
  - Individual activity details modal

**B. Activity Details API**
- **File:** `garminsync/web/routes.py`
- **Implementation:**
  ```python
  @router.get("/activities")
  async def get_activities(
      limit: int = 100,
      offset: int = 0,
      downloaded: bool = None,
      start_date: str = None,
      end_date: str = None
  ):
      """Get activities with filtering and pagination"""
      session = get_session()
      try:
          query = session.query(Activity)
          
          if downloaded is not None:
              query = query.filter(Activity.downloaded == downloaded)
          if start_date:
              query = query.filter(Activity.start_time >= start_date)
          if end_date:
              query = query.filter(Activity.start_time <= end_date)
          
          total = query.count()
          activities = query.order_by(Activity.start_time.desc()).offset(offset).limit(limit).all()
          
          return {
              "activities": [activity_to_dict(a) for a in activities],
              "total": total,
              "limit": limit,
              "offset": offset
          }
      finally:
          session.close()
  
  @router.post("/activities/{activity_id}/download")
  async def download_single_activity(activity_id: int):
      """Download a specific activity"""
      # Implementation to download single activity
      pass
  ```

#### **5. System Status Page**

**A. Create System Status Template**
- **File:** `garminsync/web/templates/system.html`
- **Show:**
  - Database statistics
  - Disk usage
  - Memory usage
  - API rate limiting status
  - Last errors

**B. System Status API**
- **File:** `garminsync/web/routes.py`
- **Implementation:**
  ```python
  @router.get("/system/status")
  async def get_system_status():
      """Get comprehensive system status"""
      import psutil
      import os
      from pathlib import Path
      
      # Database stats
      session = get_session()
      try:
          db_stats = {
              "total_activities": session.query(Activity).count(),
              "downloaded_activities": session.query(Activity).filter_by(downloaded=True).count(),
              "total_logs": session.query(SyncLog).count(),
              "database_size": get_database_size()
          }
      finally:
          session.close()
      
      # System stats
      data_dir = Path(os.getenv("DATA_DIR", "data"))
      disk_usage = psutil.disk_usage(str(data_dir))
      
      return {
          "database": db_stats,
          "system": {
              "cpu_percent": psutil.cpu_percent(),
              "memory": psutil.virtual_memory()._asdict(),
              "disk_usage": {
                  "total": disk_usage.total,
                  "used": disk_usage.used,
                  "free": disk_usage.free
              }
          },
          "garmin_api": {
              "last_successful_call": get_last_successful_api_call(),
              "rate_limit_remaining": get_rate_limit_status()
          }
      }
  ```

#### **6. Enhanced Navigation and Layout**

**A. Update Base Template**
- **File:** `garminsync/web/templates/base.html`
- **Add Complete Navigation:**
  ```html
  <div class="collapse navbar-collapse" id="navbarNav">
      <ul class="navbar-nav">
          <li class="nav-item">
              <a class="nav-link" href="/">Dashboard</a>
          </li>
          <li class="nav-item">
              <a class="nav-link" href="/activities">Activities</a>
          </li>
          <li class="nav-item">
              <a class="nav-link" href="/logs">Logs</a>
          </li>
          <li class="nav-item">
              <a class="nav-link" href="/config">Configuration</a>
          </li>
          <li class="nav-item">
              <a class="nav-link" href="/system">System</a>
          </li>
      </ul>
      <ul class="navbar-nav ms-auto">
          <li class="nav-item">
              <span class="navbar-text" id="connection-status">
                  <i class="fas fa-circle text-success"></i> Connected
              </span>
          </li>
      </ul>
  </div>
  ```

**B. Add FontAwesome Icons**
- **Update base template with:**
  ```html
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
  ```

### **🔄 Implementation Order**

1. **Week 1: Enhanced Dashboard**
   - Add real-time counters and charts
   - Implement activity progress visualization
   - Add sync status indicators

2. **Week 2: Logs Page**
   - Create comprehensive logs template
   - Implement filtering and pagination APIs
   - Add log management features

3. **Week 3: Activities Management**
   - Build activities listing page
   - Add filtering and search capabilities
   - Implement individual activity actions

4. **Week 4: System Status & Configuration**
   - Create system monitoring page
   - Enhanced configuration options
   - Notification system setup

5. **Week 5: Polish & Testing**
   - Improve responsive design
   - Add error handling and loading states
   - Performance optimization

### **📁 New Files Needed**

```
garminsync/web/
├── templates/
│   ├── activities.html        # New: Activity management
│   ├── logs.html             # New: Enhanced logs page
│   └── system.html           # New: System status
├── static/
│   ├── charts.js             # New: Chart.js integration
│   ├── activities.js         # New: Activity management JS
│   └── system.js             # New: System monitoring JS
```

### **🛠️ Required Dependencies**

Add to `requirements.txt`:
```
psutil==5.9.6                # For system monitoring
python-dateutil==2.8.2       # For date parsing
```

This comprehensive implementation plan will transform the basic web interface into a full-featured dashboard for managing GarminSync operations.

### **Planned Features**
- **Authentication**: Support for two-factor authentication
- **Selective Sync**: Date range and activity type filtering
- **Export Options**: Support for additional export formats (GPX, TCX)
- **Notification System**: Email/webhook notifications for sync completion
- **Activity Analysis**: Basic statistics and activity summary features
- **Multi-user Support**: Support for multiple Garmin accounts
- **Cloud Storage**: Integration with cloud storage providers
- **Mobile Interface**: Responsive design improvements for mobile devices

### **Technical Improvements**
- **Health Checks**: Comprehensive health monitoring endpoints
- **Metrics**: Prometheus metrics for monitoring and alerting
- **Database Migrations**: Automatic schema migration support
- **Configuration Validation**: Enhanced validation for cron expressions and settings
- **Logging Enhancement**: Structured logging with configurable levels
- **Test Coverage**: Comprehensive unit and integration tests
- **CI/CD Pipeline**: Automated testing and deployment workflows