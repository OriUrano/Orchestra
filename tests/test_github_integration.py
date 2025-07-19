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
            json.dumps([{"sha": "abc123", "message": "Recent commit"}]),
            # get_all_branches call (new in enhanced version)
            json.dumps([{"name": "main"}, {"name": "feature-branch"}])
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
        
        # Check that branches data is present (may be empty due to git command failure in test)
        assert "branches" in data
        
        # Verify correct number of gh command calls (updated for enhanced version)
        assert mock_run_command.call_count == 6  # 5 original + 1 from get_all_branches


class TestNewGitHubIntegrationFeatures:
    """Test the new enhanced GitHub integration features."""
    
    @patch('subprocess.run')
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_get_all_branches_success(self, mock_gh_command, mock_subprocess):
        # Mock gh api call for remote branches
        mock_gh_command.return_value = json.dumps([
            {"name": "main"}, {"name": "develop"}
        ])
        
        # Mock git branch -vv output
        mock_subprocess.return_value = Mock(
            stdout="* main 1234567 [origin/main] Latest commit\n  feature-branch abcdefg [origin/feature-branch: ahead 2, behind 1] Feature work\n",
            returncode=0
        )
        
        github = GitHubIntegration("/tmp/test")
        branches = github.get_all_branches()
        
        assert len(branches) == 2
        assert branches[0].name == "main"
        assert branches[0].current == True
        assert branches[0].ahead_count == 0
        assert branches[0].behind_count == 0
        
        assert branches[1].name == "feature-branch"
        assert branches[1].current == False
        assert branches[1].ahead_count == 2
        assert branches[1].behind_count == 1
        assert branches[1].needs_rebase == True
    
    @patch('subprocess.run')
    def test_rebase_branch_success(self, mock_subprocess):
        # Mock successful rebase
        mock_subprocess.side_effect = [
            Mock(returncode=0),  # git fetch
            Mock(stdout="", returncode=0),  # git status --porcelain
            Mock(returncode=0),  # git checkout
            Mock(returncode=0, stderr="")  # git rebase
        ]
        
        github = GitHubIntegration("/tmp/test")
        result = github.rebase_branch("feature-branch")
        
        assert result["success"] == True
        assert "Successfully rebased" in result["message"]
    
    @patch('subprocess.run')
    def test_rebase_branch_with_conflicts(self, mock_subprocess):
        # Mock rebase with conflicts
        mock_subprocess.side_effect = [
            Mock(returncode=0),  # git fetch
            Mock(stdout="", returncode=0),  # git status --porcelain
            Mock(returncode=0),  # git checkout
            Mock(returncode=1, stderr="CONFLICT (content): Merge conflict in file.txt"),  # git rebase
            Mock(returncode=0)  # git rebase --abort
        ]
        
        github = GitHubIntegration("/tmp/test")
        result = github.rebase_branch("feature-branch")
        
        assert result["success"] == False
        assert result["error"] == "Merge conflicts detected"
        assert result["action_needed"] == "manual_resolution"
    
    @patch('subprocess.run')
    def test_rebase_branch_uncommitted_changes(self, mock_subprocess):
        # Mock uncommitted changes
        mock_subprocess.side_effect = [
            Mock(returncode=0),  # git fetch
            Mock(stdout="M modified_file.py\n", returncode=0),  # git status --porcelain
        ]
        
        github = GitHubIntegration("/tmp/test")
        result = github.rebase_branch("feature-branch")
        
        assert result["success"] == False
        assert result["error"] == "Uncommitted changes present"
        assert result["action_needed"] == "commit_or_stash"
    
    @patch('subprocess.run')
    def test_get_commits_since_success(self, mock_subprocess):
        # Mock git log output
        mock_subprocess.return_value = Mock(
            stdout="abc123|Fix bug in authentication|John Doe|2024-01-01 10:00:00 +0000|\ndef456|Add new feature|Jane Smith|2024-01-01 09:00:00 +0000|\n",
            returncode=0
        )
        
        github = GitHubIntegration("/tmp/test")
        commits = github.get_commits_since("main", "2024-01-01")
        
        assert len(commits) == 2
        assert commits[0].sha == "abc123"
        assert commits[0].message == "Fix bug in authentication"
        assert commits[0].author == "John Doe"
        assert commits[1].sha == "def456"
        assert commits[1].message == "Add new feature"
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_create_pr_success(self, mock_gh_command):
        mock_gh_command.return_value = "https://github.com/test/test/pull/123\nPR created successfully"
        
        github = GitHubIntegration("/tmp/test")
        result = github.create_pr("feature-branch", "New Feature", "This adds a new feature", "main")
        
        assert result["success"] == True
        assert result["pr_number"] == 123
        assert result["pr_url"] == "https://github.com/test/test/pull/123"
        
        mock_gh_command.assert_called_once_with([
            'pr', 'create',
            '--title', 'New Feature',
            '--body', 'This adds a new feature',
            '--base', 'main',
            '--head', 'feature-branch'
        ])
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_create_pr_draft(self, mock_gh_command):
        mock_gh_command.return_value = "https://github.com/test/test/pull/456\nDraft PR created"
        
        github = GitHubIntegration("/tmp/test")
        result = github.create_pr("draft-branch", "Draft Feature", "Work in progress", draft=True)
        
        assert result["success"] == True
        assert result["pr_number"] == 456
        
        # Verify draft flag was included
        call_args = mock_gh_command.call_args[0][0]
        assert '--draft' in call_args
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_read_file_success(self, mock_gh_command):
        import base64
        content = "# README\nThis is a test file"
        encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        mock_gh_command.return_value = f'"{encoded_content}"'
        
        github = GitHubIntegration("/tmp/test")
        result = github.read_file("README.md")
        
        assert result["success"] == True
        assert result["content"] == content
        assert result["path"] == "README.md"
        
        mock_gh_command.assert_called_once_with([
            'api', '/repos/:owner/:repo/contents/README.md',
            '--jq', '.content',
            '-H', 'ref=main'
        ])
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_read_file_not_found(self, mock_gh_command):
        mock_gh_command.return_value = ""
        
        github = GitHubIntegration("/tmp/test")
        result = github.read_file("nonexistent.txt")
        
        assert result["success"] == False
        assert "File not found" in result["error"]
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    @patch.object(GitHubIntegration, 'read_file')
    def test_write_file_new(self, mock_read_file, mock_gh_command):
        # Mock file doesn't exist
        mock_read_file.return_value = {"success": False}
        mock_gh_command.side_effect = [
            Exception("File not found"),  # First call for SHA
            ""  # Second call for actual write
        ]
        
        github = GitHubIntegration("/tmp/test")
        result = github.write_file("new_file.txt", "New content", "Add new file")
        
        assert result["success"] == True
        assert "Successfully updated" in result["message"]
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_get_dependency_files_success(self, mock_gh_command):
        # Mock reading multiple dependency files
        import base64
        
        package_json = '{"name": "test", "dependencies": {}}'
        requirements_txt = "requests==2.28.0\nflask==2.2.0"
        
        def mock_read_responses(args):
            if 'package.json' in args[1]:
                return f'"{base64.b64encode(package_json.encode()).decode()}"'
            elif 'requirements.txt' in args[1]:
                return f'"{base64.b64encode(requirements_txt.encode()).decode()}"'
            else:
                raise Exception("File not found")
        
        mock_gh_command.side_effect = mock_read_responses
        
        github = GitHubIntegration("/tmp/test")
        files = github.get_dependency_files()
        
        assert "package.json" in files
        assert "requirements.txt" in files
        assert files["package.json"]["content"] == package_json
        assert files["requirements.txt"]["content"] == requirements_txt
        assert "npm/yarn projects" in files["package.json"]["description"]
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_check_vulnerabilities_success(self, mock_gh_command):
        # Mock security advisories and vulnerability alerts
        advisories = [{"id": "GHSA-1234", "severity": "HIGH"}]
        vulnerabilities = [{"id": "CVE-2024-1234", "severity": "MEDIUM"}]
        
        mock_gh_command.side_effect = [
            json.dumps(advisories),
            json.dumps(vulnerabilities)
        ]
        
        github = GitHubIntegration("/tmp/test")
        result = github.check_vulnerabilities()
        
        assert result["total_issues"] == 2
        assert len(result["security_advisories"]) == 1
        assert len(result["vulnerability_alerts"]) == 1
        assert result["security_advisories"][0]["severity"] == "HIGH"
    
    @patch.object(GitHubIntegration, '_run_gh_command')
    def test_check_vulnerabilities_error(self, mock_gh_command, capsys):
        mock_gh_command.side_effect = Exception("API Error")
        
        github = GitHubIntegration("/tmp/test")
        result = github.check_vulnerabilities()
        
        assert result["total_issues"] == 0
        assert result["security_advisories"] == []
        assert result["vulnerability_alerts"] == []
        assert "error" in result
        
        captured = capsys.readouterr()
        assert "Error checking vulnerabilities" in captured.out
    
    @patch.object(GitHubIntegration, 'get_dependency_files')
    @patch.object(GitHubIntegration, 'get_security_files')
    @patch.object(GitHubIntegration, 'check_vulnerabilities')
    @patch.object(GitHubIntegration, 'get_all_branches')
    @patch.object(GitHubIntegration, 'get_my_open_prs')
    def test_gather_weekend_data(self, mock_my_prs, mock_branches, mock_vulns, mock_security_files, mock_dep_files):
        # Mock all weekend data gathering methods
        mock_dep_files.return_value = {"package.json": {"description": "npm project"}}
        mock_security_files.return_value = {"CLAUDE.md": {"description": "Claude instructions"}}
        mock_vulns.return_value = {"total_issues": 5}
        mock_branches.return_value = [Mock()]
        mock_my_prs.return_value = [Mock(), Mock()]
        
        github = GitHubIntegration("/tmp/test")
        data = github.gather_weekend_data()
        
        assert "dependency_files" in data
        assert "security_files" in data  
        assert "vulnerabilities" in data
        assert "branches" in data
        assert "my_prs" in data
        
        assert len(data["dependency_files"]) == 1
        assert data["vulnerabilities"]["total_issues"] == 5
        assert len(data["my_prs"]) == 2
        
        # Verify all methods called
        mock_dep_files.assert_called_once()
        mock_security_files.assert_called_once()
        mock_vulns.assert_called_once()
        mock_branches.assert_called_once()
        mock_my_prs.assert_called_once()


