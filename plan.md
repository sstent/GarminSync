# GarminSync Improvement Plan - Junior Developer Guide

## Overview
This plan focuses on keeping things simple while making meaningful improvements. We'll avoid complex async patterns and stick to a single-container approach.

---

## Phase 1: Fix Blocking Issues & Add GPX Support (Week 1-2)

### Problem: Sync blocks the web UI
**Current Issue:** When sync runs, users can't use the web interface.

### Solution: Simple Threading
Instead of complex async, use Python's threading module:

```python
# garminsync/daemon.py - Update sync_and_download method
import threading
from datetime import datetime

class GarminSyncDaemon:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.running = False
        self.web_server = None
        self.sync_lock = threading.Lock()  # Prevent multiple syncs
        self.sync_in_progress = False

    def sync_and_download(self):
        """Non-blocking sync job"""
        # Check if sync is already running
        if not self.sync_lock.acquire(blocking=False):
            logger.info("Sync already in progress, skipping...")
            return
            
        try:
            self.sync_in_progress = True
            self._do_sync_work()
        finally:
            self.sync_in_progress = False
            self.sync_lock.release()
    
    def _do_sync_work(self):
        """The actual sync logic (moved from sync_and_download)"""
        # ... existing sync code here ...
```

### Add GPX Parser
Create a new parser for GPX files:

```python
# garminsync/parsers/gpx_parser.py
import xml.etree.ElementTree as ET
from datetime import datetime

def parse_gpx_file(file_path):
    """Parse GPX file to extract activity metrics"""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # GPX uses different namespace
        ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
        
        # Extract basic info
        track = root.find('.//gpx:trk', ns)
        if not track:
            return None
            
        # Get track points
        track_points = root.findall('.//gpx:trkpt', ns)
        
        if not track_points:
            return None
        
        # Calculate basic metrics
        start_time = None
        end_time = None
        total_distance = 0.0
        elevations = []
        
        prev_point = None
        for point in track_points:
            # Get time
            time_elem = point.find('gpx:time', ns)
            if time_elem is not None:
                current_time = datetime.fromisoformat(time_elem.text.replace('Z', '+00:00'))
                if start_time is None:
                    start_time = current_time
                end_time = current_time
            
            # Get elevation
            ele_elem = point.find('gpx:ele', ns)
            if ele_elem is not None:
                elevations.append(float(ele_elem.text))
            
            # Calculate distance
            if prev_point is not None:
                lat1, lon1 = float(prev_point.get('lat')), float(prev_point.get('lon'))
                lat2, lon2 = float(point.get('lat')), float(point.get('lon'))
                total_distance += calculate_distance(lat1, lon1, lat2, lon2)
            
            prev_point = point
        
        # Calculate duration
        duration = None
        if start_time and end_time:
            duration = (end_time - start_time).total_seconds()
        
        return {
            "activityType": {"typeKey": "other"},  # GPX doesn't specify activity type
            "summaryDTO": {
                "duration": duration,
                "distance": total_distance,
                "maxHR": None,  # GPX rarely has HR data
                "avgPower": None,
                "calories": None
            }
        }
    except Exception as e:
        print(f"Error parsing GPX file: {e}")
        return None

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two GPS points using Haversine formula"""
    import math
    
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth's radius in meters
    earth_radius = 6371000
    return c * earth_radius
```

### Update Activity Parser
```python
# garminsync/activity_parser.py - Add GPX support
def detect_file_type(file_path):
    """Detect file format (FIT, XML, GPX, or unknown)"""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(256)  # Read more to catch GPX
            
            # Check for XML-based formats
            if b'<?xml' in header[:50]:
                if b'<gpx' in header[:200] or b'topografix.com/GPX' in header:
                    return 'gpx'
                elif b'TrainingCenterDatabase' in header:
                    return 'xml'  # TCX
                else:
                    return 'xml'  # Generic XML, assume TCX
                    
            # Check for FIT
            if len(header) >= 8 and header[4:8] == b'.FIT':
                return 'fit'
            if (len(header) >= 8 and 
                (header[0:4] == b'.FIT' or 
                 header[4:8] == b'FIT.' or 
                 header[8:12] == b'.FIT')):
                return 'fit'
                
            return 'unknown'
    except Exception as e:
        return 'error'

# Update get_activity_metrics to include GPX
def get_activity_metrics(activity, client=None):
    """Get activity metrics from local file or Garmin API"""
    metrics = None
    if activity.filename and os.path.exists(activity.filename):
        file_type = detect_file_type(activity.filename)
        if file_type == 'fit':
            metrics = parse_fit_file(activity.filename)
        elif file_type == 'xml':
            metrics = parse_xml_file(activity.filename)
        elif file_type == 'gpx':
            from .parsers.gpx_parser import parse_gpx_file
            metrics = parse_gpx_file(activity.filename)
    
    # Only call Garmin API if we don't have local file data
    if not metrics and client:
        try:
            metrics = client.get_activity_details(activity.activity_id)
        except Exception:
            pass
    return metrics
```

---

