"""Database module for GarminSync application with async support."""

import os
from datetime import datetime
from contextlib import asynccontextmanager

from sqlalchemy import Boolean, Column, Float, Integer, String
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.orm import sessionmaker

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
    reprocessed = Column(Boolean, default=False, nullable=False)
    created_at = Column(String, nullable=False)
    last_sync = Column(String, nullable=True)

    @classmethod
    async def get_paginated(cls, db, page=1, per_page=10):
        """Get paginated list of activities (async)."""
        async with db.begin() as session:
            query = select(cls).order_by(cls.start_time.desc())
            result = await session.execute(query.offset((page-1)*per_page).limit(per_page))
            activities = result.scalars().all()
            count_result = await session.execute(select(select(cls).count()))
            total = count_result.scalar_one()
            return {
                "items": activities,
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page
            }

    def to_dict(self):
        """Convert activity to dictionary representation."""
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

    @classmethod
    async def get(cls, db):
        """Get configuration record (async)."""
        async with db.begin() as session:
            result = await session.execute(select(cls))
            return result.scalars().first()


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


# Database initialization and session management
engine = None
async_session = None

async def init_db():
    """Initialize database connection and create tables."""
    global engine, async_session
    db_path = os.getenv("DB_PATH", "data/garmin.db")
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        pool_size=10, 
        max_overflow=20,
        pool_pre_ping=True
    )
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_db():
    """Async context manager for database sessions."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except SQLAlchemyError:
            await session.rollback()
            raise


# Compatibility layer for legacy sync functions
def get_legacy_session():
    """Temporary synchronous session for migration purposes."""
    db_path = os.getenv("DB_PATH", "data/garmin.db")
    sync_engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(sync_engine)
    Session = sessionmaker(bind=sync_engine)
    return Session()


async def sync_database(garmin_client):
    """Sync local database with Garmin Connect activities (async)."""
    from garminsync.activity_parser import get_activity_metrics
    async with get_db() as session:
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

                result = await session.execute(
                    select(Activity).filter_by(activity_id=activity_id)
                )
                existing = result.scalars().first()
                
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
                else:
                    activity = existing
                
                # Update metrics using shared parser
                metrics = get_activity_metrics(activity, garmin_client)
                if metrics:
                    activity.activity_type = metrics.get("activityType", {}).get("typeKey")
                    # ... rest of metric processing ...
                
                # Update sync timestamp
                activity.last_sync = datetime.now().isoformat()

            await session.commit()
        except SQLAlchemyError as e:
            await session.rollback()
            raise e


async def get_offline_stats():
    """Return statistics about cached data without API calls (async)."""
    async with get_db() as session:
        try:
            result = await session.execute(select(Activity))
            total = len(result.scalars().all())
            
            result = await session.execute(
                select(Activity).filter_by(downloaded=True)
            )
            downloaded = len(result.scalars().all())
            
            result = await session.execute(
                select(Activity).order_by(Activity.last_sync.desc())
            )
            last_sync = result.scalars().first()
            
            return {
                "total": total,
                "downloaded": downloaded,
                "missing": total - downloaded,
                "last_sync": last_sync.last_sync if last_sync else "Never synced",
            }
        except SQLAlchemyError as e:
            print(f"Database error: {e}")
            return {
                "total": 0,
                "downloaded": 0,
                "missing": 0,
                "last_sync": "Error"
            }
