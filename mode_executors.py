"""
Mode-specific execution logic for different work periods.
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from github_integration import GitHubIntegration
from usage_tracker import SessionTracker


@dataclass
class RepoConfig:
    name: str
    path: str
    priority: str  # high, medium, low
    watch_branches: List[str]


class BaseExecutor:
    def __init__(self, session_tracker: SessionTracker):
        self.session_tracker = session_tracker
    
    def should_skip_due_to_session(self) -> bool:
        """Check if we should skip execution due to session status"""
        status = self.session_tracker.check_session_status()
        return status == "session_expired"
    
    def should_maximize_usage(self) -> bool:
        """Check if we should maximize usage (final 15 minutes of session)"""
        status = self.session_tracker.check_session_status()
        return status == "maximize_usage"
    
    def get_session_mode(self) -> str:
        """Get current session mode for execution strategy"""
        return self.session_tracker.check_session_status()
    
    def log_session_status(self) -> None:
        """Log current session status"""
        summary = self.session_tracker.get_session_summary()
        status = self.session_tracker.check_session_status()
        session_info = ""
        if "session_remaining_minutes" in summary:
            session_info = f" - {summary['session_remaining_minutes']} min remaining"
        print(f"Session status: {status}{session_info}")


class WorkdayExecutor(BaseExecutor):
    """
    Conservative mode - planning only, minimal token usage.
    Pre-fetches GitHub data and passes structured data to Claude Code.
    """
    
    def execute(self, repos: List[RepoConfig]) -> Dict[str, Any]:
        """Execute workday tasks for all repositories"""
        session_mode = self.get_session_mode()
        
        if session_mode == "session_expired":
            print("Skipping workday execution - session expired")
            return {"status": "skipped", "reason": "session_expired"}
        
        self.log_session_status()
        
        results = {}
        
        # Adjust repo processing based on session mode
        if session_mode == "maximize_usage":
            print("Maximizing usage in final session window - processing all high priority repos")
            active_repos = [repo for repo in repos if repo.priority == "high"]
        else:
            # Normal workday mode - limit repos for conservative approach
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
        
        # Check branch status and recommend rebasing (conservative)
        branches_needing_attention = [b for b in github_data['branches'] if b.needs_rebase and not b.current]
        if branches_needing_attention:
            tasks.append({
                "type": "branch_management",
                "data": branches_needing_attention,
                "prompt": self._build_branch_status_prompt(branches_needing_attention)
            })
        
        # Check for new commits on reviewed PRs (since yesterday)
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        new_commits_on_reviewed = []
        
        for pr in github_data['pending_reviews']:
            try:
                # Get commits since yesterday on PR branch
                commits = github.get_commits_since(pr.author, yesterday)  # Simplified - in real implementation would need PR branch name
                if commits:
                    new_commits_on_reviewed.append({
                        'pr': pr,
                        'new_commits': commits
                    })
            except Exception as e:
                print(f"Error checking commits for PR #{pr.number}: {e}")
        
        if new_commits_on_reviewed:
            tasks.append({
                "type": "commit_notifications",
                "data": new_commits_on_reviewed,
                "prompt": self._build_commit_notification_prompt(new_commits_on_reviewed)
            })
        
        # Check for comments on my PRs that need responses (conservative)
        prs_needing_responses = []
        for pr in github_data['my_prs']:
            try:
                comments = github.get_pr_comments(pr.number)
                review_comments = github.get_pr_review_comments(pr.number)
                all_comments = comments + review_comments
                
                # Filter for recent comments from others that might need responses
                recent_comments = [c for c in all_comments 
                                 if c.get('user', {}).get('login') != pr.author and
                                    '?' in c.get('body', '')]  # Simple heuristic for questions
                
                if recent_comments:
                    prs_needing_responses.append({
                        'pr': pr,
                        'comments': recent_comments
                    })
            except Exception as e:
                print(f"Error checking comments for PR #{pr.number}: {e}")
        
        if prs_needing_responses:
            tasks.append({
                "type": "comment_responses",
                "data": prs_needing_responses,
                "prompt": self._build_comment_response_prompt(prs_needing_responses)
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
    
    def _build_branch_status_prompt(self, branches: List) -> str:
        """Build prompt for branch status management"""
        branch_list = "\n".join([
            f"- {branch.name}: {branch.behind_count} commits behind main, last commit: {branch.last_commit_date}"
            for branch in branches
        ])
        
        return f"""