## Phase 2: Better File Storage & Reduce API Calls (Week 3-4)

### Problem: We're calling Garmin API unnecessarily when we have the file

### Solution: Smart Caching Strategy

```python
# garminsync/database.py - Add file-first approach
def sync_database(garmin_client):
    """Sync local database with Garmin Connect activities"""
    session = get_session()
    try:
        # Get activities list from Garmin (lightweight call)
        activities = garmin_client.get_activities(0, 1000)

        if not activities:
            print("No activities returned from Garmin API")
            return

        for activity_data in activities:
            activity_id = activity_data.get("activityId")
            start_time = activity_data.get("startTimeLocal")
            
            if not activity_id or not start_time:
                continue

            existing = session.query(Activity).filter_by(activity_id=activity_id).first()
            
            if not existing:
                activity = Activity(
                    activity_id=activity_id,
                    start_time=start_time,
                    downloaded=False,
                    created_at=datetime.now().isoformat(),
                    last_sync=datetime.now().isoformat(),
                )
                session.add(activity)
                session.flush()
            else:
                activity = existing
            
            # Only get detailed metrics if we don't have a file OR file parsing failed
            if not activity.filename or not activity.duration:
                # Try to get metrics from file first
                if activity.filename and os.path.exists(activity.filename):
                    metrics = get_activity_metrics(activity, client=None)  # File only
                else:
                    metrics = None
                
                # Only call API if file parsing failed or no file
                if not metrics:
                    print(f"Getting details from API for activity {activity_id}")
                    metrics = get_activity_metrics(activity, garmin_client)
                else:
                    print(f"Using cached file data for activity {activity_id}")
                
                # Update activity with metrics
                if metrics:
                    update_activity_from_metrics(activity, metrics)
            
            activity.last_sync = datetime.now().isoformat()

        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def update_activity_from_metrics(activity, metrics):
    """Helper function to update activity from metrics data"""
    if not metrics:
        return
        
    activity.activity_type = metrics.get("activityType", {}).get("typeKey")
    
    summary = metrics.get("summaryDTO", {})
    
    if summary.get("duration"):
        activity.duration = int(float(summary["duration"]))
    if summary.get("distance"):
        activity.distance = float(summary["distance"])
    if summary.get("maxHR"):
        activity.max_heart_rate = int(float(summary["maxHR"]))
    if summary.get("avgHR"):
        activity.avg_heart_rate = int(float(summary["avgHR"]))
    if summary.get("avgPower"):
        activity.avg_power = float(summary["avgPower"])
    if summary.get("calories"):
        activity.calories = int(float(summary["calories"]))
```

### Add Original File Storage
```python
# garminsync/database.py - Update Activity model
class Activity(Base):
    __tablename__ = "activities"
    
    activity_id = Column(Integer, primary_key=True)
    start_time = Column(String, nullable=False)
    activity_type = Column(String, nullable=True)
    duration = Column(Integer, nullable=True)
    distance = Column(Float, nullable=True)
    max_heart_rate = Column(Integer, nullable=True)
    avg_heart_rate = Column(Integer, nullable=True)
    avg_power = Column(Float, nullable=True)
    calories = Column(Integer, nullable=True)
    filename = Column(String, unique=True, nullable=True)
    original_filename = Column(String, nullable=True)  # NEW: Store original name
    file_type = Column(String, nullable=True)  # NEW: Store detected file type
    file_size = Column(Integer, nullable=True)  # NEW: Store file size
    downloaded = Column(Boolean, default=False, nullable=False)
    created_at = Column(String, nullable=False)
    last_sync = Column(String, nullable=True)
    metrics_source = Column(String, nullable=True)  # NEW: 'file' or 'api'
```

---

## Phase 3: Enhanced UI with Filtering & Stats (Week 5-6)

### Add Database Indexing
```python
# Create new migration file: migrations/versions/003_add_indexes.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add indexes for common queries
    op.create_index('ix_activities_activity_type', 'activities', ['activity_type'])
    op.create_index('ix_activities_start_time', 'activities', ['start_time'])
    op.create_index('ix_activities_downloaded', 'activities', ['downloaded'])
    op.create_index('ix_activities_duration', 'activities', ['duration'])
    op.create_index('ix_activities_distance', 'activities', ['distance'])

def downgrade():
    op.drop_index('ix_activities_activity_type')
    op.drop_index('ix_activities_start_time')
    op.drop_index('ix_activities_downloaded')
    op.drop_index('ix_activities_duration')
    op.drop_index('ix_activities_distance')
```

