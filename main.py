#!/usr/bin/env python3
import os
import time
import argparse
from dotenv import load_dotenv
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import urllib.request
import json
import logging

def create_schema(db_path="garmin.db"):
    """Create SQLite schema for activity tracking"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Activity (
        activity_id INTEGER PRIMARY KEY,
        start_time TEXT NOT NULL,
        filename TEXT UNIQUE NOT NULL,
        downloaded BOOLEAN NOT NULL DEFAULT 0
    )
    ''')
    conn.commit()
    conn.close()

def initialize_garmin_client():
    """Initialize authenticated Garmin client with rate limiting"""
    load_dotenv()
    
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")
    
    if not email or not password:
        raise ValueError("Missing GARMIN_EMAIL or GARMIN_PASSWORD environment variables")
    
        import garth
    # Add 2-second delay before API calls (rate limit mitigation)
    time.sleep(2)
    garth.login(email, password)
    return garth, email

def get_garmin_activities(garth_client):
    """Fetch activity IDs and start times from Garmin Connect"""
    url = "https://connect.garmin.com/activitylist-service/activities/search/activities?start=0&limit=100"
    req = urllib.request.Request(url)
    req.add_header('authorization', str(garth_client.client.oauth2_token))
    req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2816.0 Safari/537.36')
    req.add_header('nk', 'NT')
    
    try:
        response = urllib.request.urlopen(req)
        data = json.loads(response.read())
        activities = []
        for activity in data:
            activities.append((activity['activityId'], activity['startTimeLocal']))
        return activities
    except Exception as e:
        print(f"Error fetching activities: {str(e)}")
        return []

def sync_with_garmin(client, email):
    """Sync Garmin activities with local database"""
    db_path = "garmin.db"
    data_dir = Path("/data")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get activity IDs from Garmin API
    activity_ids = get_garmin_activities(client)
    
    for activity_id, start_time in activity_ids:
        timestamp = datetime.fromisoformat(start_time).strftime("%Y%m%d")
        filename = f"activity_{activity_id}_{timestamp}.fit"
        
        # Check if file exists in data directory
        file_path = data_dir / filename
        downloaded = 1 if file_path.exists() else 0
        
        # Insert or update activity record
        cursor.execute('''
        INSERT INTO Activity (activity_id, start_time, filename, downloaded)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(activity_id) DO UPDATE SET
        downloaded = ?
        ''', (activity_id, start_time, filename, downloaded, downloaded))
    
    conn.commit()
    conn.close()

def download_activity(garth_client, activity_id, filename):
    """Download a single activity FIT file from Garmin Connect"""
    data_dir = Path("/data")
    data_dir.mkdir(exist_ok=True)
    
    url = f"https://connect.garmin.com/modern/proxy/download-service/export/{activity_id}/fit"
    req = urllib.request.Request(url)
    req.add_header('authorization', str(garth_client.client.oauth2_token))
    req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2816.0 Safari/537.36')
    req.add_header('nk', 'NT')
    
    try:
        logging.info(f"Downloading activity {activity_id} to {filename}")
        response = urllib.request.urlopen(req)
        file_path = data_dir / filename
        with open(file_path, 'wb') as f:
            f.write(response.read())
        return True
    except Exception as e:
        logging.error(f"Error downloading activity {activity_id}: {str(e)}")
        return False

def download_missing_activities(garth_client):
    """Download all activities that are not yet downloaded"""
    db_path = "garmin.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all missing activities
    cursor.execute("SELECT activity_id, filename FROM Activity WHERE downloaded = 0")
    missing_activities = cursor.fetchall()
    
    conn.close()
    
    if not missing_activities:
        print("No missing activities to download")
        return False
    
    print(f"Found {len(missing_activities)} missing activities to download:")
    for activity_id, filename in missing_activities:
        print(f"Downloading {filename}...")
        success = download_activity(garth_client, activity_id, filename)
        if success:
            # Update database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE Activity SET downloaded = 1 WHERE activity_id = ?", (activity_id,))
            conn.commit()
            conn.close()
        time.sleep(2)  # Rate limiting
    
    return True

def get_activities(where_clause=None):
    """Retrieve activities from database based on filter"""
    conn = sqlite3.connect("garmin.db")
    cursor = conn.cursor()
    
    base_query = "SELECT activity_id, start_time, filename, downloaded FROM Activity"
    if where_clause:
        base_query += f" WHERE {where_clause}"
    
    cursor.execute(base_query)
    results = cursor.fetchall()
    conn.close()
    return results

def main():
    create_schema()
    parser = argparse.ArgumentParser(description="GarminSync CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Auth test command (Phase 1)
    auth_parser = subparsers.add_parser("auth-test", help="Test Garmin authentication")
    
    # List command (Phase 2)
    list_parser = subparsers.add_parser("list", help="List activities")
    list_group = list_parser.add_mutually_exclusive_group(required=True)
    list_group.add_argument("--all", action="store_true", help="List all activities")
    list_group.add_argument("--missing", action="store_true", help="List missing activities")
    list_group.add_argument("--downloaded", action="store_true", help="List downloaded activities")
    
    # Sync command (Phase 3)
    sync_parser = subparsers.add_parser("sync", help="Sync activities and download missing FIT files")
    
    args = parser.parse_args()

    if args.command == "auth-test":
        try:
            email, _ = initialize_garmin_client()
            print(f"✓ Successfully authenticated as {email}")
            print("Container is ready for Phase 2 development")
            exit(0)
        except Exception as e:
            print(f"✗ Authentication failed: {str(e)}")
            exit(1)
    
    elif args.command == "list":
        try:
            client, email = initialize_garmin_client()
            print("Syncing activities with Garmin Connect...")
            sync_with_garmin(client, email)
            
            where_clause = None
            if args.missing:
                where_clause = "downloaded = 0"
            elif args.downloaded:
                where_clause = "downloaded = 1"
            
            activities = get_activities(where_clause)
            print(f"\nFound {len(activities)} activities:")
            print(f"{'ID':<10} | {'Start Time':<20} | {'Status':<10} | Filename")
            print("-" * 80)
            for activity in activities:
                status = "✓" if activity[3] else "✗"
                print(f"{activity[0]:<10} | {activity[1][:19]:<20} | {status:<10} | {activity[2]}")
            
            exit(0)
        except Exception as e:
            print(f"Operation failed: {str(e)}")
            exit(1)
    
    elif args.command == "sync":
        try:
            client, email = initialize_garmin_client()
            print("Syncing activities with Garmin Connect...")
            sync_with_garmin(client, email)
            
            print("Downloading missing FIT files...")
            success = download_missing_activities(client)
            
            if success:
                print("All missing activities downloaded successfully")
                exit(0)
            else:
                print("Some activities failed to download")
                exit(1)
        except Exception as e:
            print(f"Operation failed: {str(e)}")
            exit(1)

if __name__ == "__main__":
    main()
