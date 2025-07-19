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
    
    def test_should_skip_due_to_usage_normal(self):
        mock_tracker = Mock(spec=UsageTracker)
        mock_tracker.check_limits.return_value = "normal"
        
        executor = BaseExecutor(mock_tracker)
        assert executor.should_skip_due_to_usage() == False
    
    def test_log_usage_status(self, capsys):
        mock_tracker = Mock(spec=UsageTracker)
        mock_tracker.check_limits.return_value = "approaching_limit"
        mock_tracker.get_usage_summary.return_value = {
            'total_tokens': 50000,
            'requests': 100
        }
        
        executor = BaseExecutor(mock_tracker)
        executor.log_usage_status()
        
        captured = capsys.readouterr()
        assert "Usage status: approaching_limit" in captured.out
        assert "50000 tokens" in captured.out
        assert "100 requests" in captured.out


class TestWorkdayExecutorEnhancements:
    """Test the enhanced WorkdayExecutor functionality."""
    
    @patch('mode_executors.GitHubIntegration')
    def test_process_repo_workday_with_branch_management(self, mock_github_class):
        # Mock GitHub integration
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        
        # Mock branch data
        from github_integration import Branch
        branches_needing_rebase = [
            Branch(name="feature-1", current=False, remote="origin", 
                   ahead_count=1, behind_count=2, last_commit="abc123"),
            Branch(name="feature-2", current=False, remote="origin",
                   ahead_count=0, behind_count=1, last_commit="def456")
        ]
        
        mock_github.gather_workday_data.return_value = {
            'pending_reviews': [],
            'my_prs': [],
            'assigned_issues': [],
            'repo_status': {},
            'branches': branches_needing_rebase
        }
        
        mock_tracker = Mock(spec=UsageTracker)
        mock_tracker.check_limits.return_value = "normal"
        
        executor = WorkdayExecutor(mock_tracker)
        repo = RepoConfig("test-repo", "/tmp/test", "high", ["main"])
        
        result = executor._process_repo_workday(repo)
        
        assert result["status"] == "ready"
        assert len(result["tasks"]) == 1  # Should have branch management task
        
        branch_task = result["tasks"][0]
        assert branch_task["type"] == "branch_management"
        assert len(branch_task["data"]) == 2  # Both branches need attention
        assert "branch status" in branch_task["prompt"].lower()
    
    @patch('mode_executors.GitHubIntegration')
    @patch('mode_executors.datetime')
    def test_process_repo_workday_with_commit_notifications(self, mock_datetime, mock_github_class):
        # Mock current time
        mock_now = datetime(2024, 1, 15, 10, 0, 0)
        mock_datetime.now.return_value = mock_now
        
        # Mock GitHub integration
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        
        # Mock PR with recent commits
        from github_integration import PullRequest, Commit
        pr_with_commits = PullRequest(
            number=123, title="Test PR", url="https://test.com", 
            author="teammate", updated_at="2024-01-15T09:00:00Z", state="open"
        )
        
        mock_commits = [
            Commit(sha="abc123", message="Fix bug", author="teammate", 
                   date="2024-01-15T08:00:00Z", url="https://test.com/commit/abc123")
        ]
        
        mock_github.gather_workday_data.return_value = {
            'pending_reviews': [pr_with_commits],
            'my_prs': [],
            'assigned_issues': [],
            'repo_status': {},
            'branches': []
        }
        mock_github.get_commits_since.return_value = mock_commits
        
        mock_tracker = Mock(spec=UsageTracker)
        mock_tracker.check_limits.return_value = "normal"
        
        executor = WorkdayExecutor(mock_tracker)
        repo = RepoConfig("test-repo", "/tmp/test", "high", ["main"])
        
        result = executor._process_repo_workday(repo)
        
        assert result["status"] == "ready"
        
        # Should have commit notification task
        commit_tasks = [task for task in result["tasks"] if task["type"] == "commit_notifications"]
        assert len(commit_tasks) == 1
        assert "new commits" in commit_tasks[0]["prompt"].lower()
    
    @patch('mode_executors.GitHubIntegration')
    def test_process_repo_workday_with_comment_responses(self, mock_github_class):
        # Mock GitHub integration
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        
        # Mock PR with comments needing responses
        from github_integration import PullRequest
        my_pr = PullRequest(
            number=456, title="My PR", url="https://test.com/pr/456",
            author="me", updated_at="2024-01-15T09:00:00Z", state="open"
        )
        
        mock_comments = [
            {"user": {"login": "reviewer"}, "body": "Can you explain why you chose this approach?"},
            {"user": {"login": "reviewer2"}, "body": "Should we add more tests for this?"}
        ]
        
        mock_github.gather_workday_data.return_value = {
            'pending_reviews': [],
            'my_prs': [my_pr],
            'assigned_issues': [],
            'repo_status': {},
            'branches': []
        }
        mock_github.get_pr_comments.return_value = mock_comments
        mock_github.get_pr_review_comments.return_value = []
        
        mock_tracker = Mock(spec=UsageTracker)
        mock_tracker.check_limits.return_value = "normal"
        
        executor = WorkdayExecutor(mock_tracker)
        repo = RepoConfig("test-repo", "/tmp/test", "high", ["main"])
        
        result = executor._process_repo_workday(repo)
        
        assert result["status"] == "ready"
        
        # Should have comment response task
        comment_tasks = [task for task in result["tasks"] if task["type"] == "comment_responses"]
        assert len(comment_tasks) == 1
        assert len(comment_tasks[0]["data"]) == 1  # One PR with comments
        assert "comment response" in comment_tasks[0]["prompt"].lower()