### Enhanced Activities API with Filtering
```python
# garminsync/web/routes.py - Update activities endpoint
@router.get("/activities")
async def get_activities(
    page: int = 1,
    per_page: int = 50,
    activity_type: str = None,
    date_from: str = None,
    date_to: str = None,
    min_distance: float = None,
    max_distance: float = None,
    min_duration: int = None,
    max_duration: int = None,
    sort_by: str = "start_time",  # NEW: sorting
    sort_order: str = "desc"      # NEW: sort direction
):
    """Get paginated activities with enhanced filtering"""
    session = get_session()
    try:
        query = session.query(Activity)

        # Apply filters
        if activity_type:
            query = query.filter(Activity.activity_type == activity_type)
        if date_from:
            query = query.filter(Activity.start_time >= date_from)
        if date_to:
            query = query.filter(Activity.start_time <= date_to)
        if min_distance:
            query = query.filter(Activity.distance >= min_distance * 1000)  # Convert km to m
        if max_distance:
            query = query.filter(Activity.distance <= max_distance * 1000)
        if min_duration:
            query = query.filter(Activity.duration >= min_duration * 60)  # Convert min to sec
        if max_duration:
            query = query.filter(Activity.duration <= max_duration * 60)

        # Apply sorting
        sort_column = getattr(Activity, sort_by, Activity.start_time)
        if sort_order.lower() == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Get total count for pagination
        total = query.count()

        # Apply pagination
        activities = query.offset((page - 1) * per_page).limit(per_page).all()

        return {
            "activities": [activity_to_dict(activity) for activity in activities],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }
    finally:
        session.close()

def activity_to_dict(activity):
    """Convert activity to dictionary with computed fields"""
    return {
        "activity_id": activity.activity_id,
        "start_time": activity.start_time,
        "activity_type": activity.activity_type,
        "duration": activity.duration,
        "duration_formatted": format_duration(activity.duration),
        "distance": activity.distance,
        "distance_km": round(activity.distance / 1000, 2) if activity.distance else None,
        "pace": calculate_pace(activity.distance, activity.duration),
        "max_heart_rate": activity.max_heart_rate,
        "avg_heart_rate": activity.avg_heart_rate,
        "avg_power": activity.avg_power,
        "calories": activity.calories,
        "downloaded": activity.downloaded,
        "file_type": activity.file_type,
        "metrics_source": activity.metrics_source
    }

def calculate_pace(distance_m, duration_s):
    """Calculate pace in min/km"""
    if not distance_m or not duration_s or distance_m == 0:
        return None
    
    distance_km = distance_m / 1000
    pace_s_per_km = duration_s / distance_km
    
    minutes = int(pace_s_per_km // 60)
    seconds = int(pace_s_per_km % 60)
    
    return f"{minutes}:{seconds:02d}"
```

