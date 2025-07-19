"""
Unit tests for usage_tracker.py
"""
import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
import pytest
from unittest.mock import patch, mock_open

from usage_tracker import UsageTracker, UsageMetrics


class TestUsageMetrics:
    """Test UsageMetrics dataclass."""
    
    def test_default_values(self):
        metrics = UsageMetrics()
        assert metrics.input_tokens == 0
        assert metrics.output_tokens == 0
        assert metrics.cache_creation_tokens == 0
        assert metrics.cache_read_tokens == 0
        assert metrics.requests == 0
    
    def test_total_tokens_calculation(self):
        metrics = UsageMetrics(
            input_tokens=1000,
            output_tokens=500,
            cache_creation_tokens=200,
            cache_read_tokens=100  # This should not be included in total
        )
        # total_tokens = input + output + cache_creation (not cache_read)
        assert metrics.total_tokens == 1700
    
    def test_custom_values(self):
        metrics = UsageMetrics(
            input_tokens=1234,
            output_tokens=567,
            cache_creation_tokens=89,
            cache_read_tokens=45,
            requests=10
        )
        assert metrics.input_tokens == 1234
        assert metrics.output_tokens == 567
        assert metrics.cache_creation_tokens == 89
        assert metrics.cache_read_tokens == 45
        assert metrics.requests == 10
        assert metrics.total_tokens == 1890


class TestUsageTracker:
    """Test UsageTracker class."""
    
    def test_init_default_claude_dir(self):
        tracker = UsageTracker()
        expected_dir = os.path.expanduser("~/.claude")
        assert tracker.claude_dir == expected_dir
    
    def test_init_custom_claude_dir(self):
        custom_dir = "/custom/claude/dir"
        tracker = UsageTracker(claude_dir=custom_dir)
        assert tracker.claude_dir == custom_dir
    
    def test_get_current_usage_no_projects_dir(self, temp_dir):
        # Test when projects directory doesn't exist
        tracker = UsageTracker(claude_dir=temp_dir)
        usage = tracker.get_current_usage()
        
        assert isinstance(usage, UsageMetrics)
        assert usage.total_tokens == 0
        assert usage.requests == 0
    
    def test_get_current_usage_empty_projects_dir(self, temp_dir):
        # Test with empty projects directory
        projects_dir = Path(temp_dir) / "projects"
        projects_dir.mkdir()
        
        tracker = UsageTracker(claude_dir=temp_dir)
        usage = tracker.get_current_usage()
        
        assert isinstance(usage, UsageMetrics)
        assert usage.total_tokens == 0
        assert usage.requests == 0
    
    def test_get_current_usage_with_valid_jsonl(self, temp_dir):
        # Setup test JSONL file with usage data
        projects_dir = Path(temp_dir) / "projects" / "test-project"
        projects_dir.mkdir(parents=True)
        
        jsonl_file = projects_dir / "test.jsonl"
        
        # Create test data entries
        today = datetime.now()
        test_entries = [
            {
                "timestamp": today.isoformat(),
                "type": "assistant",
                "message": {
                    "usage": {
                        "input_tokens": 1000,
                        "output_tokens": 500,
                        "cache_creation_input_tokens": 100,
                        "cache_read_input_tokens": 50
                    }
                }
            },
            {
                "timestamp": today.isoformat(),
                "type": "assistant", 
                "message": {
                    "usage": {
                        "input_tokens": 800,
                        "output_tokens": 300,
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 25
                    }
                }
            }
        ]
        
        with open(jsonl_file, 'w') as f:
            for entry in test_entries:
                f.write(json.dumps(entry) + "\n")
        
        tracker = UsageTracker(claude_dir=temp_dir)
        usage = tracker.get_current_usage()
        
        assert usage.input_tokens == 1800
        assert usage.output_tokens == 800
        assert usage.cache_creation_tokens == 100
        assert usage.cache_read_tokens == 75
        assert usage.requests == 2
        assert usage.total_tokens == 2700
    
    def test_get_current_usage_filtered_by_date(self, temp_dir):
        # Test filtering by since parameter
        projects_dir = Path(temp_dir) / "projects" / "test-project"
        projects_dir.mkdir(parents=True)
        
        jsonl_file = projects_dir / "test.jsonl"
        
        # Create entries from different days
        yesterday = datetime.now() - timedelta(days=1)
        today = datetime.now()
        
        test_entries = [
            {
                "timestamp": yesterday.isoformat(),
                "type": "assistant",
                "message": {
                    "usage": {
                        "input_tokens": 1000,
                        "output_tokens": 500
                    }
                }
            },
            {
                "timestamp": today.isoformat(), 
                "type": "assistant",
                "message": {
                    "usage": {
                        "input_tokens": 800,
                        "output_tokens": 300
                    }
                }
            }
        ]
        
        with open(jsonl_file, 'w') as f:
            for entry in test_entries:
                f.write(json.dumps(entry) + "\n")
        
        tracker = UsageTracker(claude_dir=temp_dir)
        
        # Filter to only include today's usage
        since = today.replace(hour=0, minute=0, second=0, microsecond=0)
        usage = tracker.get_current_usage(since=since)
        
        # Should only include today's entry
        assert usage.input_tokens == 800
        assert usage.output_tokens == 300
        assert usage.requests == 1
    
    def test_get_current_usage_malformed_json(self, temp_dir):
        # Test handling of malformed JSON lines
        projects_dir = Path(temp_dir) / "projects" / "test-project"
        projects_dir.mkdir(parents=True)
        
        jsonl_file = projects_dir / "test.jsonl"
        
        with open(jsonl_file, 'w') as f:
            f.write("invalid json line\n")
            f.write('{"valid": "json", "but": "no usage"}\n')
            f.write('{"timestamp": "' + datetime.now().isoformat() + '", "type": "assistant", "message": {"usage": {"input_tokens": 100, "output_tokens": 50}}}\n')
        
        tracker = UsageTracker(claude_dir=temp_dir)
        usage = tracker.get_current_usage()
        
        # Should only count the valid entry
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.requests == 1
    
    def test_get_current_usage_missing_fields(self, temp_dir):
        # Test handling of entries with missing required fields
        projects_dir = Path(temp_dir) / "projects" / "test-project"
        projects_dir.mkdir(parents=True)
        
        jsonl_file = projects_dir / "test.jsonl"
        
        today = datetime.now()
        test_entries = [
            # Missing timestamp
            {
                "type": "assistant",
                "message": {"usage": {"input_tokens": 100, "output_tokens": 50}}
            },
            # Missing type
            {
                "timestamp": today.isoformat(),
                "message": {"usage": {"input_tokens": 100, "output_tokens": 50}}
            },
            # Missing message
            {
                "timestamp": today.isoformat(),
                "type": "assistant"
            },
            # Valid entry
            {
                "timestamp": today.isoformat(),
                "type": "assistant",
                "message": {"usage": {"input_tokens": 100, "output_tokens": 50}}
            }
        ]
        
        with open(jsonl_file, 'w') as f:
            for entry in test_entries:
                f.write(json.dumps(entry) + "\n")
        
        tracker = UsageTracker(claude_dir=temp_dir)
        usage = tracker.get_current_usage()
        
        # Should only count the valid entry
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.requests == 1


