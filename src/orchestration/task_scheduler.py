"""
Intelligent task scheduler with priority-based and resource-aware scheduling.

This module provides advanced task scheduling capabilities including priority queues,
resource allocation, load balancing, and intelligent scheduling algorithms.
"""

import asyncio
import heapq
import time
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field

from core.interfaces import TaskDefinition, ExecutionResult, TaskStatus, ITaskExecutor
from core.exceptions import SchedulingError, ResourceError, ValidationError
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id
from src.orchestration.dependency_graph import TaskNode, TaskPriority


class SchedulingStrategy(str, Enum):
    """Task scheduling strategies."""
    FIFO = "fifo"  # First In, First Out
    PRIORITY = "priority"  # Priority-based scheduling
    SHORTEST_JOB_FIRST = "shortest_job_first"  # Shortest estimated time first
    ROUND_ROBIN = "round_robin"  # Round-robin scheduling
    RESOURCE_AWARE = "resource_aware"  # Resource availability-based
    INTELLIGENT = "intelligent"  # AI-powered scheduling


class TaskState(str, Enum):
    """Task states in the scheduler."""
    QUEUED = "queued"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_DEPENDENCIES = "waiting_dependencies"


@dataclass
class ScheduledTask:
    """Represents a task in the scheduler."""
    task_id: str
    task_definition: TaskDefinition
    priority: TaskPriority
    estimated_duration: float
    dependencies: Set[str]
    resource_requirements: Dict[str, Any]
    scheduled_time: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    state: TaskState = TaskState.QUEUED
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __lt__(self, other):
        """Comparison for priority queue (higher priority first)."""
        if self.priority != other.priority:
            return self.priority.value > other.priority.value
        return self.estimated_duration < other.estimated_duration


@dataclass
class ResourcePool:
    """Represents available resources for task execution."""
    max_concurrent_tasks: int
    available_memory: float  # GB
    available_cpu: float  # CPU cores
    available_browsers: int
    custom_resources: Dict[str, Any] = field(default_factory=dict)
    
    def can_allocate(self, requirements: Dict[str, Any]) -> bool:
        """Check if resources can be allocated for a task."""
        required_memory = requirements.get("memory", 0.5)
        required_cpu = requirements.get("cpu", 0.5)
        required_browsers = requirements.get("browsers", 1)
        
        return (
            required_memory <= self.available_memory and
            required_cpu <= self.available_cpu and
            required_browsers <= self.available_browsers
        )
    
    def allocate(self, requirements: Dict[str, Any]) -> None:
        """Allocate resources for a task."""
        self.available_memory -= requirements.get("memory", 0.5)
        self.available_cpu -= requirements.get("cpu", 0.5)
        self.available_browsers -= requirements.get("browsers", 1)
    
    def deallocate(self, requirements: Dict[str, Any]) -> None:
        """Deallocate resources after task completion."""
        self.available_memory += requirements.get("memory", 0.5)
        self.available_cpu += requirements.get("cpu", 0.5)
        self.available_browsers += requirements.get("browsers", 1)