### Enhanced Frontend with Filtering
```javascript
// garminsync/web/static/activities.js - Add filtering capabilities
class ActivitiesPage {
    constructor() {
        this.currentPage = 1;
        this.pageSize = 25;
        this.totalPages = 1;
        this.activities = [];
        this.filters = {};
        this.sortBy = 'start_time';
        this.sortOrder = 'desc';
        this.init();
    }
    
    init() {
        this.setupFilterForm();
        this.loadActivities();
        this.setupEventListeners();
    }
    
    setupFilterForm() {
        // Create filter form dynamically
        const filterHtml = `
            <div class="filters-card card">
                <div class="card-header">
                    <h4>Filters</h4>
                    <button id="toggle-filters" class="btn btn-sm">Hide</button>
                </div>
                <div id="filter-form" class="filter-form">
                    <div class="filter-row">
                        <div class="filter-group">
                            <label>Activity Type</label>
                            <select id="activity-type-filter">
                                <option value="">All Types</option>
                                <option value="running">Running</option>
                                <option value="cycling">Cycling</option>
                                <option value="swimming">Swimming</option>
                                <option value="walking">Walking</option>
                            </select>
                        </div>
                        
                        <div class="filter-group">
                            <label>Date From</label>
                            <input type="date" id="date-from-filter">
                        </div>
                        
                        <div class="filter-group">
                            <label>Date To</label>
                            <input type="date" id="date-to-filter">
                        </div>
                    </div>
                    
                    <div class="filter-row">
                        <div class="filter-group">
                            <label>Min Distance (km)</label>
                            <input type="number" id="min-distance-filter" step="0.1">
                        </div>
                        
                        <div class="filter-group">
                            <label>Max Distance (km)</label>
                            <input type="number" id="max-distance-filter" step="0.1">
                        </div>
                        
                        <div class="filter-group">
                            <label>Sort By</label>
                            <select id="sort-by-filter">
                                <option value="start_time">Date</option>
                                <option value="distance">Distance</option>
                                <option value="duration">Duration</option>
                                <option value="activity_type">Type</option>
                            </select>
                        </div>
                        
                        <div class="filter-group">
                            <label>Order</label>
                            <select id="sort-order-filter">
                                <option value="desc">Newest First</option>
                                <option value="asc">Oldest First</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="filter-actions">
                        <button id="apply-filters" class="btn btn-primary">Apply Filters</button>
                        <button id="clear-filters" class="btn btn-secondary">Clear</button>
                    </div>
                </div>
            </div>
        `;
        
        // Insert before activities table
        const container = document.querySelector('.activities-container');
        container.insertAdjacentHTML('afterbegin', filterHtml);
    }
    
    setupEventListeners() {
        // Apply filters
        document.getElementById('apply-filters').addEventListener('click', () => {
            this.applyFilters();
        });
        
        // Clear filters
        document.getElementById('clear-filters').addEventListener('click', () => {
            this.clearFilters();
        });
        
        // Toggle filter visibility
        document.getElementById('toggle-filters').addEventListener('click', (e) => {
            const filterForm = document.getElementById('filter-form');
            const isVisible = filterForm.style.display !== 'none';
            
            filterForm.style.display = isVisible ? 'none' : 'block';
            e.target.textContent = isVisible ? 'Show' : 'Hide';
        });
    }
    
    applyFilters() {
        this.filters = {
            activity_type: document.getElementById('activity-type-filter').value,
            date_from: document.getElementById('date-from-filter').value,
            date_to: document.getElementById('date-to-filter').value,
            min_distance: document.getElementById('min-distance-filter').value,
            max_distance: document.getElementById('max-distance-filter').value
        };
        
        this.sortBy = document.getElementById('sort-by-filter').value;
        this.sortOrder = document.getElementById('sort-order-filter').value;
        
        // Remove empty filters
        Object.keys(this.filters).forEach(key => {
            if (!this.filters[key]) {
                delete this.filters[key];
            }
        });
        
        this.currentPage = 1;
        this.loadActivities();
    }
    
    clearFilters() {
        // Reset all filter inputs
        document.getElementById('activity-type-filter').value = '';
        document.getElementById('date-from-filter').value = '';
        document.getElementById('date-to-filter').value = '';
        document.getElementById('min-distance-filter').value = '';
        document.getElementById('max-distance-filter').value = '';
        document.getElementById('sort-by-filter').value = 'start_time';
        document.getElementById('sort-order-filter').value = 'desc';
        
        // Reset internal state
        this.filters = {};
        this.sortBy = 'start_time';
        this.sortOrder = 'desc';
        this.currentPage = 1;
        
        this.loadActivities();
    }
    
    createTableRow(activity, index) {
        const row = document.createElement('tr');
        row.className = index % 2 === 0 ? 'row-even' : 'row-odd';
        
        row.innerHTML = `
            <td>${Utils.formatDate(activity.start_time)}</td>
            <td>
                <span class="activity-type-badge ${activity.activity_type}">
                    ${activity.activity_type || '-'}
                </span>
            </td>
            <td>${activity.duration_formatted || '-'}</td>
            <td>${activity.distance_km ? activity.distance_km + ' km' : '-'}</td>
            <td>${activity.pace || '-'}</td>
            <td>${Utils.formatHeartRate(activity.max_heart_rate)}</td>
            <td>${Utils.formatHeartRate(activity.avg_heart_rate)}</td>
            <td>${Utils.formatPower(activity.avg_power)}</td>
            <td>${activity.calories ? activity.calories.toLocaleString() : '-'}</td>
            <td>
                <span class="source-badge ${activity.metrics_source}">
                    ${activity.file_type || 'API'}
                </span>
            </td>
        `;
        
        return row;
    }
}
```

---

## Phase 4: Activity Stats & Trends (Week 7-8)

### Add Statistics API
```python
# garminsync/web/routes.py - Add comprehensive stats
@router.get("/stats/summary")
async def get_activity_summary():
    """Get comprehensive activity statistics"""
    session = get_session()
    try:
        # Basic counts
        total_activities = session.query(Activity).count()
        downloaded_activities = session.query(Activity).filter_by(downloaded=True).count()
        
        # Activity type breakdown
        type_stats = session.query(
            Activity.activity_type,
            func.count(Activity.activity_id).label('count'),
            func.sum(Activity.distance).label('total_distance'),
            func.sum(Activity.duration).label('total_duration'),
            func.sum(Activity.calories).label('total_calories')
        ).filter(
            Activity.activity_type.isnot(None)
        ).group_by(Activity.activity_type).all()
        
        # Monthly stats (last 12 months)
        monthly_stats = session.query(
            func.strftime('%Y-%m', Activity.start_time).label('month'),
            func.count(Activity.activity_id).label('count'),
            func.sum(Activity.distance).label('total_distance'),
            func.sum(Activity.duration).label('total_duration')
        ).filter(
            Activity.start_time >= (datetime.now() - timedelta(days=365)).isoformat()
        ).group_by(
            func.strftime('%Y-%m', Activity.start_time)
        ).order_by('month').all()
        
        # Personal records
        records = {
            'longest_distance': session.query(Activity).filter(
                Activity.distance.isnot(None)
            ).order_by(Activity.distance.desc()).first(),
            
            'longest_duration': session.query(Activity).filter(
                Activity.duration.isnot(None)
            ).order_by(Activity.duration.desc()).first(),
            
            'highest_calories': session.query(Activity).filter(
                Activity.calories.isnot(None)
            ).order_by(Activity.calories.desc()).first()
        }
        
        return {
            "summary": {
                "total_activities": total_activities,
                "downloaded_activities": downloaded_activities,
                "sync_percentage": round((downloaded_activities / total_activities) * 100, 1) if total_activities > 0 else 0
            },
            "by_type": [
                {
                    "activity_type": stat.activity_type,
                    "count": stat.count,
                    "total_distance_km": round(stat.total_distance / 1000, 1) if stat.total_distance else 0,
                    "total_duration_hours": round(stat.total_duration / 3600, 1) if stat.total_duration else 0,
                    "total_calories": stat.total_calories or 0
                }
                for stat in type_stats
            ],
            "monthly": [
                {
                    "month": stat.month,
                    "count": stat.count,
                    "total_distance_km": round(stat.total_distance / 1000, 1) if stat.total_distance else 0,
                    "total_duration_hours": round(stat.total_duration / 3600, 1) if stat.total_duration else 0
                }
                for stat in monthly_stats
            ],
            "records": {
                "longest_distance": {
                    "distance_km": round(records['longest_distance'].distance / 1000, 1) if records['longest_distance'] and records['longest_distance'].distance else 0,
                    "date": records['longest_distance'].start_time if records['longest_distance'] else None
                },
                "longest_duration": {
                    "duration_hours": round(records['longest_duration'].duration / 3600, 1) if records['longest_duration'] and records['longest_duration'].duration else 0,
                    "date": records['longest_duration'].start_time if records['longest_duration'] else None
                },
                "highest_calories": {
                    "calories": records['highest_calories'].calories if records['highest_calories'] and records['highest_calories'].calories else 0,
                    "date": records['highest_calories'].start_time if records['highest_calories'] else None
                }
            }
        }
    finally:
        session.close()
```

