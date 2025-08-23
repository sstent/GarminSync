#!/usr/bin/env python3
"""
Migration script to populate activity fields from FIT files or Garmin API
"""

import os
import sys
from datetime import datetime
import logging

from sqlalchemy import MetaData, Table, create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path to import garminsync modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from garminsync.database import Activity, get_session, init_db
from garminsync.garmin import GarminClient
from garminsync.activity_parser import get_activity_metrics

def migrate_activities():
    """Migrate activities to populate fields from FIT files or Garmin API"""
    logger.info("Starting activity migration...")
    
    # We assume database schema has been updated via Alembic migrations
    # during container startup. Columns should already exist.

    # Initialize Garmin client
    try:
        client = GarminClient()
        logger.info("Garmin client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Garmin client: {e}")
        # Continue with migration but without Garmin data
        client = None

    # Get database session
    session = get_session()

    try:
        # Get all activities that need to be updated (those with NULL activity_type)
        activities = session.query(Activity).filter(Activity.activity_type.is_(None)).all()
        logger.info(f"Found {len(activities)} activities to migrate")

        # If no activities found, exit early
        if not activities:
            logger.info("No activities found for migration")
            return True

        updated_count = 0
        error_count = 0

        for i, activity in enumerate(activities):
            try:
                logger.info(f"Processing activity {i+1}/{len(activities)} (ID: {activity.activity_id})")

                # Use shared parser to get activity metrics
                activity_details = get_activity_metrics(activity, client)
                
                # Update activity fields if we have details
                if activity_details:
                    logger.info(f"Successfully parsed metrics for activity {activity.activity_id}")
                    
                    # Update activity fields
                    activity.activity_type = activity_details.get("activityType", {}).get("typeKey", "Unknown")
                    
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
                    # Set default values if we can't get details
                    activity.activity_type = "Unknown"
                    logger.warning(f"Could not retrieve metrics for activity {activity.activity_id}")

                # Update last sync timestamp
                activity.last_sync = datetime.now().isoformat()

                session.commit()
                updated_count += 1

                # Log progress every 10 activities
                if (i + 1) % 10 == 0:
                    logger.info(f"Progress: {i+1}/{len(activities)} activities processed")

            except Exception as e:
                logger.error(f"Error processing activity {activity.activity_id}: {e}")
                session.rollback()
                error_count += 1
                continue

        logger.info(f"Migration completed. Updated: {updated_count}, Errors: {error_count}")
        return updated_count > 0 or error_count == 0  # Success if we updated any or had no errors

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False
    finally:
        session.close()

if __name__ == "__main__":
    success = migrate_activities()
    sys.exit(0 if success else 1)
