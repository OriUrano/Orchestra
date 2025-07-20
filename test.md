# Orchestra Manual Testing Guide

This guide provides comprehensive instructions for manually testing all features of Orchestra to ensure each component works as intended.

## Prerequisites

1. **Install Orchestra**: Run `./install.sh` 
2. **GitHub CLI**: Ensure `gh` is installed and authenticated
3. **Test Repository**: Create or use an existing GitHub repository for testing
4. **Configuration**: Set up `config/repos.yaml` with your test repository

## Test Repository Setup

Create a test repository with the following structure for comprehensive testing:

```bash
# Create test repo and initial setup
gh repo create orchestra-test --private
git clone https://github.com/YOUR_USERNAME/orchestra-test
cd orchestra-test

# Create test files
echo "# Test Project" > README.md
echo "console.log('hello');" > app.js
echo '{"name": "test", "version": "1.0.0"}' > package.json
git add . && git commit -m "Initial setup"
git push origin main

# Create test branches
git checkout -b feature/test-feature
echo "// New feature" >> app.js
git add . && git commit -m "Add test feature"
git push origin feature/test-feature

git checkout -b fix/security-update
echo "// Security fix" >> app.js  
git add . && git commit -m "Security update"
git push origin fix/security-update
```

Add your test repository to `config/repos.yaml`:
```yaml
repositories:
  - path: "YOUR_USERNAME/orchestra-test"
    priority: "high"
    watched_branches: ["main", "feature/*", "fix/*"]
```

## Test Scenarios by Mode

### 1. Time-Based Mode Detection Tests

#### Test Current Mode Detection
```bash
python3 utils/time_utils.py
```
**Expected Output**: Current mode (`workday`, `worknight`, `weekend`, or `off`)

#### Test Mode Transitions
1. **Workday to Worknight** (Weekday 6:00 PM):
   - Run at 5:59 PM: Should show `workday`
   - Run at 6:01 PM: Should show `worknight`

2. **Worknight to Off** (Weekday 4:00 AM):
   - Run at 3:59 AM: Should show `worknight`
   - Run at 4:01 AM: Should show `off`

3. **Friday to Weekend** (Friday 6:00 PM):
   - Run at 5:59 PM Friday: Should show `workday`
   - Run at 6:01 PM Friday: Should show `weekend`

4. **Weekend to Workday** (Monday 8:00 AM):
   - Run at 7:59 AM Monday: Should show `weekend`
   - Run at 8:01 AM Monday: Should show `workday`

### 2. Session Management Tests

#### Test Session Detection
```bash
python3 usage_tracker.py
```

**Setup for Session Tests**:
1. **No Session**: Remove all `~/.claude/projects/Orchestra/*.jsonl` files
2. **Fresh Session**: Create recent JSONL entry (within 5 hours)
3. **Expired Session**: Create JSONL entry older than 5 hours
4. **Final Window**: Create JSONL entry exactly 4 hours 45 minutes ago

**Expected Outputs**:
- `no_session`: "No active session detected"
- `normal`: "Active session with X hours remaining"
- `session_expired`: "Session expired"
- `maximize_usage`: "Final 15 minutes - maximizing usage"

### 3. Workday Mode Testing

#### Setup Test Scenarios

**Scenario 1: PR Needs Review**
```bash
# Create PR requesting your review
gh pr create --title "Feature: Add new functionality" --body "Please review this PR" --base main --head feature/test-feature
gh pr review [PR_NUMBER] --request-changes --body "Needs work"
```

**Scenario 2: Empty PR Description**
```bash
# Create PR with empty description from your account
gh pr create --title "Fix: Security update" --body "" --base main --head fix/security-update
```

**Scenario 3: Assigned Issue**
```bash
# Create and assign issue to yourself
gh issue create --title "Bug: Application crashes" --body "Detailed bug description" --assignee @me
```

**Scenario 4: Stale Branch**
```bash
# Make main ahead of feature branch
git checkout main
echo "// Main update" >> app.js
git add . && git commit -m "Update main branch"
git push origin main
```

**Scenario 5: Comments Needing Response**
```bash
# Add comment to your PR asking a question
gh pr comment [PR_NUMBER] --body "Could you explain the implementation approach?"
```

#### Run Workday Test
```bash
# Set time to workday hours (8am-6pm, Mon-Fri)
python3 orchestra.py --test-mode --run-once
```

**Expected Workday Behavior**:
- ✅ Processes maximum 3 repositories
- ✅ Pre-fetches all GitHub data first
- ✅ Generates planning prompts only (no code changes)
- ✅ Creates structured responses for:
  - PR review recommendations
  - PR description suggestions
  - Issue analysis and effort estimates
  - Branch management recommendations
  - Comment response drafts