### Simple Charts with Chart.js
```html
<!-- garminsync/web/templates/dashboard.html - Add stats section -->
<div class="stats-section">
    <div class="card">
        <div class="card-header">
            <h3>Activity Statistics</h3>
        </div>
        <div class="stats-grid">
            <div class="stat-item">
                <h4 id="total-activities">{{ stats.total }}</h4>
                <p>Total Activities</p>
            </div>
            <div class="stat-item">
                <h4 id="downloaded-activities">{{ stats.downloaded }}</h4>
                <p>Downloaded</p>
            </div>
            <div class="stat-item">
                <h4 id="sync-percentage">-</h4>
                <p>Sync %</p>
            </div>
        </div>
    </div>
    
    <div class="card">
        <div class="card-header">
            <h3>Activity Types</h3>
        </div>
        <canvas id="activity-types-chart" width="400" height="200"></canvas>
    </div>
    
    <div class="card">
        <div class="card-header">
            <h3>Monthly Activity</h3>
        </div>
        <canvas id="monthly-chart" width="400" height="200"></canvas>
    </div>
</div>
```

```javascript
// garminsync/web/static/stats.js - Simple chart implementation
class StatsPage {
    constructor() {
        this.charts = {};
        this.init();
    }
    
    async init() {
        await this.loadStats();
        this.createCharts();
    }
    
    async loadStats() {
        try {
            const response = await fetch('/api/stats/summary');
            this.stats = await response.json();
            this.updateSummaryCards();
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    }
    
    updateSummaryCards() {
        document.getElementById('total-activities').textContent = this.stats.summary.total_activities;
        document.getElementById('downloaded-activities').textContent = this.stats.summary.downloaded_activities;
        document.getElementById('sync-percentage').textContent = this.stats.summary.sync_percentage + '%';
    }
    
    createCharts() {
        this.createActivityTypesChart();
        this.createMonthlyChart();
    }
    
    createActivityTypesChart() {
        const ctx = document.getElementById('activity-types-chart').getContext('2d');
        
        const data = this.stats.by_type.map(item => ({
            label: item.activity_type,
            data: item.count
        }));
        
        this.charts.activityTypes = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: data.map(item => item.label),
                datasets: [{
                    data: data.map(item => item.data),
                    backgroundColor: [
                        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
                        '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    createMonthlyChart() {
        const ctx = document.getElementById('monthly-chart').getContext('2d');
        
        const monthlyData = this.stats.monthly;
        
        this.charts.monthly = new Chart(ctx, {
            type: 'line',
            data: {
                labels: monthlyData.map(item => item.month),
                datasets: [
                    {
                        label: 'Activities',
                        data: monthlyData.map(item => item.count),
                        borderColor: '#36A2EB',
                        backgroundColor: 'rgba(54, 162, 235, 0.1)',
                        yAxisID: 'y'
                    },
                    {
                        label: 'Distance (km)',
                        data: monthlyData.map(item => item.total_distance_km),
                        borderColor: '#FF6384',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Number of Activities'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Distance (km)'
                        },
                        grid: {
                            drawOnChartArea: false,
                        },
                    }
                }
            }
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('activity-types-chart')) {
        new StatsPage();
    }
});
```

---

## Phase 5: File Management & Storage Optimization (Week 9-10)

### Problem: Better file organization and storage

### Solution: Organized File Storage with Metadata

