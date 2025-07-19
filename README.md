# 🎼 Orchestra

**Claude Code Engineering Manager Automation**

Orchestra is an intelligent automation system that helps engineering managers handle routine tasks throughout the day and night using Claude Code. It adapts its behavior based on time of day and current usage limits.

## 🌟 Features

- **Time-aware automation**: Different behaviors for workday, worknight, and weekend
- **Usage-conscious**: Monitors Claude Code token usage to avoid hitting limits
- **GitHub integration**: Uses `gh` CLI for PR reviews, issue management, and repository operations
- **Repository management**: Configurable priority levels for different projects
- **Cron-based scheduling**: Simple hourly execution without system dependencies

## 🕐 Work Modes

### Workday Mode (8am-6pm, Mon-Fri)
*Conservative mode focused on planning and responses*
- Review PRs and provide high-level feedback
- Draft responses to review comments (planning only)
- Update empty PR descriptions
- Analyze assigned issues and create implementation plans
- Answer questions and provide clarifications

### Worknight Mode (6pm-4am, Mon-Thu)
*Active development mode for implementation*
- Implement features based on daytime planning
- Address PR review comments with actual code changes
- Rebase branches and resolve merge conflicts
- Run tests and fix failures
- Perform repository maintenance

### Weekend Mode (Fri 6pm - Mon 8am)
*Monitoring mode for high-priority repositories only*
- Monitor critical repositories for urgent issues
- Basic notification handling
- Minimal resource usage

## 📁 Project Structure

```
Orchestra/
├── orchestra.py              # Main orchestrator
├── usage_tracker.py          # Claude Code usage monitoring
├── github_integration.py     # GitHub API wrapper using gh CLI
├── mode_executors.py         # Mode-specific execution logic
├── config/
│   ├── repos.yaml           # Repository configuration
│   └── settings.yaml        # System settings
├── utils/
│   └── time_utils.py        # Time/mode detection utilities
├── templates/
│   ├── workday_prompts.py   # Pre-built prompts for planning
│   └── worknight_prompts.py # Pre-built prompts for implementation
├── install.sh               # Installation script
└── requirements.txt         # Python dependencies
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- [GitHub CLI (gh)](https://cli.github.com/) installed and authenticated
- Claude Code access

### Installation

1. **Clone and install**:
   ```bash
   git clone https://github.com/OriUrano/Orchestra.git
   cd Orchestra
   ./install.sh
   ```

2. **Configure repositories** in `config/repos.yaml`:
   ```yaml
   repositories:
     - name: "my-app"
       path: "~/projects/my-app"
       priority: "high"
       watch_branches: ["main", "develop"]
   ```

3. **Adjust settings** in `config/settings.yaml`:
   ```yaml
   settings:
     max_daily_tokens: 800000
     workday_max_repos: 3
     claude_code_enabled: true
   ```

### Manual Testing

```bash
# Test once without Claude Code calls
python3 orchestra.py --test-mode --run-once

# Run once with Claude Code
python3 orchestra.py --run-once

# Run in daemon mode (continuous)
python3 orchestra.py --daemon
```

## ⚙️ Configuration

### Repository Configuration (`config/repos.yaml`)

```yaml
repositories:
  - name: "backend-api"           # Repository identifier
    path: "~/projects/backend"    # Local path to repository
    priority: "high"              # high, medium, low
    watch_branches:               # Branches to monitor
      - "main"
      - "develop"
```

### System Settings (`config/settings.yaml`)

```yaml
settings:
  max_daily_tokens: 800000      # Claude Code token limit
  max_daily_requests: 8000      # Request limit
  workday_max_repos: 3          # Max repos in workday mode
  claude_code_enabled: true     # Enable/disable Claude Code
  log_level: "INFO"             # Logging level
```

## 📊 Usage Monitoring

Orchestra automatically tracks Claude Code usage by parsing JSONL files in `~/.claude/projects/`. It will:

- Skip execution when usage limits are reached
- Provide warnings when approaching limits
- Adjust behavior based on remaining quota

## 🤖 GitHub Integration

Uses GitHub CLI (`gh`) for all repository operations:

**Workday Mode** (pre-fetch data):
```bash
gh pr list --review-requested=@me
gh issue list --assignee=@me
gh pr view <number> --json=comments
```

**Worknight Mode** (direct Claude Code access):
- Claude Code can call `gh` commands directly
- Dynamic workflow based on repository state
- Full access to git operations

## 🔧 Customization

### Adding Custom Prompts

Create custom prompts in the `templates/` directory:

```python
# templates/custom_prompts.py
def my_custom_prompt(data):
    return f"Custom prompt for {data}"
```

### Extending Executors

Inherit from base executors to add custom functionality:

```python
# custom_executor.py
from mode_executors import WorkdayExecutor

class CustomWorkdayExecutor(WorkdayExecutor):
    def _process_repo_workday(self, repo):
        # Custom logic here
        return super()._process_repo_workday(repo)
```

## 🛠️ Troubleshooting

### Common Issues

1. **"gh command failed"**: Ensure GitHub CLI is installed and authenticated
   ```bash
   gh auth login
   gh auth status
   ```

2. **"Usage limit reached"**: Adjust limits in `settings.yaml` or wait for reset

3. **"Config not found"**: Ensure `config/repos.yaml` exists and is valid YAML

### Debug Mode

```bash
# Run with debug output
python3 orchestra.py --run-once --test-mode
```

### Logs

Check cron logs for automated runs:
```bash
grep CRON /var/log/syslog
```

## 🔒 Security Notes

- Orchestra reads Claude Code usage data from local JSONL files
- GitHub access uses your existing `gh` CLI authentication
- No secrets are stored in Orchestra configuration
- All file access is limited to configured repository paths

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📜 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Built for [Claude Code](https://claude.ai/code) automation
- Uses [GitHub CLI](https://cli.github.com/) for repository operations
- Inspired by engineering management best practices