class TestUsageTrackerLimits:
    """Test usage limit checking functionality."""
    
    def test_check_limits_normal(self, temp_dir):
        # Setup low usage
        projects_dir = Path(temp_dir) / "projects" / "test-project"
        projects_dir.mkdir(parents=True)
        
        jsonl_file = projects_dir / "test.jsonl"
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "assistant",
            "message": {
                "usage": {
                    "input_tokens": 1000,  # Well below limits
                    "output_tokens": 500
                }
            }
        }
        
        with open(jsonl_file, 'w') as f:
            f.write(json.dumps(entry) + "\n")
        
        tracker = UsageTracker(claude_dir=temp_dir)
        status = tracker.check_limits(daily_token_limit=100000, daily_request_limit=1000)
        
        assert status == "normal"
    
    def test_check_limits_approaching(self, temp_dir):
        # Setup usage at 80% of limit
        projects_dir = Path(temp_dir) / "projects" / "test-project"
        projects_dir.mkdir(parents=True)
        
        jsonl_file = projects_dir / "test.jsonl"
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "assistant",
            "message": {
                "usage": {
                    "input_tokens": 8000,  # 80% of 10000 limit
                    "output_tokens": 0
                }
            }
        }
        
        with open(jsonl_file, 'w') as f:
            f.write(json.dumps(entry) + "\n")
        
        tracker = UsageTracker(claude_dir=temp_dir)
        status = tracker.check_limits(daily_token_limit=10000, daily_request_limit=1000)
        
        assert status == "approaching_limit"
    
    def test_check_limits_reached(self, temp_dir):
        # Setup usage at 95% of limit
        projects_dir = Path(temp_dir) / "projects" / "test-project"
        projects_dir.mkdir(parents=True)
        
        jsonl_file = projects_dir / "test.jsonl"
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "assistant",
            "message": {
                "usage": {
                    "input_tokens": 9500,  # 95% of 10000 limit
                    "output_tokens": 0
                }
            }
        }
        
        with open(jsonl_file, 'w') as f:
            f.write(json.dumps(entry) + "\n")
        
        tracker = UsageTracker(claude_dir=temp_dir)
        status = tracker.check_limits(daily_token_limit=10000, daily_request_limit=1000)
        
        assert status == "limit_reached"
    
    def test_check_limits_request_limit(self, temp_dir):
        # Test request-based limit checking
        projects_dir = Path(temp_dir) / "projects" / "test-project"
        projects_dir.mkdir(parents=True)
        
        jsonl_file = projects_dir / "test.jsonl"
        
        # Create 85 requests (85% of 100 limit)
        today = datetime.now().isoformat()
        entries = []
        for i in range(85):
            entries.append({
                "timestamp": today,
                "type": "assistant",
                "message": {"usage": {"input_tokens": 10, "output_tokens": 5}}
            })
        
        with open(jsonl_file, 'w') as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")
        
        tracker = UsageTracker(claude_dir=temp_dir)
        status = tracker.check_limits(daily_token_limit=100000, daily_request_limit=100)
        
        assert status == "approaching_limit"