# Workday Mode: Branch Status Review

{len(branches)} branches need attention - they are behind the main branch and may need rebasing.

IMPORTANT: This is workday mode - provide planning and recommendations only. Do not perform actual rebasing operations.

## Branches Behind Main:
{branch_list}

## Review Tasks:
For each branch, provide:

1. **Risk Assessment**:
   - How critical is it to update this branch?
   - Are there likely to be merge conflicts?
   - What's the impact of delaying the rebase?

2. **Timing Recommendation**:
   - Should this be rebased during worknight mode?
   - Can this wait until the weekend?
   - Is this urgent enough to handle manually?

3. **Conflict Prediction**:
   - Based on the age and files likely changed, what conflicts might occur?
   - Are there any high-risk areas (package files, config, etc.)?

4. **Action Plan**:
   - Recommended next steps for each branch
   - Who should be contacted if needed
   - Dependencies or prerequisites

## Response Format:
```
### Branch: [branch_name]
**Risk Level**: [Low/Medium/High]
**Timing**: [Worknight/Weekend/Manual/Urgent]
**Conflict Risk**: [Low/Medium/High - reasoning]
**Recommendation**: [Specific action plan]
```

Focus on management decisions and risk assessment, not technical implementation.
"""
    
    def _build_commit_notification_prompt(self, commit_data: List) -> str:
        """Build prompt for new commit notifications"""
        notification_list = []
        for item in commit_data:
            pr = item['pr']
            commits = item['new_commits']
            commit_summaries = [f"  - {c.message[:60]}..." for c in commits[:3]]
            notification_list.append(f"PR #{pr.number} ({pr.title}):\\n" + "\\n".join(commit_summaries))
        
        notifications = "\\n\\n".join(notification_list)
        
        return f"""
# Workday Mode: New Commit Notifications

New commits have been added to {len(commit_data)} PRs you're reviewing since yesterday.
This may affect your previous review comments.

## PRs with New Commits:
{notifications}

## Review Impact Assessment:
For each PR, provide:

1. **Review Status Impact**:
   - Do these commits address your previous review comments?
   - Do they introduce new areas that need review?
   - Has the scope of the PR changed significantly?

2. **Priority Assessment**:
   - Does this PR need immediate re-review?
   - Can the re-review wait until you have more time?
   - Are there any red flags in the new commits?

3. **Next Steps**:
   - Should you update your review comments?
   - Do you need to ask the author questions about the changes?
   - Should this PR be flagged for closer attention?

## Response Format:
```
### PR #{{number}}: {{title}}
**Impact Level**: [Low/Medium/High]
**Re-review Priority**: [Immediate/Today/Tomorrow/Next Cycle]
**Key Changes**: [Summary of what changed]
**Action Required**: [Specific next steps]
```

Focus on review management and prioritization, not detailed code analysis.
"""
    
    def _build_comment_response_prompt(self, comment_data: List) -> str:
        """Build prompt for conservative comment responses"""
        comment_list = []
        for item in comment_data:
            pr = item['pr']
            comments = item['comments']
            comment_summaries = [f"  - {c.get('body', '')[:80]}..." for c in comments[:2]]
            comment_list.append(f"PR #{pr.number} ({pr.title}):\\n" + "\\n".join(comment_summaries))
        
        comments_text = "\\n\\n".join(comment_list)
        
        return f"""
# Workday Mode: Conservative Comment Responses

{len(comment_data)} of your PRs have comments that appear to be questions or need responses.

IMPORTANT: This is workday mode - provide conservative, professional responses only. 
Do not make code changes or detailed technical discussions.

## PRs with Comments Needing Responses:
{comments_text}

## Response Guidelines:
For each comment, draft a professional response that:

1. **Acknowledges the Comment**:
   - Thank the reviewer for their feedback
   - Show that you understand their concern

2. **Provides Clarification (if simple)**:
   - Answer straightforward questions
   - Clarify intent or reasoning
   - Point to relevant documentation

3. **Defers Complex Discussions**:
   - For technical implementation details, suggest discussing during worknight
   - For architectural questions, suggest a separate meeting
   - For complex changes, indicate when you'll address them

4. **Sets Expectations**:
   - When will you make requested changes?
   - When can they expect a more detailed response?
   - Should they expect code updates?