```python
# garminsync/file_manager.py - New file for managing activity files
import os
import hashlib
from pathlib import Path
from datetime import datetime
import shutil

class ActivityFileManager:
    """Manages activity file storage with proper organization"""
    
    def __init__(self, base_data_dir=None):
        self.base_dir = Path(base_data_dir or os.getenv("DATA_DIR", "data"))
        self.activities_dir = self.base_dir / "activities"
        self.activities_dir.mkdir(parents=True, exist_ok=True)
        
    def save_activity_file(self, activity_id, file_data, original_filename=None):
        """
        Save activity file with proper organization
        Returns: (filepath, file_info)
        """
        # Detect file type from data
        file_type = self._detect_file_type_from_data(file_data)
        
        # Generate file hash for deduplication
        file_hash = hashlib.md5(file_data).hexdigest()
        
        # Create organized directory structure: activities/YYYY/MM/
        activity_date = self._extract_date_from_activity_id(activity_id)
        year_month_dir = self.activities_dir / activity_date.strftime("%Y") / activity_date.strftime("%m")
        year_month_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        extension = self._get_extension_for_type(file_type)
        filename = f"activity_{activity_id}_{file_hash[:8]}.{extension}"
        filepath = year_month_dir / filename
        
        # Check if file already exists (deduplication)
        if filepath.exists():
            existing_size = filepath.stat().st_size
            if existing_size == len(file_data):
                print(f"File already exists for activity {activity_id}, skipping...")
                return str(filepath), self._get_file_info(filepath, file_data, file_type)
        
        # Save file
        with open(filepath, 'wb') as f:
            f.write(file_data)
        
        file_info = self._get_file_info(filepath, file_data, file_type)
        
        print(f"Saved activity {activity_id} to {filepath}")
        return str(filepath), file_info
    
    def _detect_file_type_from_data(self, data):
        """Detect file type from binary data"""
        if len(data) >= 8 and data[4:8] == b'.FIT':
            return 'fit'
        elif b'<?xml' in data[:50]:
            if b'<gpx' in data[:200]:
                return 'gpx'
            elif b'TrainingCenterDatabase' in data[:500]:
                return 'tcx'
            else:
                return 'xml'
        return 'unknown'
    
    def _get_extension_for_type(self, file_type):
        """Get file extension for detected type"""
        extensions = {
            'fit': 'fit',
            'tcx': 'tcx', 
            'gpx': 'gpx',
            'xml': 'tcx',
            'unknown': 'bin'
        }
        return extensions.get(file_type, 'bin')
    
    def _extract_date_from_activity_id(self, activity_id):
        """Extract date from activity ID or use current date"""
        # For now, use current date. In a real implementation,
        # you might extract date from the activity data
        return datetime.now()
    
    def _get_file_info(self, filepath, data, file_type):
        """Get file metadata"""
        return {
            'size': len(data),
            'type': file_type,
            'created': datetime.now().isoformat(),
            'md5_hash': hashlib.md5(data).hexdigest()
        }
    
    def cleanup_orphaned_files(self, valid_activity_ids):
        """Remove files for activities no longer in database"""
        orphaned_files = []
        
        for file_path in self.activities_dir.rglob("activity_*"):
            try:
                # Extract activity ID from filename
                filename = file_path.stem
                if filename.startswith("activity_"):
                    parts = filename.split("_")
                    if len(parts) >= 2:
                        activity_id = int(parts[1])
                        if activity_id not in valid_activity_ids:
                            orphaned_files.append(file_path)
            except (ValueError, IndexError):
                continue
        
        # Remove orphaned files
        for file_path in orphaned_files:
            print(f"Removing orphaned file: {file_path}")
            file_path.unlink()
        
        return len(orphaned_files)
```

### Update Download Process
```python
# garminsync/daemon.py - Update sync_and_download to use file manager
from .file_manager import ActivityFileManager

class GarminSyncDaemon:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.running = False
        self.web_server = None
        self.sync_lock = threading.Lock()
        self.sync_in_progress = False
        self.file_manager = ActivityFileManager()  # NEW

    def sync_and_download(self):
        """Scheduled job function with improved file handling"""
        session = None
        try:
            self.log_operation("sync", "started")

            from .database import sync_database
            from .garmin import GarminClient

            client = GarminClient()
            sync_database(client)

            downloaded_count = 0
            session = get_session()
            missing_activities = (
                session.query(Activity).filter_by(downloaded=False).all()
            )

            for activity in missing_activities:
                try:
                    # Download activity data
                    fit_data = client.download_activity_fit(activity.activity_id)
                    
                    # Save using file manager
                    filepath, file_info = self.file_manager.save_activity_file(
                        activity.activity_id, 
                        fit_data
                    )
                    
                    # Update activity record
                    activity.filename = filepath
                    activity.file_type = file_info['type']
                    activity.file_size = file_info['size']
                    activity.downloaded = True
                    activity.last_sync = datetime.now().isoformat()
                    
                    # Get metrics from file
                    metrics = get_activity_metrics(activity, client=None)  # File only
                    if metrics:
                        update_activity_from_metrics(activity, metrics)
                        activity.metrics_source = 'file'
                    else:
                        # Fallback to API if file parsing fails
                        metrics = get_activity_metrics(activity, client)
                        if metrics:
                            update_activity_from_metrics(activity, metrics)
                            activity.metrics_source = 'api'
                    
                    session.commit()
                    downloaded_count += 1

                except Exception as e:
                    logger.error(f"Failed to download activity {activity.activity_id}: {e}")
                    session.rollback()

            self.log_operation("sync", "success", f"Downloaded {downloaded_count} new activities")
            self.update_daemon_last_run()

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            self.log_operation("sync", "error", str(e))
        finally:
            if session:
                session.close()
```

