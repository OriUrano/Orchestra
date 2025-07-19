"""
Task scheduling system for Orchestra worknight mode.
Manages persistent tasks that need to be completed across multiple runs.
"""
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledTask:
    id: str
    title: str
    description: str
    task_type: str  # "pr_implementation", "branch_rebase", "issue_work", etc.
    priority: TaskPriority
    status: TaskStatus
    repo_name: str
    created_at: str
    due_date: Optional[str] = None
    assigned_to_mode: str = "worknight"  # "worknight", "weekend"
    metadata: Dict[str, Any] = None
    progress_notes: List[str] = None
    estimated_effort_hours: float = 1.0
    dependencies: List[str] = None  # List of task IDs this depends on
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.progress_notes is None:
            self.progress_notes = []
        if self.dependencies is None:
            self.dependencies = []


class TaskScheduler:
    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), "config")
        self.tasks_file = os.path.join(self.config_path, "scheduled_tasks.json")
        self.tasks: List[ScheduledTask] = []
        self.load_tasks()
    
    def load_tasks(self) -> None:
        """Load tasks from the persistent storage file"""
        if not os.path.exists(self.tasks_file):
            self.tasks = []
            return
        
        try:
            with open(self.tasks_file, 'r') as f:
                data = json.load(f)
            
            self.tasks = []
            for task_data in data.get('tasks', []):
                # Convert string enums back to enum objects
                task_data['priority'] = TaskPriority(task_data['priority'])
                task_data['status'] = TaskStatus(task_data['status'])
                
                task = ScheduledTask(**task_data)
                self.tasks.append(task)
                
        except Exception as e:
            print(f"Error loading tasks: {e}")
            self.tasks = []
    
    def save_tasks(self) -> None:
        """Save tasks to persistent storage"""
        try:
            os.makedirs(self.config_path, exist_ok=True)
            
            # Convert tasks to JSON-serializable format
            tasks_data = []
            for task in self.tasks:
                task_dict = asdict(task)
                task_dict['priority'] = task.priority.value
                task_dict['status'] = task.status.value
                tasks_data.append(task_dict)
            
            data = {
                'tasks': tasks_data,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.tasks_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving tasks: {e}")
    
    def add_task(self, 
                 title: str,
                 description: str,
                 task_type: str,
                 repo_name: str,
                 priority: TaskPriority = TaskPriority.MEDIUM,
                 assigned_to_mode: str = "worknight",
                 due_date: Optional[str] = None,
                 estimated_effort_hours: float = 1.0,
                 metadata: Dict[str, Any] = None,
                 dependencies: List[str] = None) -> str:
        """Add a new task to the schedule"""
        
        task_id = f"{repo_name}_{task_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        task = ScheduledTask(
            id=task_id,
            title=title,
            description=description,
            task_type=task_type,
            priority=priority,
            status=TaskStatus.PENDING,
            repo_name=repo_name,
            created_at=datetime.now().isoformat(),
            due_date=due_date,
            assigned_to_mode=assigned_to_mode,
            estimated_effort_hours=estimated_effort_hours,
            metadata=metadata or {},
            dependencies=dependencies or []
        )
        
        self.tasks.append(task)
        self.save_tasks()
        return task_id
    
    def get_tasks_for_mode(self, mode: str, repo_name: str = None) -> List[ScheduledTask]:
        """Get tasks assigned to a specific mode, optionally filtered by repo"""
        tasks = [t for t in self.tasks 
                if t.assigned_to_mode == mode and t.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]]
        
        if repo_name:
            tasks = [t for t in tasks if t.repo_name == repo_name]
        
        # Sort by priority and due date
        def sort_key(task):
            priority_order = {
                TaskPriority.URGENT: 0,
                TaskPriority.HIGH: 1, 
                TaskPriority.MEDIUM: 2,
                TaskPriority.LOW: 3
            }
            
            # If task has due date, factor that in
            due_urgency = 0
            if task.due_date:
                try:
                    due = datetime.fromisoformat(task.due_date)
                    days_until_due = (due - datetime.now()).days
                    if days_until_due < 0:
                        due_urgency = -10  # Overdue tasks get highest priority
                    elif days_until_due <= 1:
                        due_urgency = -5   # Due soon
                    elif days_until_due <= 3:
                        due_urgency = -2   # Due in a few days
                except:
                    pass
            
            return (priority_order[task.priority] + due_urgency, task.created_at)
        
        return sorted(tasks, key=sort_key)
    
    def update_task_status(self, task_id: str, status: TaskStatus, progress_note: str = None) -> bool:
        """Update the status of a task"""
        for task in self.tasks:
            if task.id == task_id:
                task.status = status
                if progress_note:
                    task.progress_notes.append(f"{datetime.now().isoformat()}: {progress_note}")
                self.save_tasks()
                return True
        return False
    
    def add_progress_note(self, task_id: str, note: str) -> bool:
        """Add a progress note to a task"""
        for task in self.tasks:
            if task.id == task_id:
                task.progress_notes.append(f"{datetime.now().isoformat()}: {note}")
                self.save_tasks()
                return True
        return False
    
    def complete_task(self, task_id: str, completion_note: str = None) -> bool:
        """Mark a task as completed"""
        return self.update_task_status(task_id, TaskStatus.COMPLETED, completion_note)
    
    def fail_task(self, task_id: str, failure_reason: str) -> bool:
        """Mark a task as failed"""
        return self.update_task_status(task_id, TaskStatus.FAILED, f"Failed: {failure_reason}")
    
    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a specific task by ID"""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None
    
    def can_start_task(self, task_id: str) -> bool:
        """Check if a task can be started (all dependencies completed)"""
        task = self.get_task(task_id)
        if not task:
            return False
        
        if not task.dependencies:
            return True
        
        for dep_id in task.dependencies:
            dep_task = self.get_task(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        
        return True
    
    def cleanup_old_tasks(self, days_old: int = 30) -> int:
        """Remove completed/cancelled tasks older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        initial_count = len(self.tasks)
        self.tasks = [
            task for task in self.tasks
            if not (task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED] and
                   datetime.fromisoformat(task.created_at) < cutoff_date)
        ]
        
        removed_count = initial_count - len(self.tasks)
        if removed_count > 0:
            self.save_tasks()
        
        return removed_count
    
    def get_task_summary(self) -> Dict[str, Any]:
        """Get a summary of all tasks"""
        total_tasks = len(self.tasks)
        status_counts = {}
        priority_counts = {}
        mode_counts = {}
        
        for task in self.tasks:
            status_counts[task.status.value] = status_counts.get(task.status.value, 0) + 1
            priority_counts[task.priority.value] = priority_counts.get(task.priority.value, 0) + 1
            mode_counts[task.assigned_to_mode] = mode_counts.get(task.assigned_to_mode, 0) + 1
        
        # Count overdue tasks
        overdue_count = 0
        for task in self.tasks:
            if task.due_date and task.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]:
                try:
                    due = datetime.fromisoformat(task.due_date)
                    if due < datetime.now():
                        overdue_count += 1
                except:
                    pass
        
        return {
            'total_tasks': total_tasks,
            'status_breakdown': status_counts,
            'priority_breakdown': priority_counts,
            'mode_breakdown': mode_counts,
            'overdue_tasks': overdue_count
        }


