"""
GitHub integration using gh CLI commands.
"""
import json
import subprocess
from typing import List, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class PullRequest:
    number: int
    title: str
    url: str
    author: str
    updated_at: str
    state: str
    body: str = ""
    comments: List[Dict] = None
    
    def __post_init__(self):
        if self.comments is None:
            self.comments = []


@dataclass
class Issue:
    number: int
    title: str
    url: str
    author: str
    updated_at: str
    state: str
    body: str = ""
    comments: List[Dict] = None
    
    def __post_init__(self):
        if self.comments is None:
            self.comments = []


class GitHubIntegration:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
    
    def _run_gh_command(self, args: List[str], cwd: str = None) -> str:
        """Run a gh CLI command and return stdout"""
        try:
            cmd = ['gh'] + args
            result = subprocess.run(
                cmd,
                cwd=cwd or self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise Exception(f"gh command failed: {e.stderr}")
    
    def get_pending_review_prs(self) -> List[PullRequest]:
        """Get PRs that request review from current user"""
        try:
            output = self._run_gh_command([
                'search', 'prs',
                '--review-requested=@me',
                '--state=open',
                '--json=number,title,url,author,updatedAt,body'
            ])
            
            if not output:
                return []
                
            data = json.loads(output)
            return [
                PullRequest(
                    number=pr['number'],
                    title=pr['title'],
                    url=pr['url'],
                    author=pr['author']['login'],
                    updated_at=pr['updatedAt'],
                    state='open',
                    body=pr.get('body', '')
                )
                for pr in data
            ]
        except Exception as e:
            print(f"Error getting pending review PRs: {e}")
            return []
    
    def get_my_open_prs(self) -> List[PullRequest]:
        """Get open PRs authored by current user"""
        try:
            output = self._run_gh_command([
                'pr', 'list',
                '--author=@me',
                '--state=open',
                '--json=number,title,url,author,updatedAt,body'
            ])
            
            if not output:
                return []
                
            data = json.loads(output)
            return [
                PullRequest(
                    number=pr['number'],
                    title=pr['title'],
                    url=pr['url'],
                    author=pr['author']['login'],
                    updated_at=pr['updatedAt'],
                    state='open',
                    body=pr.get('body', '')
                )
                for pr in data
            ]
        except Exception as e:
            print(f"Error getting my open PRs: {e}")
            return []
    
    def get_pr_comments(self, pr_number: int) -> List[Dict]:
        """Get comments for a specific PR"""
        try:
            output = self._run_gh_command([
                'pr', 'view', str(pr_number),
                '--json=comments'
            ])
            
            if not output:
                return []
                
            data = json.loads(output)
            return data.get('comments', [])
        except Exception as e:
            print(f"Error getting PR comments for #{pr_number}: {e}")
            return []
    
    def get_pr_review_comments(self, pr_number: int) -> List[Dict]:
        """Get review comments for a specific PR"""
        try:
            output = self._run_gh_command([
                'api', f'/repos/:owner/:repo/pulls/{pr_number}/comments'
            ])
            
            if not output:
                return []
                
            return json.loads(output)
        except Exception as e:
            print(f"Error getting PR review comments for #{pr_number}: {e}")
            return []
    
    def update_pr_description(self, pr_number: int, description: str) -> bool:
        """Update PR description"""
        try:
            self._run_gh_command([
                'pr', 'edit', str(pr_number),
                '--body', description
            ])
            return True
        except Exception as e:
            print(f"Error updating PR #{pr_number} description: {e}")
            return False
    
    def comment_on_pr(self, pr_number: int, comment: str) -> bool:
        """Add a comment to a PR"""
        try:
            self._run_gh_command([
                'pr', 'comment', str(pr_number),
                '--body', comment
            ])
            return True
        except Exception as e:
            print(f"Error commenting on PR #{pr_number}: {e}")
            return False
    
    def get_assigned_issues(self) -> List[Issue]:
        """Get issues assigned to current user"""
        try:
            output = self._run_gh_command([
                'issue', 'list',
                '--assignee=@me',
                '--state=open',
                '--json=number,title,url,author,updatedAt,body'
            ])
            
            if not output:
                return []
                
            data = json.loads(output)
            return [
                Issue(
                    number=issue['number'],
                    title=issue['title'],
                    url=issue['url'],
                    author=issue['author']['login'],
                    updated_at=issue['updatedAt'],
                    state='open',
                    body=issue.get('body', '')
                )
                for issue in data
            ]
        except Exception as e:
            print(f"Error getting assigned issues: {e}")
            return []
    
    def get_issue_comments(self, issue_number: int) -> List[Dict]:
        """Get comments for a specific issue"""
        try:
            output = self._run_gh_command([
                'issue', 'view', str(issue_number),
                '--json=comments'
            ])
            
            if not output:
                return []
                
            data = json.loads(output)
            return data.get('comments', [])
        except Exception as e:
            print(f"Error getting issue comments for #{issue_number}: {e}")
            return []
    
    def comment_on_issue(self, issue_number: int, comment: str) -> bool:
        """Add a comment to an issue"""
        try:
            self._run_gh_command([
                'issue', 'comment', str(issue_number),
                '--body', comment
            ])
            return True
        except Exception as e:
            print(f"Error commenting on issue #{issue_number}: {e}")
            return False
    
    def get_repo_status(self) -> Dict[str, Any]:
        """Get repository status information"""
        try:
            # Get current branch
            branch_output = self._run_gh_command(['api', '/repos/:owner/:repo/branches'])
            branches = json.loads(branch_output) if branch_output else []
            
            # Get recent commits
            commits_output = self._run_gh_command([
                'api', '/repos/:owner/:repo/commits',
                '--jq', '.[0:5]'
            ])
            commits = json.loads(commits_output) if commits_output else []
            
            return {
                'branches': branches,
                'recent_commits': commits,
                'timestamp': None  # Will be set by caller
            }
        except Exception as e:
            print(f"Error getting repo status: {e}")
            return {}
    
    def gather_workday_data(self) -> Dict[str, Any]:
        """Gather all relevant data for workday mode processing"""
        return {
            'pending_reviews': self.get_pending_review_prs(),
            'my_prs': self.get_my_open_prs(),
            'assigned_issues': self.get_assigned_issues(),
            'repo_status': self.get_repo_status()
        }