---

## Phase 6: Advanced Features & Polish (Week 11-12)

### Add Activity Search
```python
# garminsync/web/routes.py - Add search endpoint
@router.get("/activities/search")
async def search_activities(
    q: str,  # Search query
    page: int = 1,
    per_page: int = 20
):
    """Search activities by various fields"""
    session = get_session()
    try:
        # Build search query
        query = session.query(Activity)
        
        search_terms = q.lower().split()
        
        for term in search_terms:
            # Search in multiple fields
            query = query.filter(
                or_(
                    Activity.activity_type.ilike(f'%{term}%'),
                    Activity.filename.ilike(f'%{term}%'),
                    # Add more searchable fields as needed
                )
            )
        
        total = query.count()
        activities = query.order_by(Activity.start_time.desc()).offset(
            (page - 1) * per_page
        ).limit(per_page).all()

        return {
            "activities": [activity_to_dict(activity) for activity in activities],
            "total": total,
            "page": page,
            "per_page": per_page,
            "query": q
        }
    finally:
        session.close()
```

### Add Bulk Operations
```javascript
// garminsync/web/static/bulk-operations.js
class BulkOperations {
    constructor() {
        this.selectedActivities = new Set();
        this.init();
    }
    
    init() {
        this.addBulkControls();
        this.setupEventListeners();
    }
    
    addBulkControls() {
        const bulkHtml = `
            <div id="bulk-operations" class="bulk-operations" style="display: none;">
                <div class="bulk-info">
                    <span id="selected-count">0</span> activities selected
                </div>
                <div class="bulk-actions">
                    <button id="bulk-reprocess" class="btn btn-sm">Reprocess Files</button>
                    <button id="bulk-export" class="btn btn-sm">Export Data</button>
                    <button id="clear-selection" class="btn btn-sm btn-secondary">Clear Selection</button>
                </div>
            </div>
        `;
        
        document.querySelector('.activities-table-card').insertAdjacentHTML('afterbegin', bulkHtml);
    }
    
    setupEventListeners() {
        // Add checkboxes to table
        this.addCheckboxesToTable();
        
        // Bulk action buttons
        document.getElementById('clear-selection').addEventListener('click', () => {
            this.clearSelection();
        });
        
        document.getElementById('bulk-reprocess').addEventListener('click', () => {
            this.reprocessSelectedFiles();
        });
    }
    
    addCheckboxesToTable() {
        // Add header checkbox
        const headerRow = document.querySelector('.activities-table thead tr');
        headerRow.insertAdjacentHTML('afterbegin', '<th><input type="checkbox" id="select-all"></th>');
        
        // Add row checkboxes
        const rows = document.querySelectorAll('.activities-table tbody tr');
        rows.forEach((row, index) => {
            const activityId = this.extractActivityIdFromRow(row);
            row.insertAdjacentHTML('afterbegin', 
                `<td><input type="checkbox" class="activity-checkbox" data-activity-id="${activityId}"></td>`
            );
        });
        
        // Setup checkbox events
        document.getElementById('select-all').addEventListener('change', (e) => {
            this.selectAll(e.target.checked);
        });
        
        document.querySelectorAll('.activity-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                this.toggleActivity(e.target.dataset.activityId, e.target.checked);
            });
        });
    }
    
    extractActivityIdFromRow(row) {
        // Extract activity ID from the row (you'll need to adjust this based on your table structure)
        return row.dataset.activityId || row.cells[1].textContent; // Adjust as needed
    }
    
    selectAll(checked) {
        document.querySelectorAll('.activity-checkbox').forEach(checkbox => {
            checkbox.checked = checked;
            this.toggleActivity(checkbox.dataset.activityId, checked);
        });
    }
    
    toggleActivity(activityId, selected) {
        if (selected) {
            this.selectedActivities.add(activityId);
        } else {
            this.selectedActivities.delete(activityId);
        }
        
        this.updateBulkControls();
    }
    
    updateBulkControls() {
        const count = this.selectedActivities.size;
        const bulkDiv = document.getElementById('bulk-operations');
        const countSpan = document.getElementById('selected-count');
        
        countSpan.textContent = count;
        bulkDiv.style.display = count > 0 ? 'block' : 'none';
    }
    
    clearSelection() {
        this.selectedActivities.clear();
        document.querySelectorAll('.activity-checkbox').forEach(checkbox => {
            checkbox.checked = false;
        });
        document.getElementById('select-all').checked = false;
        this.updateBulkControls();
    }
    
    async reprocessSelectedFiles() {
        if (this.selectedActivities.size === 0) return;
        
        const button = document.getElementById('bulk-reprocess');
        button.disabled = true;
        button.textContent = 'Processing...';
        
        try {
            const response = await fetch('/api/activities/reprocess', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    activity_ids: Array.from(this.selectedActivities)
                })
            });
            
            if (response.ok) {
                Utils.showSuccess('Files reprocessed successfully');
                // Refresh the page or reload data
                window.location.reload();
            } else {
                throw new Error('Reprocessing failed');
            }
        } catch (error) {
            Utils.showError('Failed to reprocess files: ' + error.message);
        } finally {
            button.disabled = false;
            button.textContent = 'Reprocess Files';
        }
    }
}
```

