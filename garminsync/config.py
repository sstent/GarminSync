import os

from dotenv import load_dotenv


def load_config():
    """Load environment variables from .env file"""
    load_dotenv()


class Config:
    GARMIN_EMAIL = os.getenv("GARMIN_EMAIL")
    GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")

    @classmethod
    def validate(cls):
        if not cls.GARMIN_EMAIL or not cls.GARMIN_PASSWORD:
            raise ValueError("Missing GARMIN_EMAIL or GARMIN_PASSWORD in environment")
