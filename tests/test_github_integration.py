"""
Unit tests for github_integration.py
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess

from github_integration import GitHubIntegration, PullRequest, Issue


class TestPullRequest:
    """Test PullRequest dataclass."""
    
    def test_pull_request_creation(self):
        pr = PullRequest(
            number=123,
            title="Test PR",
            url="https://github.com/test/test/pull/123",
            author="test-user",
            updated_at="2024-01-01T00:00:00Z",
            state="open",
            body="Test body"
        )
        
        assert pr.number == 123
        assert pr.title == "Test PR"
        assert pr.url == "https://github.com/test/test/pull/123"
        assert pr.author == "test-user"
        assert pr.updated_at == "2024-01-01T00:00:00Z"
        assert pr.state == "open"
        assert pr.body == "Test body"
        assert pr.comments == []
    
    def test_pull_request_default_values(self):
        pr = PullRequest(
            number=456,
            title="Simple PR",
            url="https://github.com/test/test/pull/456",
            author="user",
            updated_at="2024-01-01T00:00:00Z",
            state="open"
        )
        
        assert pr.body == ""
        assert pr.comments == []
    
    def test_pull_request_with_comments(self):
        comments = [{"id": 1, "body": "Test comment"}]
        pr = PullRequest(
            number=789,
            title="PR with comments",
            url="https://github.com/test/test/pull/789",
            author="user",
            updated_at="2024-01-01T00:00:00Z",
            state="open",
            comments=comments
        )
        
        assert pr.comments == comments


class TestIssue:
    """Test Issue dataclass."""
    
    def test_issue_creation(self):
        issue = Issue(
            number=456,
            title="Test Issue",
            url="https://github.com/test/test/issues/456",
            author="issue-author",
            updated_at="2024-01-01T00:00:00Z",
            state="open",
            body="Issue description"
        )
        
        assert issue.number == 456
        assert issue.title == "Test Issue"
        assert issue.url == "https://github.com/test/test/issues/456"
        assert issue.author == "issue-author"
        assert issue.updated_at == "2024-01-01T00:00:00Z"
        assert issue.state == "open"
        assert issue.body == "Issue description"
        assert issue.comments == []
    
    def test_issue_default_values(self):
        issue = Issue(
            number=789,
            title="Simple Issue",
            url="https://github.com/test/test/issues/789",
            author="user",
            updated_at="2024-01-01T00:00:00Z",
            state="open"
        )
        
        assert issue.body == ""
        assert issue.comments == []


class TestGitHubIntegration:
    """Test GitHubIntegration class."""
    
    def test_init(self):
        repo_path = "/tmp/test-repo"
        github = GitHubIntegration(repo_path)
        
        assert github.repo_path == repo_path
    
    @patch('subprocess.run')
    def test_run_gh_command_success(self, mock_run):
        mock_run.return_value = Mock(stdout="command output", returncode=0)
        
        github = GitHubIntegration("/tmp/test")
        result = github._run_gh_command(['pr', 'list'])
        
        assert result == "command output"
        mock_run.assert_called_once_with(
            ['gh', 'pr', 'list'],
            cwd="/tmp/test",
            capture_output=True,
            text=True,
            check=True
        )
    
    @patch('subprocess.run')
    def test_run_gh_command_with_custom_cwd(self, mock_run):
        mock_run.return_value = Mock(stdout="output", returncode=0)
        
        github = GitHubIntegration("/tmp/test")
        result = github._run_gh_command(['status'], cwd="/custom/path")
        
        mock_run.assert_called_once_with(
            ['gh', 'status'],
            cwd="/custom/path",
            capture_output=True,
            text=True,
            check=True
        )
    
    @patch('subprocess.run')
    def test_run_gh_command_failure(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ['gh', 'pr', 'list'], stderr="Error message"
        )
        
        github = GitHubIntegration("/tmp/test")
        
        with pytest.raises(Exception, match="gh command failed: Error message"):
            github._run_gh_command(['pr', 'list'])
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_get_pending_review_prs_success(self, mock_run_command):
        mock_output = json.dumps([
            {
                "number": 123,
                "title": "Review me",
                "url": "https://github.com/test/test/pull/123",
                "author": {"login": "author1"},
                "updatedAt": "2024-01-01T00:00:00Z",
                "body": "Please review this PR"
            },
            {
                "number": 456,
                "title": "Another PR",
                "url": "https://github.com/test/test/pull/456", 
                "author": {"login": "author2"},
                "updatedAt": "2024-01-02T00:00:00Z",
                "body": ""
            }
        ])
        mock_run_command.return_value = mock_output
        
        github = GitHubIntegration("/tmp/test")
        prs = github.get_pending_review_prs()
        
        assert len(prs) == 2
        assert prs[0].number == 123
        assert prs[0].title == "Review me"
        assert prs[0].author == "author1"
        assert prs[0].body == "Please review this PR"
        assert prs[1].number == 456
        assert prs[1].body == ""
        
        mock_run_command.assert_called_once_with([
            'search', 'prs',
            '--review-requested=@me',
            '--state=open',
            '--json=number,title,url,author,updatedAt,body'
        ])
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_get_pending_review_prs_empty(self, mock_run_command):
        mock_run_command.return_value = ""
        
        github = GitHubIntegration("/tmp/test")
        prs = github.get_pending_review_prs()
        
        assert prs == []
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_get_pending_review_prs_error(self, mock_run_command, capsys):
        mock_run_command.side_effect = Exception("API error")
        
        github = GitHubIntegration("/tmp/test")
        prs = github.get_pending_review_prs()
        
        assert prs == []
        captured = capsys.readouterr()
        assert "Error getting pending review PRs: API error" in captured.out
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_get_my_open_prs_success(self, mock_run_command):
        mock_output = json.dumps([
            {
                "number": 789,
                "title": "My PR",
                "url": "https://github.com/test/test/pull/789",
                "author": {"login": "me"},
                "updatedAt": "2024-01-03T00:00:00Z",
                "body": "My contribution"
            }
        ])
        mock_run_command.return_value = mock_output
        
        github = GitHubIntegration("/tmp/test")
        prs = github.get_my_open_prs()
        
        assert len(prs) == 1
        assert prs[0].number == 789
        assert prs[0].title == "My PR"
        assert prs[0].author == "me"
        
        mock_run_command.assert_called_once_with([
            'pr', 'list',
            '--author=@me',
            '--state=open',
            '--json=number,title,url,author,updatedAt,body'
        ])
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_get_pr_comments_success(self, mock_run_command):
        mock_output = json.dumps({
            "comments": [
                {"id": 1, "body": "First comment"},
                {"id": 2, "body": "Second comment"}
            ]
        })
        mock_run_command.return_value = mock_output
        
        github = GitHubIntegration("/tmp/test")
        comments = github.get_pr_comments(123)
        
        assert len(comments) == 2
        assert comments[0]["body"] == "First comment"
        assert comments[1]["body"] == "Second comment"
        
        mock_run_command.assert_called_once_with([
            'pr', 'view', '123',
            '--json=comments'
        ])
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_get_pr_review_comments_success(self, mock_run_command):
        mock_output = json.dumps([
            {"id": 1, "body": "Review comment 1"},
            {"id": 2, "body": "Review comment 2"}
        ])
        mock_run_command.return_value = mock_output
        
        github = GitHubIntegration("/tmp/test")
        comments = github.get_pr_review_comments(456)
        
        assert len(comments) == 2
        assert comments[0]["body"] == "Review comment 1"
        
        mock_run_command.assert_called_once_with([
            'api', '/repos/:owner/:repo/pulls/456/comments'
        ])
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_update_pr_description_success(self, mock_run_command):
        mock_run_command.return_value = ""
        
        github = GitHubIntegration("/tmp/test")
        result = github.update_pr_description(123, "New description")
        
        assert result == True
        mock_run_command.assert_called_once_with([
            'pr', 'edit', '123',
            '--body', 'New description'
        ])
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_update_pr_description_error(self, mock_run_command, capsys):
        mock_run_command.side_effect = Exception("Update failed")
        
        github = GitHubIntegration("/tmp/test")
        result = github.update_pr_description(123, "New description")
        
        assert result == False
        captured = capsys.readouterr()
        assert "Error updating PR #123 description: Update failed" in captured.out
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_comment_on_pr_success(self, mock_run_command):
        mock_run_command.return_value = ""
        
        github = GitHubIntegration("/tmp/test")
        result = github.comment_on_pr(456, "Great work!")
        
        assert result == True
        mock_run_command.assert_called_once_with([
            'pr', 'comment', '456',
            '--body', 'Great work!'
        ])
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_get_assigned_issues_success(self, mock_run_command):
        mock_output = json.dumps([
            {
                "number": 101,
                "title": "Bug to fix",
                "url": "https://github.com/test/test/issues/101",
                "author": {"login": "reporter"},
                "updatedAt": "2024-01-04T00:00:00Z",
                "body": "There's a bug"
            },
            {
                "number": 102,
                "title": "Feature request",
                "url": "https://github.com/test/test/issues/102",
                "author": {"login": "user"},
                "updatedAt": "2024-01-05T00:00:00Z"
            }
        ])
        mock_run_command.return_value = mock_output
        
        github = GitHubIntegration("/tmp/test")
        issues = github.get_assigned_issues()
        
        assert len(issues) == 2
        assert issues[0].number == 101
        assert issues[0].title == "Bug to fix"
        assert issues[0].author == "reporter"
        assert issues[0].body == "There's a bug"
        assert issues[1].number == 102
        assert issues[1].body == ""  # Default empty body
        
        mock_run_command.assert_called_once_with([
            'issue', 'list',
            '--assignee=@me',
            '--state=open',
            '--json=number,title,url,author,updatedAt,body'
        ])
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_get_issue_comments_success(self, mock_run_command):
        mock_output = json.dumps({
            "comments": [
                {"id": 10, "body": "Issue comment 1"},
                {"id": 11, "body": "Issue comment 2"}
            ]
        })
        mock_run_command.return_value = mock_output
        
        github = GitHubIntegration("/tmp/test")
        comments = github.get_issue_comments(101)
        
        assert len(comments) == 2
        assert comments[0]["body"] == "Issue comment 1"
        
        mock_run_command.assert_called_once_with([
            'issue', 'view', '101',
            '--json=comments'
        ])
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_comment_on_issue_success(self, mock_run_command):
        mock_run_command.return_value = ""
        
        github = GitHubIntegration("/tmp/test")
        result = github.comment_on_issue(102, "Working on this")
        
        assert result == True
        mock_run_command.assert_called_once_with([
            'issue', 'comment', '102',
            '--body', 'Working on this'
        ])
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_comment_on_issue_error(self, mock_run_command, capsys):
        mock_run_command.side_effect = Exception("Comment failed")
        
        github = GitHubIntegration("/tmp/test")
        result = github.comment_on_issue(102, "Comment")
        
        assert result == False
        captured = capsys.readouterr()
        assert "Error commenting on issue #102: Comment failed" in captured.out
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_get_repo_status_success(self, mock_run_command):
        # Mock multiple command calls
        mock_run_command.side_effect = [
            json.dumps([{"name": "main"}, {"name": "develop"}]),  # branches
            json.dumps([{"sha": "abc123", "message": "Latest commit"}])  # commits
        ]
        
        github = GitHubIntegration("/tmp/test")
        status = github.get_repo_status()
        
        assert len(status["branches"]) == 2
        assert status["branches"][0]["name"] == "main"
        assert len(status["recent_commits"]) == 1
        assert status["recent_commits"][0]["sha"] == "abc123"
        assert status["timestamp"] is None
        
        assert mock_run_command.call_count == 2
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_get_repo_status_error(self, mock_run_command, capsys):
        mock_run_command.side_effect = Exception("API error")
        
        github = GitHubIntegration("/tmp/test")
        status = github.get_repo_status()
        
        assert status == {}
        captured = capsys.readouterr()
        assert "Error getting repo status: API error" in captured.out
    
    @patch.object(GitHubIntegration, 'get_pending_review_prs')
    @patch.object(GitHubIntegration, 'get_my_open_prs')
    @patch.object(GitHubIntegration, 'get_assigned_issues')
    @patch.object(GitHubIntegration, 'get_repo_status')
    def test_gather_workday_data(self, mock_repo_status, mock_issues, mock_my_prs, mock_pending):
        # Mock all the individual methods
        mock_pending.return_value = [Mock()]
        mock_my_prs.return_value = [Mock(), Mock()]
        mock_issues.return_value = [Mock()]
        mock_repo_status.return_value = {"branches": []}
        
        github = GitHubIntegration("/tmp/test")
        data = github.gather_workday_data()
        
        assert "pending_reviews" in data
        assert "my_prs" in data
        assert "assigned_issues" in data
        assert "repo_status" in data
        
        assert len(data["pending_reviews"]) == 1
        assert len(data["my_prs"]) == 2
        assert len(data["assigned_issues"]) == 1
        
        # Verify all methods were called
        mock_pending.assert_called_once()
        mock_my_prs.assert_called_once()
        mock_issues.assert_called_once()
        mock_repo_status.assert_called_once()


class TestGitHubIntegrationEdgeCases:
    """Test edge cases and error scenarios."""
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_json_parse_error(self, mock_run_command, capsys):
        mock_run_command.return_value = "invalid json"
        
        github = GitHubIntegration("/tmp/test")
        prs = github.get_pending_review_prs()
        
        assert prs == []
        captured = capsys.readouterr()
        assert "Error getting pending review PRs" in captured.out
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_missing_author_field(self, mock_run_command):
        # Mock output with missing author field
        mock_output = json.dumps([
            {
                "number": 123,
                "title": "PR without author",
                "url": "https://github.com/test/test/pull/123",
                "updatedAt": "2024-01-01T00:00:00Z",
                "body": "Test"
                # Missing author field
            }
        ])
        mock_run_command.return_value = mock_output
        
        github = GitHubIntegration("/tmp/test")
        prs = github.get_pending_review_prs()
        
        # Should handle missing fields gracefully
        assert prs == []
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_empty_json_response(self, mock_run_command):
        mock_run_command.return_value = "[]"
        
        github = GitHubIntegration("/tmp/test")
        prs = github.get_pending_review_prs()
        issues = github.get_assigned_issues()
        
        assert prs == []
        assert issues == []
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_null_json_response(self, mock_run_command):
        mock_run_command.return_value = "null"
        
        github = GitHubIntegration("/tmp/test")
        comments = github.get_pr_comments(123)
        
        # Should handle null gracefully
        assert comments == []


class TestGitHubIntegrationIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_complete_workday_workflow(self, mock_run_command):
        # Simulate a complete workday data gathering scenario
        mock_responses = [
            # pending_reviews call
            json.dumps([
                {
                    "number": 100,
                    "title": "Feature implementation",
                    "url": "https://github.com/test/test/pull/100",
                    "author": {"login": "teammate"},
                    "updatedAt": "2024-01-01T10:00:00Z",
                    "body": "Please review this feature"
                }
            ]),
            # my_prs call
            json.dumps([
                {
                    "number": 200,
                    "title": "My contribution",
                    "url": "https://github.com/test/test/pull/200",
                    "author": {"login": "me"},
                    "updatedAt": "2024-01-01T09:00:00Z",
                    "body": ""  # Empty description
                }
            ]),
            # assigned_issues call
            json.dumps([
                {
                    "number": 300,
                    "title": "URGENT: Critical bug",
                    "url": "https://github.com/test/test/issues/300",
                    "author": {"login": "user"},
                    "updatedAt": "2024-01-01T08:00:00Z",
                    "body": "System is down"
                }
            ]),
            # repo_status calls (branches, then commits)
            json.dumps([{"name": "main"}, {"name": "feature-branch"}]),
            json.dumps([{"sha": "abc123", "message": "Recent commit"}])
        ]
        
        mock_run_command.side_effect = mock_responses
        
        github = GitHubIntegration("/tmp/test")
        data = github.gather_workday_data()
        
        # Verify complete data structure
        assert len(data["pending_reviews"]) == 1
        assert data["pending_reviews"][0].number == 100
        assert data["pending_reviews"][0].title == "Feature implementation"
        
        assert len(data["my_prs"]) == 1
        assert data["my_prs"][0].number == 200
        assert data["my_prs"][0].body == ""  # Empty description
        
        assert len(data["assigned_issues"]) == 1
        assert data["assigned_issues"][0].number == 300
        assert "URGENT" in data["assigned_issues"][0].title
        
        assert len(data["repo_status"]["branches"]) == 2
        assert len(data["repo_status"]["recent_commits"]) == 1
        
        # Verify correct number of gh command calls
        assert mock_run_command.call_count == 5