class TestWorknightExecutorEnhancements:
    """Test the enhanced WorknightExecutor functionality."""
    
    @patch('task_scheduler.TaskScheduler')
    @patch('mode_executors.GitHubIntegration')
    def test_worknight_executor_init_with_scheduler(self, mock_github_class, mock_scheduler_class):
        mock_tracker = Mock(spec=UsageTracker)
        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        
        executor = WorknightExecutor(mock_tracker)
        
        assert executor.usage_tracker == mock_tracker
        assert executor.task_scheduler == mock_scheduler
        mock_scheduler_class.assert_called_once()
    
    @patch('task_scheduler.TaskScheduler')
    @patch('mode_executors.GitHubIntegration')
    def test_process_repo_worknight_with_scheduled_tasks(self, mock_github_class, mock_scheduler_class):
        # Mock task scheduler
        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        
        from task_scheduler import ScheduledTask, TaskPriority, TaskStatus
        scheduled_task = ScheduledTask(
            id="task_1", title="Implement feature", description="Add new API endpoint",
            task_type="pr_implementation", priority=TaskPriority.HIGH, 
            status=TaskStatus.PENDING, repo_name="test-repo",
            created_at="2024-01-15T10:00:00", metadata={"pr_number": 123}
        )
        mock_scheduler.get_tasks_for_mode.return_value = [scheduled_task]
        
        # Mock GitHub integration
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        mock_github.gather_workday_data.return_value = {
            'pending_reviews': [], 'my_prs': [], 'assigned_issues': [],
            'repo_status': {}, 'branches': []
        }
        
        mock_tracker = Mock(spec=UsageTracker)
        mock_tracker.check_limits.return_value = "normal"
        
        executor = WorknightExecutor(mock_tracker)
        repo = RepoConfig("test-repo", "/tmp/test", "high", ["main"])
        
        result = executor._process_repo_worknight(repo)
        
        assert result["status"] == "ready"
        assert result["mode"] == "worknight"
        assert result["scheduled_tasks"] == ["task_1"]
        assert "Implement feature" in result["prompt"]
        assert "HIGH" in result["prompt"]  # Priority should be in prompt
    
    @patch('task_scheduler.TaskScheduler')
    @patch('mode_executors.GitHubIntegration')
    def test_find_implementation_requests(self, mock_github_class, mock_scheduler_class):
        # Mock task scheduler
        mock_scheduler_class.return_value = Mock()
        
        # Mock GitHub integration
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        
        # Mock PR search results with implementation requests
        implementation_pr = {
            "number": 789,
            "title": "Feature request: Add user authentication",
            "url": "https://github.com/test/test/pull/789",
            "author": {"login": "requester"},
            "body": "Please implement user authentication system",
            "updatedAt": "2024-01-15T10:00:00Z"
        }
        
        mock_github._run_gh_command.return_value = json.dumps([implementation_pr])
        mock_github.get_pr_comments.return_value = [
            {"body": "Can you implement the JWT token validation?"}
        ]
        
        mock_tracker = Mock(spec=UsageTracker)
        executor = WorknightExecutor(mock_tracker)
        
        github_data = {'pending_reviews': [], 'my_prs': []}
        requests = executor._find_implementation_requests(mock_github, github_data)
        
        assert len(requests) == 1
        assert requests[0]['pr']['number'] == 789
        assert requests[0]['implementation_type'] == 'requested_feature'
        assert len(requests[0]['comments']) == 1
    
    @patch('task_scheduler.TaskScheduler')
    @patch('mode_executors.GitHubIntegration')
    def test_find_my_pr_implementations_needed(self, mock_github_class, mock_scheduler_class):
        # Mock task scheduler
        mock_scheduler_class.return_value = Mock()
        
        # Mock GitHub integration
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        
        from github_integration import PullRequest
        my_pr = PullRequest(
            number=555, title="My feature PR", url="https://test.com/pr/555",
            author="me", updated_at="2024-01-15T09:00:00Z", state="open"
        )
        
        # Mock review comments requesting implementation
        mock_comments = [
            {"body": "Please change the validation logic here"},
            {"body": "You should implement error handling for this case"}
        ]
        mock_review_comments = [
            {"body": "This needs to be fixed before we can merge"}
        ]
        
        mock_github.get_pr_comments.return_value = mock_comments
        mock_github.get_pr_review_comments.return_value = mock_review_comments
        
        mock_tracker = Mock(spec=UsageTracker)
        executor = WorknightExecutor(mock_tracker)
        
        github_data = {'my_prs': [my_pr]}
        implementations = executor._find_my_pr_implementations_needed(mock_github, github_data)
        
        assert len(implementations) == 1
        assert implementations[0]['pr'].number == 555
        assert len(implementations[0]['implementation_comments']) == 3  # All comments contain keywords
    
    @patch('task_scheduler.TaskScheduler')
    @patch('mode_executors.GitHubIntegration')
    def test_build_worknight_prompt_comprehensive(self, mock_github_class, mock_scheduler_class):
        # Mock task scheduler
        mock_scheduler_class.return_value = Mock()
        
        mock_tracker = Mock(spec=UsageTracker)
        executor = WorknightExecutor(mock_tracker)
        
        # Mock data for comprehensive prompt
        from task_scheduler import ScheduledTask, TaskPriority, TaskStatus
        from github_integration import Branch
        
        scheduled_tasks = [
            ScheduledTask(
                id="urgent_task", title="Fix critical bug", description="Auth system broken",
                task_type="bug_fix", priority=TaskPriority.URGENT, status=TaskStatus.PENDING,
                repo_name="test-repo", created_at="2024-01-15T10:00:00"
            )
        ]
        
        implementation_requests = [
            {
                'pr': {"number": 123, "title": "Add feature", "author": {"login": "teammate"}, "url": "https://github.com/test/test/pull/123"},
                'comments': [],
                'implementation_type': 'requested_feature'
            }
        ]
        
        rebase_needed = [
            Branch(name="old-feature", current=False, remote="origin", 
                   ahead_count=0, behind_count=3, last_commit="abc123")
        ]
        
        my_pr_implementations = [
            {
                'pr': Mock(number=456, title="My PR", url="https://github.com/test/test/pull/456"),
                'implementation_comments': [{"body": "Please fix this"}]
            }
        ]
        
        github_data = {
            'pending_reviews': [],
            'my_prs': [Mock()],
            'assigned_issues': [Mock(), Mock()]
        }
        
        repo = RepoConfig("test-repo", "/tmp/test", "high", ["main"])
        
        prompt = executor._build_worknight_prompt(
            repo, scheduled_tasks, implementation_requests, 
            rebase_needed, my_pr_implementations, github_data
        )
        
        # Verify prompt contains all sections
        assert "Worknight Mode: Active Development Session" in prompt
        assert "Scheduled Tasks (PRIORITY)" in prompt
        assert "Fix critical bug" in prompt
        assert "URGENT" in prompt
        assert "Implementation Requests from Others" in prompt
        assert "My PRs Needing Implementation" in prompt
        assert "Branch Management" in prompt
        assert "old-feature" in prompt
        assert "Standard Development Tasks" in prompt
        assert "Repository Info" in prompt


