"""
Task dependency graph system.

This module provides a comprehensive dependency graph system for managing
task execution order, parallel execution, and dependency resolution.
"""

import asyncio
from typing import Dict, List, Set, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict, deque
import uuid

from core.interfaces import TaskStatus
from core.exceptions import DependencyError, ValidationError
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id


class DependencyType(str, Enum):
    """Dependency type enumeration."""
    HARD = "hard"          # Must complete successfully
    SOFT = "soft"          # Can fail without blocking dependents
    CONDITIONAL = "conditional"  # Depends on condition evaluation
    RESOURCE = "resource"  # Resource dependency (shared resources)


class TaskPriority(str, Enum):
    """Task priority enumeration."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TaskNode:
    """Represents a task node in the dependency graph."""
    task_id: str
    task_name: str
    task_definition: Dict[str, Any]
    priority: TaskPriority = TaskPriority.NORMAL
    estimated_duration: Optional[float] = None
    max_retries: int = 3
    timeout: Optional[float] = None
    resources_required: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Execution state
    status: TaskStatus = TaskStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[Exception] = None
    retry_count: int = 0


@dataclass
class Dependency:
    """Represents a dependency between tasks."""
    from_task: str
    to_task: str
    dependency_type: DependencyType = DependencyType.HARD
    condition: Optional[str] = None  # Condition for conditional dependencies
    metadata: Dict[str, Any] = field(default_factory=dict)


class DependencyGraph:
    """Task dependency graph with topological sorting and parallel execution support."""
    
    def __init__(self, graph_id: Optional[str] = None):
        """Initialize dependency graph."""
        self.graph_id = graph_id or str(uuid.uuid4())
        self.logger = StructuredLogger(f"dependency_graph.{self.graph_id}")
        
        # Graph structure
        self.nodes: Dict[str, TaskNode] = {}
        self.dependencies: List[Dependency] = []
        self.adjacency_list: Dict[str, List[str]] = defaultdict(list)
        self.reverse_adjacency_list: Dict[str, List[str]] = defaultdict(list)
        
        # Execution tracking
        self.execution_order: List[List[str]] = []  # List of parallel execution groups
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self.running_tasks: Set[str] = set()
        
        # Resource tracking
        self.resource_usage: Dict[str, Set[str]] = defaultdict(set)  # resource -> tasks using it
        self.available_resources: Set[str] = set()
    
    def add_task(self, task_node: TaskNode) -> None:
        """Add a task node to the graph."""
        if task_node.task_id in self.nodes:
            raise ValidationError(f"Task {task_node.task_id} already exists in graph")
        
        self.nodes[task_node.task_id] = task_node
        
        # Track required resources
        for resource in task_node.resources_required:
            self.available_resources.add(resource)
        
        self.logger.debug(
            "Task added to dependency graph",
            task_id=task_node.task_id,
            task_name=task_node.task_name,
            priority=task_node.priority.value,
            resources_required=task_node.resources_required
        )
    
    def add_dependency(self, dependency: Dependency) -> None:
        """Add a dependency between tasks."""
        # Validate that both tasks exist
        if dependency.from_task not in self.nodes:
            raise ValidationError(f"Source task {dependency.from_task} not found")
        if dependency.to_task not in self.nodes:
            raise ValidationError(f"Target task {dependency.to_task} not found")
        
        # Check for self-dependency
        if dependency.from_task == dependency.to_task:
            raise ValidationError(f"Task cannot depend on itself: {dependency.from_task}")
        
        self.dependencies.append(dependency)
        self.adjacency_list[dependency.from_task].append(dependency.to_task)
        self.reverse_adjacency_list[dependency.to_task].append(dependency.from_task)
        
        self.logger.debug(
            "Dependency added",
            from_task=dependency.from_task,
            to_task=dependency.to_task,
            dependency_type=dependency.dependency_type.value
        )
    
    def validate_graph(self) -> bool:
        """Validate the dependency graph for cycles and other issues."""
        # Check for cycles using DFS
        if self._has_cycle():
            raise DependencyError("Circular dependency detected in task graph")
        
        # Validate resource dependencies
        self._validate_resource_dependencies()
        
        # Validate conditional dependencies
        self._validate_conditional_dependencies()
        
        self.logger.info(
            "Dependency graph validated successfully",
            task_count=len(self.nodes),
            dependency_count=len(self.dependencies)
        )
        
        return True
    
    def _has_cycle(self) -> bool:
        """Check for cycles in the dependency graph using DFS."""
        WHITE, GRAY, BLACK = 0, 1, 2
        colors = {task_id: WHITE for task_id in self.nodes}
        
        def dfs(node: str) -> bool:
            if colors[node] == GRAY:
                return True  # Back edge found, cycle detected
            if colors[node] == BLACK:
                return False  # Already processed
            
            colors[node] = GRAY
            for neighbor in self.adjacency_list[node]:
                if dfs(neighbor):
                    return True
            colors[node] = BLACK
            return False
        
        for task_id in self.nodes:
            if colors[task_id] == WHITE:
                if dfs(task_id):
                    return True
        
        return False
    
    def _validate_resource_dependencies(self) -> None:
        """Validate resource dependencies."""
        for task_id, task_node in self.nodes.items():
            for resource in task_node.resources_required:
                if not resource:
                    raise ValidationError(f"Empty resource name in task {task_id}")
    
    def _validate_conditional_dependencies(self) -> None:
        """Validate conditional dependencies."""
        for dependency in self.dependencies:
            if dependency.dependency_type == DependencyType.CONDITIONAL:
                if not dependency.condition:
                    raise ValidationError(
                        f"Conditional dependency from {dependency.from_task} to {dependency.to_task} "
                        "must have a condition"
                    )
    
    def compute_execution_order(self) -> List[List[str]]:
        """Compute execution order using topological sort with parallel groups."""
        # Reset execution order
        self.execution_order = []
        
        # Calculate in-degrees
        in_degree = {task_id: 0 for task_id in self.nodes}
        for dependency in self.dependencies:
            if dependency.dependency_type in [DependencyType.HARD, DependencyType.CONDITIONAL]:
                in_degree[dependency.to_task] += 1
        
        # Find tasks with no dependencies (in-degree 0)
        queue = deque([task_id for task_id, degree in in_degree.items() if degree == 0])
        
        while queue:
            # Current parallel group
            current_group = []
            next_queue = deque()
            
            # Process all tasks that can run in parallel
            while queue:
                task_id = queue.popleft()
                current_group.append(task_id)
                
                # Update in-degrees of dependent tasks
                for dependent_task in self.adjacency_list[task_id]:
                    in_degree[dependent_task] -= 1
                    if in_degree[dependent_task] == 0:
                        next_queue.append(dependent_task)
            
            if current_group:
                # Sort by priority within the group
                current_group.sort(key=lambda tid: self._get_task_priority_value(tid), reverse=True)
                self.execution_order.append(current_group)
            
            queue = next_queue
        
        # Check if all tasks are included (no cycles)
        total_tasks_in_order = sum(len(group) for group in self.execution_order)
        if total_tasks_in_order != len(self.nodes):
            remaining_tasks = set(self.nodes.keys()) - {
                task_id for group in self.execution_order for task_id in group
            }
            raise DependencyError(f"Circular dependency detected. Remaining tasks: {remaining_tasks}")
        
        self.logger.info(
            "Execution order computed",
            parallel_groups=len(self.execution_order),
            total_tasks=total_tasks_in_order,
            max_parallelism=max(len(group) for group in self.execution_order) if self.execution_order else 0
        )
        
        return self.execution_order
    
    def _get_task_priority_value(self, task_id: str) -> int:
        """Get numeric priority value for sorting."""
        priority_values = {
            TaskPriority.LOW: 1,
            TaskPriority.NORMAL: 2,
            TaskPriority.HIGH: 3,
            TaskPriority.CRITICAL: 4
        }
        return priority_values.get(self.nodes[task_id].priority, 2)
    
    def get_ready_tasks(self, exclude_running: bool = True) -> List[str]:
        """Get tasks that are ready to execute (all dependencies satisfied)."""
        ready_tasks = []
        
        for task_id, task_node in self.nodes.items():
            if task_node.status != TaskStatus.PENDING:
                continue
            
            if exclude_running and task_id in self.running_tasks:
                continue
            
            # Check if all dependencies are satisfied
            if self._are_dependencies_satisfied(task_id):
                ready_tasks.append(task_id)
        
        # Sort by priority
        ready_tasks.sort(key=lambda tid: self._get_task_priority_value(tid), reverse=True)
        
        return ready_tasks
    
    def _are_dependencies_satisfied(self, task_id: str) -> bool:
        """Check if all dependencies for a task are satisfied."""
        for dependency in self.dependencies:
            if dependency.to_task != task_id:
                continue
            
            from_task_node = self.nodes[dependency.from_task]
            
            if dependency.dependency_type == DependencyType.HARD:
                if from_task_node.status != TaskStatus.COMPLETED:
                    return False
            
            elif dependency.dependency_type == DependencyType.SOFT:
                if from_task_node.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    return False
            
            elif dependency.dependency_type == DependencyType.CONDITIONAL:
                if from_task_node.status != TaskStatus.COMPLETED:
                    return False
                # Evaluate condition (simplified - would need proper condition evaluator)
                if not self._evaluate_condition(dependency.condition, from_task_node.result):
                    return False
            
            elif dependency.dependency_type == DependencyType.RESOURCE:
                # Resource dependencies are handled separately
                continue
        
        return True
    
    def _evaluate_condition(self, condition: str, result: Any) -> bool:
        """Evaluate a conditional dependency (simplified implementation)."""
        if not condition:
            return True
        
        # Simple condition evaluation - in practice, this would be more sophisticated
        if condition == "success" and result is not None:
            return True
        elif condition == "failure" and result is None:
            return True
        
        return False
    
    def can_allocate_resources(self, task_id: str) -> bool:
        """Check if resources required by a task can be allocated."""
        task_node = self.nodes[task_id]
        
        for resource in task_node.resources_required:
            # Check if resource is already in use by another task
            if self.resource_usage[resource] and task_id not in self.resource_usage[resource]:
                return False
        
        return True
    
    def allocate_resources(self, task_id: str) -> None:
        """Allocate resources for a task."""
        task_node = self.nodes[task_id]
        
        for resource in task_node.resources_required:
            self.resource_usage[resource].add(task_id)
        
        self.logger.debug(
            "Resources allocated",
            task_id=task_id,
            resources=task_node.resources_required
        )
    
    def release_resources(self, task_id: str) -> None:
        """Release resources used by a task."""
        task_node = self.nodes[task_id]
        
        for resource in task_node.resources_required:
            self.resource_usage[resource].discard(task_id)
        
        self.logger.debug(
            "Resources released",
            task_id=task_id,
            resources=task_node.resources_required
        )
    
    def mark_task_running(self, task_id: str) -> None:
        """Mark a task as running."""
        self.nodes[task_id].status = TaskStatus.RUNNING
        self.nodes[task_id].start_time = datetime.utcnow()
        self.running_tasks.add(task_id)
        self.allocate_resources(task_id)
    
    def mark_task_completed(self, task_id: str, result: Any = None) -> None:
        """Mark a task as completed."""
        self.nodes[task_id].status = TaskStatus.COMPLETED
        self.nodes[task_id].end_time = datetime.utcnow()
        self.nodes[task_id].result = result
        self.completed_tasks.add(task_id)
        self.running_tasks.discard(task_id)
        self.release_resources(task_id)
    
    def mark_task_failed(self, task_id: str, error: Exception) -> None:
        """Mark a task as failed."""
        self.nodes[task_id].status = TaskStatus.FAILED
        self.nodes[task_id].end_time = datetime.utcnow()
        self.nodes[task_id].error = error
        self.failed_tasks.add(task_id)
        self.running_tasks.discard(task_id)
        self.release_resources(task_id)
    
    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get statistics about the dependency graph."""
        total_tasks = len(self.nodes)
        completed_tasks = len(self.completed_tasks)
        failed_tasks = len(self.failed_tasks)
        running_tasks = len(self.running_tasks)
        pending_tasks = total_tasks - completed_tasks - failed_tasks - running_tasks
        
        # Calculate execution metrics
        completed_nodes = [node for node in self.nodes.values() if node.status == TaskStatus.COMPLETED]
        if completed_nodes:
            execution_times = [
                (node.end_time - node.start_time).total_seconds()
                for node in completed_nodes
                if node.start_time and node.end_time
            ]
            avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        else:
            avg_execution_time = 0
        
        return {
            "graph_id": self.graph_id,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "running_tasks": running_tasks,
            "pending_tasks": pending_tasks,
            "completion_rate": completed_tasks / total_tasks if total_tasks > 0 else 0,
            "failure_rate": failed_tasks / total_tasks if total_tasks > 0 else 0,
            "parallel_groups": len(self.execution_order),
            "max_parallelism": max(len(group) for group in self.execution_order) if self.execution_order else 0,
            "dependencies_count": len(self.dependencies),
            "resources_count": len(self.available_resources),
            "average_execution_time": avg_execution_time
        }
    
    def get_critical_path(self) -> List[str]:
        """Calculate the critical path through the dependency graph."""
        # This is a simplified implementation
        # In practice, would use more sophisticated algorithms
        
        if not self.execution_order:
            self.compute_execution_order()
        
        # For now, return the longest path based on estimated durations
        longest_path = []
        max_duration = 0
        
        for group in self.execution_order:
            group_duration = 0
            longest_task = None
            
            for task_id in group:
                task_node = self.nodes[task_id]
                duration = task_node.estimated_duration or 60  # Default 1 minute
                if duration > group_duration:
                    group_duration = duration
                    longest_task = task_id
            
            if longest_task:
                longest_path.append(longest_task)
                max_duration += group_duration
        
        return longest_path
    
    def visualize_graph(self) -> str:
        """Generate a simple text visualization of the graph."""
        lines = [f"Dependency Graph: {self.graph_id}"]
        lines.append(f"Tasks: {len(self.nodes)}, Dependencies: {len(self.dependencies)}")
        lines.append("")
        
        for i, group in enumerate(self.execution_order):
            lines.append(f"Parallel Group {i + 1}:")
            for task_id in group:
                task_node = self.nodes[task_id]
                status_symbol = {
                    TaskStatus.PENDING: "⏳",
                    TaskStatus.RUNNING: "🔄",
                    TaskStatus.COMPLETED: "✅",
                    TaskStatus.FAILED: "❌"
                }.get(task_node.status, "❓")
                
                lines.append(f"  {status_symbol} {task_id} ({task_node.task_name}) - {task_node.priority.value}")
            lines.append("")
        
        return "\n".join(lines)