- ❌ No direct GitHub CLI commands during prompt execution
- ❌ No actual code commits or PR updates

### 4. Worknight Mode Testing

#### Setup Worknight Scenarios

**Scenario 1: Scheduled Task**
```bash
# Add high-priority task to scheduler
python3 -c "
from task_scheduler import TaskScheduler
scheduler = TaskScheduler()
scheduler.add_task(
    'pr_implementation',
    'Implement feature X',
    priority='HIGH',
    metadata={'pr_number': 123, 'repo': 'orchestra-test'}
)
"
```

**Scenario 2: Implementation Request**
```bash
# Create PR from another user requesting implementation
gh pr create --title "[REQUEST] Implement user authentication" --body "Please implement OAuth login" --label "implementation-request"
```

**Scenario 3: Review Comments to Address**
```bash
# Add review comments to your PR
gh pr review [YOUR_PR_NUMBER] --request-changes --body "Please add error handling and tests"
```

**Scenario 4: Branch Needs Rebasing**
```bash
# Branch is behind main (created in workday setup)
# This should be detected automatically
```

#### Run Worknight Test
```bash
# Set time to worknight hours (6pm-4am, Mon-Thu)
python3 orchestra.py --test-mode --run-once
```

**Expected Worknight Behavior**:
- ✅ Executes actual GitHub CLI commands
- ✅ Makes real code changes and commits
- ✅ Processes scheduled tasks by priority
- ✅ Addresses implementation requests
- ✅ Responds to review comments with code
- ✅ Rebases stale branches
- ✅ Creates and updates PRs
- ✅ Resolves assigned issues

### 5. Weekend Mode Testing

#### Setup Weekend Scenarios

**Scenario 1: Documentation Needs Updates**
```bash
# Create outdated CLAUDE.md
echo "# Old documentation" > CLAUDE.md
git add . && git commit -m "Add old documentation"
git push origin main
```

**Scenario 2: Security Vulnerabilities**
```bash
# Add vulnerable dependency
echo '{"dependencies": {"lodash": "3.0.0"}}' > package.json
git add . && git commit -m "Add vulnerable dependency"
git push origin main
```

**Scenario 3: Missing Tests**
```bash
# Add untested code
mkdir -p src
echo "function untested() { return 'no tests'; }" > src/untested.js
git add . && git commit -m "Add untested code"
git push origin main
```

**Scenario 4: Performance Issues**
```bash
# Add inefficient code
echo "for(let i=0; i<1000000; i++) { console.log(i); }" > slow.js
git add . && git commit -m "Add inefficient code"
git push origin main
```

#### Run Weekend Test
```bash
# Set time to weekend hours (Fri 6pm - Mon 8am)
python3 orchestra.py --test-mode --run-once
```

**Expected Weekend Behavior**:
- ✅ Processes all repositories by priority
- ✅ Comprehensive GitHub data gathering (including security)
- ✅ Creates documentation update PRs
- ✅ Fixes security vulnerabilities
- ✅ Updates dependencies
- ✅ Improves test coverage
- ✅ Optimizes performance issues
- ✅ Generates compliance reports

### 6. GitHub Integration Tests

#### Test Data Gathering
```bash
python3 github_integration.py
```

**Expected Operations**:
- ✅ List pull requests and issues
- ✅ Get branch information
- ✅ Read file contents
- ✅ Check for vulnerabilities
- ✅ Scan dependencies
- ✅ Handle API errors gracefully

#### Test GitHub CLI Operations
```bash
# Test each operation manually
gh pr list
gh issue list
gh repo view
gh api repos/:owner/:repo/vulnerability-alerts
```

### 7. Task Scheduler Tests

#### Test Task Management
```bash
python3 task_scheduler.py
```

**Test Operations**:
1. **Add Task**: Create task with different priorities
2. **Get Tasks**: Retrieve tasks filtered by mode
3. **Update Status**: Mark tasks as completed
4. **Dependencies**: Create task with dependencies
5. **Persistence**: Verify tasks survive restart

**Expected Behavior**:
- ✅ Tasks stored in JSON format
- ✅ Priority-based sorting
- ✅ Mode-specific filtering
- ✅ Dependency resolution
- ✅ Status tracking

### 8. Configuration Tests

