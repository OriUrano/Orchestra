"""
Unit tests for task_scheduler.py
"""
import json
import os
import tempfile
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, mock_open

from task_scheduler import (
    TaskScheduler, ScheduledTask, TaskPriority, TaskStatus,
    create_pr_implementation_task, create_branch_rebase_task, 
    create_issue_implementation_task
)


class TestTaskPriority:
    """Test TaskPriority enum."""
    
    def test_priority_values(self):
        assert TaskPriority.LOW.value == "low"
        assert TaskPriority.MEDIUM.value == "medium"
        assert TaskPriority.HIGH.value == "high"
        assert TaskPriority.URGENT.value == "urgent"


class TestTaskStatus:
    """Test TaskStatus enum."""
    
    def test_status_values(self):
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"


class TestScheduledTask:
    """Test ScheduledTask dataclass."""
    
    def test_task_creation(self):
        task = ScheduledTask(
            id="test_task_1",
            title="Test Task",
            description="A test task for validation",
            task_type="pr_implementation",
            priority=TaskPriority.HIGH,
            status=TaskStatus.PENDING,
            repo_name="test-repo",
            created_at="2024-01-01T10:00:00",
            due_date="2024-01-02T10:00:00",
            assigned_to_mode="worknight",
            estimated_effort_hours=2.5,
            metadata={"pr_number": 123},
            dependencies=["other_task_1"]
        )
        
        assert task.id == "test_task_1"
        assert task.title == "Test Task"
        assert task.description == "A test task for validation"
        assert task.task_type == "pr_implementation"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING
        assert task.repo_name == "test-repo"
        assert task.created_at == "2024-01-01T10:00:00"
        assert task.due_date == "2024-01-02T10:00:00"
        assert task.assigned_to_mode == "worknight"
        assert task.estimated_effort_hours == 2.5
        assert task.metadata == {"pr_number": 123}
        assert task.dependencies == ["other_task_1"]
    
    def test_task_default_values(self):
        task = ScheduledTask(
            id="simple_task",
            title="Simple Task",
            description="Simple description",
            task_type="issue_work",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.PENDING,
            repo_name="simple-repo",
            created_at="2024-01-01T10:00:00"
        )
        
        assert task.due_date is None
        assert task.assigned_to_mode == "worknight"
        assert task.metadata == {}
        assert task.progress_notes == []
        assert task.estimated_effort_hours == 1.0
        assert task.dependencies == []


