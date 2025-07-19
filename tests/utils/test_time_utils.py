"""
Unit tests for utils/time_utils.py
"""
import pytest
from datetime import datetime
from utils.time_utils import (
    get_work_mode, 
    is_work_hours, 
    get_next_work_period,
    should_run_automation
)


class TestGetWorkMode:
    """Test work mode detection logic."""
    
    def test_workday_monday_morning(self):
        # Monday 10:00 AM
        dt = datetime(2024, 1, 15, 10, 0, 0)
        assert get_work_mode(dt) == "workday"
    
    def test_workday_friday_afternoon(self):
        # Friday 3:00 PM
        dt = datetime(2024, 1, 19, 15, 0, 0)
        assert get_work_mode(dt) == "workday"
    
    def test_workday_boundary_8am(self):
        # Tuesday 8:00 AM (start of workday)
        dt = datetime(2024, 1, 16, 8, 0, 0)
        assert get_work_mode(dt) == "workday"
    
    def test_workday_boundary_before_6pm(self):
        # Wednesday 5:59 PM (end of workday)
        dt = datetime(2024, 1, 17, 17, 59, 0)
        assert get_work_mode(dt) == "workday"
    
    def test_worknight_monday_evening(self):
        # Monday 8:00 PM
        dt = datetime(2024, 1, 15, 20, 0, 0)
        assert get_work_mode(dt) == "worknight"
    
    def test_worknight_tuesday_late(self):
        # Wednesday 2:00 AM (early morning)
        dt = datetime(2024, 1, 17, 2, 0, 0)
        assert get_work_mode(dt) == "worknight"
    
    def test_worknight_boundary_6pm(self):
        # Tuesday 6:00 PM (start of worknight)
        dt = datetime(2024, 1, 16, 18, 0, 0)
        assert get_work_mode(dt) == "worknight"
    
    def test_worknight_boundary_4am(self):
        # Wednesday 3:59 AM (end of worknight)
        dt = datetime(2024, 1, 17, 3, 59, 0)
        assert get_work_mode(dt) == "worknight"
    
    def test_weekend_saturday(self):
        # Saturday 2:00 PM
        dt = datetime(2024, 1, 20, 14, 0, 0)
        assert get_work_mode(dt) == "weekend"
    
    def test_weekend_sunday(self):
        # Sunday 11:00 AM
        dt = datetime(2024, 1, 21, 11, 0, 0)
        assert get_work_mode(dt) == "weekend"
    
    def test_weekend_friday_evening(self):
        # Friday 6:00 PM (start of weekend)
        dt = datetime(2024, 1, 19, 18, 0, 0)
        assert get_work_mode(dt) == "weekend"
    
    def test_weekend_monday_early(self):
        # Monday 7:59 AM (end of weekend)
        dt = datetime(2024, 1, 15, 7, 59, 0)
        assert get_work_mode(dt) == "weekend"
    
    def test_worknight_thursday_night(self):
        # Thursday 10:00 PM (worknight includes Thursday)
        dt = datetime(2024, 1, 18, 22, 0, 0)
        assert get_work_mode(dt) == "worknight"
    
    def test_off_hours_friday_early_morning(self):
        # Friday 5:00 AM
        dt = datetime(2024, 1, 19, 5, 0, 0)
        assert get_work_mode(dt) == "off"
    
    def test_off_hours_workday_early_morning(self):
        # Tuesday 6:00 AM
        dt = datetime(2024, 1, 16, 6, 0, 0)
        assert get_work_mode(dt) == "off"


class TestIsWorkHours:
    """Test work hours detection."""
    
    def test_workday_is_work_hours(self, workday_datetime):
        assert is_work_hours(workday_datetime) == True
    
    def test_worknight_is_work_hours(self, worknight_datetime):
        assert is_work_hours(worknight_datetime) == True
    
    def test_weekend_is_work_hours(self, weekend_datetime):
        assert is_work_hours(weekend_datetime) == True
    
    def test_off_hours_not_work_hours(self, off_hours_datetime):
        assert is_work_hours(off_hours_datetime) == False


class TestShouldRunAutomation:
    """Test automation scheduling logic."""
    
    def test_should_run_during_workday(self, workday_datetime):
        assert should_run_automation(workday_datetime) == True
    
    def test_should_run_during_worknight(self, worknight_datetime):
        assert should_run_automation(worknight_datetime) == True
    
    def test_should_run_during_weekend(self, weekend_datetime):
        assert should_run_automation(weekend_datetime) == True
    
    def test_should_not_run_during_off_hours(self, off_hours_datetime):
        assert should_run_automation(off_hours_datetime) == False


