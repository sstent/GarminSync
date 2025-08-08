# GarminSync Fixes and Updated Requirements

## Primary Issue: Dependency Conflicts

The main error you're encountering is a dependency conflict between `pydantic` and `garth` (a dependency of `garminconnect`). Here's the solution:

### Updated requirements.txt
```
typer==0.9.0
click==8.1.7
python-dotenv==1.0.0
garminconnect==0.2.29
sqlalchemy==2.0.23
tqdm==4.66.1
fastapi==0.104.1
uvicorn[standard]==0.24.0
apscheduler==3.10.4
pydantic>=2.0.0,<2.5.0
jinja2==3.1.2
python-multipart==0.0.6
aiofiles==23.2.1
```

**Key Change**: Changed `pydantic==2.5.0` to `pydantic>=2.0.0,<2.5.0` to avoid the compatibility issue with `garth`.

## Code Issues Found and Fixes

### 1. Missing utils.py File
Your `daemon.py` imports `from .utils import logger` but this file doesn't exist.

**Fix**: Create `garminsync/utils.py`:
```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('garminsync')
```

### 2. Daemon.py Import Issues
The `daemon.py` file has several import and method call issues.

**Fix for garminsync/daemon.py** (line 56-75):
```python
def sync_and_download(self):
    """Scheduled job function"""
    try:
        self.log_operation("sync", "started")
        
        # Import here to avoid circular imports
        from .garmin import GarminClient
        from .database import sync_database
        
        # Perform sync and download
        client = GarminClient()
        
        # Sync database first
        sync_database(client)
        
        # Download missing activities
        downloaded_count = 0
        session = get_session()
        missing_activities = session.query(Activity).filter_by(downloaded=False).all()
        
        for activity in missing_activities:
            try:
                # Use the correct method name
                fit_data = client.download_activity_fit(activity.activity_id)
                
                # Save the file
                import os
                from pathlib import Path
                data_dir = Path(os.getenv("DATA_DIR", "data"))
                data_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = activity.start_time.replace(":", "-").replace(" ", "_")
                filename = f"activity_{activity.activity_id}_{timestamp}.fit"
                filepath = data_dir / filename
                
                with open(filepath, "wb") as f:
                    f.write(fit_data)
                
                activity.filename = str(filepath)
                activity.downloaded = True
                activity.last_sync = datetime.now().isoformat()
                downloaded_count += 1
                session.commit()
                
            except Exception as e:
                logger.error(f"Failed to download activity {activity.activity_id}: {e}")
                session.rollback()
        
        session.close()
        self.log_operation("sync", "success", 
            f"Downloaded {downloaded_count} new activities")
        
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        self.log_operation("sync", "error", str(e))
```

### 3. Missing created_at Field in Database Sync
The `sync_database` function in `database.py` doesn't set the `created_at` field.

**Fix for garminsync/database.py** (line 64-75):
```python
def sync_database(garmin_client):
    """Sync local database with Garmin Connect activities"""
    from datetime import datetime
    session = get_session()
    try:
        # Fetch activities from Garmin Connect
        activities = garmin_client.get_activities(0, 1000)
        
        # Process activities and update database
        for activity in activities:
            activity_id = activity["activityId"]
            start_time = activity["startTimeLocal"]
            
            # Check if activity exists in database
            existing = session.query(Activity).filter_by(activity_id=activity_id).first()
            if not existing:
                new_activity = Activity(
                    activity_id=activity_id,
                    start_time=start_time,
                    downloaded=False,
                    created_at=datetime.now().isoformat(),  # Add this line
                    last_sync=datetime.now().isoformat()
                )
                session.add(new_activity)
        
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        raise e
    finally:
        session.close()
```

### 4. Add Missing created_at Field to Database Model
The `Activity` model is missing the `created_at` field that's used in the daemon.

**Fix for garminsync/database.py** (line 12):
```python
class Activity(Base):
    __tablename__ = 'activities'
    
    activity_id = Column(Integer, primary_key=True)
    start_time = Column(String, nullable=False)
    filename = Column(String, unique=True, nullable=True)
    downloaded = Column(Boolean, default=False, nullable=False)
    created_at = Column(String, nullable=False)  # Add this line
    last_sync = Column(String, nullable=True)  # ISO timestamp of last sync
```

### 5. JavaScript Function Missing in Dashboard
The dashboard template calls `toggleDaemon()` but this function doesn't exist in the JavaScript.

**Fix for garminsync/web/static/app.js** (add this function):
```javascript
async function toggleDaemon() {
    // TODO: Implement daemon toggle functionality
    alert('Daemon toggle functionality not yet implemented');
}
```

## Testing the Fixes

After applying these fixes:

1. **Rebuild the Docker image**:
   ```bash
   docker build -t garminsync .
   ```

2. **Test the daemon mode**:
   ```bash
   docker run -d --env-file .env -v $(pwd)/data:/app/data -p 8080:8080 garminsync daemon --start
   ```

3. **Check the logs**:
   ```bash
   docker logs <container_id>
   ```

4. **Access the web UI**:
   Open http://localhost:8080 in your browser

## Additional Recommendations

1. **Add error handling for missing directories**: The daemon should create the data directory if it doesn't exist.

2. **Improve logging**: Add more detailed logging throughout the application.

3. **Add health checks**: Implement health check endpoints for the daemon.

4. **Database migrations**: Consider adding database migration support for schema changes.

The primary fix for your immediate issue is updating the `pydantic` version constraint in `requirements.txt`. The other fixes address various code quality and functionality issues I found during the review.