## Response Format:
```
### PR #{{number}} - Comment Response:
**To**: [Commenter name]
**Type**: [Acknowledgment/Clarification/Deferral/Schedule]
**Response**: [Draft response text]
**Follow-up Action**: [What you'll do and when]
```

Keep responses professional, brief, and focused on communication rather than code changes.
"""


class WorknightExecutor(BaseExecutor):
    """
    Active mode - code generation and implementation.
    Allows Claude Code to call gh commands directly for dynamic workflows.
    Uses task scheduling for prioritized work management.
    """
    
    def __init__(self, session_tracker):
        super().__init__(session_tracker)
        from task_scheduler import TaskScheduler
        self.task_scheduler = TaskScheduler()
    
    def execute(self, repos: List[RepoConfig]) -> Dict[str, Any]:
        """Execute worknight tasks for all repositories"""
        session_mode = self.get_session_mode()
        
        if session_mode == "session_expired":
            print("Skipping worknight execution - session expired")
            return {"status": "skipped", "reason": "session_expired"}
        
        self.log_session_status()
        
        results = {}
        
        # Adjust processing based on session mode
        if session_mode == "maximize_usage":
            print("Maximizing usage in final session window - processing all repos with enhanced tasks")
            active_repos = repos  # Process all repos
        else:
            # Normal worknight mode
            active_repos = repos
        
        # Process scheduled tasks first (highest priority)
        for repo in active_repos:
            try:
                repo_results = self._process_repo_worknight(repo)
                results[repo.name] = repo_results
            except Exception as e:
                print(f"Error processing repo {repo.name}: {e}")
                results[repo.name] = {"status": "error", "error": str(e)}
        
        return {"status": "completed", "results": results}
    
    def _process_repo_worknight(self, repo: RepoConfig) -> Dict[str, Any]:
        """Process a single repository in worknight mode"""
        github = GitHubIntegration(repo.path)
        
        # Get scheduled tasks for this repo
        scheduled_tasks = self.task_scheduler.get_tasks_for_mode("worknight", repo.name)
        
        # Gather GitHub data
        github_data = github.gather_workday_data()  # Reuse workday data gathering
        
        # Check for PRs from others requesting implementation
        implementation_requests = self._find_implementation_requests(github, github_data)
        
        # Check for branch rebasing needs
        rebase_needed = [b for b in github_data['branches'] if b.needs_rebase and not b.current]
        
        # Check my PRs for comment responses that need implementation
        my_pr_implementations = self._find_my_pr_implementations_needed(github, github_data)
        
        # Build comprehensive worknight prompt
        prompt = self._build_worknight_prompt(
            repo, 
            scheduled_tasks, 
            implementation_requests,
            rebase_needed,
            my_pr_implementations,
            github_data
        )
        
        return {
            "status": "ready",
            "prompt": prompt,
            "mode": "worknight",
            "scheduled_tasks": [t.id for t in scheduled_tasks],
            "github_data": github_data
        }
    
    def _find_implementation_requests(self, github: GitHubIntegration, github_data: Dict) -> List[Dict]:
        """Find PRs from others that request implementation work from me"""
        implementation_requests = []
        
        try:
            # Look for PRs where I'm mentioned or assigned for implementation
            mentioned_prs_output = github._run_gh_command([
                'search', 'prs',
                '--involves=@me',
                '--state=open',
                '--json=number,title,url,author,body,updatedAt'
            ])
            
            if mentioned_prs_output:
                mentioned_prs = json.loads(mentioned_prs_output)
                
                for pr in mentioned_prs:
                    # Skip my own PRs
                    if pr['author']['login'] == '@me':
                        continue
                    
                    # Look for implementation keywords in body or comments
                    implementation_keywords = [
                        'please implement', 'can you implement', 'need implementation',
                        'could you add', 'please add', 'implement this',
                        '@me implement', 'assigned to implement'
                    ]
                    
                    pr_text = (pr.get('body', '') + ' ' + pr.get('title', '')).lower()
                    
                    if any(keyword in pr_text for keyword in implementation_keywords):
                        # Get comments to see if there are specific implementation requests
                        comments = github.get_pr_comments(pr['number'])
                        
                        implementation_requests.append({
                            'pr': pr,
                            'comments': comments,
                            'implementation_type': 'requested_feature'
                        })
        
        except Exception as e:
            print(f"Error finding implementation requests: {e}")
        
        return implementation_requests
    
    def _find_my_pr_implementations_needed(self, github: GitHubIntegration, github_data: Dict) -> List[Dict]:
        """Find my PRs that have review comments requesting implementation changes"""
        implementations_needed = []
        
        for pr in github_data['my_prs']:
            try:
                comments = github.get_pr_comments(pr.number)
                review_comments = github.get_pr_review_comments(pr.number)
                all_comments = comments + review_comments
                
                # Look for implementation-requesting comments
                implementation_comments = []
                implementation_keywords = [
                    'please change', 'needs to be', 'should implement', 'add this',
                    'fix this', 'update this', 'modify this', 'implement',
                    'requested changes', 'needs implementation'
                ]
                
                for comment in all_comments:
                    comment_body = comment.get('body', '').lower()
                    if any(keyword in comment_body for keyword in implementation_keywords):
                        implementation_comments.append(comment)
                
                if implementation_comments:
                    implementations_needed.append({
                        'pr': pr,
                        'implementation_comments': implementation_comments
                    })
                    
            except Exception as e:
                print(f"Error checking PR #{pr.number} for implementation needs: {e}")
        
        return implementations_needed
    
    def _build_worknight_prompt(self, 
                                repo: RepoConfig,
                                scheduled_tasks: List,
                                implementation_requests: List[Dict],
                                rebase_needed: List,
                                my_pr_implementations: List[Dict],
                                github_data: Dict) -> str:
        """Build comprehensive worknight mode prompt"""
        
        sections = []
        
        # Header
        sections.append(f"""# Worknight Mode: Active Development Session