class TestWeekendExecutorRewrite:
    """Test the completely rewritten WeekendExecutor."""
    
    @patch('task_scheduler.TaskScheduler')
    @patch('mode_executors.GitHubIntegration')
    def test_weekend_executor_init_with_scheduler(self, mock_github_class, mock_scheduler_class):
        mock_tracker = Mock(spec=UsageTracker)
        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        
        executor = WeekendExecutor(mock_tracker)
        
        assert executor.usage_tracker == mock_tracker
        assert executor.task_scheduler == mock_scheduler
        mock_scheduler_class.assert_called_once()
    
    @patch('task_scheduler.TaskScheduler')
    @patch('mode_executors.GitHubIntegration')
    def test_execute_processes_all_repos_prioritized(self, mock_github_class, mock_scheduler_class):
        mock_scheduler_class.return_value = Mock()
        mock_tracker = Mock(spec=UsageTracker)
        mock_tracker.check_limits.return_value = "normal"
        mock_tracker.get_usage_summary.return_value = {"total_tokens": 1000, "requests": 10}
        
        executor = WeekendExecutor(mock_tracker)
        
        # Mock _process_repo_weekend to avoid complex setup
        executor._process_repo_weekend = Mock(return_value={"status": "ready"})
        
        repos = [
            RepoConfig("low-repo", "/tmp/low", "low", ["main"]),
            RepoConfig("high-repo", "/tmp/high", "high", ["main"]),
            RepoConfig("medium-repo", "/tmp/medium", "medium", ["main"])
        ]
        
        result = executor.execute(repos)
        
        assert result["status"] == "completed"
        assert len(result["results"]) == 3
        
        # Verify all repos were processed
        assert executor._process_repo_weekend.call_count == 3
        
        # Verify high priority repo was processed first (based on call order)
        call_args = [call[0][0] for call in executor._process_repo_weekend.call_args_list]
        assert call_args[0].priority == "high"  # First call should be high priority
    
    @patch('task_scheduler.TaskScheduler')
    @patch('mode_executors.GitHubIntegration')
    def test_analyze_weekend_work_needed_documentation(self, mock_github_class, mock_scheduler_class):
        mock_scheduler_class.return_value = Mock()
        mock_tracker = Mock(spec=UsageTracker)
        executor = WeekendExecutor(mock_tracker)
        
        # Mock weekend data with documentation files
        weekend_data = {
            'security_files': {
                'CLAUDE.md': {'description': 'Claude instructions'},
                'Architecture.md': {'description': 'Architecture docs'}
            },
            'vulnerabilities': {'total_issues': 0},
            'dependency_files': {}
        }
        
        repo = RepoConfig("test-repo", "/tmp/test", "high", ["main"])
        work_needed = executor._analyze_weekend_work_needed(Mock(), weekend_data, repo)
        
        assert len(work_needed["documentation_updates"]) == 2
        
        claude_update = next((item for item in work_needed["documentation_updates"] 
                             if item["type"] == "claude_md_update"), None)
        assert claude_update is not None
        assert claude_update["priority"] == "medium"
        
        arch_update = next((item for item in work_needed["documentation_updates"]
                           if item["type"] == "architecture_md_update"), None)
        assert arch_update is not None
        assert arch_update["priority"] == "medium"
    
    @patch('task_scheduler.TaskScheduler')
    @patch('mode_executors.GitHubIntegration')
    def test_analyze_weekend_work_needed_security(self, mock_github_class, mock_scheduler_class):
        mock_scheduler_class.return_value = Mock()
        mock_tracker = Mock(spec=UsageTracker)
        executor = WeekendExecutor(mock_tracker)
        
        # Mock weekend data with security vulnerabilities
        weekend_data = {
            'security_files': {},
            'vulnerabilities': {'total_issues': 5},
            'dependency_files': {}
        }
        
        repo = RepoConfig("test-repo", "/tmp/test", "high", ["main"])
        work_needed = executor._analyze_weekend_work_needed(Mock(), weekend_data, repo)
        
        assert len(work_needed["security_improvements"]) == 2  # Vuln fixes + general audit
        
        vuln_fix = next((item for item in work_needed["security_improvements"]
                        if item["type"] == "vulnerability_fixes"), None)
        assert vuln_fix is not None
        assert vuln_fix["priority"] == "high"
        assert vuln_fix["count"] == 5
    
    @patch('task_scheduler.TaskScheduler')
    @patch('mode_executors.GitHubIntegration')
    def test_identify_framework_upgrades(self, mock_github_class, mock_scheduler_class):
        mock_scheduler_class.return_value = Mock()
        mock_tracker = Mock(spec=UsageTracker)
        executor = WeekendExecutor(mock_tracker)
        
        # Test Node.js project
        dependency_files = {
            'package.json': {'content': '{"name": "test", "dependencies": {}}'}
        }
        upgrades = executor._identify_framework_upgrades(dependency_files)
        
        assert len(upgrades) == 1
        assert upgrades[0]["type"] == "nodejs_framework_upgrade"
        assert upgrades[0]["framework"] == "Node.js/Angular/React"
        
        # Test Java project
        dependency_files = {
            'pom.xml': {'content': '<project>...</project>'}
        }
        upgrades = executor._identify_framework_upgrades(dependency_files)
        
        assert len(upgrades) == 1
        assert upgrades[0]["type"] == "java_framework_upgrade"
        assert upgrades[0]["framework"] == "SpringBoot/Java"
        
        # Test Python project
        dependency_files = {
            'requirements.txt': {'content': 'django==4.0.0'},
            'pyproject.toml': {'content': '[tool.poetry]'}
        }
        upgrades = executor._identify_framework_upgrades(dependency_files)
        
        assert len(upgrades) == 1  # Should only return one even with multiple Python files
        assert upgrades[0]["type"] == "python_framework_upgrade"
    
    @patch('task_scheduler.TaskScheduler')
    @patch('mode_executors.GitHubIntegration')
    @patch('templates.weekend_prompts.documentation_update_prompt')
    @patch('templates.weekend_prompts.security_audit_prompt')
    def test_build_weekend_prompt_comprehensive(self, mock_security_prompt, mock_doc_prompt, 
                                               mock_github_class, mock_scheduler_class):
        # Mock prompt functions
        mock_doc_prompt.return_value = "Documentation update prompt"
        mock_security_prompt.return_value = "Security audit prompt"
        
        mock_scheduler_class.return_value = Mock()
        mock_tracker = Mock(spec=UsageTracker)
        executor = WeekendExecutor(mock_tracker)
        
        # Mock comprehensive weekend work
        from task_scheduler import ScheduledTask, TaskPriority, TaskStatus
        scheduled_tasks = [
            ScheduledTask(
                id="weekend_task", title="Update docs", description="Weekend documentation work",
                task_type="documentation", priority=TaskPriority.MEDIUM, status=TaskStatus.PENDING,
                repo_name="test-repo", created_at="2024-01-15T10:00:00"
            )
        ]
        
        weekend_work = {
            "documentation_updates": [{"type": "claude_md_update", "priority": "medium"}],
            "security_improvements": [{"type": "security_audit", "priority": "medium"}],
            "dependency_updates": [{"type": "dependency_updates", "priority": "medium"}],
            "test_coverage_gaps": [{"type": "test_coverage_improvement", "priority": "medium"}],
            "performance_issues": [{"type": "performance_optimization", "priority": "low"}],
            "compliance_reports": [{"type": "status_reporting", "priority": "low"}]
        }
        
        weekend_data = {
            'security_files': {'CLAUDE.md': {'description': 'Project documentation'}},
            'dependency_files': {'package.json': {'description': 'Node.js dependencies'}},
            'vulnerabilities': {'total_issues': 2},
            'my_prs': [Mock()]
        }
        
        repo = RepoConfig("test-repo", "/tmp/test", "high", ["main"])
        
        prompt = executor._build_weekend_prompt(repo, scheduled_tasks, weekend_work, weekend_data)
        
        # Verify comprehensive prompt structure
        assert "Weekend Mode: Comprehensive Development & Maintenance" in prompt
        assert "test-repo" in prompt
        assert "high" in prompt  # Priority
        assert "Scheduled Weekend Tasks" in prompt
        assert "Update docs" in prompt
        assert "Documentation update prompt" in prompt
        assert "Security audit prompt" in prompt
        assert "Weekend Work Guidelines" in prompt
        assert "Repository Status" in prompt
        
        # Verify prompt template functions were called
        mock_doc_prompt.assert_called_once()
        mock_security_prompt.assert_called_once()