class TaskScheduler:
    """
    Intelligent task scheduler with multiple scheduling strategies.
    
    This scheduler provides:
    - Priority-based task scheduling
    - Resource-aware allocation
    - Dependency management
    - Load balancing
    - Performance optimization
    """
    
    def __init__(
        self,
        strategy: SchedulingStrategy = SchedulingStrategy.INTELLIGENT,
        resource_pool: Optional[ResourcePool] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the task scheduler.
        
        Args:
            strategy: Scheduling strategy to use
            resource_pool: Available resources for task execution
            config: Additional configuration options
        """
        self.strategy = strategy
        self.resource_pool = resource_pool or ResourcePool(
            max_concurrent_tasks=5,
            available_memory=8.0,
            available_cpu=4.0,
            available_browsers=3
        )
        self.config = config or {}
        
        # Task queues and tracking
        self.task_queue: List[ScheduledTask] = []
        self.running_tasks: Dict[str, ScheduledTask] = {}
        self.completed_tasks: Dict[str, ScheduledTask] = {}
        self.failed_tasks: Dict[str, ScheduledTask] = {}
        
        # Scheduling state
        self.is_running = False
        self.scheduler_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.total_scheduled = 0
        self.total_completed = 0
        self.total_failed = 0
        self.average_wait_time = 0.0
        self.average_execution_time = 0.0
        
        # Initialize logger
        self.logger = StructuredLogger("task_scheduler")
        
        self.logger.info(
            "Task scheduler initialized",
            strategy=strategy.value,
            max_concurrent_tasks=self.resource_pool.max_concurrent_tasks,
            available_memory=self.resource_pool.available_memory,
            available_cpu=self.resource_pool.available_cpu
        )
    
    async def start(self) -> None:
        """Start the task scheduler."""
        if self.is_running:
            self.logger.warning("Task scheduler is already running")
            return
        
        self.is_running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        self.logger.info("Task scheduler started")
    
    async def stop(self) -> None:
        """Stop the task scheduler."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Task scheduler stopped")
    
    @with_correlation_id
    async def schedule_task(
        self,
        task_definition: TaskDefinition,
        priority: TaskPriority = TaskPriority.MEDIUM,
        dependencies: Optional[Set[str]] = None,
        resource_requirements: Optional[Dict[str, Any]] = None,
        estimated_duration: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Schedule a task for execution.
        
        Args:
            task_definition: Definition of the task to schedule
            priority: Task priority level
            dependencies: Set of task IDs this task depends on
            resource_requirements: Resource requirements for the task
            estimated_duration: Estimated execution time in seconds
            **kwargs: Additional metadata
            
        Returns:
            Task ID for tracking
            
        Raises:
            SchedulingError: If task cannot be scheduled
        """
        task_id = kwargs.get("task_id", f"task_{int(time.time() * 1000)}")
        correlation_id = kwargs.get("correlation_id", task_id)
        
        self.logger.info(
            "Scheduling task",
            task_id=task_id,
            task_name=task_definition.name,
            priority=priority.value,
            dependencies=list(dependencies) if dependencies else [],
            correlation_id=correlation_id
        )
        
        try:
            # Validate dependencies
            if dependencies:
                await self._validate_dependencies(dependencies)
            
            # Estimate duration if not provided
            if estimated_duration is None:
                estimated_duration = self._estimate_task_duration(task_definition)
            
            # Set default resource requirements
            if resource_requirements is None:
                resource_requirements = self._get_default_resource_requirements(task_definition)
            
            # Create scheduled task
            scheduled_task = ScheduledTask(
                task_id=task_id,
                task_definition=task_definition,
                priority=priority,
                estimated_duration=estimated_duration,
                dependencies=dependencies or set(),
                resource_requirements=resource_requirements,
                metadata=kwargs
            )
            
            # Add to appropriate queue based on dependencies
            if dependencies and not self._dependencies_satisfied(dependencies):
                scheduled_task.state = TaskState.WAITING_DEPENDENCIES
            else:
                scheduled_task.state = TaskState.QUEUED
                self._add_to_queue(scheduled_task)
            
            self.total_scheduled += 1
            
            self.logger.info(
                "Task scheduled successfully",
                task_id=task_id,
                state=scheduled_task.state.value,
                queue_size=len(self.task_queue),
                correlation_id=correlation_id
            )
            
            return task_id
            
        except Exception as e:
            self.logger.error(
                "Failed to schedule task",
                task_id=task_id,
                error=str(e),
                correlation_id=correlation_id
            )
            raise SchedulingError(f"Failed to schedule task {task_id}: {e}") from e
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a scheduled or running task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if task was cancelled successfully
        """
        try:
            # Check if task is in queue
            for i, task in enumerate(self.task_queue):
                if task.task_id == task_id:
                    task.state = TaskState.CANCELLED
                    self.task_queue.pop(i)
                    self.failed_tasks[task_id] = task
                    
                    self.logger.info("Task cancelled from queue", task_id=task_id)
                    return True
            
            # Check if task is running
            if task_id in self.running_tasks:
                task = self.running_tasks[task_id]
                task.state = TaskState.CANCELLED
                # Note: Actual task cancellation would need to be handled by the executor
                
                self.logger.info("Task marked for cancellation", task_id=task_id)
                return True
            
            self.logger.warning("Task not found for cancellation", task_id=task_id)
            return False
            
        except Exception as e:
            self.logger.error(
                "Failed to cancel task",
                task_id=task_id,
                error=str(e)
            )
            return False
    
    def get_task_status(self, task_id: str) -> Optional[TaskState]:
        """Get the current status of a task."""
        # Check running tasks
        if task_id in self.running_tasks:
            return self.running_tasks[task_id].state
        
        # Check completed tasks
        if task_id in self.completed_tasks:
            return TaskState.COMPLETED
        
        # Check failed tasks
        if task_id in self.failed_tasks:
            return self.failed_tasks[task_id].state
        
        # Check queued tasks
        for task in self.task_queue:
            if task.task_id == task_id:
                return task.state
        
        return None
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status and statistics."""
        return {
            "queued_tasks": len(self.task_queue),
            "running_tasks": len(self.running_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "total_scheduled": self.total_scheduled,
            "total_completed": self.total_completed,
            "total_failed": self.total_failed,
            "success_rate": self.total_completed / max(1, self.total_scheduled),
            "average_wait_time": self.average_wait_time,
            "average_execution_time": self.average_execution_time,
            "resource_utilization": {
                "memory_used": self.resource_pool.available_memory,
                "cpu_used": self.resource_pool.available_cpu,
                "browsers_used": self.resource_pool.available_browsers
            },
            "strategy": self.strategy.value,
            "is_running": self.is_running
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the task scheduler."""
        try:
            queue_status = self.get_queue_status()
            
            return {
                "status": "healthy" if self.is_running else "stopped",
                "scheduler": "task_scheduler",
                "queue_status": queue_status,
                "resource_pool": {
                    "max_concurrent_tasks": self.resource_pool.max_concurrent_tasks,
                    "available_memory": self.resource_pool.available_memory,
                    "available_cpu": self.resource_pool.available_cpu,
                    "available_browsers": self.resource_pool.available_browsers
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "scheduler": "task_scheduler",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    # Private helper methods

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop that processes tasks."""
        while self.is_running:
            try:
                await self._process_queue()
                await asyncio.sleep(0.1)  # Small delay to prevent busy waiting

            except Exception as e:
                self.logger.error("Error in scheduler loop", error=str(e))
                await asyncio.sleep(1)  # Longer delay on error

    async def _process_queue(self) -> None:
        """Process tasks in the queue based on scheduling strategy."""
        if not self.task_queue:
            return

        # Check if we can schedule more tasks
        if len(self.running_tasks) >= self.resource_pool.max_concurrent_tasks:
            return

        # Sort queue based on strategy
        if self.strategy == SchedulingStrategy.PRIORITY:
            self.task_queue.sort(key=lambda t: (-t.priority.value, t.estimated_duration))
        elif self.strategy == SchedulingStrategy.SHORTEST_JOB_FIRST:
            self.task_queue.sort(key=lambda t: t.estimated_duration)
        elif self.strategy == SchedulingStrategy.INTELLIGENT:
            self._intelligent_sort()

        # Try to schedule tasks
        tasks_to_remove = []
        for i, task in enumerate(self.task_queue):
            if len(self.running_tasks) >= self.resource_pool.max_concurrent_tasks:
                break

            # Check dependencies
            if not self._dependencies_satisfied(task.dependencies):
                continue

            # Check resource availability
            if not self.resource_pool.can_allocate(task.resource_requirements):
                continue

            # Schedule the task
            await self._schedule_task_for_execution(task)
            tasks_to_remove.append(i)

        # Remove scheduled tasks from queue (in reverse order to maintain indices)
        for i in reversed(tasks_to_remove):
            self.task_queue.pop(i)

    async def _schedule_task_for_execution(self, task: ScheduledTask) -> None:
        """Schedule a task for immediate execution."""
        try:
            # Allocate resources
            self.resource_pool.allocate(task.resource_requirements)

            # Update task state
            task.state = TaskState.SCHEDULED
            task.scheduled_time = datetime.now(timezone.utc)

            # Move to running tasks
            self.running_tasks[task.task_id] = task

            self.logger.info(
                "Task scheduled for execution",
                task_id=task.task_id,
                priority=task.priority.value,
                estimated_duration=task.estimated_duration
            )

        except Exception as e:
            self.logger.error(
                "Failed to schedule task for execution",
                task_id=task.task_id,
                error=str(e)
            )
            task.state = TaskState.FAILED
            self.failed_tasks[task.task_id] = task

    def _add_to_queue(self, task: ScheduledTask) -> None:
        """Add a task to the appropriate queue."""
        if self.strategy == SchedulingStrategy.PRIORITY:
            heapq.heappush(self.task_queue, task)
        else:
            self.task_queue.append(task)

    async def _validate_dependencies(self, dependencies: Set[str]) -> None:
        """Validate that dependencies exist and are valid."""
        for dep_id in dependencies:
            if dep_id not in self.completed_tasks and dep_id not in self.running_tasks:
                # Check if dependency is in queue
                found = any(task.task_id == dep_id for task in self.task_queue)
                if not found:
                    raise ValidationError(f"Dependency task {dep_id} not found")

    def _dependencies_satisfied(self, dependencies: Set[str]) -> bool:
        """Check if all dependencies are satisfied (completed)."""
        return all(dep_id in self.completed_tasks for dep_id in dependencies)

    def _estimate_task_duration(self, task_definition: TaskDefinition) -> float:
        """Estimate task execution duration based on historical data."""
        # Simple estimation based on task timeout
        # In a real implementation, this could use ML models or historical data
        base_duration = task_definition.timeout / 4  # Assume 25% of timeout

        # Adjust based on task complexity (simple heuristic)
        complexity_factor = len(task_definition.prompt_template) / 1000
        estimated = base_duration * (1 + complexity_factor)

        return min(estimated, task_definition.timeout * 0.8)  # Cap at 80% of timeout

    def _get_default_resource_requirements(self, task_definition: TaskDefinition) -> Dict[str, Any]:
        """Get default resource requirements for a task."""
        return {
            "memory": 0.5,  # GB
            "cpu": 0.5,     # CPU cores
            "browsers": 1,  # Browser instances
            "network": "standard"
        }

    def _intelligent_sort(self) -> None:
        """Intelligent sorting algorithm that considers multiple factors."""
        def score_task(task: ScheduledTask) -> float:
            # Multi-factor scoring
            priority_score = task.priority.value * 10
            duration_score = 1.0 / (task.estimated_duration + 1)  # Prefer shorter tasks
            wait_time_score = time.time() - task.metadata.get("created_at", time.time())

            # Combine scores with weights
            total_score = (
                priority_score * 0.5 +
                duration_score * 0.3 +
                wait_time_score * 0.2
            )

            return total_score

        self.task_queue.sort(key=score_task, reverse=True)


# Factory function for easy scheduler creation
def create_task_scheduler(
    strategy: SchedulingStrategy = SchedulingStrategy.INTELLIGENT,
    max_concurrent_tasks: int = 5,
    available_memory: float = 8.0,
    available_cpu: float = 4.0,
    available_browsers: int = 3,
    config: Optional[Dict[str, Any]] = None
) -> TaskScheduler:
    """
    Factory function to create a task scheduler with specified resources.

    Args:
        strategy: Scheduling strategy to use
        max_concurrent_tasks: Maximum number of concurrent tasks
        available_memory: Available memory in GB
        available_cpu: Available CPU cores
        available_browsers: Available browser instances
        config: Additional configuration

    Returns:
        Configured TaskScheduler instance
    """
    resource_pool = ResourcePool(
        max_concurrent_tasks=max_concurrent_tasks,
        available_memory=available_memory,
        available_cpu=available_cpu,
        available_browsers=available_browsers
    )

    return TaskScheduler(
        strategy=strategy,
        resource_pool=resource_pool,
        config=config or {}
    )
