from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from garminsync.database import get_session, DaemonConfig, SyncLog

router = APIRouter(prefix="/api")

class ScheduleConfig(BaseModel):
    enabled: bool
    cron_schedule: str

@router.get("/status")
async def get_status():
    """Get current daemon status"""
    session = get_session()
    try:
        config = session.query(DaemonConfig).first()
        
        # Get recent logs
        logs = session.query(SyncLog).order_by(SyncLog.timestamp.desc()).limit(10).all()
        
        # Convert to dictionaries to avoid session issues
        daemon_data = {
            "running": config.status == "running" if config else False,
            "next_run": config.next_run if config else None,
            "schedule": config.schedule_cron if config else None,
            "last_run": config.last_run if config else None,
            "enabled": config.enabled if config else False
        }
        
        log_data = []
        for log in logs:
            log_data.append({
                "timestamp": log.timestamp,
                "operation": log.operation,
                "status": log.status,
                "message": log.message,
                "activities_processed": log.activities_processed,
                "activities_downloaded": log.activities_downloaded
            })
        
        return {
            "daemon": daemon_data,
            "recent_logs": log_data
        }
    finally:
        session.close()

@router.post("/schedule")
async def update_schedule(config: ScheduleConfig):
    """Update daemon schedule configuration"""
    session = get_session()
    try:
        daemon_config = session.query(DaemonConfig).first()
        
        if not daemon_config:
            daemon_config = DaemonConfig()
            session.add(daemon_config)
        
        daemon_config.enabled = config.enabled
        daemon_config.schedule_cron = config.cron_schedule
        session.commit()
        
        return {"message": "Configuration updated successfully"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")
    finally:
        session.close()

@router.post("/sync/trigger")
async def trigger_sync():
    """Manually trigger a sync operation"""
    try:
        # Import here to avoid circular imports
        from garminsync.garmin import GarminClient
        from garminsync.database import sync_database, Activity
        from datetime import datetime
        import os
        from pathlib import Path
        
        # Create client and sync
        client = GarminClient()
        sync_database(client)
        
        # Download missing activities
        session = get_session()
        try:
            missing_activities = session.query(Activity).filter_by(downloaded=False).all()
            downloaded_count = 0
            
            data_dir = Path(os.getenv("DATA_DIR", "data"))
            data_dir.mkdir(parents=True, exist_ok=True)
            
            for activity in missing_activities:
                try:
                    fit_data = client.download_activity_fit(activity.activity_id)
                    
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
                    print(f"Failed to download activity {activity.activity_id}: {e}")
                    session.rollback()
            
            return {"message": f"Sync completed successfully. Downloaded {downloaded_count} activities."}
        finally:
            session.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@router.get("/activities/stats")
async def get_activity_stats():
    """Get activity statistics"""
    from garminsync.database import get_offline_stats
    return get_offline_stats()

@router.get("/logs")
async def get_logs(limit: int = 50):
    """Get recent sync logs"""
    session = get_session()
    try:
        logs = session.query(SyncLog).order_by(SyncLog.timestamp.desc()).limit(limit).all()
        
        log_data = []
        for log in logs:
            log_data.append({
                "id": log.id,
                "timestamp": log.timestamp,
                "operation": log.operation,
                "status": log.status,
                "message": log.message,
                "activities_processed": log.activities_processed,
                "activities_downloaded": log.activities_downloaded
            })
        
        return {"logs": log_data}
    finally:
        session.close()

@router.post("/daemon/start")
async def start_daemon():
    """Start the daemon process"""
    from garminsync.daemon import daemon_instance
    try:
        # Start the daemon in a separate thread to avoid blocking
        import threading
        daemon_thread = threading.Thread(target=daemon_instance.start)
        daemon_thread.daemon = True
        daemon_thread.start()
        
        # Update daemon status in database
        session = get_session()
        config = session.query(DaemonConfig).first()
        if not config:
            config = DaemonConfig()
            session.add(config)
        config.status = "running"
        session.commit()
        
        return {"message": "Daemon started successfully"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to start daemon: {str(e)}")
    finally:
        session.close()

@router.post("/daemon/stop")
async def stop_daemon():
    """Stop the daemon process"""
    from garminsync.daemon import daemon_instance
    try:
        # Stop the daemon
        daemon_instance.stop()
        
        # Update daemon status in database
        session = get_session()
        config = session.query(DaemonConfig).first()
        if config:
            config.status = "stopped"
            session.commit()
        
        return {"message": "Daemon stopped successfully"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to stop daemon: {str(e)}")
    finally:
        session.close()

@router.delete("/logs")
async def clear_logs():
    """Clear all sync logs"""
    session = get_session()
    try:
        session.query(SyncLog).delete()
        session.commit()
        return {"message": "Logs cleared successfully"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear logs: {str(e)}")
    finally:
        session.close()
