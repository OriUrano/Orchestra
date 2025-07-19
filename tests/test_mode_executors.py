"""
Unit tests for mode_executors.py
"""
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
from usage_tracker import UsageTracker


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
    
    def test_init(self):
        mock_tracker = Mock(spec=UsageTracker)
        executor = BaseExecutor(mock_tracker)
        
        assert executor.usage_tracker == mock_tracker
    
    def test_should_skip_due_to_usage_limit_reached(self):
        mock_tracker = Mock(spec=UsageTracker)
        mock_tracker.check_limits.return_value = "limit_reached"
        
        executor = BaseExecutor(mock_tracker)
        assert executor.should_skip_due_to_usage() == True
    
    def test_should_skip_due_to_usage_within_limits(self):
        mock_tracker = Mock(spec=UsageTracker)
        mock_tracker.check_limits.return_value = "normal"
        
        executor = BaseExecutor(mock_tracker)
        assert executor.should_skip_due_to_usage() == False
    
    def test_log_usage_status(self, capsys):
        mock_tracker = Mock(spec=UsageTracker)
        mock_tracker.check_limits.return_value = "normal"
        mock_tracker.get_usage_summary.return_value = {
            "total_tokens": 1500,
            "requests": 5
        }
        
        executor = BaseExecutor(mock_tracker)
        executor.log_usage_status()
        
        captured = capsys.readouterr()
        assert "Usage status: normal - 1500 tokens, 5 requests" in captured.out