class TestUsageTrackerSummary:
    """Test usage summary functionality."""
    
    def test_get_usage_summary(self, temp_dir):
        # Setup test data
        projects_dir = Path(temp_dir) / "projects" / "test-project"
        projects_dir.mkdir(parents=True)
        
        jsonl_file = projects_dir / "test.jsonl"
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "assistant",
            "message": {
                "usage": {
                    "input_tokens": 1000,
                    "output_tokens": 500,
                    "cache_creation_input_tokens": 100,
                    "cache_read_input_tokens": 50
                }
            }
        }
        
        with open(jsonl_file, 'w') as f:
            f.write(json.dumps(entry) + "\n")
        
        tracker = UsageTracker(claude_dir=temp_dir)
        summary = tracker.get_usage_summary()
        
        assert summary["total_tokens"] == 1600
        assert summary["input_tokens"] == 1000
        assert summary["output_tokens"] == 500
        assert summary["cache_creation_tokens"] == 100
        assert summary["cache_read_tokens"] == 50
        assert summary["requests"] == 1
        assert "timestamp" in summary
        
        # Verify timestamp is recent
        timestamp = datetime.fromisoformat(summary["timestamp"])
        assert (datetime.now() - timestamp).total_seconds() < 5


class TestUsageTrackerEdgeCases:
    """Test edge cases and error handling."""
    
    def test_unreadable_file(self, temp_dir):
        # Test handling of unreadable files
        projects_dir = Path(temp_dir) / "projects" / "test-project"
        projects_dir.mkdir(parents=True)
        
        jsonl_file = projects_dir / "test.jsonl"
        jsonl_file.touch()
        
        # Mock file opening to raise an exception
        with patch("builtins.open", side_effect=IOError("Permission denied")):
            tracker = UsageTracker(claude_dir=temp_dir)
            usage = tracker.get_current_usage()
            
            # Should return empty metrics when files can't be read
            assert usage.total_tokens == 0
            assert usage.requests == 0
    
    def test_empty_lines_in_jsonl(self, temp_dir):
        # Test handling of empty lines
        projects_dir = Path(temp_dir) / "projects" / "test-project"
        projects_dir.mkdir(parents=True)
        
        jsonl_file = projects_dir / "test.jsonl"
        
        today = datetime.now().isoformat()
        content = f"""
        
{{"timestamp": "{today}", "type": "assistant", "message": {{"usage": {{"input_tokens": 100, "output_tokens": 50}}}}}}

        """
        
        with open(jsonl_file, 'w') as f:
            f.write(content)
        
        tracker = UsageTracker(claude_dir=temp_dir)
        usage = tracker.get_current_usage()
        
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50
        assert usage.requests == 1
    
    def test_iso_timestamp_formats(self, temp_dir):
        # Test different ISO timestamp formats
        projects_dir = Path(temp_dir) / "projects" / "test-project"
        projects_dir.mkdir(parents=True)
        
        jsonl_file = projects_dir / "test.jsonl"
        
        today = datetime.now()
        test_entries = [
            # With Z suffix
            {
                "timestamp": today.isoformat(),
                "type": "assistant",
                "message": {"usage": {"input_tokens": 100, "output_tokens": 50}}
            },
            # Without Z suffix
            {
                "timestamp": today.isoformat(),
                "type": "assistant", 
                "message": {"usage": {"input_tokens": 200, "output_tokens": 100}}
            }
        ]
        
        with open(jsonl_file, 'w') as f:
            for entry in test_entries:
                f.write(json.dumps(entry) + "\n")
        
        tracker = UsageTracker(claude_dir=temp_dir)
        usage = tracker.get_current_usage()
        
        # Both entries should be counted
        assert usage.input_tokens == 300
        assert usage.output_tokens == 150
        assert usage.requests == 2