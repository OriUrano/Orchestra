"""
Claude Code session tracking for 5-hour session detection.
"""
import json
import glob
import os
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class SessionInfo:
    session_start: Optional[datetime] = None
    is_active: bool = False
    
    @property
    def elapsed_time(self) -> timedelta:
        if self.session_start is None:
            return timedelta(0)
        return datetime.now() - self.session_start
    
    @property
    def remaining_time(self) -> timedelta:
        session_duration = timedelta(hours=5)
        return max(timedelta(0), session_duration - self.elapsed_time)
    
    def is_in_final_window(self, window_minutes: int = 15) -> bool:
        return self.remaining_time <= timedelta(minutes=window_minutes)
    
    @property
    def session_expired(self) -> bool:
        return self.elapsed_time >= timedelta(hours=5)


class SessionTracker:
    def __init__(self, claude_dir: Optional[str] = None):
        self.claude_dir = claude_dir or os.path.expanduser("~/.claude")
        self._current_session = None
        
    def find_session_start(self) -> Optional[datetime]:
        """Find the start time of the current 5-hour session from JSONL logs"""
        projects_dir = os.path.join(self.claude_dir, "projects")
        if not os.path.exists(projects_dir):
            return None
            
        jsonl_pattern = os.path.join(projects_dir, "*", "*.jsonl")
        jsonl_files = glob.glob(jsonl_pattern)
        
        all_timestamps = []
        
        for file_path in jsonl_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                            
                        try:
                            data = json.loads(line)
                            timestamp_str = data.get('timestamp', '')
                            if not timestamp_str:
                                continue
                                
                            # Handle ISO format with Z suffix
                            if timestamp_str.endswith('Z'):
                                timestamp_str = timestamp_str[:-1] + '+00:00'
                            
                            timestamp = datetime.fromisoformat(timestamp_str)
                            
                            # Convert to naive datetime if timezone-aware
                            if timestamp.tzinfo is not None:
                                timestamp = timestamp.replace(tzinfo=None)
                            
                            all_timestamps.append(timestamp)
                                
                        except (json.JSONDecodeError, ValueError, KeyError):
                            continue
                            
            except (IOError, OSError):
                continue
        
        if not all_timestamps:
            return None
        
        # Sort timestamps and find the most recent session start
        all_timestamps.sort(reverse=True)
        now = datetime.now()
        
        # Look for gaps of more than 5 hours to identify session boundaries
        session_start = None
        
        for i, timestamp in enumerate(all_timestamps):
            time_diff = now - timestamp
            
            # If this timestamp is within 5 hours, it could be part of current session
            if time_diff <= timedelta(hours=5):
                # For the first session candidate, check if there's a significant gap before it
                if i < len(all_timestamps) - 1:
                    next_timestamp = all_timestamps[i + 1]
                    gap = timestamp - next_timestamp
                    
                    # If gap is more than 5 hours, this timestamp starts the session
                    if gap > timedelta(hours=5):
                        session_start = timestamp
                        break
                else:
                    # This is the earliest timestamp and it's within 5 hours
                    session_start = timestamp
                    break
        
        # Additional validation: ensure we have reasonable activity for a session
        # A single message doesn't constitute an active session
        # Also, messages with identical timestamps aren't a real session
        if session_start:
            session_messages = [ts for ts in all_timestamps if (now - ts) <= timedelta(hours=5)]
            if len(session_messages) < 2:  # Need at least 2 messages for an active session
                return None
            
            # Check for unrealistic patterns (all messages at exact same time)
            unique_timestamps = set(session_messages)
            if len(unique_timestamps) == 1 and len(session_messages) > 5:
                # All messages at same timestamp - likely a test scenario, not real usage
                return None
        
        return session_start
    
    def get_current_session(self) -> SessionInfo:
        """Get current session information"""
        # Always refresh if session is None or expired
        should_refresh = (
            self._current_session is None or 
            (self._current_session.is_active and self._current_session.session_expired)
        )
        
        if should_refresh:
            session_start = self.find_session_start()
            self._current_session = SessionInfo(
                session_start=session_start,
                is_active=session_start is not None
            )
        
        return self._current_session
    
    def check_session_status(self) -> str:
        """
        Check current session status based on timing only.
        Returns: 'no_session', 'normal', 'maximize_usage', 'session_expired'
        """
        session = self.get_current_session()
        
        # If no active session
        if not session.is_active:
            return "no_session"
        
        # If session has expired, start fresh
        if session.session_expired:
            return "session_expired"
        
        # If we're in the final 15 minutes of the session, maximize usage
        if session.is_in_final_window(15):
            return "maximize_usage"
        
        return "normal"
    
    def get_session_summary(self) -> dict:
        """Get session timing summary for logging"""
        session = self.get_current_session()
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "session_active": session.is_active
        }
        
        # Add session information if active
        if session.is_active:
            summary.update({
                "session_start": session.session_start.isoformat() if session.session_start else None,
                "session_elapsed_minutes": int(session.elapsed_time.total_seconds() / 60),
                "session_remaining_minutes": int(session.remaining_time.total_seconds() / 60),
                "is_final_window": session.is_in_final_window(15),
                "session_expired": session.session_expired
            })
        
        return summary


# For backward compatibility, create an alias
UsageTracker = SessionTracker