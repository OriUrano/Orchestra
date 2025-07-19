"""
Pre-built prompt templates for workday mode (conservative, planning-focused).
"""

def review_response_prompt(prs: list) -> str:
    """Generate prompt for PR review responses"""
    pr_list = "\n".join([
        f"- PR #{pr.number}: {pr.title} by {pr.author}"
        for pr in prs
    ])
    
    return f"""# Engineering Manager: PR Review Planning

You are reviewing {len(prs)} pull requests as an engineering manager. 
For each PR, provide structured feedback focusing on:

## Review Guidelines:
1. **Architectural concerns** - Does this fit our system design?
2. **Business impact** - Does this solve the right problem?
3. **Risk assessment** - What could go wrong?
4. **Testing strategy** - What testing is needed?
5. **Questions for author** - What needs clarification?

## PRs to Review:
{pr_list}

## Response Format:
For each PR, provide:
```
### PR #{number}: {title}
**Approach Assessment**: [High-level feedback on the solution approach]
**Questions**: [Specific questions for the author]
**Testing Recommendations**: [What testing should be added/verified]
**Risk Level**: [Low/Medium/High with reasoning]
**Recommendation**: [Approve/Request Changes/Needs Discussion]
```

IMPORTANT: Focus on planning and strategy. Do not write code or detailed technical implementation.
"""


def pr_description_prompt(prs: list) -> str:
    """Generate prompt for updating PR descriptions"""
    pr_list = "\n".join([
        f"- PR #{pr.number}: {pr.title} (URL: {pr.url})"
        for pr in prs
    ])
    
    return f"""# Engineering Manager: PR Description Updates

{len(prs)} of your PRs have empty descriptions. Based on the titles and any available context,
draft comprehensive PR descriptions that will help reviewers understand the changes.

## PRs Needing Descriptions:
{pr_list}

## Description Template:
For each PR, provide a description following this structure:

```
## What
Brief summary of what this PR does

## Why
Explanation of why this change is needed

## How
High-level approach taken

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests verified
- [ ] Manual testing completed

## Deployment Notes
Any special considerations for deployment

## Breaking Changes
List any breaking changes (or "None")
```

Provide a complete description for each PR that reviewers can use to understand the context and impact.
"""


def issue_analysis_prompt(issues: list) -> str:
    """Generate prompt for issue analysis and planning"""
    issue_list = "\n".join([
        f"- Issue #{issue.number}: {issue.title} by {issue.author}"
        for issue in issues
    ])
    
    return f"""# Engineering Manager: Issue Analysis & Planning

You have {len(issues)} assigned issues requiring analysis and planning.
Provide structured analysis for each issue to guide implementation.

## Issues to Analyze:
{issue_list}

## Analysis Format:
For each issue, provide:

```
### Issue #{number}: {title}

**Problem Analysis**:
- Root cause assessment
- Impact on users/system
- Priority justification

**Solution Approach**:
- High-level implementation strategy
- Alternative approaches considered
- Technical dependencies

**Effort Estimation**:
- Complexity: [Low/Medium/High]
- Estimated time: [hours/days]
- Required expertise: [frontend/backend/fullstack/etc]

**Implementation Plan**:
1. Step 1: [First action]
2. Step 2: [Second action]
3. Step 3: [etc]

**Questions/Blockers**:
- What additional information is needed?
- Are there any dependencies or blockers?

**Success Criteria**:
- How will we know this is complete?
- What metrics should we track?
```

IMPORTANT: Provide planning and analysis only. Do not implement solutions or write code.
"""


def branch_status_prompt(repo_name: str, branches: list) -> str:
    """Generate prompt for branch status review"""
    return f"""# Engineering Manager: Branch Status Review

Review the status of development branches in {repo_name} and provide recommendations
for branch management and cleanup.

## Current Branches:
{chr(10).join([f"- {branch}" for branch in branches])}

## Review Tasks:
1. **Branch Health Assessment**:
   - Which branches are actively being worked on?
   - Which branches are stale and can be cleaned up?
   - Are there any branches that need to be merged urgently?

2. **Merge Strategy Review**:
   - Identify branches ready for main
   - Highlight any potential merge conflicts
   - Recommend merge order if dependencies exist

3. **Team Communication**:
   - Which branch owners need to be contacted?
   - What status updates are needed?

## Response Format:
```
### Active Branches
- [List branches currently in development]

### Ready to Merge
- [List branches ready for main]

### Stale Branches (Cleanup Candidates)
- [List old/abandoned branches]

### Action Items
1. [Priority actions needed]
2. [Team communications required]
3. [Cleanup tasks]
```

Focus on management decisions and team coordination, not technical implementation.
"""


def team_update_prompt(repo_data: dict) -> str:
    """Generate prompt for team status updates"""
    return f"""# Engineering Manager: Team Status Update

Based on the current repository status, draft a status update for the team
highlighting progress, blockers, and next steps.

## Repository Data:
- Pending Reviews: {len(repo_data.get('pending_reviews', []))}
- Open PRs: {len(repo_data.get('my_prs', []))}
- Assigned Issues: {len(repo_data.get('assigned_issues', []))}

## Update Format:
```
### Weekly Engineering Update

**Progress This Week**:
- [Key accomplishments]
- [PRs merged]
- [Issues resolved]

**Current Focus**:
- [Active development areas]
- [Key PRs in review]

**Blockers & Risks**:
- [Items needing attention]
- [Potential delays]

**Next Week Priorities**:
1. [Top priority item]
2. [Second priority]
3. [Third priority]

**Team Needs**:
- [Review requests]
- [Help needed]
- [Resource requirements]
```

Create a professional update that keeps stakeholders informed about engineering progress.
"""