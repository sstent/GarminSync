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

        for activity in activities:
            # Check if activity is a dictionary and has required fields
            if not isinstance(activity, dict):
                print(f"Invalid activity data: {activity}")
                continue

            # Safely access dictionary keys
            activity_id = activity.get("activityId")
            start_time = activity.get("startTimeLocal")
            avg_heart_rate = activity.get("averageHR", None)
            calories = activity.get("calories", None)

            if not activity_id or not start_time:
                print(f"Missing required fields in activity: {activity}")
                continue

            existing = (
                session.query(Activity).filter_by(activity_id=activity_id).first()
            )
            if not existing:
                new_activity = Activity(
                    activity_id=activity_id,
                    start_time=start_time,
                    avg_heart_rate=avg_heart_rate,
                    calories=calories,
                    downloaded=False,
                    created_at=datetime.now().isoformat(),
                    last_sync=datetime.now().isoformat(),
                )
                session.add(new_activity)

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
