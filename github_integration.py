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


@dataclass
class Branch:
    name: str
    current: bool
    remote: str
    ahead_count: int = 0
    behind_count: int = 0
    last_commit: str = ""
    last_commit_date: str = ""
    
    @property
    def needs_rebase(self) -> bool:
        return self.behind_count > 0
    
    @property
    def can_push(self) -> bool:
        return self.ahead_count > 0


@dataclass  
class Commit:
    sha: str
    message: str
    author: str
    date: str
    url: str
    files_changed: List[str] = None
    
    def __post_init__(self):
        if self.files_changed is None:
            self.files_changed = []


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
    
    def get_all_branches(self) -> List[Branch]:
        """Get all local and remote branches with status"""
        try:
            # Get branch status
            output = self._run_gh_command([
                'api', '/repos/:owner/:repo/branches'
            ])
            
            if not output:
                return []
            
            remote_branches = json.loads(output)
            
            # Get local branch status using git commands
            local_cmd = ['git', 'branch', '-vv']
            local_result = subprocess.run(
                local_cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            branches = []
            for line in local_result.stdout.strip().split('\n'):
                if not line.strip():
                    continue
                    
                current = line.startswith('*')
                parts = line.strip('* ').split()
                if len(parts) < 2:
                    continue
                    
                name = parts[0]
                commit = parts[1]
                
                # Find remote info
                remote_info = ""
                if '[' in line and ']' in line:
                    remote_info = line[line.find('[') + 1:line.find(']')]
                
                # Parse ahead/behind counts
                ahead_count = 0
                behind_count = 0
                if 'ahead' in remote_info:
                    ahead_count = int(remote_info.split('ahead ')[1].split(',')[0].split(']')[0])
                if 'behind' in remote_info:
                    behind_count = int(remote_info.split('behind ')[1].split(',')[0].split(']')[0])
                
                # Get last commit info
                commit_info = self._get_commit_info(commit)
                
                branches.append(Branch(
                    name=name,
                    current=current,
                    remote=remote_info.split(':')[0] if ':' in remote_info else 'origin',
                    ahead_count=ahead_count,
                    behind_count=behind_count,
                    last_commit=commit,
                    last_commit_date=commit_info.get('date', '')
                ))
            
            return branches
            
        except Exception as e:
            print(f"Error getting branches: {e}")
            return []
    
    def _get_commit_info(self, commit_sha: str) -> Dict[str, str]:
        """Get commit information"""
        try:
            cmd = ['git', 'show', '--format=%cd|%s|%an', '--date=iso', '-s', commit_sha]
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            if result.stdout.strip():
                parts = result.stdout.strip().split('|')
                return {
                    'date': parts[0] if len(parts) > 0 else '',
                    'message': parts[1] if len(parts) > 1 else '',
                    'author': parts[2] if len(parts) > 2 else ''
                }
            return {}
        except Exception:
            return {}
    
    def rebase_branch(self, branch_name: str, base_branch: str = 'main') -> Dict[str, Any]:
        """Safely rebase a branch from base branch"""
        try:
            # First, fetch latest changes
            subprocess.run(['git', 'fetch'], cwd=self.repo_path, check=True)
            
            # Check if there are uncommitted changes
            status_result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            if status_result.stdout.strip():
                return {
                    'success': False,
                    'error': 'Uncommitted changes present',
                    'action_needed': 'commit_or_stash'
                }
            
            # Switch to the branch
            subprocess.run(['git', 'checkout', branch_name], cwd=self.repo_path, check=True)
            
            # Attempt rebase
            rebase_result = subprocess.run(
                ['git', 'rebase', f'origin/{base_branch}'],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if rebase_result.returncode == 0:
                return {
                    'success': True,
                    'message': f'Successfully rebased {branch_name} from {base_branch}'
                }
            else:
                # Check if it's a conflict
                if 'conflict' in rebase_result.stderr.lower():
                    # Abort the rebase
                    subprocess.run(['git', 'rebase', '--abort'], cwd=self.repo_path)
                    return {
                        'success': False,
                        'error': 'Merge conflicts detected',
                        'action_needed': 'manual_resolution',
                        'conflicts': self._get_conflict_files()
                    }
                else:
                    return {
                        'success': False,
                        'error': rebase_result.stderr,
                        'action_needed': 'investigate'
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'action_needed': 'investigate'
            }
    
    def _get_conflict_files(self) -> List[str]:
        """Get list of files with merge conflicts"""
        try:
            result = subprocess.run(
                ['git', 'diff', '--name-only', '--diff-filter=U'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip().split('\n') if result.stdout.strip() else []
        except Exception:
            return []
    
    def get_commits_since(self, branch_name: str, since_date: str) -> List[Commit]:
        """Get commits on a branch since a specific date"""
        try:
            cmd = [
                'git', 'log', branch_name,
                f'--since={since_date}',
                '--format=%H|%s|%an|%cd|%D',
                '--date=iso'
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line.strip():
                    continue
                    
                parts = line.split('|')
                if len(parts) >= 4:
                    # Get file changes for this commit
                    files_changed = self._get_commit_files(parts[0])
                    
                    commits.append(Commit(
                        sha=parts[0],
                        message=parts[1],
                        author=parts[2],
                        date=parts[3],
                        url=f"https://github.com/:owner/:repo/commit/{parts[0]}",
                        files_changed=files_changed
                    ))
            
            return commits
            
        except Exception as e:
            print(f"Error getting commits since {since_date}: {e}")
            return []
    
    def _get_commit_files(self, commit_sha: str) -> List[str]:
        """Get list of files changed in a commit"""
        try:
            result = subprocess.run(
                ['git', 'diff-tree', '--no-commit-id', '--name-only', '-r', commit_sha],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip().split('\n') if result.stdout.strip() else []
        except Exception:
            return []
    
    def create_pr(self, branch_name: str, title: str, body: str, base_branch: str = 'main', draft: bool = False) -> Dict[str, Any]:
        """Create a new pull request"""
        try:
            cmd = [
                'pr', 'create',
                '--title', title,
                '--body', body,
                '--base', base_branch,
                '--head', branch_name
            ]
            
            if draft:
                cmd.append('--draft')
            
            output = self._run_gh_command(cmd)
            
            # Parse the PR URL from output
            if 'https://github.com' in output:
                pr_url = [line for line in output.split('\n') if 'https://github.com' in line][0].strip()
                pr_number = int(pr_url.split('/')[-1])
                
                return {
                    'success': True,
                    'pr_number': pr_number,
                    'pr_url': pr_url,
                    'message': f'Created PR #{pr_number}: {title}'
                }
            else:
                return {
                    'success': False,
                    'error': 'Could not parse PR URL from output',
                    'output': output
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_branch_commits_ahead_of_main(self, branch_name: str) -> List[Commit]:
        """Get commits that are in branch but not in main"""
        try:
            cmd = [
                'git', 'log', f'main..{branch_name}',
                '--format=%H|%s|%an|%cd',
                '--date=iso'
            ]
            
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line.strip():
                    continue
                    
                parts = line.split('|')
                if len(parts) >= 4:
                    files_changed = self._get_commit_files(parts[0])
                    
                    commits.append(Commit(
                        sha=parts[0],
                        message=parts[1],
                        author=parts[2],
                        date=parts[3],
                        url=f"https://github.com/:owner/:repo/commit/{parts[0]}",
                        files_changed=files_changed
                    ))
            
            return commits
            
        except Exception as e:
            print(f"Error getting commits ahead of main: {e}")
            return []

    def read_file(self, file_path: str, branch: str = 'main') -> Dict[str, Any]:
        """Read a file from the repository via GitHub API"""
        try:
            output = self._run_gh_command([
                'api', f'/repos/:owner/:repo/contents/{file_path}',
                '--jq', '.content',
                '-H', f'ref={branch}'
            ])
            
            if output:
                import base64
                content = base64.b64decode(output.strip('"')).decode('utf-8')
                return {
                    'success': True,
                    'content': content,
                    'path': file_path
                }
            else:
                return {
                    'success': False,
                    'error': 'File not found or empty response'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def write_file(self, file_path: str, content: str, commit_message: str, branch: str = 'main') -> Dict[str, Any]:
        """Write/update a file in the repository via GitHub API"""
        try:
            import base64
            import tempfile
            import os
            
            # First, try to get the current file to get its SHA (required for updates)
            sha_param = []
            try:
                sha_output = self._run_gh_command([
                    'api', f'/repos/:owner/:repo/contents/{file_path}',
                    '--jq', '.sha',
                    '-H', f'ref={branch}'
                ])
                if sha_output and sha_output.strip().strip('"'):
                    sha_param = ['-f', f'sha={sha_output.strip().strip('"')}']
            except Exception:
                # File doesn't exist, that's okay for new files
                pass
            
            # Encode content to base64
            encoded_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            # Write the file using gh api with field parameters
            cmd = [
                'api', f'/repos/:owner/:repo/contents/{file_path}',
                '-X', 'PUT',
                '-f', f'message={commit_message}',
                '-f', f'content={encoded_content}',
                '-f', f'branch={branch}'
            ] + sha_param
            
            output = self._run_gh_command(cmd)
            
            return {
                'success': True,
                'message': f'Successfully updated {file_path}',
                'commit_message': commit_message
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_dependency_files(self) -> Dict[str, Any]:
        """Get common dependency files from the repository"""
        dependency_files = {
            'package.json': 'npm/yarn projects',
            'requirements.txt': 'Python pip projects', 
            'Pipfile': 'Python pipenv projects',
            'pyproject.toml': 'Python poetry projects',
            'pom.xml': 'Java Maven projects',
            'build.gradle': 'Java Gradle projects',
            'Cargo.toml': 'Rust projects',
            'composer.json': 'PHP projects',
            'Gemfile': 'Ruby projects'
        }
        
        found_files = {}
        
        for file_name, description in dependency_files.items():
            result = self.read_file(file_name)
            if result.get('success'):
                found_files[file_name] = {
                    'description': description,
                    'content': result['content']
                }
        
        return found_files
    
    def get_security_files(self) -> Dict[str, Any]:
        """Get security-related files from the repository"""
        security_files = {
            'SECURITY.md': 'Security policy',
            '.github/workflows/security.yml': 'Security CI workflow',
            '.github/workflows/codeql-analysis.yml': 'CodeQL analysis',
            'CLAUDE.md': 'Claude Code instructions',
            'Architecture.md': 'Architecture documentation'
        }
        
        found_files = {}
        
        for file_name, description in security_files.items():
            result = self.read_file(file_name)
            if result.get('success'):
                found_files[file_name] = {
                    'description': description,
                    'content': result['content']
                }
        
        return found_files
    
    def check_vulnerabilities(self) -> Dict[str, Any]:
        """Check for known vulnerabilities using GitHub's security advisories"""
        try:
            # Get security advisories for the repository
            output = self._run_gh_command([
                'api', '/repos/:owner/:repo/security-advisories'
            ])
            
            advisories = json.loads(output) if output else []
            
            # Get dependency vulnerabilities
            vuln_output = self._run_gh_command([
                'api', '/repos/:owner/:repo/vulnerability-alerts'
            ])
            
            vulnerabilities = json.loads(vuln_output) if vuln_output else []
            
            return {
                'security_advisories': advisories,
                'vulnerability_alerts': vulnerabilities,
                'total_issues': len(advisories) + len(vulnerabilities)
            }
            
        except Exception as e:
            print(f"Error checking vulnerabilities: {e}")
            return {
                'security_advisories': [],
                'vulnerability_alerts': [],
                'total_issues': 0,
                'error': str(e)
            }

    def gather_workday_data(self) -> Dict[str, Any]:
        """Gather all relevant data for workday mode processing"""
        return {
            'pending_reviews': self.get_pending_review_prs(),
            'my_prs': self.get_my_open_prs(),
            'assigned_issues': self.get_assigned_issues(),
            'repo_status': self.get_repo_status(),
            'branches': self.get_all_branches()
        }
    
    def gather_weekend_data(self) -> Dict[str, Any]:
        """Gather all relevant data for weekend mode processing"""
        return {
            'dependency_files': self.get_dependency_files(),
            'security_files': self.get_security_files(),
            'vulnerabilities': self.check_vulnerabilities(),
            'branches': self.get_all_branches(),
            'my_prs': self.get_my_open_prs()
        }


