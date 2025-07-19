"""
Pre-built prompt templates for worknight mode (active development and implementation).
"""

def implementation_prompt(repo_name: str, repo_path: str, priority: str) -> str:
    """Generate comprehensive worknight implementation prompt"""
    return f"""# Worknight Mode: Active Development Session

You are working on {repo_name} (priority: {priority}) located at {repo_path}.
This is an active development session where you can make code changes, run commands, and implement features.

## Primary Tasks:

### 1. Repository Health Check
- Run `git status` to check current state
- Review any uncommitted changes
- Check if main branch is up to date

### 2. Branch Management
- List all local branches: `git branch -a`
- For each feature branch:
  - Rebase from main: `git rebase main`
  - Resolve any merge conflicts
  - Push updates if needed

### 3. PR Implementation Work
- Check my open PRs: `gh pr list --author=@me`
- For each open PR:
  - Review any new comments since last check
  - Implement requested changes
  - Address review feedback with actual code
  - Update PR description if needed
  - Run tests and ensure CI passes

### 4. Issue Resolution
- Check assigned issues: `gh issue list --assignee=@me`
- For high-priority issues:
  - Implement solutions based on previous planning
  - Write tests for new functionality
  - Update documentation if needed

### 5. Code Quality Tasks
- Run linting tools and fix issues
- Update dependencies if needed
- Clean up old branches: `git branch -d <branch>`
- Ensure all tests pass

### 6. Documentation Updates
- Update README if there are new features
- Add inline code documentation
- Update API documentation if applicable

## Working Guidelines:
- Make atomic commits with clear messages
- Run tests before committing
- Push changes frequently to backup work
- Comment code that isn't immediately obvious
- Follow existing code style and patterns

## Tools Available:
- Full git access for branch management
- `gh` CLI for GitHub operations
- All development tools in the repository
- Ability to run tests, linters, and build processes

Work systematically through each task area. Report your progress as you complete each section.
Start with the repository health check and work through the list methodically.
"""


def feature_implementation_prompt(feature_description: str, repo_path: str) -> str:
    """Generate prompt for implementing a specific feature"""
    return f"""# Feature Implementation: {feature_description}

Implement the requested feature in the repository at {repo_path}.

## Feature Requirements:
{feature_description}

## Implementation Process:

### 1. Analysis & Planning
- Understand existing codebase structure
- Identify files that need modification
- Plan the implementation approach
- Consider edge cases and error handling

### 2. Implementation
- Create or modify necessary files
- Follow existing code patterns and style
- Add proper error handling
- Include logging where appropriate

### 3. Testing
- Write unit tests for new functionality
- Update integration tests if needed
- Run existing test suite to ensure no regressions
- Test edge cases and error conditions

### 4. Documentation
- Update inline code documentation
- Add README updates if user-facing
- Update API documentation if applicable

### 5. Code Review Preparation
- Review your own code for quality
- Ensure code follows project conventions
- Check for any TODO comments or incomplete work
- Verify all tests pass

## Quality Checklist:
- [ ] Code follows project style guide
- [ ] Tests cover new functionality
- [ ] Documentation is updated
- [ ] No console errors or warnings
- [ ] Edge cases are handled
- [ ] Error messages are user-friendly

Implement this feature completely and thoroughly. Take time to understand the existing codebase before making changes.
"""


def bug_fix_prompt(bug_description: str, repo_path: str) -> str:
    """Generate prompt for fixing a specific bug"""
    return f"""# Bug Fix: {bug_description}

Fix the reported bug in the repository at {repo_path}.

## Bug Report:
{bug_description}

## Bug Fix Process:

### 1. Investigation
- Reproduce the bug if possible
- Understand the root cause
- Identify all affected code paths
- Check if there are similar issues elsewhere

### 2. Solution Development
- Implement the minimal fix that addresses the root cause
- Avoid over-engineering the solution
- Consider backward compatibility
- Ensure the fix doesn't introduce new issues

### 3. Testing
- Write a test that reproduces the bug (should fail before fix)
- Verify the test passes after your fix
- Run full test suite to check for regressions
- Test related functionality to ensure no side effects

### 4. Validation
- Verify the original bug is completely resolved
- Check that all edge cases are covered
- Ensure performance isn't negatively impacted

## Fix Guidelines:
- Make minimal changes to fix the specific issue
- Add comments explaining why the fix is needed
- Include regression tests to prevent the bug from returning
- Update documentation if the bug was due to unclear behavior

Complete the bug fix thoroughly and ensure it's properly tested before considering it done.
"""


def review_response_prompt(pr_number: int, comments: list, repo_path: str) -> str:
    """Generate prompt for responding to PR review comments"""
    comments_text = "\n".join([
        f"- {comment.get('author', 'Unknown')}: {comment.get('body', '')}"
        for comment in comments
    ])
    
    return f"""# PR Review Response: #{pr_number}

Address the review comments on PR #{pr_number} in repository at {repo_path}.

## Review Comments to Address:
{comments_text}

## Response Process:

### 1. Comment Analysis
- Read and understand each review comment
- Identify which comments require code changes
- Determine which comments need clarification or discussion

### 2. Code Changes
- Implement requested changes systematically
- Follow the reviewer's suggestions when appropriate
- If you disagree with a suggestion, explain your reasoning in a comment

### 3. Testing
- Run tests after each change
- Add new tests if reviewers requested them
- Ensure all CI checks pass

### 4. Communication
- Respond to each comment appropriately:
  - "Fixed in [commit hash]" for implemented changes
  - Explanation for alternative approaches taken
  - Questions if clarification is needed

### 5. Final Review
- Review all your changes before pushing
- Ensure you've addressed every comment
- Update PR description if significant changes were made

## Response Guidelines:
- Be respectful and professional in all responses
- Explain your reasoning for implementation choices
- Ask for clarification if comments are unclear
- Thank reviewers for their time and feedback

Work through each comment systematically and implement the necessary changes. Push your updates when complete.
"""


def maintenance_prompt(repo_path: str) -> str:
    """Generate prompt for repository maintenance tasks"""
    return f"""# Repository Maintenance Session

Perform maintenance tasks on the repository at {repo_path} to keep it healthy and up-to-date.

## Maintenance Checklist:

### 1. Dependency Management
- Check for outdated dependencies
- Update dependencies that have security patches
- Test that updates don't break functionality
- Update lock files if needed

### 2. Code Quality
- Run linting tools and fix issues
- Remove unused imports and variables
- Update deprecated API usage
- Refactor code smells if any are obvious

### 3. Documentation
- Update README if it's outdated
- Fix broken links in documentation
- Update API documentation for any changes
- Check that examples in docs still work

### 4. Testing
- Run full test suite and fix any flaky tests
- Add tests for any untested code paths
- Update test data if needed
- Ensure test coverage is adequate

### 5. Branch Cleanup
- Delete merged feature branches
- Clean up old/stale branches
- Ensure main branch is clean and up-to-date

### 6. CI/CD Health
- Check that all CI jobs are passing
- Update CI configuration if needed
- Ensure deployment processes are working

### 7. Security
- Run security scans if available
- Update any security-related configurations
- Check for exposed secrets or credentials

## Maintenance Guidelines:
- Make incremental changes and test frequently
- Create separate commits for different types of changes
- Don't make breaking changes during maintenance
- Document any significant changes in commit messages

Work through this checklist systematically. Focus on items that will have the most positive impact on code quality and developer experience.
"""