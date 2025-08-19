#!/usr/bin/env python3
"""
Simple test script to verify the new UI is working correctly
"""

import requests
import time
import sys
from pathlib import Path

# Add the parent directory to the path to import garminsync modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def test_ui_endpoints():
    """Test that the new UI endpoints are working correctly"""
    base_url = "http://localhost:8000"
    
    # Test endpoints to check
    endpoints = [
        "/",
        "/activities",
        "/config",
        "/logs",
        "/api/status",
        "/api/activities/stats",
        "/api/dashboard/stats"
    ]
    
    print("Testing UI endpoints...")
    
    failed_endpoints = []
    
    for endpoint in endpoints:
        try:
            url = base_url + endpoint
            print(f"Testing {url}...")
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                print(f"  ✓ {endpoint} - OK")
            else:
                print(f"  ✗ {endpoint} - Status code: {response.status_code}")
                failed_endpoints.append(endpoint)
                
        except requests.exceptions.ConnectionError:
            print(f"  ✗ {endpoint} - Connection error (server not running?)")
            failed_endpoints.append(endpoint)
        except requests.exceptions.Timeout:
            print(f"  ✗ {endpoint} - Timeout")
            failed_endpoints.append(endpoint)
        except Exception as e:
            print(f"  ✗ {endpoint} - Error: {e}")
            failed_endpoints.append(endpoint)
    
    if failed_endpoints:
        print(f"\nFailed endpoints: {failed_endpoints}")
        return False
    else:
        print("\nAll endpoints are working correctly!")
        return True

def test_api_endpoints():
    """Test that the new API endpoints are working correctly"""
    base_url = "http://localhost:8000"
    
    # Test API endpoints
    api_endpoints = [
        ("/api/activities", "GET"),
        ("/api/activities/1", "GET"),  # This might fail if activity doesn't exist, which is OK
        ("/api/dashboard/stats", "GET")
    ]
    
    print("\nTesting API endpoints...")
    
    for endpoint, method in api_endpoints:
        try:
            url = base_url + endpoint
            print(f"Testing {method} {url}...")
            
            if method == "GET":
                response = requests.get(url, timeout=10)
            else:
                response = requests.post(url, timeout=10)
            
            # For activity details, 404 is acceptable if activity doesn't exist
            if endpoint == "/api/activities/1" and response.status_code == 404:
                print(f"  ✓ {endpoint} - OK (404 expected if activity doesn't exist)")
                continue
                
            if response.status_code == 200:
                print(f"  ✓ {endpoint} - OK")
                # Try to parse JSON
                try:
                    data = response.json()
                    print(f"    Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                except:
                    print("    Response is not JSON")
            else:
                print(f"  ✗ {endpoint} - Status code: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"  ✗ {endpoint} - Connection error (server not running?)")
        except requests.exceptions.Timeout:
            print(f"  ✗ {endpoint} - Timeout")
        except Exception as e:
            print(f"  ✗ {endpoint} - Error: {e}")

if __name__ == "__main__":
    print("GarminSync UI Test Script")
    print("=" * 30)
    
    # Test UI endpoints
    ui_success = test_ui_endpoints()
    
    # Test API endpoints
    test_api_endpoints()
    
    print("\n" + "=" * 30)
    if ui_success:
        print("UI tests completed successfully!")
        sys.exit(0)
    else:
        print("Some UI tests failed!")
        sys.exit(1)
