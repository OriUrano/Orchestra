"""
Unit tests for session_tracker.py (formerly usage_tracker.py)
"""
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
import pytest
from unittest.mock import patch, mock_open

from usage_tracker import SessionTracker, SessionInfo


class TestSessionInfo:
    """Test SessionInfo dataclass."""
    
    def test_default_values(self):
        session = SessionInfo()
        assert session.session_start is None
        assert session.is_active is False
    
    def test_elapsed_time_no_start(self):
        session = SessionInfo()
        assert session.elapsed_time == timedelta(0)
    
    def test_elapsed_time_with_start(self):
        start_time = datetime.now() - timedelta(hours=2)
        session = SessionInfo(session_start=start_time, is_active=True)
        
        # Should be approximately 2 hours
        elapsed = session.elapsed_time
        assert abs(elapsed.total_seconds() - 7200) < 60  # Within 1 minute tolerance
    
    def test_remaining_time(self):
        start_time = datetime.now() - timedelta(hours=2)
        session = SessionInfo(session_start=start_time, is_active=True)
        
        remaining = session.remaining_time
        expected_remaining = timedelta(hours=3)  # 5 - 2 = 3 hours
        assert abs(remaining.total_seconds() - expected_remaining.total_seconds()) < 60
    
    def test_is_in_final_window(self):
        # Test session with 10 minutes remaining
        start_time = datetime.now() - timedelta(hours=4, minutes=50)
        session = SessionInfo(session_start=start_time, is_active=True)
        
        assert session.is_in_final_window(15) is True
        assert session.is_in_final_window(5) is False
    
    def test_session_expired(self):
        # Test expired session
        start_time = datetime.now() - timedelta(hours=6)
        session = SessionInfo(session_start=start_time, is_active=True)
        assert session.session_expired is True
        
        # Test active session
        start_time = datetime.now() - timedelta(hours=2)
        session = SessionInfo(session_start=start_time, is_active=True)
        assert session.session_expired is False