class TestGetExecutorFactory:
    """Test the executor factory function."""
    
    def test_get_executor_workday(self):
        mock_tracker = Mock(spec=UsageTracker)
        executor = get_executor("workday", mock_tracker)
        
        assert isinstance(executor, WorkdayExecutor)
        assert executor.usage_tracker == mock_tracker
    
    @patch('task_scheduler.TaskScheduler')
    def test_get_executor_worknight(self, mock_scheduler_class):
        mock_scheduler_class.return_value = Mock()
        mock_tracker = Mock(spec=UsageTracker)
        executor = get_executor("worknight", mock_tracker)
        
        assert isinstance(executor, WorknightExecutor)
        assert executor.usage_tracker == mock_tracker
    
    @patch('task_scheduler.TaskScheduler')
    def test_get_executor_weekend(self, mock_scheduler_class):
        mock_scheduler_class.return_value = Mock()
        mock_tracker = Mock(spec=UsageTracker)
        executor = get_executor("weekend", mock_tracker)
        
        assert isinstance(executor, WeekendExecutor)
        assert executor.usage_tracker == mock_tracker
    
    def test_get_executor_invalid_mode(self):
        mock_tracker = Mock(spec=UsageTracker)
        
        with pytest.raises(ValueError, match="Unknown work mode: invalid"):
            get_executor("invalid", mock_tracker)


