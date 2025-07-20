# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Orchestra is a Claude Code engineering manager automation system that operates in three time-based modes:
- **Workday Mode (8am-6pm, Mon-Fri)**: Conservative planning and review responses
- **Worknight Mode (6pm-4am, Mon-Thu)**: Active development and implementation
- **Weekend Mode (Fri 6pm - Mon 8am)**: Monitoring high-priority repositories only

## Core Architecture

### Time-Based Mode System
The system's behavior is driven by `utils/time_utils.py` which determines the current work mode. Each mode has different execution strategies implemented in `mode_executors.py`:

- `WorkdayExecutor`: Pre-fetches GitHub data, generates planning prompts, minimal token usage
- `WorknightExecutor`: Allows direct GitHub CLI access, performs actual code changes
- `WeekendExecutor`: Monitors only high-priority repos for urgent issues

### Usage-Conscious Design
`usage_tracker.py` parses Claude Code JSONL files from `~/.claude/projects/` to track token consumption and prevent hitting usage limits. The system will skip execution when limits are approached.

### GitHub Integration Strategy
`github_integration.py` wraps the `gh` CLI tool. The integration follows a hybrid approach:
- **Workday**: Pre-fetch data via `gh` commands, pass structured data to Claude Code
- **Worknight**: Claude Code calls `gh` commands directly for dynamic workflows

## Development Commands

### Installation and Setup
```bash
# Install dependencies and set up cron job
./install.sh

# Install Python dependencies only
pip3 install -r requirements.txt
```

### Running Orchestra
```bash
# Test run without Claude Code calls
python3 orchestra.py --test-mode --run-once

# Single execution with Claude Code
python3 orchestra.py --run-once

# Continuous daemon mode
python3 orchestra.py --daemon

# Custom config directory
python3 orchestra.py --config /path/to/config --run-once
```

### Testing Individual Components
```bash
# Test usage tracking
python3 usage_tracker.py

# Test time/mode detection
python3 utils/time_utils.py

# Test GitHub integration
python3 github_integration.py

# Test logging system
python3 utils/logging_utils.py

# Test mode executors
python3 mode_executors.py
```

### Configuration
```bash
# Edit repository configuration
vim config/repos.yaml

# Edit system settings
vim config/settings.yaml

# View logs
tail -f logs/orchestra.log
tail -f logs/orchestra.jsonl
```

## Key Configuration Files

### Repository Configuration (`config/repos.yaml`)
Defines which repositories Orchestra manages, their priority levels, and watched branches.

### System Settings (`config/settings.yaml`)
Controls token limits, repo processing limits per mode, and feature toggles.

## Architecture Patterns

### Executor Pattern
Mode-specific behavior is implemented via executor classes inheriting from `BaseExecutor`. Each executor handles usage checking, GitHub data gathering, and Claude Code prompt generation differently.

### Template System
Pre-built prompts in `templates/` directory provide mode-specific prompt templates for common tasks like PR reviews, issue analysis, and feature implementation.

### Configuration-Driven Behavior
Repository selection, priority handling, and system limits are all configurable via YAML files, allowing the system to adapt to different engineering workflows.

### Defensive Usage Tracking
The system monitors its own Claude Code usage by parsing local JSONL files and self-regulates to avoid hitting API limits.

## Integration Points

### Claude Code SDK
Orchestra uses `claude_code_sdk` to make API calls, with prompts tailored to each work mode's objectives.

### GitHub CLI (`gh`)
All GitHub operations go through the `gh` CLI tool rather than direct API calls, leveraging existing authentication and avoiding token management.

### Daemon Operation
The system runs as a daemon process with built-in hourly scheduling and mode detection to determine if execution should proceed.

## Prompt Engineering Strategy

### Workday Prompts
Focus on high-level planning, analysis, and structured responses. Explicitly instruct against code generation to preserve token usage.

### Worknight Prompts
Enable full development workflows with code generation, testing, and repository operations.

### Context Management
Prompts include structured data from GitHub pre-fetching to provide rich context while minimizing token usage for data gathering.