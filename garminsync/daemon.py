import signal
import sys
import threading
import time
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .database import Activity, DaemonConfig, SyncLog, get_session
from .garmin import GarminClient
from .utils import logger
from .activity_parser import get_activity_metrics


class GarminSyncDaemon:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.running = False
        self.web_server = None

    def start(self, web_port=8888, run_migrations=True):
        """Start daemon with scheduler and web UI
        :param web_port: Port for the web UI
        :param run_migrations: Whether to run database migrations on startup
        """
        # Set migration flag for entrypoint
        if run_migrations:
            os.environ['RUN_MIGRATIONS'] = "1"
        else:
            os.environ['RUN_MIGRATIONS'] = "0"
            
        try:
            # Load configuration from database
            config_data = self.load_config()

            # Setup scheduled job
            if config_data["enabled"]:
                cron_str = config_data["schedule_cron"]
                try:
                    # Validate cron string
                    if not cron_str or len(cron_str.strip().split()) != 5:
                        logger.error(
                            f"Invalid cron schedule: '{cron_str}'. Using default '0 */6 * * *'"
                        )
                        cron_str = "0 */6 * * *"

                    self.scheduler.add_job(
                        func=self.sync_and_download,
                        trigger=CronTrigger.from_crontab(cron_str),
                        id="sync_job",
                        replace_existing=True,
                    )
                    logger.info(f"Scheduled job created with cron: '{cron_str}'")
                except Exception as e:
                    logger.error(f"Failed to create scheduled job: {str(e)}")
                    # Fallback to default schedule
                    self.scheduler.add_job(
                        func=self.sync_and_download,
                        trigger=CronTrigger.from_crontab("0 */6 * * *"),
                        id="sync_job",
                        replace_existing=True,
                    )
                    logger.info("Using default schedule '0 */6 * * *'")

            # Start scheduler
            self.scheduler.start()
            self.running = True

            # Update daemon status to running
            self.update_daemon_status("running")

            # Start web UI in separate thread
            self.start_web_ui(web_port)

            # Setup signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)

            logger.info(
                f"Daemon started. Web UI available at http://localhost:{web_port}"
            )

            # Keep daemon running
            while self.running:
                time.sleep(1)

        except Exception as e:
            logger.error(f"Failed to start daemon: {str(e)}")
            self.update_daemon_status("error")
            self.stop()

    def sync_and_download(self):
        """Scheduled job function"""
        session = None
        try:
            self.log_operation("sync", "started")

            # Import here to avoid circular imports
            from .database import sync_database
            from .garmin import GarminClient

            # Perform sync and download
            client = GarminClient()

            # Sync database first
            sync_database(client)

            # Download missing activities
            downloaded_count = 0
            session = get_session()
            missing_activities = (
                session.query(Activity).filter_by(downloaded=False).all()
            )

            for activity in missing_activities:
                try:
                    # Download FIT file
                    fit_data = client.download_activity_fit(activity.activity_id)
                    
                    # Save to file
                    import os
                    from pathlib import Path
                    data_dir = Path(os.getenv("DATA_DIR", "data"))
                    data_dir.mkdir(parents=True, exist_ok=True)
                    timestamp = activity.start_time.replace(":", "-").replace(" ", "_")
                    filename = f"activity_{activity.activity_id}_{timestamp}.fit"
                    filepath = data_dir / filename
                    
                    with open(filepath, "wb") as f:
                        f.write(fit_data)
                    
                    # Update activity record
                    activity.filename = str(filepath)
                    activity.downloaded = True
                    activity.last_sync = datetime.now().isoformat()
                    
                    # Get metrics immediately after download
                    metrics = get_activity_metrics(activity, client)
                    if metrics:
                        # Update metrics if available
                        activity.activity_type = metrics.get("activityType", {}).get("typeKey")
                        activity.duration = int(float(metrics.get("summaryDTO", {}).get("duration", 0)))
                        activity.distance = float(metrics.get("summaryDTO", {}).get("distance", 0))
                        activity.max_heart_rate = int(float(metrics.get("summaryDTO", {}).get("maxHR", 0)))
                        activity.avg_power = float(metrics.get("summaryDTO", {}).get("avgPower", 0))
                        activity.calories = int(float(metrics.get("summaryDTO", {}).get("calories", 0)))
                    
                    session.commit()
                    downloaded_count += 1
                    session.commit()

                except Exception as e:
                    logger.error(
                        f"Failed to download activity {activity.activity_id}: {e}"
                    )
                    session.rollback()

            self.log_operation(
                "sync", "success", 
                f"Downloaded {downloaded_count} new activities and updated metrics"
            )

            # Update last run time
            self.update_daemon_last_run()

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            self.log_operation("sync", "error", str(e))
        finally:
            if session:
                session.close()

    def load_config(self):
        """Load daemon configuration from database and return dict"""
        session = get_session()
        try:
            config = session.query(DaemonConfig).first()
            if not config:
                # Create default configuration with explicit cron schedule
                config = DaemonConfig(
                    schedule_cron="0 */6 * * *", enabled=True, status="stopped"
                )
                session.add(config)
                session.commit()
                session.refresh(config)  # Ensure we have the latest data

            # Return configuration as dictionary to avoid session issues
            return {
                "id": config.id,
                "enabled": config.enabled,
                "schedule_cron": config.schedule_cron,
                "last_run": config.last_run,
                "next_run": config.next_run,
                "status": config.status,
            }
        finally:
            session.close()

    def update_daemon_status(self, status):
        """Update daemon status in database"""
        session = get_session()
        try:
            config = session.query(DaemonConfig).first()
            if not config:
                config = DaemonConfig()
                session.add(config)

            config.status = status
            session.commit()
        finally:
            session.close()

    def update_daemon_last_run(self):
        """Update daemon last run timestamp"""
        session = get_session()
        try:
            config = session.query(DaemonConfig).first()
            if config:
                config.last_run = datetime.now().isoformat()
                session.commit()
        finally:
            session.close()

    def start_web_ui(self, port):
        """Start FastAPI web server in a separate thread"""
        try:
            import uvicorn

            from .web.app import app

            def run_server():
                try:
                    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
                except Exception as e:
                    logger.error(f"Failed to start web server: {e}")

            web_thread = threading.Thread(target=run_server, daemon=True)
            web_thread.start()
            self.web_server = web_thread
        except ImportError as e:
            logger.warning(f"Could not start web UI: {e}")

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Received shutdown signal, stopping daemon...")
        self.stop()

    def stop(self):
        """Stop daemon and clean up resources"""
        if self.scheduler.running:
            self.scheduler.shutdown()
        self.running = False
        self.update_daemon_status("stopped")
        self.log_operation("daemon", "stopped", "Daemon shutdown completed")
        logger.info("Daemon stopped")

    def log_operation(self, operation, status, message=None):
        """Log sync operation to database"""
        session = get_session()
        try:
            log = SyncLog(
                timestamp=datetime.now().isoformat(),
                operation=operation,
                status=status,
                message=message,
                activities_processed=0,  # Can be updated later if needed
                activities_downloaded=0,  # Can be updated later if needed
            )
            session.add(log)
            session.commit()
        except Exception as e:
            logger.error(f"Failed to log operation: {e}")
        finally:
            session.close()

    def count_missing(self):
        """Count missing activities"""
        session = get_session()
        try:
            return session.query(Activity).filter_by(downloaded=False).count()
        finally:
            session.close()
