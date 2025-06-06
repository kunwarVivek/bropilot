"""
Parallel task execution with proper synchronization.

This module provides comprehensive parallel execution capabilities with
resource management, load balancing, and proper synchronization.
"""

import asyncio
import time
from typing import Dict, List, Set, Optional, Any, Callable, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import uuid

from core.interfaces import TaskStatus, ITaskExecutor
from core.exceptions import ExecutionError, ResourceError, ConcurrencyError
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id
from src.infrastructure.reliability.retry import retry_manager, RetryConfig
from src.infrastructure.reliability.timeout import timeout_manager, TimeoutConfig
from .dependency_graph import DependencyGraph, TaskNode, TaskPriority


class ExecutionMode(str, Enum):
    """Execution mode enumeration."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HYBRID = "hybrid"  # Mix of sequential and parallel


class ResourceType(str, Enum):
    """Resource type enumeration."""
    BROWSER = "browser"
    DATABASE = "database"
    API_CLIENT = "api_client"
    FILE_HANDLE = "file_handle"
    MEMORY = "memory"
    CPU = "cpu"


@dataclass
class ExecutionConfig:
    """Configuration for parallel execution."""
    max_parallel_tasks: int = 5
    max_workers: int = 10
    execution_mode: ExecutionMode = ExecutionMode.HYBRID
    resource_limits: Dict[str, int] = field(default_factory=dict)
    task_timeout: float = 300.0  # 5 minutes default
    retry_config: Optional[RetryConfig] = None
    enable_load_balancing: bool = True
    worker_pool_type: str = "thread"  # "thread" or "process"


@dataclass
class ExecutionResult:
    """Result of task execution."""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    execution_time: float = 0.0
    retry_count: int = 0
    worker_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


@dataclass
class WorkerInfo:
    """Information about a worker."""
    worker_id: str
    worker_type: str
    is_busy: bool = False
    current_task: Optional[str] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_execution_time: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)


class ParallelExecutor:
    """Parallel task executor with resource management and load balancing."""
    
    def __init__(self, config: ExecutionConfig):
        """Initialize parallel executor."""
        self.config = config
        self.logger = StructuredLogger("parallel_executor")
        
        # Execution state
        self.dependency_graph: Optional[DependencyGraph] = None
        self.execution_results: Dict[str, ExecutionResult] = {}
        self.active_tasks: Dict[str, asyncio.Task] = {}
        
        # Worker management
        self.workers: Dict[str, WorkerInfo] = {}
        self.worker_semaphore = asyncio.Semaphore(config.max_parallel_tasks)
        
        # Resource management
        self.resource_pools: Dict[str, asyncio.Semaphore] = {}
        self.resource_usage: Dict[str, Set[str]] = {}  # resource -> task_ids
        
        # Load balancing
        self.task_queue = asyncio.Queue()
        self.worker_load: Dict[str, float] = {}
        
        # Synchronization
        self.execution_lock = asyncio.Lock()
        self.completion_event = asyncio.Event()
        
        # Statistics
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.total_tasks_executed = 0
        self.total_tasks_failed = 0
        
        # Initialize resource pools
        self._initialize_resource_pools()
    
    def _initialize_resource_pools(self) -> None:
        """Initialize resource pools based on configuration."""
        for resource_type, limit in self.config.resource_limits.items():
            self.resource_pools[resource_type] = asyncio.Semaphore(limit)
            self.resource_usage[resource_type] = set()
        
        self.logger.info(
            "Resource pools initialized",
            resource_limits=self.config.resource_limits
        )
    
    async def execute_graph(
        self,
        dependency_graph: DependencyGraph,
        task_executor: ITaskExecutor
    ) -> Dict[str, ExecutionResult]:
        """Execute a dependency graph with parallel execution."""
        
        self.dependency_graph = dependency_graph
        self.start_time = datetime.utcnow()
        
        self.logger.info(
            "Starting parallel execution",
            graph_id=dependency_graph.graph_id,
            total_tasks=len(dependency_graph.nodes),
            max_parallel_tasks=self.config.max_parallel_tasks,
            execution_mode=self.config.execution_mode.value
        )
        
        try:
            # Validate and compute execution order
            dependency_graph.validate_graph()
            dependency_graph.compute_execution_order()
            
            # Execute based on mode
            if self.config.execution_mode == ExecutionMode.SEQUENTIAL:
                await self._execute_sequential(task_executor)
            elif self.config.execution_mode == ExecutionMode.PARALLEL:
                await self._execute_parallel(task_executor)
            else:  # HYBRID
                await self._execute_hybrid(task_executor)
            
            self.end_time = datetime.utcnow()
            
            # Generate execution summary
            self._log_execution_summary()
            
            return self.execution_results
            
        except Exception as e:
            self.logger.error(
                "Parallel execution failed",
                error=str(e),
                graph_id=dependency_graph.graph_id
            )
            raise ExecutionError(f"Parallel execution failed: {e}") from e
    
    async def _execute_sequential(self, task_executor: ITaskExecutor) -> None:
        """Execute tasks sequentially."""
        
        for group in self.dependency_graph.execution_order:
            for task_id in group:
                await self._execute_single_task(task_id, task_executor)
    
    async def _execute_parallel(self, task_executor: ITaskExecutor) -> None:
        """Execute tasks with maximum parallelism."""
        
        # Start worker tasks
        worker_tasks = []
        for i in range(self.config.max_parallel_tasks):
            worker_id = f"worker_{i}"
            worker_info = WorkerInfo(
                worker_id=worker_id,
                worker_type=self.config.worker_pool_type
            )
            self.workers[worker_id] = worker_info
            
            task = asyncio.create_task(
                self._worker_loop(worker_id, task_executor)
            )
            worker_tasks.append(task)
        
        # Queue all ready tasks
        await self._queue_ready_tasks()
        
        # Wait for all tasks to complete
        await self._wait_for_completion()
        
        # Cancel worker tasks
        for task in worker_tasks:
            task.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*worker_tasks, return_exceptions=True)
    
    async def _execute_hybrid(self, task_executor: ITaskExecutor) -> None:
        """Execute tasks with hybrid approach (parallel groups, sequential between groups)."""
        
        for group_index, group in enumerate(self.dependency_graph.execution_order):
            self.logger.info(
                "Executing parallel group",
                group_index=group_index,
                group_size=len(group),
                tasks=group
            )
            
            # Execute group in parallel
            group_tasks = []
            for task_id in group:
                if self._can_execute_task(task_id):
                    task = asyncio.create_task(
                        self._execute_single_task(task_id, task_executor)
                    )
                    group_tasks.append(task)
            
            # Wait for all tasks in the group to complete
            if group_tasks:
                await asyncio.gather(*group_tasks, return_exceptions=True)
            
            # Check if we should continue
            if not self._should_continue_execution():
                break
    
    async def _worker_loop(self, worker_id: str, task_executor: ITaskExecutor) -> None:
        """Worker loop for processing tasks from the queue."""
        
        worker_info = self.workers[worker_id]
        
        self.logger.debug(
            "Worker started",
            worker_id=worker_id
        )
        
        try:
            while True:
                try:
                    # Get next task from queue
                    task_id = await asyncio.wait_for(
                        self.task_queue.get(),
                        timeout=1.0
                    )
                    
                    if task_id is None:  # Shutdown signal
                        break
                    
                    # Execute task
                    worker_info.is_busy = True
                    worker_info.current_task = task_id
                    worker_info.last_activity = datetime.utcnow()
                    
                    await self._execute_single_task(task_id, task_executor, worker_id)
                    
                    worker_info.tasks_completed += 1
                    worker_info.is_busy = False
                    worker_info.current_task = None
                    
                    # Queue new ready tasks
                    await self._queue_ready_tasks()
                    
                except asyncio.TimeoutError:
                    # No tasks available, continue waiting
                    continue
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.error(
                        "Worker error",
                        worker_id=worker_id,
                        error=str(e)
                    )
                    worker_info.tasks_failed += 1
                    worker_info.is_busy = False
                    worker_info.current_task = None
        
        finally:
            self.logger.debug(
                "Worker stopped",
                worker_id=worker_id,
                tasks_completed=worker_info.tasks_completed,
                tasks_failed=worker_info.tasks_failed
            )
    
    async def _execute_single_task(
        self,
        task_id: str,
        task_executor: ITaskExecutor,
        worker_id: Optional[str] = None
    ) -> ExecutionResult:
        """Execute a single task with proper resource management."""
        
        task_node = self.dependency_graph.nodes[task_id]
        start_time = datetime.utcnow()
        
        self.logger.info(
            "Executing task",
            task_id=task_id,
            task_name=task_node.task_name,
            worker_id=worker_id,
            priority=task_node.priority.value
        )
        
        # Acquire worker semaphore
        async with self.worker_semaphore:
            try:
                # Acquire required resources
                await self._acquire_task_resources(task_id)
                
                # Mark task as running
                self.dependency_graph.mark_task_running(task_id)
                
                # Execute task with timeout and retry
                result = await self._execute_task_with_resilience(
                    task_id, task_executor, task_node
                )
                
                # Mark task as completed
                self.dependency_graph.mark_task_completed(task_id, result)
                
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                
                execution_result = ExecutionResult(
                    task_id=task_id,
                    success=True,
                    result=result,
                    execution_time=execution_time,
                    worker_id=worker_id,
                    start_time=start_time,
                    end_time=datetime.utcnow()
                )
                
                self.execution_results[task_id] = execution_result
                self.total_tasks_executed += 1
                
                self.logger.info(
                    "Task completed successfully",
                    task_id=task_id,
                    execution_time=execution_time,
                    worker_id=worker_id
                )
                
                return execution_result
                
            except Exception as e:
                # Mark task as failed
                self.dependency_graph.mark_task_failed(task_id, e)
                
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                
                execution_result = ExecutionResult(
                    task_id=task_id,
                    success=False,
                    error=e,
                    execution_time=execution_time,
                    worker_id=worker_id,
                    start_time=start_time,
                    end_time=datetime.utcnow()
                )
                
                self.execution_results[task_id] = execution_result
                self.total_tasks_failed += 1
                
                self.logger.error(
                    "Task execution failed",
                    task_id=task_id,
                    error=str(e),
                    execution_time=execution_time,
                    worker_id=worker_id
                )
                
                return execution_result
                
            finally:
                # Release resources
                await self._release_task_resources(task_id)
    
    async def _execute_task_with_resilience(
        self,
        task_id: str,
        task_executor: ITaskExecutor,
        task_node: TaskNode
    ) -> Any:
        """Execute task with timeout and retry mechanisms."""
        
        # Configure timeout
        timeout_config = TimeoutConfig(
            timeout_seconds=task_node.timeout or self.config.task_timeout
        )
        
        # Configure retry
        retry_config = self.config.retry_config or RetryConfig(
            max_attempts=task_node.max_retries + 1
        )
        
        async def execute_task():
            return await task_executor.execute_task(
                task_node.task_definition,
                context={"task_id": task_id, "task_name": task_node.task_name}
            )
        
        # Execute with timeout
        timeout_result = await timeout_manager.execute_with_timeout(
            execute_task,
            timeout_config,
            f"task_{task_id}"
        )
        
        if timeout_result.success:
            return timeout_result.result
        else:
            raise timeout_result.exception
    
    async def _acquire_task_resources(self, task_id: str) -> None:
        """Acquire resources required by a task."""
        
        task_node = self.dependency_graph.nodes[task_id]
        acquired_resources = []
        
        try:
            for resource in task_node.resources_required:
                if resource in self.resource_pools:
                    await self.resource_pools[resource].acquire()
                    acquired_resources.append(resource)
                    self.resource_usage[resource].add(task_id)
                    
                    self.logger.debug(
                        "Resource acquired",
                        task_id=task_id,
                        resource=resource
                    )
        
        except Exception as e:
            # Release any acquired resources
            for resource in acquired_resources:
                self.resource_pools[resource].release()
                self.resource_usage[resource].discard(task_id)
            
            raise ResourceError(f"Failed to acquire resources for task {task_id}: {e}") from e
    
    async def _release_task_resources(self, task_id: str) -> None:
        """Release resources used by a task."""
        
        task_node = self.dependency_graph.nodes[task_id]
        
        for resource in task_node.resources_required:
            if resource in self.resource_pools:
                self.resource_pools[resource].release()
                self.resource_usage[resource].discard(task_id)
                
                self.logger.debug(
                    "Resource released",
                    task_id=task_id,
                    resource=resource
                )
    
    def _can_execute_task(self, task_id: str) -> bool:
        """Check if a task can be executed."""
        
        task_node = self.dependency_graph.nodes[task_id]
        
        # Check task status
        if task_node.status != TaskStatus.PENDING:
            return False
        
        # Check dependencies
        ready_tasks = self.dependency_graph.get_ready_tasks()
        if task_id not in ready_tasks:
            return False
        
        # Check resource availability
        if not self.dependency_graph.can_allocate_resources(task_id):
            return False
        
        return True
    
    async def _queue_ready_tasks(self) -> None:
        """Queue tasks that are ready for execution."""
        
        ready_tasks = self.dependency_graph.get_ready_tasks()
        
        for task_id in ready_tasks:
            if task_id not in self.execution_results:  # Not already executed
                await self.task_queue.put(task_id)
                
                self.logger.debug(
                    "Task queued for execution",
                    task_id=task_id
                )
    
    async def _wait_for_completion(self) -> None:
        """Wait for all tasks to complete."""
        
        while True:
            # Check if all tasks are completed
            total_tasks = len(self.dependency_graph.nodes)
            completed_tasks = len(self.dependency_graph.completed_tasks)
            failed_tasks = len(self.dependency_graph.failed_tasks)
            
            if completed_tasks + failed_tasks >= total_tasks:
                break
            
            # Check if there are any running tasks or queued tasks
            running_tasks = len(self.dependency_graph.running_tasks)
            queue_size = self.task_queue.qsize()
            
            if running_tasks == 0 and queue_size == 0:
                # No more tasks to execute
                break
            
            await asyncio.sleep(0.1)
        
        # Signal workers to stop
        for _ in range(self.config.max_parallel_tasks):
            await self.task_queue.put(None)
    
    def _should_continue_execution(self) -> bool:
        """Check if execution should continue."""
        
        # Continue if there are pending tasks and no critical failures
        pending_tasks = [
            task_id for task_id, task_node in self.dependency_graph.nodes.items()
            if task_node.status == TaskStatus.PENDING
        ]
        
        return len(pending_tasks) > 0
    
    def _log_execution_summary(self) -> None:
        """Log execution summary."""
        
        if not self.start_time or not self.end_time:
            return
        
        total_execution_time = (self.end_time - self.start_time).total_seconds()
        total_tasks = len(self.dependency_graph.nodes)
        
        self.logger.info(
            "Parallel execution completed",
            total_tasks=total_tasks,
            completed_tasks=self.total_tasks_executed,
            failed_tasks=self.total_tasks_failed,
            success_rate=self.total_tasks_executed / total_tasks if total_tasks > 0 else 0,
            total_execution_time=total_execution_time,
            average_task_time=total_execution_time / total_tasks if total_tasks > 0 else 0,
            max_parallel_tasks=self.config.max_parallel_tasks
        )
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """Get detailed execution statistics."""
        
        if not self.start_time:
            return {"status": "not_started"}
        
        total_execution_time = 0
        if self.end_time:
            total_execution_time = (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            total_execution_time = (datetime.utcnow() - self.start_time).total_seconds()
        
        total_tasks = len(self.dependency_graph.nodes) if self.dependency_graph else 0
        
        # Worker statistics
        worker_stats = {}
        for worker_id, worker_info in self.workers.items():
            worker_stats[worker_id] = {
                "tasks_completed": worker_info.tasks_completed,
                "tasks_failed": worker_info.tasks_failed,
                "is_busy": worker_info.is_busy,
                "current_task": worker_info.current_task,
                "total_execution_time": worker_info.total_execution_time
            }
        
        # Resource usage statistics
        resource_stats = {}
        for resource, usage in self.resource_usage.items():
            resource_stats[resource] = {
                "current_usage": len(usage),
                "max_capacity": self.resource_pools[resource]._value if resource in self.resource_pools else 0,
                "utilization": len(usage) / self.resource_pools[resource]._value if resource in self.resource_pools and self.resource_pools[resource]._value > 0 else 0
            }
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": self.total_tasks_executed,
            "failed_tasks": self.total_tasks_failed,
            "success_rate": self.total_tasks_executed / total_tasks if total_tasks > 0 else 0,
            "total_execution_time": total_execution_time,
            "average_task_time": total_execution_time / total_tasks if total_tasks > 0 else 0,
            "execution_mode": self.config.execution_mode.value,
            "max_parallel_tasks": self.config.max_parallel_tasks,
            "worker_statistics": worker_stats,
            "resource_statistics": resource_stats,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "is_running": self.end_time is None and self.start_time is not None
        }