class TestModeExecutorIntegrationScenarios:
    """Test realistic integration scenarios across different modes."""
    
    @patch('mode_executors.GitHubIntegration')
    def test_workday_to_worknight_task_flow(self, mock_github_class):
        """Test how tasks identified in workday mode get executed in worknight mode."""
        # Setup workday executor
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        
        from github_integration import Branch, PullRequest
        
        # Mock workday data - branch needing rebase
        branches_needing_rebase = [
            Branch(name="feature-urgent", current=False, remote="origin",
                   ahead_count=1, behind_count=3, last_commit="abc123")
        ]
        
        my_pr_with_comments = PullRequest(
            number=789, title="My implementation PR", url="https://test.com/pr/789",
            author="me", updated_at="2024-01-15T09:00:00Z", state="open", body="This PR implements error handling"
        )
        
        mock_github.gather_workday_data.return_value = {
            'pending_reviews': [],
            'my_prs': [my_pr_with_comments],
            'assigned_issues': [],
            'repo_status': {},
            'branches': branches_needing_rebase
        }
        
        mock_github.get_pr_comments.return_value = [
            {"user": {"login": "reviewer"}, "body": "Can you please implement the error handling?"}
        ]
        mock_github.get_pr_review_comments.return_value = []
        mock_github.get_commits_since.return_value = []  # No new commits
        
        mock_tracker = Mock(spec=UsageTracker)
        mock_tracker.check_limits.return_value = "normal"
        
        # Execute workday analysis
        workday_executor = WorkdayExecutor(mock_tracker)
        repo = RepoConfig("test-repo", "/tmp/test", "high", ["main"])
        
        workday_result = workday_executor._process_repo_workday(repo)
        
        # Verify workday identified tasks
        assert len(workday_result["tasks"]) == 2  # Branch management + comment responses
        
        branch_task = next((t for t in workday_result["tasks"] if t["type"] == "branch_management"), None)
        assert branch_task is not None
        assert len(branch_task["data"]) == 1
        
        comment_task = next((t for t in workday_result["tasks"] if t["type"] == "comment_responses"), None)
        assert comment_task is not None
        assert len(comment_task["data"]) == 1
        
        # Now test worknight executor picks up similar work
        with patch('task_scheduler.TaskScheduler') as mock_scheduler_class:
            mock_scheduler = Mock()
            mock_scheduler_class.return_value = mock_scheduler
            mock_scheduler.get_tasks_for_mode.return_value = []  # No scheduled tasks
            
            worknight_executor = WorknightExecutor(mock_tracker)
            worknight_result = worknight_executor._process_repo_worknight(repo)
            
            # Verify worknight mode creates comprehensive implementation prompt
            assert worknight_result["status"] == "ready"
            assert worknight_result["mode"] == "worknight"
            
            prompt = worknight_result["prompt"]
            assert "Active Development Session" in prompt
            assert "Branch Management" in prompt
            assert "feature-urgent" in prompt  # Should include branch needing rebase
            assert "My PRs Needing Implementation" in prompt  # Should detect PR with comments
    
    @patch('task_scheduler.TaskScheduler')
    @patch('mode_executors.GitHubIntegration')
    def test_weekend_mode_comprehensive_analysis(self, mock_github_class, mock_scheduler_class):
        """Test weekend mode comprehensive repository analysis."""
        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        mock_scheduler.get_tasks_for_mode.return_value = []
        
        mock_github = Mock()
        mock_github_class.return_value = mock_github
        
        # Mock comprehensive weekend data
        mock_github.gather_weekend_data.return_value = {
            'dependency_files': {
                'package.json': {'description': 'npm project', 'content': '{}'},
                'requirements.txt': {'description': 'Python project', 'content': 'django==3.2'}
            },
            'security_files': {
                'CLAUDE.md': {'description': 'Claude instructions'},
                'Architecture.md': {'description': 'Architecture docs'}
            },
            'vulnerabilities': {
                'total_issues': 3,
                'security_advisories': [{'severity': 'HIGH'}],
                'vulnerability_alerts': [{'severity': 'MEDIUM'}, {'severity': 'LOW'}]
            },
            'branches': [],
            'my_prs': []
        }
        
        mock_tracker = Mock(spec=UsageTracker)
        mock_tracker.check_limits.return_value = "normal"
        
        weekend_executor = WeekendExecutor(mock_tracker)
        repo = RepoConfig("test-repo", "/tmp/test", "high", ["main"])
        
        result = weekend_executor._process_repo_weekend(repo)
        
        assert result["status"] == "ready"
        assert result["mode"] == "weekend"
        
        # Verify comprehensive weekend work analysis
        weekend_work = result["weekend_work"]
        
        # Should identify documentation updates
        assert len(weekend_work["documentation_updates"]) == 2
        doc_types = [item["type"] for item in weekend_work["documentation_updates"]]
        assert "claude_md_update" in doc_types
        assert "architecture_md_update" in doc_types
        
        # Should identify security work
        assert len(weekend_work["security_improvements"]) == 2  # Vulnerability fixes + audit
        security_work = weekend_work["security_improvements"]
        vuln_work = next((item for item in security_work if item["type"] == "vulnerability_fixes"), None)
        assert vuln_work is not None
        assert vuln_work["count"] == 3
        assert vuln_work["priority"] == "high"
        
        # Should identify dependency work
        assert len(weekend_work["dependency_updates"]) >= 1
        dep_work = weekend_work["dependency_updates"][0]
        assert dep_work["type"] == "dependency_updates"
        assert len(dep_work["files"]) == 2
        
        # Should identify test and performance work
        assert len(weekend_work["test_coverage_gaps"]) == 1
        assert len(weekend_work["performance_issues"]) == 1
        assert len(weekend_work["compliance_reports"]) == 1
    
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
            'assigned_issues': [],
            'repo_status': {},
            'branches': []
        }
        mock_gh.get_commits_since.return_value = []  # No new commits
        mock_gh.get_pr_comments.return_value = []  # No comments
        mock_gh.get_pr_review_comments.return_value = []  # No review comments
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
            'assigned_issues': [],
            'repo_status': {},
            'branches': []
        }
        mock_gh.get_commits_since.return_value = []
        mock_gh.get_pr_comments.return_value = []
        mock_gh.get_pr_review_comments.return_value = []
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
            'assigned_issues': [mock_issue],
            'repo_status': {},
            'branches': []
        }
        mock_gh.get_commits_since.return_value = []
        mock_gh.get_pr_comments.return_value = []
        mock_gh.get_pr_review_comments.return_value = []
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
    
    @patch('task_scheduler.TaskScheduler')
    @patch('mode_executors.GitHubIntegration')
    def test_process_repo_worknight(self, mock_github_class, mock_scheduler_class, mock_usage_tracker):
        # Mock task scheduler
        mock_scheduler = Mock()
        mock_scheduler.get_tasks_for_mode.return_value = []
        mock_scheduler_class.return_value = mock_scheduler
        
        # Mock GitHub integration
        mock_gh = Mock()
        mock_gh.gather_workday_data.return_value = {
            'pending_reviews': [],
            'my_prs': [],
            'assigned_issues': [],
            'repo_status': {},
            'branches': []
        }
        import json
        mock_gh._run_gh_command.return_value = json.dumps([])  # Empty search results
        mock_gh.get_pr_comments.return_value = []
        mock_gh.get_pr_review_comments.return_value = []
        mock_github_class.return_value = mock_gh
        
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
        assert "`gh` CLI" in prompt
    
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
    
    @patch('task_scheduler.TaskScheduler')
    @patch('mode_executors.GitHubIntegration')
    def test_execute_all_repos_prioritized(self, mock_gh_class, mock_scheduler_class, mock_usage_tracker, mixed_priority_repos):
        mock_usage_tracker.check_limits.return_value = "normal"
        
        # Mock task scheduler
        mock_scheduler = Mock()
        mock_scheduler.get_tasks_for_mode.return_value = []
        mock_scheduler_class.return_value = mock_scheduler
        
        # Mock GitHub integration
        mock_gh = Mock()
        mock_gh.gather_weekend_data.return_value = {
            'security_files': {},
            'dependency_files': {},
            'vulnerabilities': {'total_issues': 0},
            'my_prs': []
        }
        mock_gh_class.return_value = mock_gh
        
        executor = WeekendExecutor(mock_usage_tracker)
        result = executor.execute(mixed_priority_repos)
        
        assert result["status"] == "completed"
        assert "results" in result
        
        # Weekend mode processes all repos but prioritizes them
        assert len(result["results"]) == 4
        assert "high-repo-1" in result["results"]
        assert "high-repo-2" in result["results"]
        assert "medium-repo" in result["results"]
        assert "low-repo" in result["results"]
    
    @patch('task_scheduler.TaskScheduler')
    @patch('mode_executors.GitHubIntegration')
    def test_weekend_development_with_security_work(self, mock_gh_class, mock_scheduler_class, mock_usage_tracker):
        mock_usage_tracker.check_limits.return_value = "normal"
        
        # Mock task scheduler
        mock_scheduler = Mock()
        mock_scheduler.get_tasks_for_mode.return_value = []
        mock_scheduler_class.return_value = mock_scheduler
        
        # Mock GitHub integration with security vulnerabilities
        mock_gh = Mock()
        mock_gh.gather_weekend_data.return_value = {
            'security_files': {'SECURITY.md': {'description': 'Security documentation'}},
            'vulnerabilities': {'total_issues': 3},
            'dependency_files': {'package.json': {'description': 'Node.js dependencies'}},
            'my_prs': []
        }
        mock_gh_class.return_value = mock_gh
        
        repo = RepoConfig("test-repo", "/tmp/test", "high", ["main"])
        executor = WeekendExecutor(mock_usage_tracker)
        result = executor._process_repo_weekend(repo)
        
        assert result["status"] == "ready"
        assert result["mode"] == "weekend"
        assert "prompt" in result
        assert len(result["scheduled_tasks"]) == 0  # No scheduled tasks
        assert "weekend_work" in result
    
    @patch('task_scheduler.TaskScheduler')
    @patch('mode_executors.GitHubIntegration')
    def test_weekend_development_no_issues(self, mock_gh_class, mock_scheduler_class, mock_usage_tracker):
        mock_usage_tracker.check_limits.return_value = "normal"
        
        # Mock task scheduler
        mock_scheduler = Mock()
        mock_scheduler.get_tasks_for_mode.return_value = []
        mock_scheduler_class.return_value = mock_scheduler
        
        # Mock clean repository with no issues
        mock_gh = Mock()
        mock_gh.gather_weekend_data.return_value = {
            'security_files': {},
            'vulnerabilities': {'total_issues': 0},
            'dependency_files': {},
            'my_prs': []
        }
        mock_gh_class.return_value = mock_gh
        
        repo = RepoConfig("test-repo", "/tmp/test", "medium", ["main"])
        executor = WeekendExecutor(mock_usage_tracker)
        result = executor._process_repo_weekend(repo)
        
        assert result["status"] == "ready"
        assert result["mode"] == "weekend"
        assert "prompt" in result
        assert len(result["scheduled_tasks"]) == 0
    
    @patch('task_scheduler.TaskScheduler')
    @patch('mode_executors.GitHubIntegration')
    def test_weekend_development_with_dependencies(self, mock_gh_class, mock_scheduler_class, mock_usage_tracker):
        mock_usage_tracker.check_limits.return_value = "normal"
        
        # Mock task scheduler
        mock_scheduler = Mock()
        mock_scheduler.get_tasks_for_mode.return_value = []
        mock_scheduler_class.return_value = mock_scheduler
        
        # Mock repository with dependency issues
        mock_gh = Mock()
        mock_gh.gather_weekend_data.return_value = {
            'security_files': {},
            'vulnerabilities': {'total_issues': 0},
            'dependency_files': {
                'package.json': {'description': 'Node.js dependencies'},
                'requirements.txt': {'description': 'Python dependencies'}
            },
            'my_prs': []
        }
        mock_gh_class.return_value = mock_gh
        
        repo = RepoConfig("test-repo", "/tmp/test", "high", ["main"])
        executor = WeekendExecutor(mock_usage_tracker)
        result = executor._process_repo_weekend(repo)
        
        # Should include dependency update work
        assert result["status"] == "ready"
        assert "weekend_work" in result
        dependency_work = result["weekend_work"]["dependency_updates"]
        assert len(dependency_work) > 0


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