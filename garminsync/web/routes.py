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
    # TODO: Implement sync triggering
    return {"message": "Sync triggered successfully"}