### Add Configuration Management
```python
# garminsync/web/routes.py - Add configuration endpoints
@router.get("/config")
async def get_configuration():
    """Get current configuration"""
    session = get_session()
    try:
        daemon_config = session.query(DaemonConfig).first()
        
        return {
            "sync": {
                "enabled": daemon_config.enabled if daemon_config else True,
                "schedule": daemon_config.schedule_cron if daemon_config else "0 */6 * * *",
                "status": daemon_config.status if daemon_config else "stopped"
            },
            "storage": {
                "data_dir": os.getenv("DATA_DIR", "data"),
                "total_activities": session.query(Activity).count(),
                "downloaded_files": session.query(Activity).filter_by(downloaded=True).count()
            },
            "api": {
                "garmin_configured": bool(os.getenv("GARMIN_EMAIL") and os.getenv("GARMIN_PASSWORD")),
                "rate_limit_delay": 2  # seconds between API calls
            }
        }
    finally:
        session.close()

@router.post("/config/sync")
async def update_sync_config(config_data: dict):
    """Update sync configuration"""
    session = get_session()
    try:
        daemon_config = session.query(DaemonConfig).first()
        if not daemon_config:
            daemon_config = DaemonConfig()
            session.add(daemon_config)
        
        if 'enabled' in config_data:
            daemon_config.enabled = config_data['enabled']
        if 'schedule' in config_data:
            # Validate cron expression
            try:
                from apscheduler.triggers.cron import CronTrigger
                CronTrigger.from_crontab(config_data['schedule'])
                daemon_config.schedule_cron = config_data['schedule']
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid cron expression: {e}")
        
        session.commit()
        return {"message": "Configuration updated successfully"}
    finally:
        session.close()
```

---

## Testing & Deployment Guide

### Simple Testing Strategy
```python
# tests/test_basic_functionality.py - Basic tests for junior developers
import pytest
import os
import tempfile
from pathlib import Path

def test_file_type_detection():
    """Test that we can detect different file types correctly"""
    from garminsync.activity_parser import detect_file_type
    
    # Create temporary test files
    with tempfile.NamedTemporaryFile(suffix='.fit', delete=False) as f:
        # Write FIT file header
        f.write(b'\x0E\x10\x43\x08.FIT\x00\x00\x00\x00')
        fit_file = f.name
    
    with tempfile.NamedTemporaryFile(suffix='.gpx', delete=False) as f:
        f.write(b'<?xml version="1.0"?><gpx version="1.1">')
        gpx_file = f.name
    
    try:
        assert detect_file_type(fit_file) == 'fit'
        assert detect_file_type(gpx_file) == 'gpx'
    finally:
        os.unlink(fit_file)
        os.unlink(gpx_file)

def test_activity_metrics_parsing():
    """Test that we can parse activity metrics"""
    # This would test your parsing functions
    pass

# Run with: python -m pytest tests/
```

### Deployment Checklist
```yaml
# docker-compose.yml - Updated for new features
version: '3.8'
services:
  garminsync:
    build: .
    ports:
      - "8888:8888"
    environment:
      - GARMIN_EMAIL=${GARMIN_EMAIL}
      - GARMIN_PASSWORD=${GARMIN_PASSWORD}
      - DATA_DIR=/data
    volumes:
      - ./data:/data
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8888/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## Summary & Next Steps

### What This Plan Achieves:
1. **Non-blocking sync** - Users can browse while sync runs
2. **Multi-format support** - FIT, TCX, GPX files
3. **Reduced API calls** - File-first approach with smart caching
4. **Enhanced UI** - Filtering, search, stats, and trends
5. **Better file management** - Organized storage with deduplication
6. **Simple architecture** - Single container, threading instead of complex async

### Implementation Tips for Junior Developers:
- **Start small** - Implement one phase at a time
- **Test frequently** - Run the app after each major change
- **Keep backups** - Always backup your database before migrations
- **Use logging** - Add print statements and logs liberally
- **Ask for help** - Don't hesitate to ask questions about complex parts

### Estimated Timeline:
- **Phase 1-2**: 2-4 weeks (core improvements)
- **Phase 3-4**: 2-4 weeks (UI enhancements) 
- **Phase 5-6**: 2-4 weeks (advanced features)

Would you like me to elaborate on any specific phase or create detailed code examples for any particular feature?