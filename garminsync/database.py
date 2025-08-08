import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

Base = declarative_base()

class Activity(Base):
    __tablename__ = 'activities'
    
    activity_id = Column(Integer, primary_key=True)
    start_time = Column(String, nullable=False)
    filename = Column(String, unique=True, nullable=True)
    downloaded = Column(Boolean, default=False, nullable=False)
    last_sync = Column(String, nullable=True)  # ISO timestamp of last sync

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

def init_db():
    """Initialize database connection and create tables"""
    db_path = os.path.join(os.getenv("DATA_DIR", "data"), "garmin.db")
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    return engine

def get_session():
    """Create a new database session"""
    engine = init_db()
    Session = sessionmaker(bind=engine)
    return Session()

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
                    last_sync=datetime.now().isoformat()
                )
                session.add(new_activity)
        
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        raise e
    finally:
        session.close()
        
def get_offline_stats():
    """Return statistics about cached data without API calls"""
    session = get_session()
    try:
        total = session.query(Activity).count()
        downloaded = session.query(Activity).filter_by(downloaded=True).count()
        missing = total - downloaded
        # Get most recent sync timestamp
        last_sync = session.query(Activity).order_by(Activity.last_sync.desc()).first()
        return {
            'total': total,
            'downloaded': downloaded,
            'missing': missing,
            'last_sync': last_sync.last_sync if last_sync else 'Never synced'
        }
    finally:
        session.close()

# Example usage:
# from .garmin import GarminClient
# client = GarminClient()
# sync_database(client)