class TestGetNextWorkPeriod:
    """Test next work period calculation."""
    
    def test_next_work_period_during_work_hours(self, workday_datetime):
        # If already in work hours, should return current time
        result = get_next_work_period(workday_datetime)
        assert result == workday_datetime
    
    def test_next_work_period_early_morning_workday(self):
        # Tuesday 6:00 AM -> should be 8:00 AM same day
        dt = datetime(2024, 1, 16, 6, 0, 0)
        expected = datetime(2024, 1, 16, 8, 0, 0)
        result = get_next_work_period(dt)
        assert result == expected
    
    def test_next_work_period_between_workday_and_worknight(self):
        # Tuesday 4:00 PM is during workday, so should return current time
        dt = datetime(2024, 1, 16, 16, 0, 0)
        result = get_next_work_period(dt)
        assert result == dt  # Returns current time since it's during work hours
    
    def test_next_work_period_friday_evening(self):
        # Friday 8:00 PM is weekend, so should return current time
        dt = datetime(2024, 1, 19, 20, 0, 0)
        result = get_next_work_period(dt)
        assert result == dt  # Returns current time since weekend is work hours
    
    def test_next_work_period_sunday(self):
        # Sunday is weekend, so should return current time
        dt = datetime(2024, 1, 21, 14, 0, 0)
        result = get_next_work_period(dt)
        assert result == dt  # Returns current time since weekend is work hours


class TestWeekdayLogic:
    """Test specific weekday edge cases."""
    
    def test_monday_weekday_zero(self):
        # Monday should be weekday 0
        monday = datetime(2024, 1, 15, 10, 0, 0)
        assert monday.weekday() == 0
        assert get_work_mode(monday) == "workday"
    
    def test_friday_weekday_four(self):
        # Friday should be weekday 4
        friday = datetime(2024, 1, 19, 10, 0, 0)
        assert friday.weekday() == 4
        assert get_work_mode(friday) == "workday"
    
    def test_saturday_weekday_five(self):
        # Saturday should be weekday 5
        saturday = datetime(2024, 1, 20, 10, 0, 0)
        assert saturday.weekday() == 5
        assert get_work_mode(saturday) == "weekend"
    
    def test_sunday_weekday_six(self):
        # Sunday should be weekday 6
        sunday = datetime(2024, 1, 21, 10, 0, 0)
        assert sunday.weekday() == 6
        assert get_work_mode(sunday) == "weekend"


class TestBoundaryConditions:
    """Test boundary conditions and edge cases."""
    
    def test_exact_hour_boundaries(self):
        # Test exact hour boundaries
        tuesday_8am = datetime(2024, 1, 16, 8, 0, 0)
        tuesday_6pm = datetime(2024, 1, 16, 18, 0, 0)
        tuesday_759am = datetime(2024, 1, 16, 7, 59, 59)
        tuesday_600pm = datetime(2024, 1, 16, 18, 0, 1)
        
        assert get_work_mode(tuesday_8am) == "workday"
        assert get_work_mode(tuesday_6pm) == "worknight"
        assert get_work_mode(tuesday_759am) == "off"
        assert get_work_mode(tuesday_600pm) == "worknight"
    
    def test_worknight_thursday_boundary(self):
        # Thursday has worknight, Friday doesn't
        thursday_6pm = datetime(2024, 1, 18, 18, 0, 0)  # Thursday 6 PM
        thursday_11pm = datetime(2024, 1, 18, 23, 0, 0)  # Thursday 11 PM
        friday_11pm = datetime(2024, 1, 19, 23, 0, 0)  # Friday 11 PM
        
        # Thursday should have worknight
        assert get_work_mode(thursday_6pm) == "worknight"
        assert get_work_mode(thursday_11pm) == "worknight"
        # Friday should be weekend  
        assert get_work_mode(friday_11pm) == "weekend"
    
    def test_weekend_start_end(self):
        # Friday 6 PM starts weekend
        friday_6pm = datetime(2024, 1, 19, 18, 0, 0)
        friday_559pm = datetime(2024, 1, 19, 17, 59, 59)
        
        # Monday 8 AM ends weekend
        monday_8am = datetime(2024, 1, 22, 8, 0, 0)
        monday_759am = datetime(2024, 1, 22, 7, 59, 59)
        
        assert get_work_mode(friday_6pm) == "weekend"
        assert get_work_mode(friday_559pm) == "workday"
        assert get_work_mode(monday_8am) == "workday"
        assert get_work_mode(monday_759am) == "weekend"