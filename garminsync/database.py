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
                    downloaded=False
                )
                session.add(new_activity)
        
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        raise e
    finally:
        session.close()

# Example usage:
# from .garmin import GarminClient
# client = GarminClient()
# sync_database(client)
