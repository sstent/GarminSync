"""Database module for GarminSync application."""

import os
from datetime import datetime

from sqlalchemy import Boolean, Column, Float, Integer, String, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Activity(Base):
    """Activity model representing a Garmin activity record."""

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
    downloaded = Column(Boolean, default=False, nullable=False)
    created_at = Column(String, nullable=False)
    last_sync = Column(String, nullable=True)

    @classmethod
    def get_paginated(cls, page=1, per_page=10):
        """Get paginated list of activities.

        Args:
            page: Page number (1-based)
            per_page: Number of items per page

        Returns:
            Pagination object with activities
        """
        session = get_session()
        try:
            query = session.query(cls).order_by(cls.start_time.desc())
            page = int(page)
            per_page = int(per_page)
            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            return pagination
        finally:
            session.close()

    def to_dict(self):
        """Convert activity to dictionary representation.

        Returns:
            Dictionary with activity data
        """
        return {
            "id": self.activity_id,
            "name": self.filename or "Unnamed Activity",
            "distance": self.distance,
            "duration": self.duration,
            "start_time": self.start_time,
            "activity_type": self.activity_type,
            "max_heart_rate": self.max_heart_rate,
            "avg_heart_rate": self.avg_heart_rate,
            "avg_power": self.avg_power,
            "calories": self.calories,
        }


class DaemonConfig(Base):
    """Daemon configuration model."""

    __tablename__ = "daemon_config"

    id = Column(Integer, primary_key=True, default=1)
    enabled = Column(Boolean, default=True, nullable=False)
    schedule_cron = Column(String, default="0 */6 * * *", nullable=False)
    last_run = Column(String, nullable=True)
    next_run = Column(String, nullable=True)
    status = Column(String, default="stopped", nullable=False)


class SyncLog(Base):
    """Sync log model for tracking sync operations."""

    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(String, nullable=False)
    operation = Column(String, nullable=False)
    status = Column(String, nullable=False)
    message = Column(String, nullable=True)
    activities_processed = Column(Integer, default=0, nullable=False)
    activities_downloaded = Column(Integer, default=0, nullable=False)


def init_db():
    """Initialize database connection and create tables.

    Returns:
        SQLAlchemy engine instance
    """
    db_path = os.path.join(os.getenv("DATA_DIR", "data"), "garmin.db")
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    return engine


def get_session():
    """Create a new database session.

    Returns:
        SQLAlchemy session instance
    """
    engine = init_db()
    Session = sessionmaker(bind=engine)
    return Session()


from garminsync.activity_parser import get_activity_metrics

def sync_database(garmin_client):
    """Sync local database with Garmin Connect activities.

    Args:
        garmin_client: GarminClient instance for API communication
    """
    session = get_session()
    try:
        activities = garmin_client.get_activities(0, 1000)

        if not activities:
            print("No activities returned from Garmin API")
            return

        for activity_data in activities:
            if not isinstance(activity_data, dict):
                print(f"Invalid activity data: {activity_data}")
                continue

            activity_id = activity_data.get("activityId")
            start_time = activity_data.get("startTimeLocal")
            
            if not activity_id or not start_time:
                print(f"Missing required fields in activity: {activity_data}")
                continue

            existing = session.query(Activity).filter_by(activity_id=activity_id).first()
            
            # Create or update basic activity info
            if not existing:
                activity = Activity(
                    activity_id=activity_id,
                    start_time=start_time,
                    downloaded=False,
                    created_at=datetime.now().isoformat(),
                    last_sync=datetime.now().isoformat(),
                )
                session.add(activity)
                session.flush()  # Assign ID
            else:
                activity = existing
            
            # Update metrics using shared parser
            metrics = get_activity_metrics(activity, garmin_client)
            if metrics:
                activity.activity_type = metrics.get("activityType", {}).get("typeKey")
                
                # Extract duration in seconds
                duration = metrics.get("summaryDTO", {}).get("duration")
                if duration is not None:
                    activity.duration = int(float(duration))
                
                # Extract distance in meters
                distance = metrics.get("summaryDTO", {}).get("distance")
                if distance is not None:
                    activity.distance = float(distance)
                
                # Extract heart rates
                max_hr = metrics.get("summaryDTO", {}).get("maxHR")
                if max_hr is not None:
                    activity.max_heart_rate = int(float(max_hr))
                
                avg_hr = metrics.get("summaryDTO", {}).get("avgHR", None) or \
                         metrics.get("summaryDTO", {}).get("averageHR", None)
                if avg_hr is not None:
                    activity.avg_heart_rate = int(float(avg_hr))
                
                # Extract power and calories
                avg_power = metrics.get("summaryDTO", {}).get("avgPower")
                if avg_power is not None:
                    activity.avg_power = float(avg_power)
                
                calories = metrics.get("summaryDTO", {}).get("calories")
                if calories is not None:
                    activity.calories = int(float(calories))
            
            # Update sync timestamp
            activity.last_sync = datetime.now().isoformat()

        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_offline_stats():
    """Return statistics about cached data without API calls.

    Returns:
        Dictionary with activity statistics
    """
    session = get_session()
    try:
        total = session.query(Activity).count()
        downloaded = session.query(Activity).filter_by(downloaded=True).count()
        missing = total - downloaded
        last_sync = session.query(Activity).order_by(Activity.last_sync.desc()).first()
        return {
            "total": total,
            "downloaded": downloaded,
            "missing": missing,
            "last_sync": last_sync.last_sync if last_sync else "Never synced",
        }
    finally:
        session.close()
