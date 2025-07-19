"""
Mode-specific execution logic for different work periods.
"""
import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from github_integration import GitHubIntegration
from usage_tracker import UsageTracker


@dataclass
class RepoConfig:
    name: str
    path: str
    priority: str  # high, medium, low
    watch_branches: List[str]


class BaseExecutor:
    def __init__(self, usage_tracker: UsageTracker):
        self.usage_tracker = usage_tracker
    
    def should_skip_due_to_usage(self) -> bool:
        """Check if we should skip execution due to usage limits"""
        status = self.usage_tracker.check_limits()
        return status == "limit_reached"
    
    def log_usage_status(self) -> None:
        """Log current usage status"""
        summary = self.usage_tracker.get_usage_summary()
        status = self.usage_tracker.check_limits()
        print(f"Usage status: {status} - {summary['total_tokens']} tokens, {summary['requests']} requests")


class WorkdayExecutor(BaseExecutor):
    """
    Conservative mode - planning only, minimal token usage.
    Pre-fetches GitHub data and passes structured data to Claude Code.
    """
    
    def execute(self, repos: List[RepoConfig]) -> Dict[str, Any]:
        """Execute workday tasks for all repositories"""
        if self.should_skip_due_to_usage():
            print("Skipping workday execution due to usage limits")
            return {"status": "skipped", "reason": "usage_limit"}
        
        self.log_usage_status()
        
        results = {}
        
        # Limit repos in workday mode to preserve usage
        high_priority_repos = [repo for repo in repos if repo.priority == "high"]
        active_repos = high_priority_repos[:3]  # Max 3 repos in workday mode
        
        for repo in active_repos:
            try:
                repo_results = self._process_repo_workday(repo)
                results[repo.name] = repo_results
            except Exception as e:
                print(f"Error processing repo {repo.name}: {e}")
                results[repo.name] = {"status": "error", "error": str(e)}
        
        return {"status": "completed", "results": results}
    
    def _process_repo_workday(self, repo: RepoConfig) -> Dict[str, Any]:
        """Process a single repository in workday mode"""
        github = GitHubIntegration(repo.path)
        
        # Pre-fetch all GitHub data
        github_data = github.gather_workday_data()
        
        tasks = []
        
        # Check for pending reviews
        if github_data['pending_reviews']:
            tasks.append({
                "type": "review_responses",
                "data": github_data['pending_reviews'],
                "prompt": self._build_review_prompt(github_data['pending_reviews'])
            })
        
        # Check for PRs needing description updates
        empty_desc_prs = [pr for pr in github_data['my_prs'] if not pr.body.strip()]
        if empty_desc_prs:
            tasks.append({
                "type": "pr_descriptions",
                "data": empty_desc_prs,
                "prompt": self._build_pr_description_prompt(empty_desc_prs)
            })
        
        # Check for issue responses needed
        if github_data['assigned_issues']:
            tasks.append({
                "type": "issue_responses",
                "data": github_data['assigned_issues'],
                "prompt": self._build_issue_prompt(github_data['assigned_issues'])
            })
        
        return {
            "status": "ready",
            "tasks": tasks,
            "github_data": github_data
        }
    
    def _build_review_prompt(self, prs: List) -> str:
        """Build prompt for PR review responses"""
        return f"""
# Workday Mode: PR Review Planning

You are an engineering manager reviewing {len(prs)} pull requests. For each PR, provide:
1. High-level feedback on the approach
2. Questions for the author (no detailed code review)
3. Suggestions for testing or documentation
4. Approval/changes requested recommendation

IMPORTANT: Provide planning and feedback only. Do not generate code.

PRs to review:
{json.dumps([{"number": pr.number, "title": pr.title, "author": pr.author, "url": pr.url} for pr in prs], indent=2)}

Respond with structured feedback for each PR.
"""
    
    def _build_pr_description_prompt(self, prs: List) -> str:
        """Build prompt for updating PR descriptions"""
        return f"""
# Workday Mode: PR Description Updates

{len(prs)} of your PRs have empty descriptions. Based on the PR titles and any available context, 
draft appropriate descriptions that include:
1. What the PR does
2. Why the change is needed
3. Any testing considerations
4. Breaking changes (if any)

PRs needing descriptions:
{json.dumps([{"number": pr.number, "title": pr.title, "url": pr.url} for pr in prs], indent=2)}

Provide suggested descriptions for each PR.
"""
    
    def _build_issue_prompt(self, issues: List) -> str:
        """Build prompt for issue responses"""
        return f"""
# Workday Mode: Issue Response Planning

You have {len(issues)} assigned issues. For each issue, provide:
1. Initial analysis of the problem
2. Questions for clarification (if needed)
3. High-level implementation approach
4. Effort estimation
5. Priority recommendation

IMPORTANT: Provide planning only. Do not implement solutions.

Issues assigned:
{json.dumps([{"number": issue.number, "title": issue.title, "author": issue.author, "url": issue.url} for issue in issues], indent=2)}

Respond with structured analysis for each issue.
"""


