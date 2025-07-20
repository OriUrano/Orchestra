"""
Unit tests for mode_executors.py
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from mode_executors import (
    RepoConfig, 
    BaseExecutor, 
    WorkdayExecutor,
    WorknightExecutor, 
    WeekendExecutor,
    get_executor
)
from usage_tracker import SessionTracker


class TestRepoConfig:
    """Test RepoConfig dataclass."""
    
    def test_repo_config_creation(self):
        repo = RepoConfig(
            name="test-repo",
            path="/tmp/test-repo",
            priority="high",
            watch_branches=["main", "develop"]
        )
        
        assert repo.name == "test-repo"
        assert repo.path == "/tmp/test-repo"
        assert repo.priority == "high"
        assert repo.watch_branches == ["main", "develop"]


class TestBaseExecutor:
    """Test BaseExecutor base class."""
    
    @pytest.fixture
    def mock_session_tracker(self):
        """Mock session tracker for testing."""
        mock_tracker = Mock(spec=SessionTracker)
        mock_tracker.check_session_status.return_value = "normal"
        mock_tracker.get_session_summary.return_value = {
            "session_active": True,
            "session_remaining_minutes": 120,
            "timestamp": "2024-01-01T12:00:00"
        }
        return mock_tracker
    
    def test_init(self, mock_session_tracker):
        executor = BaseExecutor(mock_session_tracker)
        assert executor.session_tracker == mock_session_tracker
    
    def test_should_skip_due_to_session_expired(self, mock_session_tracker):
        mock_session_tracker.check_session_status.return_value = "session_expired"
        
        executor = BaseExecutor(mock_session_tracker)
        assert executor.should_skip_due_to_session() == True
    
    def test_should_skip_due_to_session_normal(self, mock_session_tracker):
        mock_session_tracker.check_session_status.return_value = "normal"
        
        executor = BaseExecutor(mock_session_tracker)
        assert executor.should_skip_due_to_session() == False
    
    def test_should_maximize_usage(self, mock_session_tracker):
        mock_session_tracker.check_session_status.return_value = "maximize_usage"
        
        executor = BaseExecutor(mock_session_tracker)
        assert executor.should_maximize_usage() == True
    
    def test_log_session_status(self, mock_session_tracker, capsys):
        mock_session_tracker.check_session_status.return_value = "normal"
        mock_session_tracker.get_session_summary.return_value = {
            "session_active": True,
            "session_remaining_minutes": 90,
            "timestamp": "2024-01-01T12:00:00"
        }
        
        executor = BaseExecutor(mock_session_tracker)
        executor.log_session_status()
        
        captured = capsys.readouterr()
        assert "Session status: normal" in captured.out
        assert "90 min remaining" in captured.out


class TestWorkdayExecutor:
    """Test WorkdayExecutor functionality."""
    
    @pytest.fixture
    def mock_session_tracker(self):
        mock_tracker = Mock(spec=SessionTracker)
        mock_tracker.check_session_status.return_value = "normal"
        mock_tracker.get_session_summary.return_value = {
            "session_active": True,
            "session_remaining_minutes": 120,
            "timestamp": "2024-01-01T12:00:00"
        }
        return mock_tracker
    
    @pytest.fixture
    def sample_repos(self):
        return [
            RepoConfig("high-repo-1", "/tmp/high1", "high", ["main"]),
            RepoConfig("high-repo-2", "/tmp/high2", "high", ["main"]),
            RepoConfig("high-repo-3", "/tmp/high3", "high", ["main"]),
            RepoConfig("high-repo-4", "/tmp/high4", "high", ["main"]),
            RepoConfig("medium-repo", "/tmp/medium", "medium", ["main"]),
            RepoConfig("low-repo", "/tmp/low", "low", ["main"])
        ]
    
    def test_execute_skip_due_to_session_expired(self, mock_session_tracker):
        mock_session_tracker.check_session_status.return_value = "session_expired"
        
        executor = WorkdayExecutor(mock_session_tracker)
        result = executor.execute([])
        
        assert result["status"] == "skipped"
        assert result["reason"] == "session_expired"
    
    @patch('mode_executors.GitHubIntegration')
    def test_execute_success(self, mock_gh_class, mock_session_tracker, sample_repos):
        # Mock GitHub integration
        mock_gh = Mock()
        mock_gh.gather_workday_data.return_value = {
            'pending_reviews': [],
            'my_prs': [],
            'assigned_issues': [],
            'repo_status': {},
            'branches': []
        }
        mock_gh_class.return_value = mock_gh
        
        executor = WorkdayExecutor(mock_session_tracker)
        result = executor.execute(sample_repos)
        
        assert result["status"] == "completed"
        assert "results" in result
        
        # Should only process first 3 high-priority repos
        assert len(result["results"]) == 3
        assert "high-repo-1" in result["results"]
        assert "high-repo-2" in result["results"]
        assert "high-repo-3" in result["results"]
        assert "high-repo-4" not in result["results"]
    
    def test_execute_maximize_usage_mode(self, mock_session_tracker, sample_repos):
        mock_session_tracker.check_session_status.return_value = "maximize_usage"
        
        with patch('mode_executors.GitHubIntegration') as mock_gh_class:
            mock_gh = Mock()
            mock_gh.gather_workday_data.return_value = {
                'pending_reviews': [],
                'my_prs': [],
                'assigned_issues': [],
                'repo_status': {},
                'branches': []
            }
            mock_gh_class.return_value = mock_gh
            
            executor = WorkdayExecutor(mock_session_tracker)
            result = executor.execute(sample_repos)
            
            # In maximize mode, should process all high priority repos
            assert result["status"] == "completed"
            high_priority_count = sum(1 for repo in sample_repos if repo.priority == "high")
            assert len(result["results"]) == high_priority_count


class TestWorknightExecutor:
    """Test WorknightExecutor functionality."""
    
    @pytest.fixture
    def mock_session_tracker(self):
        mock_tracker = Mock(spec=SessionTracker)
        mock_tracker.check_session_status.return_value = "normal"
        mock_tracker.get_session_summary.return_value = {
            "session_active": True,
            "session_remaining_minutes": 120,
            "timestamp": "2024-01-01T12:00:00"
        }
        return mock_tracker
    
    def test_execute_skip_due_to_session_expired(self, mock_session_tracker):
        mock_session_tracker.check_session_status.return_value = "session_expired"
        
        executor = WorknightExecutor(mock_session_tracker)
        result = executor.execute([])
        
        assert result["status"] == "skipped"
        assert result["reason"] == "session_expired"
    
    @patch('task_scheduler.TaskScheduler')
    def test_execute_success(self, mock_scheduler_class, mock_session_tracker):
        mock_scheduler_class.return_value = Mock()
        
        repos = [
            RepoConfig("repo1", "/tmp/repo1", "high", ["main"]),
            RepoConfig("repo2", "/tmp/repo2", "medium", ["main"])
        ]
        
        executor = WorknightExecutor(mock_session_tracker)
        
        # Mock the _process_repo_worknight method to avoid complex setup
        executor._process_repo_worknight = Mock(return_value={"status": "ready"})
        
        result = executor.execute(repos)
        
        assert result["status"] == "completed"
        assert "results" in result
        assert len(result["results"]) == 2


class TestWeekendExecutor:
    """Test WeekendExecutor functionality."""
    
    @pytest.fixture
    def mock_session_tracker(self):
        mock_tracker = Mock(spec=SessionTracker)
        mock_tracker.check_session_status.return_value = "normal"
        mock_tracker.get_session_summary.return_value = {
            "session_active": True,
            "session_remaining_minutes": 120,
            "timestamp": "2024-01-01T12:00:00"
        }
        return mock_tracker
    
    def test_execute_skip_due_to_session_expired(self, mock_session_tracker):
        mock_session_tracker.check_session_status.return_value = "session_expired"
        
        executor = WeekendExecutor(mock_session_tracker)
        result = executor.execute([])
        
        assert result["status"] == "skipped"
        assert result["reason"] == "session_expired"
    
    @patch('task_scheduler.TaskScheduler')
    @patch('mode_executors.GitHubIntegration')
    def test_execute_all_repos_prioritized(self, mock_gh_class, mock_scheduler_class, mock_session_tracker):
        # Mock dependencies
        mock_scheduler_class.return_value = Mock()
        mock_gh = Mock()
        mock_gh.gather_weekend_data.return_value = {
            'security_files': {},
            'dependency_files': {},
            'vulnerabilities': {'total_issues': 0},
            'my_prs': []
        }
        mock_gh_class.return_value = mock_gh
        
        repos = [
            RepoConfig("low-repo", "/tmp/low", "low", ["main"]),
            RepoConfig("high-repo", "/tmp/high", "high", ["main"]),
            RepoConfig("medium-repo", "/tmp/medium", "medium", ["main"])
        ]
        
        executor = WeekendExecutor(mock_session_tracker)
        
        # Mock the complex weekend processing
        executor._process_repo_weekend = Mock(return_value={"status": "ready"})
        
        result = executor.execute(repos)
        
        assert result["status"] == "completed"
        assert len(result["results"]) == 3
        
        # Verify high priority repo was processed first
        call_args = [call[0][0] for call in executor._process_repo_weekend.call_args_list]
        assert call_args[0].priority == "high"


class TestGetExecutor:
    """Test executor factory function."""
    
    @pytest.fixture
    def mock_session_tracker(self):
        return Mock(spec=SessionTracker)
    
    def test_get_workday_executor(self, mock_session_tracker):
        executor = get_executor("workday", mock_session_tracker)
        assert isinstance(executor, WorkdayExecutor)
        assert executor.session_tracker == mock_session_tracker
    
    @patch('task_scheduler.TaskScheduler')
    def test_get_worknight_executor(self, mock_scheduler_class, mock_session_tracker):
        mock_scheduler_class.return_value = Mock()
        executor = get_executor("worknight", mock_session_tracker)
        assert isinstance(executor, WorknightExecutor)
        assert executor.session_tracker == mock_session_tracker
    
    @patch('task_scheduler.TaskScheduler') 
    def test_get_weekend_executor(self, mock_scheduler_class, mock_session_tracker):
        mock_scheduler_class.return_value = Mock()
        executor = get_executor("weekend", mock_session_tracker)
        assert isinstance(executor, WeekendExecutor)
        assert executor.session_tracker == mock_session_tracker
    
    def test_get_executor_invalid_mode(self, mock_session_tracker):
        with pytest.raises(ValueError, match="Unknown work mode: invalid"):
            get_executor("invalid", mock_session_tracker)


class TestSessionBasedLogic:
    """Test session-based execution logic."""
    
    @pytest.fixture
    def mock_session_tracker(self):
        return Mock(spec=SessionTracker)
    
    def test_maximize_usage_behavior(self, mock_session_tracker):
        """Test behavior when in maximize usage window."""
        mock_session_tracker.check_session_status.return_value = "maximize_usage"
        mock_session_tracker.get_session_summary.return_value = {
            "session_active": True,
            "session_remaining_minutes": 10,  # In final window
            "timestamp": "2024-01-01T12:00:00"
        }
        
        # Test with workday executor
        executor = WorkdayExecutor(mock_session_tracker)
        assert executor.should_maximize_usage() == True
        
        # Should process more aggressively in maximize mode
        repos = [
            RepoConfig("high-1", "/tmp/high1", "high", ["main"]),
            RepoConfig("high-2", "/tmp/high2", "high", ["main"]),
            RepoConfig("medium-1", "/tmp/medium1", "medium", ["main"])
        ]
        
        with patch('mode_executors.GitHubIntegration') as mock_gh_class:
            mock_gh = Mock()
            mock_gh.gather_workday_data.return_value = {
                'pending_reviews': [],
                'my_prs': [],
                'assigned_issues': [],
                'repo_status': {},
                'branches': []
            }
            mock_gh_class.return_value = mock_gh
            
            result = executor.execute(repos)
            
            # Should process all high priority repos in maximize mode
            assert result["status"] == "completed"
            assert len(result["results"]) == 2  # Only high priority repos
    
    def test_no_session_behavior(self, mock_session_tracker):
        """Test behavior when no session is active."""
        mock_session_tracker.check_session_status.return_value = "no_session"
        
        executor = BaseExecutor(mock_session_tracker)
        assert executor.should_skip_due_to_session() == False
        assert executor.should_maximize_usage() == False
    
    def test_session_summary_logging(self, mock_session_tracker, capsys):
        """Test session summary logging."""
        mock_session_tracker.get_session_summary.return_value = {
            "session_active": True,
            "session_start": "2024-01-01T10:00:00",
            "session_elapsed_minutes": 120,
            "session_remaining_minutes": 180,
            "is_final_window": False,
            "session_expired": False,
            "timestamp": "2024-01-01T12:00:00"
        }
        mock_session_tracker.check_session_status.return_value = "normal"
        
        executor = BaseExecutor(mock_session_tracker)
        executor.log_session_status()
        
        captured = capsys.readouterr()
        assert "Session status: normal" in captured.out
        assert "180 min remaining" in captured.out


class TestErrorHandling:
    """Test error handling in session-based execution."""
    
    @pytest.fixture
    def mock_session_tracker(self):
        mock_tracker = Mock(spec=SessionTracker)
        mock_tracker.check_session_status.return_value = "normal"
        mock_tracker.get_session_summary.return_value = {
            "session_active": True,
            "session_remaining_minutes": 120,
            "timestamp": "2024-01-01T12:00:00"
        }
        return mock_tracker
    
    @patch('mode_executors.GitHubIntegration')
    def test_workday_executor_error_handling(self, mock_gh_class, mock_session_tracker):
        mock_gh_class.side_effect = Exception("GitHub API error")
        
        repos = [RepoConfig("test-repo", "/tmp/test", "high", ["main"])]
        executor = WorkdayExecutor(mock_session_tracker)
        result = executor.execute(repos)
        
        assert result["status"] == "completed"
        assert "test-repo" in result["results"]
        assert result["results"]["test-repo"]["status"] == "error"
        assert "GitHub API error" in result["results"]["test-repo"]["error"]
    
    @patch('task_scheduler.TaskScheduler')
    @patch('mode_executors.GitHubIntegration')  
    def test_weekend_executor_error_handling(self, mock_gh_class, mock_scheduler_class, mock_session_tracker):
        mock_scheduler_class.return_value = Mock()
        mock_gh_class.side_effect = Exception("Network error")
        
        repos = [RepoConfig("test-repo", "/tmp/test", "high", ["main"])]
        executor = WeekendExecutor(mock_session_tracker)
        result = executor.execute(repos)
        
        assert result["status"] == "completed"
        assert "test-repo" in result["results"]
        assert result["results"]["test-repo"]["status"] == "error"
        assert "Network error" in result["results"]["test-repo"]["error"]