class TestWorkdayExecutor:
    """Test WorkdayExecutor functionality."""
    
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
    
    def test_execute_skip_due_to_usage(self, mock_usage_tracker):
        mock_usage_tracker.check_limits.return_value = "limit_reached"
        
        executor = WorkdayExecutor(mock_usage_tracker)
        result = executor.execute([])
        
        assert result["status"] == "skipped"
        assert result["reason"] == "usage_limit"
    
    @patch('mode_executors.GitHubIntegration')
    def test_execute_success(self, mock_gh_class, mock_usage_tracker, sample_repos):
        mock_usage_tracker.check_limits.return_value = "normal"
        
        # Mock GitHub integration
        mock_gh = Mock()
        mock_gh.gather_workday_data.return_value = {
            'pending_reviews': [],
            'my_prs': [],
            'assigned_issues': []
        }
        mock_gh_class.return_value = mock_gh
        
        executor = WorkdayExecutor(mock_usage_tracker)
        result = executor.execute(sample_repos)
        
        assert result["status"] == "completed"
        assert "results" in result
        
        # Should only process first 3 high-priority repos
        assert len(result["results"]) == 3
        assert "high-repo-1" in result["results"]
        assert "high-repo-2" in result["results"]
        assert "high-repo-3" in result["results"]
        assert "high-repo-4" not in result["results"]
        assert "medium-repo" not in result["results"]
    
    @patch('mode_executors.GitHubIntegration')
    def test_process_repo_workday_with_pending_reviews(self, mock_gh_class, mock_usage_tracker):
        mock_usage_tracker.check_limits.return_value = "normal"
        
        # Mock pending review data
        mock_pr = Mock()
        mock_pr.number = 123
        mock_pr.title = "Test PR"
        mock_pr.author = "test-user"
        mock_pr.url = "https://github.com/test/test/pull/123"
        
        mock_gh = Mock()
        mock_gh.gather_workday_data.return_value = {
            'pending_reviews': [mock_pr],
            'my_prs': [],
            'assigned_issues': []
        }
        mock_gh_class.return_value = mock_gh
        
        repo = RepoConfig("test-repo", "/tmp/test", "high", ["main"])
        executor = WorkdayExecutor(mock_usage_tracker)
        result = executor._process_repo_workday(repo)
        
        assert result["status"] == "ready"
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["type"] == "review_responses"
        assert "prompt" in result["tasks"][0]
    
    @patch('mode_executors.GitHubIntegration')
    def test_process_repo_workday_with_empty_pr_descriptions(self, mock_gh_class, mock_usage_tracker):
        mock_usage_tracker.check_limits.return_value = "normal"
        
        # Mock PR with empty description
        mock_pr = Mock()
        mock_pr.number = 456
        mock_pr.title = "Empty description PR"
        mock_pr.url = "https://github.com/test/test/pull/456"
        mock_pr.body = "   "  # Empty/whitespace only
        
        mock_gh = Mock()
        mock_gh.gather_workday_data.return_value = {
            'pending_reviews': [],
            'my_prs': [mock_pr],
            'assigned_issues': []
        }
        mock_gh_class.return_value = mock_gh
        
        repo = RepoConfig("test-repo", "/tmp/test", "high", ["main"])
        executor = WorkdayExecutor(mock_usage_tracker)
        result = executor._process_repo_workday(repo)
        
        assert result["status"] == "ready"
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["type"] == "pr_descriptions"
    
    @patch('mode_executors.GitHubIntegration')
    def test_process_repo_workday_with_assigned_issues(self, mock_gh_class, mock_usage_tracker):
        mock_usage_tracker.check_limits.return_value = "normal"
        
        # Mock assigned issue
        mock_issue = Mock()
        mock_issue.number = 789
        mock_issue.title = "Bug to fix"
        mock_issue.author = "user"
        mock_issue.url = "https://github.com/test/test/issues/789"
        
        mock_gh = Mock()
        mock_gh.gather_workday_data.return_value = {
            'pending_reviews': [],
            'my_prs': [],
            'assigned_issues': [mock_issue]
        }
        mock_gh_class.return_value = mock_gh
        
        repo = RepoConfig("test-repo", "/tmp/test", "high", ["main"])
        executor = WorkdayExecutor(mock_usage_tracker)
        result = executor._process_repo_workday(repo)
        
        assert result["status"] == "ready"
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["type"] == "issue_responses"
    
    def test_build_review_prompt(self, mock_usage_tracker):
        mock_pr = Mock()
        mock_pr.number = 123
        mock_pr.title = "Test PR"
        mock_pr.author = "test-user"
        mock_pr.url = "https://github.com/test/test/pull/123"
        
        executor = WorkdayExecutor(mock_usage_tracker)
        prompt = executor._build_review_prompt([mock_pr])
        
        assert "Workday Mode: PR Review Planning" in prompt
        assert "Do not generate code" in prompt
        assert str(mock_pr.number) in prompt
        assert mock_pr.title in prompt
    
    def test_build_pr_description_prompt(self, mock_usage_tracker):
        mock_pr = Mock()
        mock_pr.number = 456
        mock_pr.title = "Feature implementation"
        mock_pr.url = "https://github.com/test/test/pull/456"
        
        executor = WorkdayExecutor(mock_usage_tracker)
        prompt = executor._build_pr_description_prompt([mock_pr])
        
        assert "Workday Mode: PR Description Updates" in prompt
        assert "empty descriptions" in prompt
        assert str(mock_pr.number) in prompt
        assert mock_pr.title in prompt
    
    def test_build_issue_prompt(self, mock_usage_tracker):
        mock_issue = Mock()
        mock_issue.number = 789
        mock_issue.title = "Bug report"
        mock_issue.author = "user"
        mock_issue.url = "https://github.com/test/test/issues/789"
        
        executor = WorkdayExecutor(mock_usage_tracker)
        prompt = executor._build_issue_prompt([mock_issue])
        
        assert "Workday Mode: Issue Response Planning" in prompt
        assert "Provide planning only" in prompt
        assert str(mock_issue.number) in prompt
        assert mock_issue.title in prompt


