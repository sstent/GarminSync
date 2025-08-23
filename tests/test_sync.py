import pytest
import sys
from unittest.mock import Mock, patch

# Add the project root to the Python path
sys.path.insert(0, '/app')

from garminsync.database import sync_database
from garminsync.garmin import GarminClient


def test_sync_database_with_valid_activities():
    """Test sync_database with valid API response"""
    mock_client = Mock(spec=GarminClient)
    mock_client.get_activities.return_value = [
        {"activityId": 12345, "startTimeLocal": "2023-01-01T10:00:00"},
        {"activityId": 67890, "startTimeLocal": "2023-01-02T11:00:00"}
    ]
    
    with patch('garminsync.database.get_session') as mock_session:
        mock_session.return_value.query.return_value.filter_by.return_value.first.return_value = None
        
        sync_database(mock_client)
        
        # Verify get_activities was called
        mock_client.get_activities.assert_called_once_with(0, 1000)
        
        # Verify database operations
        mock_session.return_value.add.assert_called()
        mock_session.return_value.commit.assert_called()


def test_sync_database_with_none_activities():
    """Test sync_database with None response from API"""
    mock_client = Mock(spec=GarminClient)
    mock_client.get_activities.return_value = None
    
    with patch('garminsync.database.get_session') as mock_session:
        sync_database(mock_client)
        
        # Verify get_activities was called
        mock_client.get_activities.assert_called_once_with(0, 1000)
        
        # Verify no database operations
        mock_session.return_value.add.assert_not_called()
        mock_session.return_value.commit.assert_not_called()


def test_sync_database_with_missing_fields():
    """Test sync_database with activities missing required fields"""
    mock_client = Mock(spec=GarminClient)
    mock_client.get_activities.return_value = [
        {"activityId": 12345},  # Missing startTimeLocal
        {"startTimeLocal": "2023-01-02T11:00:00"},  # Missing activityId
        {"activityId": 67890, "startTimeLocal": "2023-01-03T12:00:00"}  # Valid
    ]
    
    with patch('garminsync.database.get_session') as mock_session:
        mock_session.return_value.query.return_value.filter_by.return_value.first.return_value = None
        
        sync_database(mock_client)
        
        # Verify only one activity was added (the valid one)
        assert mock_session.return_value.add.call_count == 1
        mock_session.return_value.commit.assert_called()


def test_sync_database_with_existing_activities():
    """Test sync_database doesn't duplicate existing activities"""
    mock_client = Mock(spec=GarminClient)
    mock_client.get_activities.return_value = [
        {"activityId": 12345, "startTimeLocal": "2023-01-01T10:00:00"}
    ]
    
    with patch('garminsync.database.get_session') as mock_session:
        # Mock existing activity
        mock_session.return_value.query.return_value.filter_by.return_value.first.return_value = Mock()
        
        sync_database(mock_client)
        
        # Verify no new activities were added
        mock_session.return_value.add.assert_not_called()
        mock_session.return_value.commit.assert_called()


def test_sync_database_with_invalid_activity_data():
    """Test sync_database with invalid activity data types"""
    mock_client = Mock(spec=GarminClient)
    mock_client.get_activities.return_value = [
        "invalid activity data",  # Not a dict
        None,  # None value
        {"activityId": 12345, "startTimeLocal": "2023-01-01T10:00:00"}  # Valid
    ]
    
    with patch('garminsync.database.get_session') as mock_session:
        mock_session.return_value.query.return_value.filter_by.return_value.first.return_value = None
        
        sync_database(mock_client)
        
        # Verify only one activity was added (the valid one)
        assert mock_session.return_value.add.call_count == 1
        mock_session.return_value.commit.assert_called()
