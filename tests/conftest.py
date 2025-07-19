"""
Pytest configuration and shared fixtures for Orchestra tests.
"""
import os
import tempfile
import yaml
from pathlib import Path
from datetime import datetime
import pytest
from unittest.mock import Mock, patch


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_repo_config():
    """Sample repository configuration for testing."""
    return {
        'repositories': [
            {
                'name': 'test-repo-1',
                'path': '/tmp/test-repo-1',
                'priority': 'high',
                'watch_branches': ['main', 'develop']
            },
            {
                'name': 'test-repo-2', 
                'path': '/tmp/test-repo-2',
                'priority': 'medium',
                'watch_branches': ['main']
            },
            {
                'name': 'test-repo-3',
                'path': '/tmp/test-repo-3', 
                'priority': 'low',
                'watch_branches': ['main']
            }
        ]
    }


@pytest.fixture
def sample_settings_config():
    """Sample settings configuration for testing."""
    return {
        'settings': {
            'max_daily_tokens': 100000,
            'max_daily_requests': 1000,
            'workday_max_repos': 2,
            'log_level': 'INFO',
            'claude_code_enabled': True
        }
    }


@pytest.fixture
def config_dir(temp_dir, sample_repo_config, sample_settings_config):
    """Create a temporary config directory with test configs."""
    config_path = Path(temp_dir) / "config"
    config_path.mkdir()
    
    # Write repos.yaml
    repos_file = config_path / "repos.yaml"
    with open(repos_file, 'w') as f:
        yaml.dump(sample_repo_config, f)
    
    # Write settings.yaml  
    settings_file = config_path / "settings.yaml"
    with open(settings_file, 'w') as f:
        yaml.dump(sample_settings_config, f)
        
    return str(config_path)


@pytest.fixture
def mock_claude_dir(temp_dir):
    """Create a mock Claude directory structure for usage tracking tests."""
    claude_dir = Path(temp_dir) / ".claude"
    projects_dir = claude_dir / "projects"
    project_dir = projects_dir / "test-project"
    project_dir.mkdir(parents=True)
    
    # Create sample JSONL file with usage data
    jsonl_file = project_dir / "usage.jsonl"
    sample_entries = [
        {
            "timestamp": "2024-01-15T10:00:00Z",
            "usage": {
                "input_tokens": 1000,
                "output_tokens": 500,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0
            }
        },
        {
            "timestamp": "2024-01-15T11:00:00Z", 
            "usage": {
                "input_tokens": 800,
                "output_tokens": 300,
                "cache_creation_tokens": 100,
                "cache_read_tokens": 50
            }
        }
    ]
    
    with open(jsonl_file, 'w') as f:
        for entry in sample_entries:
            f.write(f"{entry}\n")
    
    return str(claude_dir)


@pytest.fixture
def mock_usage_tracker(mock_claude_dir):
    """Mock UsageTracker with test data."""
    with patch('usage_tracker.UsageTracker') as mock_tracker:
        tracker = mock_tracker.return_value
        tracker.claude_dir = mock_claude_dir
        tracker.get_current_usage.return_value.total_tokens = 2750
        tracker.get_current_usage.return_value.requests = 2
        tracker.check_limits.return_value = "within_limits"
        tracker.get_usage_summary.return_value = {
            "total_tokens": 2750,
            "requests": 2,
            "input_tokens": 1800,
            "output_tokens": 800
        }
        yield tracker


@pytest.fixture
def mock_github_integration():
    """Mock GitHubIntegration for testing."""
    with patch('github_integration.GitHubIntegration') as mock_gh:
        gh = mock_gh.return_value
        gh.get_recent_activity.return_value = {
            "pulls": [],
            "issues": [],
            "commits": []
        }
        gh.get_repo_status.return_value = {
            "has_changes": False,
            "branch": "main", 
            "ahead": 0,
            "behind": 0
        }
        yield gh


@pytest.fixture
def mock_claude_code_sdk():
    """Mock claude_code_sdk for testing."""
    with patch('claude_code_sdk.query') as mock_sdk:
        mock_sdk.return_value = "Mock Claude response"
        yield mock_sdk


@pytest.fixture
def fixed_datetime():
    """Fixed datetime for consistent testing."""
    # Tuesday, January 16, 2024, 10:00 AM (workday)
    return datetime(2024, 1, 16, 10, 0, 0)


@pytest.fixture
def workday_datetime():
    """Datetime during workday hours."""
    # Tuesday 10:00 AM
    return datetime(2024, 1, 16, 10, 0, 0)


@pytest.fixture 
def worknight_datetime():
    """Datetime during worknight hours."""
    # Tuesday 8:00 PM
    return datetime(2024, 1, 16, 20, 0, 0)


@pytest.fixture
def weekend_datetime():
    """Datetime during weekend hours."""
    # Saturday 2:00 PM
    return datetime(2024, 1, 20, 14, 0, 0)


@pytest.fixture
def off_hours_datetime():
    """Datetime during off hours."""
    # Friday 2:00 AM
    return datetime(2024, 1, 19, 2, 0, 0)