class TestWorknightExecutor:
    """Test WorknightExecutor functionality."""
    
    def test_execute_skip_due_to_usage(self, mock_usage_tracker):
        mock_usage_tracker.check_limits.return_value = "limit_reached"
        
        executor = WorknightExecutor(mock_usage_tracker)
        result = executor.execute([])
        
        assert result["status"] == "skipped"
        assert result["reason"] == "usage_limit"
    
    def test_execute_success(self, mock_usage_tracker):
        mock_usage_tracker.check_limits.return_value = "normal"
        
        repos = [
            RepoConfig("repo1", "/tmp/repo1", "high", ["main"]),
            RepoConfig("repo2", "/tmp/repo2", "medium", ["main"])
        ]
        
        executor = WorknightExecutor(mock_usage_tracker)
        result = executor.execute(repos)
        
        assert result["status"] == "completed"
        assert "results" in result
        assert len(result["results"]) == 2
        assert "repo1" in result["results"]
        assert "repo2" in result["results"]
    
    def test_process_repo_worknight(self, mock_usage_tracker):
        repo = RepoConfig("test-repo", "/tmp/test", "high", ["main", "develop"])
        
        executor = WorknightExecutor(mock_usage_tracker)
        result = executor._process_repo_worknight(repo)
        
        assert result["status"] == "ready"
        assert result["mode"] == "worknight"
        assert "prompt" in result
        
        prompt = result["prompt"]
        assert "Worknight Mode: Active Development" in prompt
        assert repo.name in prompt
        assert repo.path in prompt
        assert repo.priority in prompt
        assert "main, develop" in prompt
        assert "gh commands" in prompt
    
    def test_execute_with_exception(self, mock_usage_tracker):
        mock_usage_tracker.check_limits.return_value = "normal"
        
        # Mock an exception in the _process_repo_worknight method
        repos = [RepoConfig("error-repo", "/tmp/error", "high", ["main"])]
        
        executor = WorknightExecutor(mock_usage_tracker)
        
        # Mock _process_repo_worknight to raise an exception
        with patch.object(executor, '_process_repo_worknight', side_effect=Exception("Test error")):
            result = executor.execute(repos)
        
        assert result["status"] == "completed"
        assert "error-repo" in result["results"]
        assert result["results"]["error-repo"]["status"] == "error"
        assert "Test error" in result["results"]["error-repo"]["error"]


class TestWeekendExecutor:
    """Test WeekendExecutor functionality."""
    
    @pytest.fixture
    def mixed_priority_repos(self):
        return [
            RepoConfig("high-repo-1", "/tmp/high1", "high", ["main"]),
            RepoConfig("high-repo-2", "/tmp/high2", "high", ["main"]),
            RepoConfig("medium-repo", "/tmp/medium", "medium", ["main"]),
            RepoConfig("low-repo", "/tmp/low", "low", ["main"])
        ]
    
    def test_execute_skip_due_to_usage(self, mock_usage_tracker):
        mock_usage_tracker.check_limits.return_value = "limit_reached"
        
        executor = WeekendExecutor(mock_usage_tracker)
        result = executor.execute([])
        
        assert result["status"] == "skipped"
        assert result["reason"] == "usage_limit"
    
    @patch('mode_executors.GitHubIntegration')
    def test_execute_only_high_priority(self, mock_gh_class, mock_usage_tracker, mixed_priority_repos):
        mock_usage_tracker.check_limits.return_value = "normal"
        
        # Mock GitHub integration
        mock_gh = Mock()
        mock_gh.get_pending_review_prs.return_value = []
        mock_gh.get_assigned_issues.return_value = []
        mock_gh_class.return_value = mock_gh
        
        executor = WeekendExecutor(mock_usage_tracker)
        result = executor.execute(mixed_priority_repos)
        
        assert result["status"] == "completed"
        assert "results" in result
        
        # Should only process high-priority repos
        assert len(result["results"]) == 2
        assert "high-repo-1" in result["results"]
        assert "high-repo-2" in result["results"]
        assert "medium-repo" not in result["results"]
        assert "low-repo" not in result["results"]
    
    @patch('mode_executors.GitHubIntegration')
    def test_monitor_repo_with_notifications(self, mock_gh_class, mock_usage_tracker):
        mock_usage_tracker.check_limits.return_value = "normal"
        
        # Mock pending reviews and urgent issues
        mock_review = Mock()
        mock_urgent_issue = Mock()
        mock_urgent_issue.title = "URGENT: Critical bug"
        mock_normal_issue = Mock()
        mock_normal_issue.title = "Normal issue"
        
        mock_gh = Mock()
        mock_gh.get_pending_review_prs.return_value = [mock_review]
        mock_gh.get_assigned_issues.return_value = [mock_urgent_issue, mock_normal_issue]
        mock_gh_class.return_value = mock_gh
        
        repo = RepoConfig("test-repo", "/tmp/test", "high", ["main"])
        executor = WeekendExecutor(mock_usage_tracker)
        result = executor._monitor_repo(repo)
        
        assert result["status"] == "monitored"
        assert len(result["notifications"]) == 2
        assert "1 pending reviews" in result["notifications"]
        assert "1 urgent issues" in result["notifications"]
        assert result["pending_reviews"] == 1
        assert result["urgent_issues"] == 1
    
    @patch('mode_executors.GitHubIntegration')
    def test_monitor_repo_no_notifications(self, mock_gh_class, mock_usage_tracker):
        mock_usage_tracker.check_limits.return_value = "normal"
        
        # Mock no pending items
        mock_gh = Mock()
        mock_gh.get_pending_review_prs.return_value = []
        mock_gh.get_assigned_issues.return_value = []
        mock_gh_class.return_value = mock_gh
        
        repo = RepoConfig("test-repo", "/tmp/test", "high", ["main"])
        executor = WeekendExecutor(mock_usage_tracker)
        result = executor._monitor_repo(repo)
        
        assert result["status"] == "monitored"
        assert result["notifications"] == []
        assert result["pending_reviews"] == 0
        assert result["urgent_issues"] == 0
    
    @patch('mode_executors.GitHubIntegration')
    def test_urgent_issue_detection(self, mock_gh_class, mock_usage_tracker):
        mock_usage_tracker.check_limits.return_value = "normal"
        
        # Create issues with different urgency levels
        urgent_issue1 = Mock()
        urgent_issue1.title = "URGENT: System down"
        urgent_issue2 = Mock()
        urgent_issue2.title = "Critical security vulnerability"
        normal_issue = Mock()
        normal_issue.title = "Feature request"
        
        mock_gh = Mock()
        mock_gh.get_pending_review_prs.return_value = []
        mock_gh.get_assigned_issues.return_value = [urgent_issue1, urgent_issue2, normal_issue]
        mock_gh_class.return_value = mock_gh
        
        repo = RepoConfig("test-repo", "/tmp/test", "high", ["main"])
        executor = WeekendExecutor(mock_usage_tracker)
        result = executor._monitor_repo(repo)
        
        # Should detect 2 urgent issues (containing "urgent" or "critical")
        assert result["urgent_issues"] == 2


