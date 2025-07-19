"""
Claude Code usage tracking by parsing JSONL files.
"""
import json
import glob
import os
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class UsageMetrics:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    requests: int = 0
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens + self.cache_creation_tokens


class UsageTracker:
    def __init__(self, claude_dir: Optional[str] = None):
        self.claude_dir = claude_dir or os.path.expanduser("~/.claude")
        
    def get_current_usage(self, since: Optional[datetime] = None) -> UsageMetrics:
        """Parse JSONL files to calculate usage since given time (default: today)"""
        if since is None:
            since = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
        total_usage = UsageMetrics()
        
        # Find all JSONL files in projects directory
        projects_dir = os.path.join(self.claude_dir, "projects")
        if not os.path.exists(projects_dir):
            return total_usage
            
        jsonl_pattern = os.path.join(projects_dir, "*", "*.jsonl")
        jsonl_files = glob.glob(jsonl_pattern)
        
        for file_path in jsonl_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                            
                        try:
                            data = json.loads(line)
                            
                            # Parse timestamp
                            timestamp_str = data.get('timestamp', '')
                            if not timestamp_str:
                                continue
                                
                            # Handle ISO format with Z suffix
                            if timestamp_str.endswith('Z'):
                                timestamp_str = timestamp_str[:-1] + '+00:00'
                            
                            timestamp = datetime.fromisoformat(timestamp_str)
                            
                            # Only count usage since the specified time
                            if timestamp < since:
                                continue
                                
                            # Extract usage data from assistant messages
                            if (data.get('type') == 'assistant' and 
                                'message' in data and 
                                'usage' in data['message']):
                                
                                usage = data['message']['usage']
                                total_usage.input_tokens += usage.get('input_tokens', 0)
                                total_usage.output_tokens += usage.get('output_tokens', 0)
                                total_usage.cache_creation_tokens += usage.get('cache_creation_input_tokens', 0)
                                total_usage.cache_read_tokens += usage.get('cache_read_input_tokens', 0)
                                total_usage.requests += 1
                                
                        except (json.JSONDecodeError, ValueError, KeyError) as e:
                            # Skip malformed lines
                            continue
                            
            except (IOError, OSError) as e:
                # Skip files we can't read
                continue
                
        return total_usage
    
    def check_limits(self, daily_token_limit: int = 800000, daily_request_limit: int = 8000) -> str:
        """
        Check current usage against limits.
        Returns: 'normal', 'approaching_limit', 'limit_reached'
        """
        usage = self.get_current_usage()
        
        token_usage_percent = (usage.total_tokens / daily_token_limit) * 100
        request_usage_percent = (usage.requests / daily_request_limit) * 100
        
        max_usage_percent = max(token_usage_percent, request_usage_percent)
        
        if max_usage_percent >= 90:
            return "limit_reached"
        elif max_usage_percent >= 75:
            return "approaching_limit"
        else:
            return "normal"
    
    def get_usage_summary(self) -> dict:
        """Get detailed usage summary for logging"""
        usage = self.get_current_usage()
        return {
            "total_tokens": usage.total_tokens,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cache_creation_tokens": usage.cache_creation_tokens,
            "cache_read_tokens": usage.cache_read_tokens,
            "requests": usage.requests,
            "timestamp": datetime.now().isoformat()
        }


if __name__ == "__main__":
    # Test the usage tracker
    tracker = UsageTracker()
    usage = tracker.get_current_usage()
    print(f"Current usage: {usage}")
    print(f"Status: {tracker.check_limits()}")
    print(f"Summary: {tracker.get_usage_summary()}")