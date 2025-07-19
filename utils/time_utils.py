"""
Time and work mode detection utilities.
"""
from datetime import datetime
from typing import Literal

WorkMode = Literal["workday", "worknight", "weekend", "off"]


def get_work_mode(now: datetime = None) -> WorkMode:
    """
    Determine current work mode based on time.
    
    Args:
        now: Current datetime, defaults to datetime.now()
        
    Returns:
        WorkMode: One of "workday", "worknight", "weekend", "off"
    """
    if now is None:
        now = datetime.now()
    
    weekday = now.weekday()  # 0=Monday, 6=Sunday
    hour = now.hour
    
    # Weekend: Friday 6pm - Monday 8am
    if (weekday >= 5 or  # Saturday, Sunday
        (weekday == 0 and hour < 8) or  # Monday before 8am
        (weekday == 4 and hour >= 18)):  # Friday after 6pm
        return "weekend"
    
    # Workday: Monday-Friday 8am-6pm
    if weekday < 5 and 8 <= hour < 18:
        return "workday"
    
    # Worknight: Monday-Thursday 6pm-4am (next day)
    if weekday < 4 and (hour >= 18 or hour < 4):
        return "worknight"
    
    # Off hours (e.g., Thursday 6pm - Friday 8am, weekday early morning 4am-8am)
    return "off"


def is_work_hours(now: datetime = None) -> bool:
    """Check if current time is during work hours (any active mode)"""
    mode = get_work_mode(now)
    return mode in ["workday", "worknight", "weekend"]


def get_next_work_period(now: datetime = None) -> datetime:
    """Get the start time of the next work period"""
    if now is None:
        now = datetime.now()
    
    weekday = now.weekday()
    hour = now.hour
    
    # If currently in work hours, return now
    if is_work_hours(now):
        return now
    
    # Calculate next work period start
    if weekday < 4:  # Monday-Thursday
        if hour < 8:
            # Before workday starts
            return now.replace(hour=8, minute=0, second=0, microsecond=0)
        elif hour < 18:
            # During workday (shouldn't happen if not in work hours)
            return now
        else:
            # After workday, before worknight
            return now.replace(hour=18, minute=0, second=0, microsecond=0)
    
    elif weekday == 4:  # Friday
        if hour < 8:
            # Before workday
            return now.replace(hour=8, minute=0, second=0, microsecond=0)
        elif hour < 18:
            # During workday
            return now
        else:
            # Friday evening - weekend starts
            return now.replace(hour=18, minute=0, second=0, microsecond=0)
    
    else:  # Weekend
        # Next Monday 8am
        days_until_monday = (7 - weekday) % 7
        if days_until_monday == 0:  # It's Sunday
            days_until_monday = 1
        
        next_monday = now.replace(hour=8, minute=0, second=0, microsecond=0)
        next_monday = next_monday.replace(day=now.day + days_until_monday)
        return next_monday


def should_run_automation(now: datetime = None) -> bool:
    """Determine if automation should run at the current time"""
    mode = get_work_mode(now)
    return mode != "off"