You are working on {repo.name} (priority: {repo.priority}) located at {repo.path}.
This is an active development session where you can make code changes, run commands, and implement features.

You have full access to:
- All git commands for branch management
- `gh` CLI for GitHub operations  
- Development tools in the repository
- Ability to run tests, linters, and build processes""")

        # Scheduled Tasks (Highest Priority)
        if scheduled_tasks:
            task_list = []
            for task in scheduled_tasks[:5]:  # Limit to top 5 tasks
                task_list.append(f"  - [{task.priority.value.upper()}] {task.title}")
                task_list.append(f"    {task.description}")
                if task.metadata:
                    task_list.append(f"    Metadata: {task.metadata}")
            
            sections.append(f"""## 🎯 Scheduled Tasks (PRIORITY)

You have {len(scheduled_tasks)} scheduled tasks for this repository. Work on these first:

{chr(10).join(task_list[:10])}  # Limit display

When you complete a task, make sure to update its status in the task scheduler.""")

        # Implementation Requests from Others
        if implementation_requests:
            impl_list = []
            for req in implementation_requests[:3]:  # Limit to 3
                pr = req['pr']
                impl_list.append(f"  - PR #{pr['number']}: {pr['title']} by {pr['author']['login']}")
                impl_list.append(f"    URL: {pr['url']}")
            
            sections.append(f"""## 🤝 Implementation Requests from Others

{len(implementation_requests)} PRs from other developers request your implementation work:

{chr(10).join(impl_list)}

For each PR:
1. Review the request details
2. Understand what needs to be implemented  
3. Implement the requested functionality
4. Test thoroughly
5. Comment on the PR with your progress""")

        # My PR Implementation Work  
        if my_pr_implementations:
            my_impl_list = []
            for impl in my_pr_implementations[:3]:  # Limit to 3
                pr = impl['pr']
                comment_count = len(impl['implementation_comments'])
                my_impl_list.append(f"  - PR #{pr.number}: {pr.title}")
                my_impl_list.append(f"    {comment_count} implementation comments to address")
                my_impl_list.append(f"    URL: {pr.url}")
            
            sections.append(f"""## 🔧 My PRs Needing Implementation

{len(my_pr_implementations)} of your PRs have review comments requesting implementation changes:

{chr(10).join(my_impl_list)}

For each PR:
1. Read all review comments carefully
2. Implement the requested changes
3. Run tests after each change
4. Respond to reviewers with updates
5. Push changes and update PR description if needed""")

        # Branch Management
        if rebase_needed:
            branch_list = [f"  - {b.name}: {b.behind_count} commits behind main" 
                          for b in rebase_needed[:5]]
            
            sections.append(f"""## 🌿 Branch Management

{len(rebase_needed)} branches need rebasing from main:

{chr(10).join(branch_list)}

For each branch:
1. Switch to the branch: `git checkout branch_name`
2. Rebase from main: `git rebase main`  
3. Resolve any conflicts if they occur
4. Force push if needed: `git push --force-with-lease`
5. Verify CI passes after rebase""")

        # Standard Worknight Tasks
        sections.append(f"""## 🔄 Standard Development Tasks

1. **Repository Health Check**:
   - Run `git status` to check current state
   - Review any uncommitted changes
   - Ensure main branch is up to date

2. **Code Quality Tasks**:
   - Run linting tools and fix issues
   - Update dependencies if needed  
   - Ensure all tests pass
   - Update documentation if needed

3. **Issue Work**:
   - Check assigned issues: `gh issue list --assignee=@me`
   - Work on high-priority issues based on previous planning
   - Create PRs for completed issue work

## 🎯 Work Guidelines

- **Work Systematically**: Complete higher priority tasks first
- **Atomic Commits**: Make small, focused commits with clear messages
- **Test Frequently**: Run tests before committing changes
- **Document Progress**: Add comments explaining non-obvious code
- **Follow Patterns**: Use existing code style and architectural patterns

## 📊 Repository Info

- **Priority**: {repo.priority}
- **Watch Branches**: {', '.join(repo.watch_branches)}
- **Pending Reviews**: {len(github_data.get('pending_reviews', []))}
- **My Open PRs**: {len(github_data.get('my_prs', []))}
- **Assigned Issues**: {len(github_data.get('assigned_issues', []))}

