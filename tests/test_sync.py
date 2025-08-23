import pytest
import sys
from unittest.mock import Mock, patch, MagicMock

# Add the project root to the Python path
sys.path.insert(0, '/app')

from garminsync.database import sync_database, Activity, get_activity_metrics

def test_sync_database_with_valid_activities():
    """Test sync_database with valid API response"""
    mock_client = Mock()
    mock_client.get_activities.return_value = [
        {"activityId": 12345, "startTimeLocal": "2023-01-01T10:00:00"},
        {"activityId": 67890, "startTimeLocal": "2023-01-02T11:00:00"}
    ]
    
    mock_session = MagicMock()
    mock_session.query.return_value.filter_by.return_value.first.return_value = None
    
    with patch('garminsync.database.get_session', return_value=mock_session), \
         patch('garminsync.database.get_activity_metrics', return_value={
             "activityType": {"typeKey": "running"},
             "summaryDTO": {
                 "duration": 3600,
                 "distance": 10.0,
                 "maxHR": 180,
                 "calories": 400
             }
         }):
        
        sync_database(mock_client)
        
        # Verify activities processed
        assert mock_session.add.call_count == 2
        assert mock_session.commit.called

def test_sync_database_with_none_activities():
    """Test sync_database with None response from API"""
    mock_client = Mock()
    mock_client.get_activities.return_value = None
    
    mock_session = MagicMock()
    
    with patch('garminsync.database.get_session', return_value=mock_session):
        sync_database(mock_client)
        mock_session.add.assert_not_called()

def test_sync_database_with_missing_fields():
    """Test sync_database with activities missing required fields"""
    mock_client = Mock()
    mock_client.get_activities.return_value = [
        {"activityId": 12345},
        {"startTimeLocal": "2023-01-02T11:00:00"},
        {"activityId": 67890, "startTimeLocal": "2023-01-03T12:00:00"}
    ]
    
    # Create a mock that returns None for existing activity
    mock_session = MagicMock()
    mock_session.query.return_value.filter_by.return_value.first.return_value = None
    
    with patch('garminsync.database.get_session', return_value=mock_session), \
         patch('garminsync.database.get_activity_metrics', return_value={
             "summaryDTO": {"duration": 3600.0}
         }):
        sync_database(mock_client)
        # Only valid activity should be added
        assert mock_session.add.call_count == 1
        added_activity = mock_session.add.call_args[0][0]
        assert added_activity.activity_id == 67890

def test_sync_database_with_existing_activities():
    """Test sync_database doesn't duplicate existing activities"""
    mock_client = Mock()
    mock_client.get_activities.return_value = [
        {"activityId": 12345, "startTimeLocal": "2023-01-01T10:00:00"}
    ]
    
    mock_session = MagicMock()
    mock_session.query.return_value.filter_by.return_value.first.return_value = Mock()
    
    with patch('garminsync.database.get_session', return_value=mock_session), \
         patch('garminsync.database.get_activity_metrics', return_value={
             "summaryDTO": {"duration": 3600.0}
         }):
        sync_database(mock_client)
        mock_session.add.assert_not_called()

def test_sync_database_with_invalid_activity_data():
    """Test sync_database with invalid activity data types"""
    mock_client = Mock()
    mock_client.get_activities.return_value = [
        "invalid data",
        None,
        {"activityId": 12345, "startTimeLocal": "2023-01-01T10:00:00"}
    ]
    
    # Create a mock that returns None for existing activity
    mock_session = MagicMock()
    mock_session.query.return_value.filter_by.return_value.first.return_value = None
    
    with patch('garminsync.database.get_session', return_value=mock_session), \
         patch('garminsync.database.get_activity_metrics', return_value={
             "summaryDTO": {"duration": 3600.0}
         }):
        sync_database(mock_client)
        # Only valid activity should be added
        assert mock_session.add.call_count == 1
        added_activity = mock_session.add.call_args[0][0]
        assert added_activity.activity_id == 12345