class TestGetExecutor:
    """Test executor factory function."""
    
    def test_get_workday_executor(self, mock_usage_tracker):
        executor = get_executor("workday", mock_usage_tracker)
        assert isinstance(executor, WorkdayExecutor)
        assert executor.usage_tracker == mock_usage_tracker
    
    def test_get_worknight_executor(self, mock_usage_tracker):
        executor = get_executor("worknight", mock_usage_tracker)
        assert isinstance(executor, WorknightExecutor)
        assert executor.usage_tracker == mock_usage_tracker
    
    def test_get_weekend_executor(self, mock_usage_tracker):
        executor = get_executor("weekend", mock_usage_tracker)
        assert isinstance(executor, WeekendExecutor)
        assert executor.usage_tracker == mock_usage_tracker
    
    def test_get_executor_invalid_mode(self, mock_usage_tracker):
        with pytest.raises(ValueError, match="Unknown work mode: invalid"):
            get_executor("invalid", mock_usage_tracker)


class TestExecutorErrorHandling:
    """Test error handling across all executors."""
    
    @patch('mode_executors.GitHubIntegration')
    def test_workday_executor_github_error(self, mock_gh_class, mock_usage_tracker):
        mock_usage_tracker.check_limits.return_value = "normal"
        mock_gh_class.side_effect = Exception("GitHub API error")
        
        repos = [RepoConfig("test-repo", "/tmp/test", "high", ["main"])]
        executor = WorkdayExecutor(mock_usage_tracker)
        result = executor.execute(repos)
        
        assert result["status"] == "completed"
        assert "test-repo" in result["results"]
        assert result["results"]["test-repo"]["status"] == "error"
        assert "GitHub API error" in result["results"]["test-repo"]["error"]
    
    @patch('mode_executors.GitHubIntegration')
    def test_weekend_executor_github_error(self, mock_gh_class, mock_usage_tracker):
        mock_usage_tracker.check_limits.return_value = "normal"
        mock_gh_class.side_effect = Exception("Network error")
        
        repos = [RepoConfig("test-repo", "/tmp/test", "high", ["main"])]
        executor = WeekendExecutor(mock_usage_tracker)
        result = executor.execute(repos)
        
        assert result["status"] == "completed"
        assert "test-repo" in result["results"]
        assert result["results"]["test-repo"]["status"] == "error"
        assert "Network error" in result["results"]["test-repo"]["error"]