class TestTaskScheduler:
    """Test TaskScheduler class."""
    
    def setup_method(self):
        """Set up test with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.scheduler = TaskScheduler(config_path=self.temp_dir)
    
    def test_init_with_custom_path(self):
        custom_path = "/custom/path"
        scheduler = TaskScheduler(config_path=custom_path)
        assert scheduler.config_path == custom_path
        assert scheduler.tasks_file == os.path.join(custom_path, "scheduled_tasks.json")
    
    def test_init_with_default_path(self):
        scheduler = TaskScheduler()
        expected_path = os.path.join(os.path.dirname(__file__).replace("/tests", ""), "config")
        assert scheduler.config_path == expected_path
    
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    def test_load_tasks_file_not_exists(self, mock_exists, mock_file):
        mock_exists.return_value = False
        
        scheduler = TaskScheduler(config_path=self.temp_dir)
        scheduler.load_tasks()
        
        assert scheduler.tasks == []
        mock_file.assert_not_called()
    
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    def test_load_tasks_success(self, mock_exists, mock_file):
        mock_exists.return_value = True
        
        # Mock file content
        task_data = {
            "tasks": [
                {
                    "id": "task_1",
                    "title": "Test Task 1",
                    "description": "First test task",
                    "task_type": "pr_implementation",
                    "priority": "high",
                    "status": "pending",
                    "repo_name": "repo1",
                    "created_at": "2024-01-01T10:00:00",
                    "due_date": None,
                    "assigned_to_mode": "worknight",
                    "metadata": {},
                    "progress_notes": [],
                    "estimated_effort_hours": 1.0,
                    "dependencies": []
                }
            ],
            "last_updated": "2024-01-01T10:00:00"
        }
        
        mock_file.return_value.read.return_value = json.dumps(task_data)
        
        scheduler = TaskScheduler(config_path=self.temp_dir)
        scheduler.load_tasks()
        
        assert len(scheduler.tasks) == 1
        assert scheduler.tasks[0].id == "task_1"
        assert scheduler.tasks[0].priority == TaskPriority.HIGH
        assert scheduler.tasks[0].status == TaskStatus.PENDING
    
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    def test_load_tasks_json_error(self, mock_exists, mock_file, capsys):
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = "invalid json"
        
        scheduler = TaskScheduler(config_path=self.temp_dir)
        scheduler.load_tasks()
        
        assert scheduler.tasks == []
        captured = capsys.readouterr()
        assert "Error loading tasks" in captured.out
    
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    def test_save_tasks_success(self, mock_makedirs, mock_file):
        scheduler = TaskScheduler(config_path=self.temp_dir)
        
        # Add a task
        task = ScheduledTask(
            id="save_test",
            title="Save Test",
            description="Test saving",
            task_type="test",
            priority=TaskPriority.MEDIUM,
            status=TaskStatus.PENDING,
            repo_name="test-repo",
            created_at="2024-01-01T10:00:00"
        )
        scheduler.tasks = [task]
        
        scheduler.save_tasks()
        
        # Verify makedirs was called
        mock_makedirs.assert_called_once_with(self.temp_dir, exist_ok=True)
        
        # Verify file was written
        mock_file.assert_called_once_with(f"{self.temp_dir}/scheduled_tasks.json", 'w')
        
        # Verify JSON content
        written_content = ''.join(call.args[0] for call in mock_file().write.call_args_list)
        data = json.loads(written_content)
        
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["id"] == "save_test"
        assert data["tasks"][0]["priority"] == "medium"
        assert data["tasks"][0]["status"] == "pending"
        assert "last_updated" in data
    
    @patch("builtins.open", side_effect=IOError("Write failed"))
    @patch("os.makedirs")
    def test_save_tasks_error(self, mock_makedirs, mock_file, capsys):
        scheduler = TaskScheduler(config_path=self.temp_dir)
        scheduler.tasks = [Mock()]
        
        scheduler.save_tasks()
        
        captured = capsys.readouterr()
        assert "Error saving tasks" in captured.out
    
    @patch.object(TaskScheduler, 'save_tasks')
    def test_add_task_success(self, mock_save):
        scheduler = TaskScheduler(config_path=self.temp_dir)
        
        task_id = scheduler.add_task(
            title="New Task",
            description="Task description",
            task_type="pr_implementation",
            repo_name="test-repo",
            priority=TaskPriority.HIGH,
            due_date="2024-01-02T10:00:00",
            estimated_effort_hours=3.0,
            metadata={"pr_number": 456},
            dependencies=["dep_task"]
        )
        
        assert task_id.startswith("test-repo_pr_implementation_")
        assert len(scheduler.tasks) == 1
        
        task = scheduler.tasks[0]
        assert task.title == "New Task"
        assert task.description == "Task description"
        assert task.task_type == "pr_implementation"
        assert task.repo_name == "test-repo"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING
        assert task.due_date == "2024-01-02T10:00:00"
        assert task.estimated_effort_hours == 3.0
        assert task.metadata == {"pr_number": 456}
        assert task.dependencies == ["dep_task"]
        
        mock_save.assert_called_once()
    
    def test_get_tasks_for_mode_worknight(self):
        scheduler = TaskScheduler(config_path=self.temp_dir)
        
        # Add multiple tasks with different modes and statuses
        task1 = ScheduledTask(
            id="task_1", title="Task 1", description="Desc 1", task_type="type1",
            priority=TaskPriority.HIGH, status=TaskStatus.PENDING, repo_name="repo1",
            created_at="2024-01-01T10:00:00", assigned_to_mode="worknight"
        )
        task2 = ScheduledTask(
            id="task_2", title="Task 2", description="Desc 2", task_type="type2", 
            priority=TaskPriority.MEDIUM, status=TaskStatus.IN_PROGRESS, repo_name="repo1",
            created_at="2024-01-01T11:00:00", assigned_to_mode="worknight"
        )
        task3 = ScheduledTask(
            id="task_3", title="Task 3", description="Desc 3", task_type="type3",
            priority=TaskPriority.LOW, status=TaskStatus.PENDING, repo_name="repo2",
            created_at="2024-01-01T12:00:00", assigned_to_mode="weekend"
        )
        task4 = ScheduledTask(
            id="task_4", title="Task 4", description="Desc 4", task_type="type4",
            priority=TaskPriority.MEDIUM, status=TaskStatus.COMPLETED, repo_name="repo1",
            created_at="2024-01-01T13:00:00", assigned_to_mode="worknight"
        )
        
        scheduler.tasks = [task1, task2, task3, task4]
        
        # Get worknight tasks for repo1
        worknight_tasks = scheduler.get_tasks_for_mode("worknight", "repo1")
        
        assert len(worknight_tasks) == 2  # task1 and task2 (not completed task4)
        assert worknight_tasks[0].id == "task_1"  # HIGH priority first
        assert worknight_tasks[1].id == "task_2"  # MEDIUM priority second
    
    def test_get_tasks_for_mode_priority_sorting(self):
        scheduler = TaskScheduler(config_path=self.temp_dir)
        
        # Create tasks with different priorities
        urgent_task = ScheduledTask(
            id="urgent", title="Urgent", description="Urgent task", task_type="type1",
            priority=TaskPriority.URGENT, status=TaskStatus.PENDING, repo_name="repo1",
            created_at="2024-01-01T10:00:00", assigned_to_mode="worknight"
        )
        low_task = ScheduledTask(
            id="low", title="Low", description="Low task", task_type="type2",
            priority=TaskPriority.LOW, status=TaskStatus.PENDING, repo_name="repo1", 
            created_at="2024-01-01T09:00:00", assigned_to_mode="worknight"
        )
        high_task = ScheduledTask(
            id="high", title="High", description="High task", task_type="type3",
            priority=TaskPriority.HIGH, status=TaskStatus.PENDING, repo_name="repo1",
            created_at="2024-01-01T11:00:00", assigned_to_mode="worknight"
        )
        
        scheduler.tasks = [low_task, urgent_task, high_task]  # Unsorted order
        
        tasks = scheduler.get_tasks_for_mode("worknight", "repo1")
        
        # Should be sorted by priority: URGENT, HIGH, LOW
        assert len(tasks) == 3
        assert tasks[0].priority == TaskPriority.URGENT
        assert tasks[1].priority == TaskPriority.HIGH  
        assert tasks[2].priority == TaskPriority.LOW
    
    @patch.object(TaskScheduler, 'save_tasks')
    def test_update_task_status_success(self, mock_save):
        scheduler = TaskScheduler(config_path=self.temp_dir)
        
        task = ScheduledTask(
            id="update_test", title="Update Test", description="Test update", 
            task_type="test", priority=TaskPriority.MEDIUM, status=TaskStatus.PENDING,
            repo_name="repo", created_at="2024-01-01T10:00:00"
        )
        scheduler.tasks = [task]
        
        result = scheduler.update_task_status("update_test", TaskStatus.IN_PROGRESS, "Started work")
        
        assert result == True
        assert task.status == TaskStatus.IN_PROGRESS
        assert len(task.progress_notes) == 1
        assert "Started work" in task.progress_notes[0]
        mock_save.assert_called_once()
    
    def test_update_task_status_not_found(self):
        scheduler = TaskScheduler(config_path=self.temp_dir)
        scheduler.tasks = []
        
        result = scheduler.update_task_status("nonexistent", TaskStatus.COMPLETED)
        
        assert result == False
    
    @patch.object(TaskScheduler, 'save_tasks')
    def test_add_progress_note_success(self, mock_save):
        scheduler = TaskScheduler(config_path=self.temp_dir)
        
        task = ScheduledTask(
            id="note_test", title="Note Test", description="Test notes",
            task_type="test", priority=TaskPriority.MEDIUM, status=TaskStatus.IN_PROGRESS,
            repo_name="repo", created_at="2024-01-01T10:00:00"
        )
        scheduler.tasks = [task]
        
        result = scheduler.add_progress_note("note_test", "Making progress")
        
        assert result == True
        assert len(task.progress_notes) == 1
        assert "Making progress" in task.progress_notes[0]
        mock_save.assert_called_once()
    
    def test_add_progress_note_not_found(self):
        scheduler = TaskScheduler(config_path=self.temp_dir)
        scheduler.tasks = []
        
        result = scheduler.add_progress_note("nonexistent", "Note")
        
        assert result == False
    
    @patch.object(TaskScheduler, 'update_task_status')
    def test_complete_task(self, mock_update):
        scheduler = TaskScheduler(config_path=self.temp_dir)
        mock_update.return_value = True
        
        result = scheduler.complete_task("task_id", "Task completed successfully")
        
        assert result == True
        mock_update.assert_called_once_with("task_id", TaskStatus.COMPLETED, "Task completed successfully")
    
    @patch.object(TaskScheduler, 'update_task_status')
    def test_fail_task(self, mock_update):
        scheduler = TaskScheduler(config_path=self.temp_dir)
        mock_update.return_value = True
        
        result = scheduler.fail_task("task_id", "Network timeout")
        
        assert result == True
        mock_update.assert_called_once_with("task_id", TaskStatus.FAILED, "Failed: Network timeout")
    
    def test_get_task_found(self):
        scheduler = TaskScheduler(config_path=self.temp_dir)
        
        task = ScheduledTask(
            id="find_me", title="Find Me", description="Find this task",
            task_type="test", priority=TaskPriority.MEDIUM, status=TaskStatus.PENDING,
            repo_name="repo", created_at="2024-01-01T10:00:00"
        )
        scheduler.tasks = [task]
        
        found_task = scheduler.get_task("find_me")
        
        assert found_task is not None
        assert found_task.id == "find_me"
        assert found_task.title == "Find Me"
    
    def test_get_task_not_found(self):
        scheduler = TaskScheduler(config_path=self.temp_dir)
        scheduler.tasks = []
        
        found_task = scheduler.get_task("nonexistent")
        
        assert found_task is None
    
    def test_can_start_task_no_dependencies(self):
        scheduler = TaskScheduler(config_path=self.temp_dir)
        
        task = ScheduledTask(
            id="no_deps", title="No Dependencies", description="Task with no deps",
            task_type="test", priority=TaskPriority.MEDIUM, status=TaskStatus.PENDING,
            repo_name="repo", created_at="2024-01-01T10:00:00", dependencies=[]
        )
        scheduler.tasks = [task]
        
        can_start = scheduler.can_start_task("no_deps")
        
        assert can_start == True
    
    def test_can_start_task_dependencies_completed(self):
        scheduler = TaskScheduler(config_path=self.temp_dir)
        
        dep_task = ScheduledTask(
            id="dependency", title="Dependency", description="Dependency task",
            task_type="test", priority=TaskPriority.MEDIUM, status=TaskStatus.COMPLETED,
            repo_name="repo", created_at="2024-01-01T10:00:00"
        )
        main_task = ScheduledTask(
            id="main_task", title="Main Task", description="Task with dependency",
            task_type="test", priority=TaskPriority.MEDIUM, status=TaskStatus.PENDING,
            repo_name="repo", created_at="2024-01-01T11:00:00", dependencies=["dependency"]
        )
        scheduler.tasks = [dep_task, main_task]
        
        can_start = scheduler.can_start_task("main_task")
        
        assert can_start == True
    
    def test_can_start_task_dependencies_not_completed(self):
        scheduler = TaskScheduler(config_path=self.temp_dir)
        
        dep_task = ScheduledTask(
            id="dependency", title="Dependency", description="Dependency task",
            task_type="test", priority=TaskPriority.MEDIUM, status=TaskStatus.IN_PROGRESS,
            repo_name="repo", created_at="2024-01-01T10:00:00"
        )
        main_task = ScheduledTask(
            id="main_task", title="Main Task", description="Task with dependency", 
            task_type="test", priority=TaskPriority.MEDIUM, status=TaskStatus.PENDING,
            repo_name="repo", created_at="2024-01-01T11:00:00", dependencies=["dependency"]
        )
        scheduler.tasks = [dep_task, main_task]
        
        can_start = scheduler.can_start_task("main_task")
        
        assert can_start == False
    
    def test_can_start_task_missing_dependency(self):
        scheduler = TaskScheduler(config_path=self.temp_dir)
        
        main_task = ScheduledTask(
            id="main_task", title="Main Task", description="Task with missing dependency",
            task_type="test", priority=TaskPriority.MEDIUM, status=TaskStatus.PENDING,
            repo_name="repo", created_at="2024-01-01T11:00:00", dependencies=["missing_dep"]
        )
        scheduler.tasks = [main_task]
        
        can_start = scheduler.can_start_task("main_task")
        
        assert can_start == False
    
    def test_can_start_task_not_found(self):
        scheduler = TaskScheduler(config_path=self.temp_dir)
        scheduler.tasks = []
        
        can_start = scheduler.can_start_task("nonexistent")
        
        assert can_start == False
    
    @patch.object(TaskScheduler, 'save_tasks')
    def test_cleanup_old_tasks(self, mock_save):
        scheduler = TaskScheduler(config_path=self.temp_dir)
        
        # Create old completed task
        old_completed = ScheduledTask(
            id="old_completed", title="Old Completed", description="Old task",
            task_type="test", priority=TaskPriority.MEDIUM, status=TaskStatus.COMPLETED,
            repo_name="repo", created_at=(datetime.now() - timedelta(days=35)).isoformat()
        )
        
        # Create recent completed task
        recent_completed = ScheduledTask(
            id="recent_completed", title="Recent Completed", description="Recent task",
            task_type="test", priority=TaskPriority.MEDIUM, status=TaskStatus.COMPLETED,
            repo_name="repo", created_at=(datetime.now() - timedelta(days=10)).isoformat()
        )
        
        # Create old pending task (should not be removed)
        old_pending = ScheduledTask(
            id="old_pending", title="Old Pending", description="Old pending task",
            task_type="test", priority=TaskPriority.MEDIUM, status=TaskStatus.PENDING,
            repo_name="repo", created_at=(datetime.now() - timedelta(days=35)).isoformat()
        )
        
        scheduler.tasks = [old_completed, recent_completed, old_pending]
        
        removed_count = scheduler.cleanup_old_tasks(days_old=30)
        
        assert removed_count == 1  # Only old_completed should be removed
        assert len(scheduler.tasks) == 2
        assert old_completed not in scheduler.tasks
        assert recent_completed in scheduler.tasks
        assert old_pending in scheduler.tasks
        
        mock_save.assert_called_once()
    
    def test_cleanup_old_tasks_no_removal(self):
        scheduler = TaskScheduler(config_path=self.temp_dir)
        
        # Create only recent tasks
        recent_task = ScheduledTask(
            id="recent", title="Recent", description="Recent task",
            task_type="test", priority=TaskPriority.MEDIUM, status=TaskStatus.COMPLETED,
            repo_name="repo", created_at=(datetime.now() - timedelta(days=10)).isoformat()
        )
        
        scheduler.tasks = [recent_task]
        
        with patch.object(scheduler, 'save_tasks') as mock_save:
            removed_count = scheduler.cleanup_old_tasks(days_old=30)
        
        assert removed_count == 0
        assert len(scheduler.tasks) == 1
        mock_save.assert_not_called()  # Should not save if nothing removed
    
    def test_get_task_summary(self):
        scheduler = TaskScheduler(config_path=self.temp_dir)
        
        # Create tasks with different statuses, priorities, and modes
        tasks = [
            ScheduledTask(
                id="task1", title="Task 1", description="Desc 1", task_type="type1",
                priority=TaskPriority.HIGH, status=TaskStatus.PENDING, repo_name="repo1",
                created_at="2024-01-01T10:00:00", assigned_to_mode="worknight"
            ),
            ScheduledTask(
                id="task2", title="Task 2", description="Desc 2", task_type="type2",
                priority=TaskPriority.MEDIUM, status=TaskStatus.COMPLETED, repo_name="repo1",
                created_at="2024-01-01T11:00:00", assigned_to_mode="weekend"
            ),
            ScheduledTask(
                id="task3", title="Task 3", description="Desc 3", task_type="type3",
                priority=TaskPriority.HIGH, status=TaskStatus.IN_PROGRESS, repo_name="repo2",
                created_at="2024-01-01T12:00:00", assigned_to_mode="worknight",
                due_date=(datetime.now() - timedelta(days=1)).isoformat()  # Overdue
            ),
            ScheduledTask(
                id="task4", title="Task 4", description="Desc 4", task_type="type4",
                priority=TaskPriority.LOW, status=TaskStatus.FAILED, repo_name="repo1",
                created_at="2024-01-01T13:00:00", assigned_to_mode="weekend"
            )
        ]
        
        scheduler.tasks = tasks
        
        summary = scheduler.get_task_summary()
        
        assert summary["total_tasks"] == 4
        
        # Check status breakdown
        assert summary["status_breakdown"]["pending"] == 1
        assert summary["status_breakdown"]["completed"] == 1  
        assert summary["status_breakdown"]["in_progress"] == 1
        assert summary["status_breakdown"]["failed"] == 1
        
        # Check priority breakdown
        assert summary["priority_breakdown"]["high"] == 2
        assert summary["priority_breakdown"]["medium"] == 1
        assert summary["priority_breakdown"]["low"] == 1
        
        # Check mode breakdown
        assert summary["mode_breakdown"]["worknight"] == 2
        assert summary["mode_breakdown"]["weekend"] == 2
        
        # Check overdue count
        assert summary["overdue_tasks"] == 1


class TestConvenienceFunctions:
    """Test convenience functions for creating common task types."""
    
    def setup_method(self):
        """Set up test with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.scheduler = TaskScheduler(config_path=self.temp_dir)
    
    @patch.object(TaskScheduler, 'add_task')
    def test_create_pr_implementation_task(self, mock_add_task):
        mock_add_task.return_value = "test_task_id"
        
        scheduler = self.scheduler
        
        task_id = create_pr_implementation_task(
            scheduler=scheduler,
            repo_name="test-repo",
            pr_number=123,
            pr_title="Feature: Add new functionality",
            implementation_request="Please implement the new API endpoint",
            priority=TaskPriority.HIGH,
            due_date="2024-01-02T10:00:00"
        )
        
        assert task_id == "test_task_id"
        
        mock_add_task.assert_called_once_with(
            title="Implement PR #123 request",
            description="Implement requested changes in PR 'Feature: Add new functionality': Please implement the new API endpoint",
            task_type="pr_implementation",
            repo_name="test-repo",
            priority=TaskPriority.HIGH,
            due_date="2024-01-02T10:00:00",
            metadata={
                'pr_number': 123,
                'pr_title': "Feature: Add new functionality",
                'implementation_request': "Please implement the new API endpoint"
            }
        )
    
    @patch.object(TaskScheduler, 'add_task')
    def test_create_branch_rebase_task(self, mock_add_task):
        mock_add_task.return_value = "rebase_task_id"
        
        scheduler = self.scheduler
        
        task_id = create_branch_rebase_task(
            scheduler=scheduler,
            repo_name="test-repo", 
            branch_name="feature-branch",
            priority=TaskPriority.MEDIUM
        )
        
        assert task_id == "rebase_task_id"
        
        mock_add_task.assert_called_once_with(
            title="Rebase branch feature-branch",
            description="Rebase feature-branch from main branch and resolve any conflicts",
            task_type="branch_rebase",
            repo_name="test-repo",
            priority=TaskPriority.MEDIUM,
            estimated_effort_hours=0.5,
            metadata={
                'branch_name': "feature-branch",
                'base_branch': 'main'
            }
        )
    
    @patch.object(TaskScheduler, 'add_task')
    def test_create_issue_implementation_task(self, mock_add_task):
        mock_add_task.return_value = "issue_task_id"
        
        scheduler = self.scheduler
        
        task_id = create_issue_implementation_task(
            scheduler=scheduler,
            repo_name="test-repo",
            issue_number=456,
            issue_title="Bug: Authentication fails on mobile",
            priority=TaskPriority.URGENT,
            due_date="2024-01-01T18:00:00",
            estimated_hours=4.0
        )
        
        assert task_id == "issue_task_id"
        
        mock_add_task.assert_called_once_with(
            title="Implement Issue #456",
            description="Implement solution for issue 'Bug: Authentication fails on mobile'",
            task_type="issue_implementation",
            repo_name="test-repo",
            priority=TaskPriority.URGENT,
            due_date="2024-01-01T18:00:00",
            estimated_effort_hours=4.0,
            metadata={
                'issue_number': 456,
                'issue_title': "Bug: Authentication fails on mobile"
            }
        )


class TestTaskSchedulerIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    def setup_method(self):
        """Set up test with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.scheduler = TaskScheduler(config_path=self.temp_dir)
    
    def test_complete_task_workflow(self):
        scheduler = self.scheduler
        
        # Add a new task
        task_id = scheduler.add_task(
            title="Fix critical bug",
            description="Authentication system is broken",
            task_type="bug_fix",
            repo_name="auth-service",
            priority=TaskPriority.URGENT,
            due_date=(datetime.now() + timedelta(hours=4)).isoformat()
        )
        
        # Verify task was added
        assert len(scheduler.tasks) == 1
        task = scheduler.get_task(task_id)
        assert task is not None
        assert task.status == TaskStatus.PENDING
        
        # Check if task can be started (should be True - no dependencies)
        assert scheduler.can_start_task(task_id) == True
        
        # Start working on the task
        scheduler.update_task_status(task_id, TaskStatus.IN_PROGRESS, "Starting investigation")
        
        # Add progress notes
        scheduler.add_progress_note(task_id, "Found the root cause in JWT validation")
        scheduler.add_progress_note(task_id, "Implementing fix")
        
        # Complete the task
        scheduler.complete_task(task_id, "Bug fixed and tests added")
        
        # Verify final state
        task = scheduler.get_task(task_id)
        assert task.status == TaskStatus.COMPLETED
        assert len(task.progress_notes) == 4  # 3 manual notes + 1 completion note
        assert "Starting investigation" in task.progress_notes[0]
        assert "Bug fixed and tests added" in task.progress_notes[3]
    
    def test_dependency_management(self):
        scheduler = self.scheduler
        
        # Create dependent tasks
        dep_task_id = scheduler.add_task(
            title="Setup test environment",
            description="Prepare environment for integration tests",
            task_type="setup",
            repo_name="test-repo",
            priority=TaskPriority.HIGH
        )
        
        main_task_id = scheduler.add_task(
            title="Run integration tests",
            description="Execute full integration test suite",
            task_type="testing",
            repo_name="test-repo",
            priority=TaskPriority.HIGH,
            dependencies=[dep_task_id]
        )
        
        # Main task should not be startable until dependency is complete
        assert scheduler.can_start_task(dep_task_id) == True
        assert scheduler.can_start_task(main_task_id) == False
        
        # Complete dependency
        scheduler.complete_task(dep_task_id, "Environment ready")
        
        # Now main task should be startable
        assert scheduler.can_start_task(main_task_id) == True
        
        # Get tasks for worknight mode - should be sorted by priority
        tasks = scheduler.get_tasks_for_mode("worknight", "test-repo")
        
        # Should only return main_task (dep_task is completed)
        assert len(tasks) == 1
        assert tasks[0].id == main_task_id
    
    def test_priority_and_due_date_sorting(self):
        scheduler = self.scheduler
        
        # Create tasks with different priorities and due dates
        now = datetime.now()
        
        # Overdue medium priority task
        overdue_task_id = scheduler.add_task(
            title="Overdue task",
            description="This task is overdue",
            task_type="maintenance",
            repo_name="test-repo",
            priority=TaskPriority.MEDIUM,
            due_date=(now - timedelta(hours=2)).isoformat()
        )
        
        # High priority task due soon
        urgent_task_id = scheduler.add_task(
            title="High priority task",
            description="High priority work",
            task_type="feature",
            repo_name="test-repo", 
            priority=TaskPriority.HIGH,
            due_date=(now + timedelta(hours=1)).isoformat()
        )
        
        # Low priority task
        low_task_id = scheduler.add_task(
            title="Low priority task",
            description="Can wait",
            task_type="cleanup",
            repo_name="test-repo",
            priority=TaskPriority.LOW
        )
        
        # Get sorted tasks
        tasks = scheduler.get_tasks_for_mode("worknight", "test-repo")
        
        # Should be sorted: overdue first, then high priority, then low priority
        assert len(tasks) == 3
        assert tasks[0].id == overdue_task_id  # Overdue gets highest priority
        assert tasks[1].id == urgent_task_id   # High priority
        assert tasks[2].id == low_task_id      # Low priority