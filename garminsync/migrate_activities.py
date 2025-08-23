#!/usr/bin/env python3
"""
Migration script to populate new activity fields from FIT files or Garmin API
"""

import os
import sys
from datetime import datetime

from sqlalchemy import MetaData, Table, create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the path to import garminsync modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from garminsync.database import Activity, get_session, init_db
from garminsync.garmin import GarminClient
from garminsync.activity_parser import get_activity_metrics


def add_columns_to_database():
    """Add new columns to the activities table if they don't exist"""

# Add the parent directory to the path to import garminsync modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from garminsync.database import Activity, get_session, init_db
from garminsync.garmin import GarminClient


def add_columns_to_database():
    """Add new columns to the activities table if they don't exist"""
    print("Adding new columns to database...", flush=True)

    # Get database engine
    db_path = os.path.join(os.getenv("DATA_DIR", "data"), "garmin.db")
    engine = create_engine(f"sqlite:///{db_path}")

    try:
        # Reflect the existing database schema
        metadata = MetaData()
        metadata.reflect(bind=engine)

        # Get the activities table
        activities_table = metadata.tables["activities"]

        # Check if columns already exist
        existing_columns = [col.name for col in activities_table.columns]
        new_columns = [
            "activity_type",
            "duration",
            "distance",
            "max_heart_rate",
            "avg_power",
            "calories",
        ]

        # Add missing columns
        with engine.connect() as conn:
            for column_name in new_columns:
                if column_name not in existing_columns:
                    print(f"Adding column {column_name}...", flush=True)
                    if column_name in ["distance", "avg_power"]:
                        conn.execute(
                            text(
                                f"ALTER TABLE activities ADD COLUMN {column_name} REAL"
                            )
                        )
                    elif column_name in ["duration", "max_heart_rate", "calories"]:
                        conn.execute(
                            text(
                                f"ALTER TABLE activities ADD COLUMN {column_name} INTEGER"
                            )
                        )
                    else:
                        conn.execute(
                            text(
                                f"ALTER TABLE activities ADD COLUMN {column_name} TEXT"
                            )
                        )
                    conn.commit()
                    print(f"Column {column_name} added successfully", flush=True)
                else:
                    print(f"Column {column_name} already exists", flush=True)

        print("Database schema updated successfully", flush=True)
        return True

    except Exception as e:
        print(f"Failed to update database schema: {e}", flush=True)
        return False



def migrate_activities():
    """Migrate activities to populate new fields from FIT files or Garmin API"""
    print("Starting activity migration...", flush=True)

    # First, add columns to database
    if not add_columns_to_database():
        return False

    # Initialize Garmin client
    try:
        client = GarminClient()
        print("Garmin client initialized successfully", flush=True)
    except Exception as e:
        print(f"Failed to initialize Garmin client: {e}", flush=True)
        # Continue with migration but without Garmin data
        client = None

    # Get database session
    session = get_session()

    try:
        # Get all activities that need to be updated (those with NULL activity_type)
        activities = (
            session.query(Activity).filter(Activity.activity_type.is_(None)).all()
        )
        print(f"Found {len(activities)} activities to migrate", flush=True)

        # If no activities found, try to get all activities (in case activity_type column was just added)
        if len(activities) == 0:
            activities = session.query(Activity).all()
            print(f"Found {len(activities)} total activities", flush=True)

        updated_count = 0
        error_count = 0

        for i, activity in enumerate(activities):
            try:
                print(
                    f"Processing activity {i+1}/{len(activities)} (ID: {activity.activity_id})", 
                    flush=True
                )

                # Use shared parser to get activity metrics
                activity_details = get_activity_metrics(activity, client)
                if activity_details is not None:
                    print(f"  Successfully parsed metrics for activity {activity.activity_id}", flush=True)
                else:
                    print(f"  Could not retrieve metrics for activity {activity.activity_id}", flush=True)

                # Update activity fields if we have details
                if activity_details:
                    # Update activity fields
                    activity.activity_type = activity_details.get(
                        "activityType", {}
                    ).get("typeKey")

                    # Extract duration in seconds
                    duration = activity_details.get("summaryDTO", {}).get("duration")
                    if duration is not None:
                        activity.duration = int(float(duration))

                    # Extract distance in meters
                    distance = activity_details.get("summaryDTO", {}).get("distance")
                    if distance is not None:
                        activity.distance = float(distance)

                    # Extract max heart rate
                    max_hr = activity_details.get("summaryDTO", {}).get("maxHR")
                    if max_hr is not None:
                        activity.max_heart_rate = int(float(max_hr))

                    # Extract average power
                    avg_power = activity_details.get("summaryDTO", {}).get("avgPower")
                    if avg_power is not None:
                        activity.avg_power = float(avg_power)

                    # Extract calories
                    calories = activity_details.get("summaryDTO", {}).get("calories")
                    if calories is not None:
                        activity.calories = int(float(calories))
                else:
                    # Set default values for activity type if we can't get details
                    activity.activity_type = "Unknown"

                # Update last sync timestamp
                activity.last_sync = datetime.now().isoformat()

                session.commit()
                updated_count += 1

                # Print progress every 10 activities
                if (i + 1) % 10 == 0:
                    print(f"  Progress: {i+1}/{len(activities)} activities processed", flush=True)

            except Exception as e:
                print(f"  Error processing activity {activity.activity_id}: {e}", flush=True)
                session.rollback()
                error_count += 1
                continue

        print(f"Migration completed. Updated: {updated_count}, Errors: {error_count}", flush=True)
        return True  # Allow partial success

    except Exception as e:
        print(f"Migration failed: {e}", flush=True)
        return False
    finally:
        session.close()


if __name__ == "__main__":
    success = migrate_activities()
    sys.exit(0 if success else 1)
