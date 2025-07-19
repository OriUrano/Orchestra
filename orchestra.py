#!/usr/bin/env python3
"""
Orchestra: Claude Code Engineering Manager Automation

Main orchestrator that runs hourly to manage engineering tasks across
different work modes (workday, worknight, weekend).
"""
import argparse
import json
import os
import sys
import time
import yaml
from datetime import datetime
from typing import List, Dict, Any

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from usage_tracker import UsageTracker
from utils.time_utils import get_work_mode, should_run_automation
from mode_executors import get_executor, RepoConfig
from claude_code_sdk import query as claude_code


class Orchestra:
    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), "config")
        self.repos = self._load_repo_config()
        self.settings = self._load_settings()
        self.usage_tracker = UsageTracker()
        
    def _load_repo_config(self) -> List[RepoConfig]:
        """Load repository configuration from repos.yaml"""
        repos_file = os.path.join(self.config_path, "repos.yaml")
        
        if not os.path.exists(repos_file):
            print(f"Warning: {repos_file} not found, using empty repo list")
            return []
        
        try:
            with open(repos_file, 'r') as f:
                config = yaml.safe_load(f)
            
            repos = []
            for repo_data in config.get('repositories', []):
                repos.append(RepoConfig(
                    name=repo_data['name'],
                    path=os.path.expanduser(repo_data['path']),
                    priority=repo_data.get('priority', 'medium'),
                    watch_branches=repo_data.get('watch_branches', ['main'])
                ))
            
            return repos
            
        except Exception as e:
            print(f"Error loading repo config: {e}")
            return []
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load system settings from settings.yaml"""
        settings_file = os.path.join(self.config_path, "settings.yaml")
        
        default_settings = {
            'max_daily_tokens': 800000,
            'max_daily_requests': 8000,
            'workday_max_repos': 3,
            'log_level': 'INFO',
            'claude_code_enabled': True
        }
        
        if not os.path.exists(settings_file):
            print(f"Warning: {settings_file} not found, using defaults")
            return default_settings
        
        try:
            with open(settings_file, 'r') as f:
                user_settings = yaml.safe_load(f)
            
            # Merge with defaults
            settings = default_settings.copy()
            settings.update(user_settings.get('settings', {}))
            
            return settings
            
        except Exception as e:
            print(f"Error loading settings: {e}")
            return default_settings
    
    def run_cycle(self) -> Dict[str, Any]:
        """Run a single orchestration cycle"""
        cycle_start = datetime.now()
        
        print(f"=== Orchestra Cycle Started at {cycle_start} ===")
        
        # Check if we should run automation at this time
        if not should_run_automation():
            return {
                "status": "skipped",
                "reason": "outside_work_hours",
                "timestamp": cycle_start.isoformat()
            }
        
        # Check usage limits
        usage_status = self.usage_tracker.check_limits(
            daily_token_limit=self.settings['max_daily_tokens'],
            daily_request_limit=self.settings['max_daily_requests']
        )
        
        if usage_status == "limit_reached":
            print("Usage limit reached, skipping cycle")
            return {
                "status": "skipped",
                "reason": "usage_limit_reached",
                "usage_summary": self.usage_tracker.get_usage_summary(),
                "timestamp": cycle_start.isoformat()
            }
        
        # Determine current work mode
        work_mode = get_work_mode()
        print(f"Work mode: {work_mode}")
        print(f"Usage status: {usage_status}")
        
        if work_mode == "off":
            return {
                "status": "skipped",
                "reason": "off_hours",
                "timestamp": cycle_start.isoformat()
            }
        
        # Get the appropriate executor
        try:
            executor = get_executor(work_mode, self.usage_tracker)
            
            # Execute tasks for the current mode
            execution_result = executor.execute(self.repos)
            
            # If workday mode and we have Claude Code enabled, process tasks
            if (work_mode == "workday" and 
                self.settings.get('claude_code_enabled', True) and
                execution_result.get('status') == 'completed'):
                
                claude_results = self._process_workday_with_claude(execution_result)
                execution_result['claude_results'] = claude_results
            
            # If worknight mode and we have Claude Code enabled, execute prompts
            elif (work_mode == "worknight" and 
                  self.settings.get('claude_code_enabled', True) and
                  execution_result.get('status') == 'completed'):
                
                claude_results = self._process_worknight_with_claude(execution_result)
                execution_result['claude_results'] = claude_results
            
            cycle_end = datetime.now()
            duration = (cycle_end - cycle_start).total_seconds()
            
            return {
                "status": "completed",
                "work_mode": work_mode,
                "usage_status": usage_status,
                "execution_result": execution_result,
                "duration_seconds": duration,
                "timestamp": cycle_start.isoformat()
            }
            
        except Exception as e:
            print(f"Error during execution: {e}")
            return {
                "status": "error",
                "error": str(e),
                "work_mode": work_mode,
                "timestamp": cycle_start.isoformat()
            }
    
    def _process_workday_with_claude(self, execution_result: Dict) -> Dict[str, Any]:
        """Process workday tasks with Claude Code"""
        claude_results = {}
        
        for repo_name, repo_result in execution_result.get('results', {}).items():
            if repo_result.get('status') != 'ready':
                continue
            
            print(f"Processing {repo_name} with Claude Code...")
            
            for task in repo_result.get('tasks', []):
                try:
                    # Find the repo config
                    repo_config = next((r for r in self.repos if r.name == repo_name), None)
                    if not repo_config:
                        continue
                    
                    # Send task to Claude Code
                    response = claude_code(
                        task['prompt'],
                        cwd=repo_config.path
                    )
                    
                    claude_results[f"{repo_name}_{task['type']}"] = {
                        "status": "completed",
                        "response": response,
                        "task_type": task['type']
                    }
                    
                    print(f"Completed {task['type']} for {repo_name}")
                    
                except Exception as e:
                    print(f"Error processing {task['type']} for {repo_name}: {e}")
                    claude_results[f"{repo_name}_{task['type']}"] = {
                        "status": "error",
                        "error": str(e),
                        "task_type": task['type']
                    }
        
        return claude_results
    
    def _process_worknight_with_claude(self, execution_result: Dict) -> Dict[str, Any]:
        """Process worknight tasks with Claude Code"""
        claude_results = {}
        
        for repo_name, repo_result in execution_result.get('results', {}).items():
            if repo_result.get('status') != 'ready':
                continue
            
            print(f"Processing {repo_name} in worknight mode...")
            
            try:
                # Find the repo config
                repo_config = next((r for r in self.repos if r.name == repo_name), None)
                if not repo_config:
                    continue
                
                # Send worknight prompt to Claude Code
                response = claude_code(
                    repo_result['prompt'],
                    cwd=repo_config.path
                )
                
                claude_results[repo_name] = {
                    "status": "completed",
                    "response": response,
                    "mode": "worknight"
                }
                
                print(f"Completed worknight tasks for {repo_name}")
                
            except Exception as e:
                print(f"Error processing worknight tasks for {repo_name}: {e}")
                claude_results[repo_name] = {
                    "status": "error",
                    "error": str(e),
                    "mode": "worknight"
                }
        
        return claude_results
    
    def run_daemon(self):
        """Run Orchestra in daemon mode (continuous operation)"""
        print("Starting Orchestra in daemon mode...")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                result = self.run_cycle()
                
                # Log result
                if result['status'] in ['completed', 'error']:
                    print(f"Cycle result: {result['status']}")
                    if result.get('usage_status'):
                        print(f"Usage status: {result['usage_status']}")
                
                # Wait for next hour
                next_run = datetime.now().replace(minute=0, second=0, microsecond=0)
                next_run = next_run.replace(hour=next_run.hour + 1)
                
                sleep_seconds = (next_run - datetime.now()).total_seconds()
                if sleep_seconds > 0:
                    print(f"Sleeping until {next_run} ({sleep_seconds:.0f} seconds)")
                    time.sleep(sleep_seconds)
                
        except KeyboardInterrupt:
            print("\\nOrchestra daemon stopped by user")
    
    def run_once(self):
        """Run Orchestra once and exit"""
        result = self.run_cycle()
        print(json.dumps(result, indent=2))
        return result


def main():
    parser = argparse.ArgumentParser(description="Orchestra: Claude Code Engineering Manager Automation")
    parser.add_argument('--config', '-c', help='Configuration directory path')
    parser.add_argument('--run-once', action='store_true', help='Run once and exit')
    parser.add_argument('--daemon', action='store_true', help='Run in daemon mode')
    parser.add_argument('--test-mode', action='store_true', help='Run in test mode (no Claude Code calls)')
    
    args = parser.parse_args()
    
    # Create Orchestra instance
    orchestra = Orchestra(config_path=args.config)
    
    # Disable Claude Code in test mode
    if args.test_mode:
        orchestra.settings['claude_code_enabled'] = False
        print("Running in test mode (Claude Code disabled)")
    
    # Run based on arguments
    if args.run_once:
        orchestra.run_once()
    elif args.daemon:
        orchestra.run_daemon()
    else:
        # Default behavior: run once
        orchestra.run_once()


if __name__ == "__main__":
    main()