class WorknightExecutor(BaseExecutor):
    """
    Active mode - code generation and implementation.
    Allows Claude Code to call gh commands directly for dynamic workflows.
    """
    
    def execute(self, repos: List[RepoConfig]) -> Dict[str, Any]:
        """Execute worknight tasks for all repositories"""
        if self.should_skip_due_to_usage():
            print("Skipping worknight execution due to usage limits")
            return {"status": "skipped", "reason": "usage_limit"}
        
        self.log_usage_status()
        
        results = {}
        
        for repo in repos:
            try:
                repo_results = self._process_repo_worknight(repo)
                results[repo.name] = repo_results
            except Exception as e:
                print(f"Error processing repo {repo.name}: {e}")
                results[repo.name] = {"status": "error", "error": str(e)}
        
        return {"status": "completed", "results": results}
    
    def _process_repo_worknight(self, repo: RepoConfig) -> Dict[str, Any]:
        """Process a single repository in worknight mode"""
        prompt = f"""
# Worknight Mode: Active Development

You are working on {repo.name} located at {repo.path}. Execute these tasks:

1. **Branch Management**:
   - Check status of my open branches
   - Rebase them from main branch
   - Resolve any merge conflicts

2. **Implementation Work**:
   - Review my open PRs and implement any planned features
   - Address review comments with actual code changes
   - Run tests and fix any failures

3. **Code Quality**:
   - Run linters and fix issues
   - Update documentation if needed
   - Ensure CI passes

4. **Repository Maintenance**:
   - Check for dependency updates
   - Clean up old branches
   - Update README if needed

You have full access to gh commands and can make direct changes.
Work systematically through each task and report your progress.

Repository: {repo.name}
Priority: {repo.priority}
Watch branches: {', '.join(repo.watch_branches)}
"""
        
        return {
            "status": "ready",
            "prompt": prompt,
            "mode": "worknight"
        }


class WeekendExecutor(BaseExecutor):
    """
    Monitoring mode - minimal activity, high-priority repos only.
    """
    
    def execute(self, repos: List[RepoConfig]) -> Dict[str, Any]:
        """Execute weekend monitoring for high-priority repositories only"""
        if self.should_skip_due_to_usage():
            print("Skipping weekend execution due to usage limits")
            return {"status": "skipped", "reason": "usage_limit"}
        
        self.log_usage_status()
        
        # Only process high-priority repos
        high_priority_repos = [repo for repo in repos if repo.priority == "high"]
        
        results = {}
        
        for repo in high_priority_repos:
            try:
                repo_results = self._monitor_repo(repo)
                results[repo.name] = repo_results
            except Exception as e:
                print(f"Error monitoring repo {repo.name}: {e}")
                results[repo.name] = {"status": "error", "error": str(e)}
        
        return {"status": "completed", "results": results}
    
    def _monitor_repo(self, repo: RepoConfig) -> Dict[str, Any]:
        """Monitor a single repository for urgent issues"""
        github = GitHubIntegration(repo.path)
        
        # Check for urgent items only
        pending_reviews = github.get_pending_review_prs()
        urgent_issues = [issue for issue in github.get_assigned_issues() 
                        if "urgent" in issue.title.lower() or "critical" in issue.title.lower()]
        
        notifications = []
        
        if pending_reviews:
            notifications.append(f"{len(pending_reviews)} pending reviews")
        
        if urgent_issues:
            notifications.append(f"{len(urgent_issues)} urgent issues")
        
        return {
            "status": "monitored",
            "notifications": notifications,
            "pending_reviews": len(pending_reviews),
            "urgent_issues": len(urgent_issues)
        }


def get_executor(mode: str, usage_tracker: UsageTracker) -> BaseExecutor:
    """Factory function to get the appropriate executor for a work mode"""
    executors = {
        "workday": WorkdayExecutor,
        "worknight": WorknightExecutor,
        "weekend": WeekendExecutor
    }
    
    executor_class = executors.get(mode)
    if not executor_class:
        raise ValueError(f"Unknown work mode: {mode}")
    
    return executor_class(usage_tracker)


if __name__ == "__main__":
    # Test the executors
    from usage_tracker import UsageTracker
    
    usage_tracker = UsageTracker()
    
    # Test repo config
    test_repos = [
        RepoConfig("test-repo", "/tmp", "high", ["main"]),
    ]
    
    # Test workday executor
    workday_executor = get_executor("workday", usage_tracker)
    result = workday_executor.execute(test_repos)
    print(f"Workday result: {result}")