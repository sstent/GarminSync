import os
import time
from garminconnect import Garmin

class GarminClient:
    def __init__(self):
        self.client = None
        
    def authenticate(self):
        """Authenticate using credentials from environment variables"""
        email = os.getenv("GARMIN_EMAIL")
        password = os.getenv("GARMIN_PASSWORD")
        
        if not email or not password:
            raise ValueError("Garmin credentials not found in environment variables")
            
        self.client = Garmin(email, password)
        self.client.login()
        return self.client
        
    def get_activities(self, start=0, limit=10):
        """Get list of activities with rate limiting"""
        if not self.client:
            self.authenticate()
            
        activities = self.client.get_activities(start, limit)
        time.sleep(2)  # Rate limiting
        return activities
        
    def download_activity_fit(self, activity_id):
        """Download .fit file for a specific activity"""
        if not self.client:
            self.authenticate()
            
        fit_data = self.client.download_activity(activity_id, dl_fmt='fit')
        time.sleep(2)  # Rate limiting
        return fit_data

# Example usage:
# client = GarminClient()
# activities = client.get_activities(0, 10)
# fit_data = client.download_activity_fit(12345)