def create_pr_implementation_task(scheduler: TaskScheduler, 
                                  repo_name: str,
                                  pr_number: int,
                                  pr_title: str,
                                  implementation_request: str,
                                  priority: TaskPriority = TaskPriority.MEDIUM,
                                  due_date: str = None) -> str:
    """Convenience function to create a PR implementation task"""
    
    return scheduler.add_task(
        title=f"Implement PR #{pr_number} request",
        description=f"Implement requested changes in PR '{pr_title}': {implementation_request}",
        task_type="pr_implementation",
        repo_name=repo_name,
        priority=priority,
        due_date=due_date,
        metadata={
            'pr_number': pr_number,
            'pr_title': pr_title,
            'implementation_request': implementation_request
        }
    )


def create_branch_rebase_task(scheduler: TaskScheduler,
                              repo_name: str,
                              branch_name: str,
                              priority: TaskPriority = TaskPriority.LOW) -> str:
    """Convenience function to create a branch rebase task"""
    
    return scheduler.add_task(
        title=f"Rebase branch {branch_name}",
        description=f"Rebase {branch_name} from main branch and resolve any conflicts",
        task_type="branch_rebase",
        repo_name=repo_name,
        priority=priority,
        estimated_effort_hours=0.5,
        metadata={
            'branch_name': branch_name,
            'base_branch': 'main'
        }
    )


def create_issue_implementation_task(scheduler: TaskScheduler,
                                     repo_name: str,
                                     issue_number: int,
                                     issue_title: str,
                                     priority: TaskPriority = TaskPriority.MEDIUM,
                                     due_date: str = None,
                                     estimated_hours: float = 2.0) -> str:
    """Convenience function to create an issue implementation task"""
    
    return scheduler.add_task(
        title=f"Implement Issue #{issue_number}",
        description=f"Implement solution for issue '{issue_title}'",
        task_type="issue_implementation",
        repo_name=repo_name,
        priority=priority,
        due_date=due_date,
        estimated_effort_hours=estimated_hours,
        metadata={
            'issue_number': issue_number,
            'issue_title': issue_title
        }
    )