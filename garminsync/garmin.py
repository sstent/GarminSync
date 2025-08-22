"""Garmin API client module for GarminSync application."""

import logging
import os
import time

from garminconnect import (Garmin, GarminConnectAuthenticationError,
                           GarminConnectConnectionError,
                           GarminConnectTooManyRequestsError)

logger = logging.getLogger(__name__)


class GarminClient:
    """Garmin API client for interacting with Garmin Connect services."""

    def __init__(self):
        self.client = None

    def authenticate(self):
        """Authenticate using credentials from environment variables"""
        email = os.getenv("GARMIN_EMAIL")
        password = os.getenv("GARMIN_PASSWORD")

        if not email or not password:
            raise ValueError("Garmin credentials not found in environment variables")

        try:
            self.client = Garmin(email, password)
            self.client.login()
            logger.info("Successfully authenticated with Garmin Connect")
            return self.client
        except GarminConnectAuthenticationError as e:
            logger.error("Authentication failed: %s", e)
            raise ValueError(f"Garmin authentication failed: {e}") from e
        except GarminConnectConnectionError as e:
            logger.error("Connection error: %s", e)
            raise ConnectionError(f"Failed to connect to Garmin Connect: {e}") from e
        except Exception as e:
            logger.error("Unexpected error during authentication: %s", e)
            raise RuntimeError(f"Unexpected error during authentication: {e}") from e

    def get_activities(self, start=0, limit=10):
        """Get list of activities with rate limiting

        Args:
            start: Starting index for activities
            limit: Maximum number of activities to return

        Returns:
            List of activities or None if failed

        Raises:
            ValueError: If authentication fails
            ConnectionError: If connection to Garmin fails
            RuntimeError: For other unexpected errors
        """
        if not self.client:
            self.authenticate()

        try:
            activities = self.client.get_activities(start, limit)
            time.sleep(2)  # Rate limiting
            logger.info("Retrieved %d activities", len(activities) if activities else 0)
            return activities
        except (GarminConnectConnectionError, TimeoutError, GarminConnectTooManyRequestsError) as e:
            logger.error("Network error while fetching activities: %s", e)
            raise ConnectionError(f"Failed to fetch activities: {e}") from e
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Unexpected error while fetching activities: %s", e)
            raise RuntimeError(f"Failed to fetch activities: {e}") from e

    def download_activity_fit(self, activity_id):
        """Download .fit file for a specific activity"""
        if not self.client:
            self.authenticate()

        print(f"Attempting to download activity {activity_id}")

        # Try multiple methods to download FIT file
        methods_to_try = [
            # Method 1: No format parameter (most likely to work)
            lambda: self.client.download_activity(activity_id),
            # Method 2: Use correct parameter name with different values
            lambda: self.client.download_activity(activity_id, dl_fmt="FIT"),
            lambda: self.client.download_activity(
                activity_id, dl_fmt="tcx"
            ),  # Fallback format
        ]

        last_exception = None

        for i, method in enumerate(methods_to_try, 1):
            try:
                # Try the download method
                print(f"Trying download method {i}...")
                fit_data = method()

                if fit_data:
                    print(
                        f"Successfully downloaded {len(fit_data)} bytes using method {i}"
                    )
                    time.sleep(2)  # Rate limiting
                    return fit_data
                print(f"Method {i} returned empty data")

            # Catch connection errors specifically
            except (GarminConnectConnectionError, ConnectionError) as e:  # pylint: disable=duplicate-except
                print(f"Method {i} failed with connection error: {e}")
                last_exception = e
                continue
            # Catch all other exceptions as a fallback
            except (TimeoutError, GarminConnectTooManyRequestsError) as e:
                print(f"Method {i} failed with retryable error: {e}")
                last_exception = e
                continue
            except Exception as e:  # pylint: disable=broad-except
                print(f"Method {i} failed with unexpected error: "
                      f"{type(e).__name__}: {e}")
                last_exception = e
                continue

        # If all methods failed, raise the last exception
        if last_exception:
            raise RuntimeError(
                f"All download methods failed. Last error: {last_exception}"
            ) from last_exception
        raise RuntimeError(
            "All download methods failed, but no specific error was captured"
        )

    def get_activity_details(self, activity_id):
        """Get detailed information about a specific activity

        Args:
            activity_id: ID of the activity to retrieve

        Returns:
            Activity details dictionary or None if failed
        """
        if not self.client:
            self.authenticate()

        try:
            activity_details = self.client.get_activity(activity_id)
            time.sleep(2)  # Rate limiting
            logger.info("Retrieved details for activity %s", activity_id)
            return activity_details
        except (GarminConnectConnectionError, TimeoutError) as e:
            logger.error(
                "Connection/timeout error fetching activity details for %s: %s",
                activity_id, e
            )
            return None
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Unexpected error fetching activity details for %s: %s", activity_id, e)
            return None

    # Example usage and testing function


def test_download(activity_id):
    """Test function to verify download functionality"""
    client = GarminClient()
    try:
        fit_data = client.download_activity_fit(activity_id)

        # Verify the data looks like a FIT file
        if not fit_data or len(fit_data) <= 14:
            print("❌ Downloaded data is empty or too small")
            return None

        header = fit_data[:14]
        if b".FIT" in header or header[8:12] == b".FIT":
            print("✅ Downloaded data appears to be a valid FIT file")
        else:
            print("⚠️ Downloaded data may not be a FIT file")
            print(f"Header: {header}")
        return fit_data

    except Exception as e:  # pylint: disable=broad-except
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