class TestSessionTracker:
    """Test SessionTracker class."""
    
    @pytest.fixture
    def temp_claude_dir(self):
        """Create a temporary claude directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            claude_dir = os.path.join(temp_dir, ".claude")
            projects_dir = os.path.join(claude_dir, "projects")
            os.makedirs(projects_dir)
            yield claude_dir
    
    @pytest.fixture
    def sample_jsonl_data(self):
        """Sample JSONL data for testing."""
        now = datetime.now()
        return [
            {
                "type": "assistant",
                "timestamp": (now - timedelta(hours=2)).isoformat() + "Z",
                "message": {"usage": {"input_tokens": 100, "output_tokens": 50}}
            },
            {
                "type": "assistant", 
                "timestamp": (now - timedelta(hours=1)).isoformat() + "Z",
                "message": {"usage": {"input_tokens": 200, "output_tokens": 100}}
            },
            {
                "type": "assistant",
                "timestamp": now.isoformat() + "Z", 
                "message": {"usage": {"input_tokens": 150, "output_tokens": 75}}
            }
        ]
    
    def test_init_default_claude_dir(self):
        tracker = SessionTracker()
        assert tracker.claude_dir == os.path.expanduser("~/.claude")
    
    def test_init_custom_claude_dir(self, temp_claude_dir):
        tracker = SessionTracker(claude_dir=temp_claude_dir)
        assert tracker.claude_dir == temp_claude_dir
    
    def test_find_session_start_no_directory(self):
        tracker = SessionTracker(claude_dir="/nonexistent")
        result = tracker.find_session_start()
        assert result is None
    
    def test_find_session_start_empty_directory(self, temp_claude_dir):
        tracker = SessionTracker(claude_dir=temp_claude_dir)
        result = tracker.find_session_start()
        assert result is None
    
    def test_find_session_start_with_data(self, temp_claude_dir, sample_jsonl_data):
        # Create a test project with JSONL data
        project_dir = os.path.join(temp_claude_dir, "projects", "test_project")
        os.makedirs(project_dir)
        
        jsonl_file = os.path.join(project_dir, "conversation.jsonl")
        with open(jsonl_file, 'w') as f:
            for entry in sample_jsonl_data:
                f.write(json.dumps(entry) + "\n")
        
        tracker = SessionTracker(claude_dir=temp_claude_dir)
        session_start = tracker.find_session_start()
        
        # Should find the earliest timestamp within 5 hours
        assert session_start is not None
        assert isinstance(session_start, datetime)
    
    def test_find_session_start_gap_detection(self, temp_claude_dir):
        # Create data with a gap > 5 hours, but with multiple messages in recent session
        now = datetime.now()
        data_with_gap = [
            {
                "type": "assistant",
                "timestamp": (now - timedelta(hours=1)).isoformat() + "Z",
                "message": {"usage": {"input_tokens": 100, "output_tokens": 50}}
            },
            {
                "type": "assistant",
                "timestamp": (now - timedelta(minutes=30)).isoformat() + "Z",  # Add second message
                "message": {"usage": {"input_tokens": 150, "output_tokens": 75}}
            },
            {
                "type": "assistant",
                "timestamp": (now - timedelta(hours=7)).isoformat() + "Z",  # 7 hours ago - different session
                "message": {"usage": {"input_tokens": 200, "output_tokens": 100}}
            }
        ]
        
        project_dir = os.path.join(temp_claude_dir, "projects", "test_project")
        os.makedirs(project_dir)
        
        jsonl_file = os.path.join(project_dir, "conversation.jsonl")
        with open(jsonl_file, 'w') as f:
            for entry in data_with_gap:
                f.write(json.dumps(entry) + "\n")
        
        tracker = SessionTracker(claude_dir=temp_claude_dir)
        session_start = tracker.find_session_start()
        
        # Should only consider the recent session (1 hour ago)
        assert session_start is not None
        expected_time = now - timedelta(hours=1)
        time_diff = abs((session_start - expected_time).total_seconds())
        assert time_diff < 60  # Within 1 minute
    
    def test_get_current_session_no_data(self, temp_claude_dir):
        tracker = SessionTracker(claude_dir=temp_claude_dir)
        session = tracker.get_current_session()
        
        assert session.session_start is None
        assert session.is_active is False
    
    def test_get_current_session_with_data(self, temp_claude_dir, sample_jsonl_data):
        # Create test data
        project_dir = os.path.join(temp_claude_dir, "projects", "test_project")
        os.makedirs(project_dir)
        
        jsonl_file = os.path.join(project_dir, "conversation.jsonl")
        with open(jsonl_file, 'w') as f:
            for entry in sample_jsonl_data:
                f.write(json.dumps(entry) + "\n")
        
        tracker = SessionTracker(claude_dir=temp_claude_dir)
        session = tracker.get_current_session()
        
        assert session.session_start is not None
        assert session.is_active is True
    
    def test_check_session_status_no_session(self, temp_claude_dir):
        tracker = SessionTracker(claude_dir=temp_claude_dir)
        status = tracker.check_session_status()
        assert status == "no_session"
    
    def test_check_session_status_normal(self, temp_claude_dir):
        # Create recent session data
        now = datetime.now()
        recent_data = [
            {
                "type": "assistant",
                "timestamp": (now - timedelta(hours=1)).isoformat() + "Z",
                "message": {"usage": {"input_tokens": 100, "output_tokens": 50}}
            },
            {
                "type": "assistant",
                "timestamp": now.isoformat() + "Z",
                "message": {"usage": {"input_tokens": 200, "output_tokens": 100}}
            }
        ]
        
        project_dir = os.path.join(temp_claude_dir, "projects", "test_project")
        os.makedirs(project_dir)
        
        jsonl_file = os.path.join(project_dir, "conversation.jsonl")
        with open(jsonl_file, 'w') as f:
            for entry in recent_data:
                f.write(json.dumps(entry) + "\n")
        
        tracker = SessionTracker(claude_dir=temp_claude_dir)
        status = tracker.check_session_status()
        assert status == "normal"
    
    def test_check_session_status_maximize_usage(self, temp_claude_dir):
        # Create session data that's in final window (< 15 minutes remaining)
        now = datetime.now()
        final_window_data = [
            {
                "type": "assistant",
                "timestamp": (now - timedelta(hours=4, minutes=50)).isoformat() + "Z",  # 4h50m ago
                "message": {"usage": {"input_tokens": 100, "output_tokens": 50}}
            },
            {
                "type": "assistant",
                "timestamp": now.isoformat() + "Z",
                "message": {"usage": {"input_tokens": 200, "output_tokens": 100}}
            }
        ]
        
        project_dir = os.path.join(temp_claude_dir, "projects", "test_project")
        os.makedirs(project_dir)
        
        jsonl_file = os.path.join(project_dir, "conversation.jsonl")
        with open(jsonl_file, 'w') as f:
            for entry in final_window_data:
                f.write(json.dumps(entry) + "\n")
        
        tracker = SessionTracker(claude_dir=temp_claude_dir)
        status = tracker.check_session_status()
        assert status == "maximize_usage"
    
    def test_check_session_status_expired(self, temp_claude_dir):
        # Create session data that's exactly at the session boundary (5+ hours old)
        # This should be detected as no_session since it's beyond the 5-hour window
        now = datetime.now()
        expired_data = [
            {
                "type": "assistant",
                "timestamp": (now - timedelta(hours=6)).isoformat() + "Z",  # 6 hours ago
                "message": {"usage": {"input_tokens": 100, "output_tokens": 50}}
            }
        ]
        
        project_dir = os.path.join(temp_claude_dir, "projects", "test_project")
        os.makedirs(project_dir)
        
        jsonl_file = os.path.join(project_dir, "conversation.jsonl")
        with open(jsonl_file, 'w') as f:
            for entry in expired_data:
                f.write(json.dumps(entry) + "\n")
        
        tracker = SessionTracker(claude_dir=temp_claude_dir)
        status = tracker.check_session_status()
        # Session older than 5 hours is considered no_session, not session_expired
        assert status == "no_session"
    
    def test_get_session_summary_no_session(self, temp_claude_dir):
        tracker = SessionTracker(claude_dir=temp_claude_dir)
        summary = tracker.get_session_summary()
        
        assert summary["session_active"] is False
        assert "timestamp" in summary
        assert "session_start" not in summary
    
    def test_get_session_summary_active_session(self, temp_claude_dir, sample_jsonl_data):
        # Create test data
        project_dir = os.path.join(temp_claude_dir, "projects", "test_project")
        os.makedirs(project_dir)
        
        jsonl_file = os.path.join(project_dir, "conversation.jsonl")
        with open(jsonl_file, 'w') as f:
            for entry in sample_jsonl_data:
                f.write(json.dumps(entry) + "\n")
        
        tracker = SessionTracker(claude_dir=temp_claude_dir)
        summary = tracker.get_session_summary()
        
        assert summary["session_active"] is True
        assert "timestamp" in summary
        assert "session_start" in summary
        assert "session_elapsed_minutes" in summary
        assert "session_remaining_minutes" in summary
        assert "is_final_window" in summary
        assert "session_expired" in summary
    
    def test_backward_compatibility_alias(self):
        """Test that UsageTracker alias works for backward compatibility."""
        from usage_tracker import UsageTracker
        
        tracker = UsageTracker()
        assert isinstance(tracker, SessionTracker)


# Integration tests
class TestSessionTrackerIntegration:
    """Integration tests for SessionTracker with real-world scenarios."""
    
    @pytest.fixture
    def temp_claude_dir_integration(self):
        """Create a temporary claude directory for integration testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            claude_dir = os.path.join(temp_dir, ".claude")
            projects_dir = os.path.join(claude_dir, "projects")
            os.makedirs(projects_dir)
            yield claude_dir
    
    def test_multiple_projects_session_detection(self, temp_claude_dir_integration):
        """Test session detection across multiple projects."""
        now = datetime.now()
        
        # Create data in multiple projects
        for project_name in ["project1", "project2"]:
            project_dir = os.path.join(temp_claude_dir_integration, "projects", project_name)
            os.makedirs(project_dir)
            
            jsonl_file = os.path.join(project_dir, "conversation.jsonl")
            with open(jsonl_file, 'w') as f:
                # Add some session data
                entry = {
                    "type": "assistant",
                    "timestamp": (now - timedelta(hours=1)).isoformat() + "Z",
                    "message": {"usage": {"input_tokens": 100, "output_tokens": 50}}
                }
                f.write(json.dumps(entry) + "\n")
        
        tracker = SessionTracker(claude_dir=temp_claude_dir_integration)
        session = tracker.get_current_session()
        
        # Should detect session from either project
        assert session.is_active is True
        assert session.session_start is not None
    
    def test_malformed_jsonl_handling(self, temp_claude_dir_integration):
        """Test handling of malformed JSONL data."""
        project_dir = os.path.join(temp_claude_dir_integration, "projects", "test_project")
        os.makedirs(project_dir)
        
        jsonl_file = os.path.join(project_dir, "conversation.jsonl")
        with open(jsonl_file, 'w') as f:
            # Mix of valid and invalid JSON
            f.write('{"valid": "json"}\n')
            f.write('invalid json line\n')
            f.write('{"type": "assistant", "timestamp": "2024-01-01T12:00:00Z"}\n')
            f.write('')  # Empty line
            
        tracker = SessionTracker(claude_dir=temp_claude_dir_integration)
        
        # Should handle malformed data gracefully
        session_start = tracker.find_session_start()
        # Depending on the data, might be None or a valid datetime
        assert session_start is None or isinstance(session_start, datetime)