#### Test Repository Configuration
```bash
# Test with different repo configs
cp config/repos.yaml config/repos.yaml.backup

# Test with invalid config
echo "invalid: yaml: content" > config/repos.yaml
python3 orchestra.py --run-once
# Should handle gracefully

# Test with missing repos
echo "repositories: []" > config/repos.yaml
python3 orchestra.py --run-once
# Should skip processing

# Restore config
mv config/repos.yaml.backup config/repos.yaml
```

#### Test Settings Configuration
```bash
# Test different session limits
python3 -c "
import yaml
with open('config/settings.yaml', 'r') as f:
    settings = yaml.safe_load(f)
settings['session_duration_hours'] = 1
with open('config/settings.yaml', 'w') as f:
    yaml.dump(settings, f)
"
```

### 9. Error Handling Tests

#### Test Network Issues
```bash
# Disable network and test
sudo ip route add blackhole 8.8.8.8
python3 orchestra.py --run-once
sudo ip route del blackhole 8.8.8.8
```

#### Test GitHub API Rate Limiting
```bash
# Make many rapid API calls
for i in {1..100}; do gh api rate_limit; done
python3 orchestra.py --run-once
```

#### Test Missing Files
```bash
# Test with missing config
mv config/repos.yaml config/repos.yaml.backup
python3 orchestra.py --run-once
mv config/repos.yaml.backup config/repos.yaml
```

### 10. End-to-End Integration Tests

#### Full Cycle Test (All Modes)
```bash
# Test complete cycle
for mode in workday worknight weekend; do
    echo "Testing $mode mode..."
    # Manually set time for mode testing
    python3 orchestra.py --run-once
    echo "Completed $mode test"
    sleep 5
done
```

#### Multi-Repository Test
```bash
# Add multiple repos to config
# Run and verify proper priority handling
python3 orchestra.py --run-once
```

## Verification Checklist

### ✅ Mode Detection
- [ ] Correct mode detected for current time
- [ ] Mode transitions work at boundaries
- [ ] Off-hours properly skip execution

### ✅ Session Management
- [ ] Session detection from JSONL files
- [ ] 5-hour session boundaries respected
- [ ] Final window maximizes usage
- [ ] Expired sessions handled correctly

### ✅ Workday Mode
- [ ] Conservative behavior (no code changes)
- [ ] Repository limit enforced (max 3)
- [ ] Planning prompts generated
- [ ] GitHub data pre-fetched
- [ ] Professional responses created

### ✅ Worknight Mode
- [ ] Active development enabled
- [ ] GitHub CLI commands executed
- [ ] Actual code changes made
- [ ] Scheduled tasks processed
- [ ] PRs created and updated

### ✅ Weekend Mode
- [ ] All repositories processed
- [ ] Comprehensive data gathered
- [ ] Maintenance tasks executed
- [ ] Documentation updated
- [ ] Security issues addressed

### ✅ GitHub Integration
- [ ] Data gathering works correctly
- [ ] GitHub operations succeed
- [ ] Error handling graceful
- [ ] Authentication maintained

### ✅ Task Scheduler
- [ ] Tasks persist correctly
- [ ] Priority ordering works
- [ ] Dependencies resolved
- [ ] Mode filtering accurate

### ✅ Configuration
- [ ] Repository config loaded
- [ ] Settings applied correctly
- [ ] Invalid config handled
- [ ] Missing files handled

### ✅ Error Handling
- [ ] Network issues handled
- [ ] API failures graceful
- [ ] Missing files handled
- [ ] Invalid data handled

## Troubleshooting

### Common Issues

1. **Mode Detection Wrong**
   - Check system timezone: `timedatectl`
   - Verify time logic in `utils/time_utils.py`

2. **No Session Detected**
   - Check JSONL files: `ls -la ~/.claude/projects/Orchestra/`
   - Verify file permissions and content

3. **GitHub CLI Errors**
   - Re-authenticate: `gh auth login`
   - Check repository access: `gh repo view`

4. **Configuration Errors**
   - Validate YAML syntax: `python3 -c "import yaml; yaml.safe_load(open('config/repos.yaml'))"`
   - Check file permissions

5. **Task Scheduler Issues**
   - Check task file: `cat tasks.json`
   - Verify JSON syntax

### Debug Commands

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python3 orchestra.py --run-once

# Test individual components
python3 -c "from utils.time_utils import get_work_mode; print(get_work_mode())"
python3 -c "from usage_tracker import get_session_state; print(get_session_state())"
python3 -c "from github_integration import GitHubIntegration; gi = GitHubIntegration(); print(gi.get_current_user())"

# Check logs
tail -f logs/orchestra.log
tail -f logs/orchestra.jsonl
```

This comprehensive testing guide ensures Orchestra operates correctly across all modes and scenarios. Run these tests after any code changes to verify functionality.