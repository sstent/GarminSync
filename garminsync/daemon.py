import os
import signal
import asyncio
import concurrent.futures
import time
from datetime import datetime
from queue import PriorityQueue
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .database import Activity, DaemonConfig, SyncLog, get_legacy_session, init_db, get_offline_stats
from .garmin import GarminClient
from .utils import logger
from .activity_parser import get_activity_metrics

# Priority levels: 1=High (API requests), 2=Medium (Sync jobs), 3=Low (Reprocessing)
PRIORITY_HIGH = 1
PRIORITY_MEDIUM = 2
PRIORITY_LOW = 3

class GarminSyncDaemon:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.running = False
        self.web_server = None
        # Process pool for CPU-bound tasks
        self.executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=os.cpu_count() - 1 or 1
        )
        # Priority queue for task scheduling
        self.task_queue = PriorityQueue()
        # Worker thread for processing tasks
        self.worker_thread = threading.Thread(target=self._process_tasks, daemon=True)
        # Lock for database access during migration
        self.db_lock = threading.Lock()

    def start(self, web_port=8888, run_migrations=True):
        """Start daemon with scheduler and web UI"""
        try:
            # Initialize database (synchronous)
            with self.db_lock:
                init_db()

            # Set migration flag for entrypoint
            if run_migrations:
                os.environ['RUN_MIGRATIONS'] = "1"
            else:
                os.environ['RUN_MIGRATIONS'] = "0"

            # Start task processing worker
            self.worker_thread.start()
            
            # Load configuration from database
            config_data = self.load_config()

            # Setup scheduled jobs
            if config_data["enabled"]:
                # Sync job
                cron_str = config_data["schedule_cron"]
                try:
                    # Validate cron string
                    if not cron_str or len(cron_str.strip().split()) != 5:
                        logger.error(
                            f"Invalid cron schedule: '{cron_str}'. Using default '0 */6 * * *'"
                        )
                        cron_str = "0 */6 * * *"

                    self.scheduler.add_job(
                        func=self._enqueue_sync,
                        trigger=CronTrigger.from_crontab(cron_str),
                        id="sync_job",
                        replace_existing=True,
                    )
                    logger.info(f"Sync job scheduled with cron: '{cron_str}'")
                except Exception as e:
                    logger.error(f"Failed to create sync job: {str(e)}")
                    # Fallback to default schedule
                    self.scheduler.add_job(
                        func=self._enqueue_sync,
                        trigger=CronTrigger.from_crontab("0 */6 * * *"),
                        id="sync_job",
                        replace_existing=True,
                    )
                    logger.info("Using default schedule for sync job: '0 */6 * * *'")
                
                # Reprocess job - run daily at 2 AM
                reprocess_cron = "0 2 * * *"
                try:
                    self.scheduler.add_job(
                        func=self._enqueue_reprocess,
                        trigger=CronTrigger.from_crontab(reprocess_cron),
                        id="reprocess_job",
                        replace_existing=True,
                    )
                    logger.info(f"Reprocess job scheduled with cron: '{reprocess_cron}'")
                except Exception as e:
                    logger.error(f"Failed to create reprocess job: {str(e)}")

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

    def _enqueue_sync(self):
        """Enqueue sync job with medium priority"""
        self.task_queue.put((PRIORITY_MEDIUM, ("sync", None)))
        logger.debug("Enqueued sync job")

    def _enqueue_reprocess(self):
        """Enqueue reprocess job with low priority"""
        self.task_queue.put((PRIORITY_LOW, ("reprocess", None)))
        logger.debug("Enqueued reprocess job")

    def _process_tasks(self):
        """Worker thread to process tasks from the priority queue"""
        logger.info("Task worker started")
        while self.running:
            try:
                priority, (task_type, data) = self.task_queue.get(timeout=1)
                logger.info(f"Processing {task_type} task (priority {priority})")
                
                if task_type == "sync":
                    self._execute_in_process_pool(self.sync_and_download)
                elif task_type == "reprocess":
                    self._execute_in_process_pool(self.reprocess_activities)
                elif task_type == "api":
                    # Placeholder for high-priority API tasks
                    logger.debug(f"Processing API task: {data}")
                
                self.task_queue.task_done()
            except Exception as e:
                logger.error(f"Task processing error: {str(e)}")
            except asyncio.TimeoutError:
                # Timeout is normal when queue is empty
                pass
        logger.info("Task worker stopped")

    def _execute_in_process_pool(self, func):
        """Execute function in process pool and handle results"""
        try:
            future = self.executor.submit(func)
            # Block until done to maintain task order but won't block main thread
            result = future.result()  
            logger.debug(f"Process pool task completed: {result}")
        except Exception as e:
            logger.error(f"Process pool task failed: {str(e)}")

    def sync_and_download(self):
        """Scheduled job function (run in process pool)"""
        session = None
        try:
            self.log_operation("sync", "started")

            # Import here to avoid circular imports
            from .database import sync_database
            from .garmin import GarminClient

            # Perform sync and download
            client = GarminClient()

            # Sync database first
            with self.db_lock:
                sync_database(client)

            # Download missing activities
            downloaded_count = 0
            session = get_legacy_session()
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
                        activity.duration = int(float(metrics.get("duration", 0)))
                        activity.distance = float(metrics.get("distance", 0))
                        activity.max_heart_rate = int(float(metrics.get("maxHR", 0)))
                        activity.avg_power = float(metrics.get("avgPower", 0))
                        activity.calories = int(float(metrics.get("calories", 0)))
                    
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
            
            # Add shutdown hook to stop worker thread
            @app.on_event("shutdown")
            def shutdown_event():
                logger.info("Web server shutting down")
                self.running = False
                self.worker_thread.join(timeout=5)

            def run_server():
                try:
                    # Use async execution model for better concurrency
                    config = uvicorn.Config(
                        app, 
                        host="0.0.0.0", 
                        port=port, 
                        log_level="info",
                        workers=1,
                        loop="asyncio"
                    )
                    server = uvicorn.Server(config)
                    server.run()
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

    def reprocess_activities(self):
        """Reprocess activities to calculate missing metrics"""
        from .database import get_session
        from .activity_parser import get_activity_metrics
        from .database import Activity
        from tqdm import tqdm

        logger.info("Starting reprocess job")
        session = get_session()
        try:
            # Get activities that need reprocessing
            activities = session.query(Activity).filter(
                Activity.downloaded == True,
                Activity.reprocessed == False
            ).all()

            if not activities:
                logger.info("No activities to reprocess")
                return

            logger.info(f"Reprocessing {len(activities)} activities")
            success_count = 0
            
            # Reprocess each activity
            for activity in tqdm(activities, desc="Reprocessing"):
                try:
                    # Use force_reprocess=True to ensure we parse the file again
                    metrics = get_activity_metrics(activity, client=None, force_reprocess=True)
                    
                    # Update activity metrics if we got new data
                    if metrics:
                        activity.activity_type = metrics.get("activityType", {}).get("typeKey")
                        activity.duration = int(float(metrics.get("duration", 0))) if metrics.get("duration") else activity.duration
                        activity.distance = float(metrics.get("distance", 0)) if metrics.get("distance") else activity.distance
                        activity.max_heart_rate = int(float(metrics.get("maxHR", 0))) if metrics.get("maxHR") else activity.max_heart_rate
                        activity.avg_heart_rate = int(float(metrics.get("avgHR", 0))) if metrics.get("avgHR") else activity.avg_heart_rate
                        activity.avg_power = float(metrics.get("avgPower", 0)) if metrics.get("avgPower") else activity.avg_power
                        activity.calories = int(float(metrics.get("calories", 0))) if metrics.get("calories") else activity.calories
                    
                    # Mark as reprocessed regardless of success
                    activity.reprocessed = True
                    session.commit()
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"Error reprocessing activity {activity.activity_id}: {str(e)}")
                    session.rollback()
                    
            logger.info(f"Reprocessed {success_count}/{len(activities)} activities successfully")
            self.log_operation("reprocess", "success", f"Reprocessed {success_count} activities")
            self.update_daemon_last_run()
            
        except Exception as e:
            logger.error(f"Reprocess job failed: {str(e)}")
            self.log_operation("reprocess", "error", str(e))
        finally:
            session.close()
