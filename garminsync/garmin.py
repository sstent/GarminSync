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
            
        print(f"Attempting to download activity {activity_id}")
        
        # Try multiple methods to download FIT file
        methods_to_try = [
            # Method 1: No format parameter (most likely to work)
            lambda: self.client.download_activity(activity_id),
            
            # Method 2: Use 'fmt' instead of 'dl_fmt'
            lambda: self.client.download_activity(activity_id, fmt='fit'),
            
            # Method 3: Use 'format' parameter
            lambda: self.client.download_activity(activity_id, format='fit'),
            
            # Method 4: Try original parameter name with different values
            lambda: self.client.download_activity(activity_id, dl_fmt='FIT'),
            lambda: self.client.download_activity(activity_id, dl_fmt='tcx'),  # Fallback format
        ]
        
        last_exception = None
        
        for i, method in enumerate(methods_to_try, 1):
            try:
                print(f"Trying download method {i}...")
                fit_data = method()
                
                if fit_data:
                    print(f"Successfully downloaded {len(fit_data)} bytes using method {i}")
                    time.sleep(2)  # Rate limiting
                    return fit_data
                else:
                    print(f"Method {i} returned empty data")
                    
            except Exception as e:
                print(f"Method {i} failed: {type(e).__name__}: {e}")
                last_exception = e
                continue
        
        # If all methods failed, raise the last exception
        raise RuntimeError(f"All download methods failed. Last error: {last_exception}")

    def get_activity_details(self, activity_id):
        """Get detailed information about a specific activity"""
        if not self.client:
            self.authenticate()
            
        try:
            activity_details = self.client.get_activity_by_id(activity_id)
            time.sleep(2)  # Rate limiting
            return activity_details
        except Exception as e:
            print(f"Failed to get activity details for {activity_id}: {e}")
            return None

# Example usage and testing function
def test_download(activity_id):
    """Test function to verify download functionality"""
    client = GarminClient()
    try:
        fit_data = client.download_activity_fit(activity_id)
        
        # Verify the data looks like a FIT file
        if fit_data and len(fit_data) > 14:
            # FIT files start with specific header
            header = fit_data[:14]
            if b'.FIT' in header or header[8:12] == b'.FIT':
                print("✅ Downloaded data appears to be a valid FIT file")
                return fit_data
            else:
                print("⚠️ Downloaded data may not be a FIT file")
                print(f"Header: {header}")
                return fit_data
        else:
            print("❌ Downloaded data is empty or too small")
            return None
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return None

if __name__ == "__main__":
    # Test with a sample activity ID if provided
    import sys
    if len(sys.argv) > 1:
        test_activity_id = sys.argv[1]
        print(f"Testing download for activity ID: {test_activity_id}")
        test_download(test_activity_id)
    else:
        print("Usage: python garmin.py <activity_id>")
        print("This will test the download functionality with the provided activity ID")