Start with the highest priority tasks and work your way down. Report your progress as you complete each section.""")

        return "\n\n".join(sections)


class WeekendExecutor(BaseExecutor):
    """
    Comprehensive development mode - documentation, security, dependencies, and maintenance.
    Active mode for strategic improvements and technical debt reduction.
    """
    
    def __init__(self, session_tracker):
        super().__init__(session_tracker)
        from task_scheduler import TaskScheduler
        self.task_scheduler = TaskScheduler()
    
    def execute(self, repos: List[RepoConfig]) -> Dict[str, Any]:
        """Execute weekend comprehensive development for all repositories"""
        if self.should_skip_due_to_session():
            print("Skipping weekend execution - session expired")
            return {"status": "skipped", "reason": "session_expired"}
        
        self.log_session_status()
        
        results = {}
        
        # Weekend mode processes all repos, but focuses on high-priority first
        prioritized_repos = sorted(repos, key=lambda r: {"high": 0, "medium": 1, "low": 2}.get(r.priority, 3))
        
        for repo in prioritized_repos:
            try:
                repo_results = self._process_repo_weekend(repo)
                results[repo.name] = repo_results
            except Exception as e:
                print(f"Error processing repo {repo.name}: {e}")
                results[repo.name] = {"status": "error", "error": str(e)}
        
        return {"status": "completed", "results": results}
    
    def _process_repo_weekend(self, repo: RepoConfig) -> Dict[str, Any]:
        """Process a single repository in weekend mode"""
        github = GitHubIntegration(repo.path)
        
        # Get scheduled weekend tasks for this repo
        scheduled_tasks = self.task_scheduler.get_tasks_for_mode("weekend", repo.name)
        
        # Gather comprehensive data for weekend work
        weekend_data = github.gather_weekend_data()
        
        # Analyze what weekend work needs to be done
        weekend_work = self._analyze_weekend_work_needed(github, weekend_data, repo)
        
        # Build comprehensive weekend prompt based on findings
        prompt = self._build_weekend_prompt(repo, scheduled_tasks, weekend_work, weekend_data)
        
        return {
            "status": "ready",
            "prompt": prompt,
            "mode": "weekend",
            "scheduled_tasks": [t.id for t in scheduled_tasks],
            "weekend_work": weekend_work,
            "weekend_data": weekend_data
        }
    
    def _analyze_weekend_work_needed(self, github: GitHubIntegration, weekend_data: Dict, repo: RepoConfig) -> Dict[str, Any]:
        """Analyze what weekend work is needed for this repository"""
        work_needed = {
            "documentation_updates": [],
            "security_improvements": [],
            "dependency_updates": [],
            "test_coverage_gaps": [],
            "performance_issues": [],
            "compliance_reports": []
        }
        
        # 1. Documentation Analysis
        security_files = weekend_data.get('security_files', {})
        if 'CLAUDE.md' in security_files:
            # Check if CLAUDE.md needs updates based on recent changes
            work_needed["documentation_updates"].append({
                "type": "claude_md_update",
                "priority": "medium",
                "description": "Update CLAUDE.md with recent project changes"
            })
        
        if 'Architecture.md' in security_files:
            work_needed["documentation_updates"].append({
                "type": "architecture_md_update", 
                "priority": "medium",
                "description": "Update Architecture.md with current system design"
            })
        
        # 2. Security Analysis
        vulnerabilities = weekend_data.get('vulnerabilities', {})
        if vulnerabilities.get('total_issues', 0) > 0:
            work_needed["security_improvements"].append({
                "type": "vulnerability_fixes",
                "priority": "high",
                "count": vulnerabilities['total_issues'],
                "description": f"Fix {vulnerabilities['total_issues']} security vulnerabilities"
            })
        
        # Check for common security improvements needed
        work_needed["security_improvements"].append({
            "type": "security_audit",
            "priority": "medium", 
            "description": "Comprehensive security audit and improvements"
        })
        
        # 3. Dependency Analysis
        dependency_files = weekend_data.get('dependency_files', {})
        if dependency_files:
            work_needed["dependency_updates"].append({
                "type": "dependency_updates",
                "priority": "medium",
                "files": list(dependency_files.keys()),
                "description": f"Update dependencies in {len(dependency_files)} files"
            })
        
        # Check for major framework upgrades
        framework_upgrades = self._identify_framework_upgrades(dependency_files)
        if framework_upgrades:
            work_needed["dependency_updates"].extend(framework_upgrades)
        
        # 4. Test Coverage Analysis
        work_needed["test_coverage_gaps"].append({
            "type": "test_coverage_improvement",
            "priority": "medium",
            "description": "Analyze and improve test coverage"
        })
        
        # 5. Performance Analysis
        work_needed["performance_issues"].append({
            "type": "performance_optimization",
            "priority": "low",
            "description": "Analyze and optimize application performance"
        })
        
        # 6. Compliance Reporting
        work_needed["compliance_reports"].append({
            "type": "status_reporting",
            "priority": "low",
            "description": "Generate compliance and status reports"
        })
        
        return work_needed
    
    def _identify_framework_upgrades(self, dependency_files: Dict) -> List[Dict]:
        """Identify potential major framework upgrades"""
        upgrades = []
        
        # Check for common frameworks that might need major upgrades
        if 'package.json' in dependency_files:
            upgrades.append({
                "type": "nodejs_framework_upgrade",
                "priority": "low",
                "framework": "Node.js/Angular/React",
                "description": "Check for major Node.js framework upgrades"
            })
        
        if 'pom.xml' in dependency_files:
            upgrades.append({
                "type": "java_framework_upgrade", 
                "priority": "low",
                "framework": "SpringBoot/Java",
                "description": "Check for major Java/SpringBoot upgrades"
            })
        
        if 'requirements.txt' in dependency_files or 'pyproject.toml' in dependency_files:
            upgrades.append({
                "type": "python_framework_upgrade",
                "priority": "low", 
                "framework": "Django/Flask/Python",
                "description": "Check for major Python framework upgrades"
            })
        
        return upgrades
    
    def _build_weekend_prompt(self, repo: RepoConfig, scheduled_tasks: List, weekend_work: Dict, weekend_data: Dict) -> str:
        """Build comprehensive weekend mode prompt"""
        from templates.weekend_prompts import (
            documentation_update_prompt,
            dependency_security_prompt,
            test_coverage_prompt,
            security_audit_prompt,
            performance_optimization_prompt,
            compliance_reporting_prompt
        )
        
        sections = []
        
        # Header
        sections.append(f"""# Weekend Mode: Comprehensive Development & Maintenance

You are working on {repo.name} (priority: {repo.priority}) located at {repo.path}.
This is weekend mode - focused on strategic improvements, documentation, security, and technical debt reduction.

You have full access to:
- All git commands and GitHub operations
- File creation and modification via GitHub API
- Ability to create PRs for all changes
- Development tools and testing frameworks
- Security scanning and analysis tools