class TestBranchDataClass:
    """Test the new Branch dataclass."""
    
    def test_branch_creation(self):
        from github_integration import Branch
        
        branch = Branch(
            name="feature-branch",
            current=False,
            remote="origin",
            ahead_count=3,
            behind_count=2,
            last_commit="abc123",
            last_commit_date="2024-01-01"
        )
        
        assert branch.name == "feature-branch"
        assert branch.current == False
        assert branch.remote == "origin"
        assert branch.ahead_count == 3
        assert branch.behind_count == 2
        assert branch.needs_rebase == True  # behind_count > 0
        assert branch.can_push == True     # ahead_count > 0
    
    def test_branch_up_to_date(self):
        from github_integration import Branch
        
        branch = Branch(
            name="main",
            current=True,
            remote="origin",
            ahead_count=0,
            behind_count=0
        )
        
        assert branch.needs_rebase == False
        assert branch.can_push == False
    
    def test_branch_ahead_only(self):
        from github_integration import Branch
        
        branch = Branch(
            name="feature",
            current=True,
            remote="origin",
            ahead_count=2,
            behind_count=0
        )
        
        assert branch.needs_rebase == False
        assert branch.can_push == True


class TestCommitDataClass:
    """Test the new Commit dataclass."""
    
    def test_commit_creation(self):
        from github_integration import Commit
        
        commit = Commit(
            sha="abc123",
            message="Fix authentication bug",
            author="John Doe",
            date="2024-01-01T10:00:00Z",
            url="https://github.com/test/test/commit/abc123",
            files_changed=["auth.py", "tests/test_auth.py"]
        )
        
        assert commit.sha == "abc123"
        assert commit.message == "Fix authentication bug"
        assert commit.author == "John Doe"
        assert commit.date == "2024-01-01T10:00:00Z"
        assert len(commit.files_changed) == 2
        assert "auth.py" in commit.files_changed
    
    def test_commit_default_files(self):
        from github_integration import Commit
        
        commit = Commit(
            sha="def456",
            message="Update documentation",
            author="Jane Smith",
            date="2024-01-01T11:00:00Z",
            url="https://github.com/test/test/commit/def456"
        )
        
        assert commit.files_changed == []