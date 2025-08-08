import signal
import sys
import time
import threading
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from .database import get_session, Activity, DaemonConfig, SyncLog
from .garmin import GarminClient
from .utils import logger

class GarminSyncDaemon:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.running = False
        self.web_server = None
        
    def start(self, web_port=8080):
        """Start daemon with scheduler and web UI"""
        try:
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
            
            logger.info(f"Daemon started. Web UI available at http://localhost:{web_port}")
            
            # Keep daemon running
            while self.running:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Failed to start daemon: {str(e)}")
            self.stop()
            
    def sync_and_download(self):
        """Scheduled job function"""
        try:
            self.log_operation("sync", "started")
            
            # Perform sync and download
            client = GarminClient()
            activities_before = self.count_missing()
            
            # Sync database
            session = get_session()
            activities = client.get_activities(0, 1000)
            for activity in activities:
                activity_id = activity["activityId"]
                existing = session.query(Activity).filter_by(activity_id=activity_id).first()
                if not existing:
                    new_activity = Activity(
                        activity_id=activity_id,
                        start_time=activity["startTimeLocal"],
                        downloaded=False,
                        created_at=datetime.now().isoformat()
                    )
                    session.add(new_activity)
            session.commit()
            
            # Download missing activities
            downloaded_count = 0
            missing_activities = session.query(Activity).filter_by(downloaded=False).all()
            for activity in missing_activities:
                if client.download_activity(activity.activity_id, activity.start_time):
                    activity.downloaded = True
                    activity.last_sync = datetime.now().isoformat()
                    downloaded_count += 1
            session.commit()
            
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
        return config
        
    def start_web_ui(self, port):
        """Start FastAPI web server in a separate thread"""
        from .web.app import app
        import uvicorn
        
        def run_server():
            uvicorn.run(app, host="0.0.0.0", port=port)
            
        web_thread = threading.Thread(target=run_server, daemon=True)
        web_thread.start()
        self.web_server = web_thread
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Received shutdown signal, stopping daemon...")
        self.stop()
        
    def stop(self):
        """Stop daemon and clean up resources"""
        if self.scheduler.running:
            self.scheduler.shutdown()
        self.running = False
        logger.info("Daemon stopped")
        
    def log_operation(self, operation, status, message=None):
        """Log sync operation to database"""
        session = get_session()
        log = SyncLog(
            timestamp=datetime.now().isoformat(),
            operation=operation,
            status=status,
            message=message
        )
        session.add(log)
        session.commit()
        
    def count_missing(self):
        """Count missing activities"""
        session = get_session()
        return session.query(Activity).filter_by(downloaded=False).count()