## Weekend Mode Objectives:
- 📚 Documentation updates and maintenance
- 🔐 Security improvements and vulnerability fixes  
- 📦 Dependency updates and framework upgrades
- 🧪 Test coverage improvements
- ⚡ Performance optimizations
- 📊 Compliance reporting and analysis""")

        # Scheduled Tasks (if any)
        if scheduled_tasks:
            task_list = []
            for task in scheduled_tasks[:3]:  # Limit to top 3 for weekend
                task_list.append(f"  - [{task.priority.value.upper()}] {task.title}")
                task_list.append(f"    {task.description}")
            
            sections.append(f"""## 🎯 Scheduled Weekend Tasks

You have {len(scheduled_tasks)} scheduled weekend tasks:

{chr(10).join(task_list)}""")

        # Documentation Updates
        doc_work = weekend_work.get("documentation_updates", [])
        if doc_work:
            files_to_update = {}
            for work in doc_work:
                if work["type"] == "claude_md_update":
                    files_to_update["CLAUDE.md"] = "Project instructions and development guidance"
                elif work["type"] == "architecture_md_update":
                    files_to_update["Architecture.md"] = "System architecture and design documentation"
            
            if files_to_update:
                sections.append(documentation_update_prompt(repo.name, repo.path, files_to_update))

        # Security Improvements
        security_work = weekend_work.get("security_improvements", [])
        if security_work:
            sections.append(security_audit_prompt(
                repo.name, 
                repo.path, 
                weekend_data.get('security_files', {})
            ))

        # Dependency Updates
        dependency_work = weekend_work.get("dependency_updates", [])
        if dependency_work:
            sections.append(dependency_security_prompt(
                repo.name,
                repo.path,
                weekend_data.get('vulnerabilities', {}),
                weekend_data.get('dependency_files', {})
            ))

        # Test Coverage Improvements
        test_work = weekend_work.get("test_coverage_gaps", [])
        if test_work:
            sections.append(test_coverage_prompt(
                repo.name,
                repo.path,
                {"summary": "Weekend test coverage analysis needed"}
            ))

        # Performance Optimizations
        perf_work = weekend_work.get("performance_issues", [])
        if perf_work:
            sections.append(performance_optimization_prompt(
                repo.name,
                repo.path,
                {"issues": "Weekend performance analysis needed"}
            ))

        # Compliance Reporting
        compliance_work = weekend_work.get("compliance_reports", [])
        if compliance_work:
            sections.append(compliance_reporting_prompt(
                repo.name,
                repo.path,
                ["Security Report", "Performance Report", "Test Coverage Report", "Dependency Report"]
            ))

        # General Weekend Guidelines
        sections.append(f"""## 🔄 Weekend Work Guidelines

### Priority Order:
1. **Security Issues** (Critical/High priority vulnerabilities)
2. **Documentation Updates** (Keep project knowledge current)
3. **Dependency Security Updates** (Patch vulnerabilities)
4. **Test Coverage** (Improve code quality)
5. **Performance Optimizations** (When time permits)
6. **Compliance Reporting** (Status visibility)

### Implementation Approach:
- **Create Separate PRs** for different types of work
- **Document Everything** - explain changes thoroughly
- **Test Thoroughly** - weekend changes should be stable
- **Focus on Value** - prioritize high-impact improvements

### PR Strategy:
- Security fixes: Immediate PR for critical issues
- Documentation: Single PR for all doc updates
- Dependencies: Separate PRs for security vs. feature updates
- Tests: Can be combined with related feature work
- Performance: Separate PR with benchmarks

## 📊 Repository Status:
- **Dependency Files**: {len(weekend_data.get('dependency_files', {}))}
- **Security Files**: {len(weekend_data.get('security_files', {}))}
- **Security Issues**: {weekend_data.get('vulnerabilities', {}).get('total_issues', 0)}
- **Open PRs**: {len(weekend_data.get('my_prs', []))}

Work systematically through each area. Weekend mode is about strategic improvements and reducing technical debt. 
Take time to do things properly and create lasting value for the project.""")

        return "\n\n".join(sections)


def get_executor(mode: str, session_tracker: SessionTracker) -> BaseExecutor:
    """Factory function to get the appropriate executor for a work mode"""
    executors = {
        "workday": WorkdayExecutor,
        "worknight": WorknightExecutor,
        "weekend": WeekendExecutor
    }
    
    executor_class = executors.get(mode)
    if not executor_class:
        raise ValueError(f"Unknown work mode: {mode}")
    
    return executor_class(session_tracker)


