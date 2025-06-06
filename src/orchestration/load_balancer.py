"""
Load balancing for distributed execution.

This module provides comprehensive load balancing capabilities for distributing
tasks across multiple execution nodes with health monitoring and failover.
"""

import asyncio
import time
import random
from typing import Dict, List, Optional, Any, Callable, Set
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import uuid
import statistics

from core.exceptions import ExecutionError, ResourceError
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategy enumeration."""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_RESPONSE_TIME = "least_response_time"
    RESOURCE_BASED = "resource_based"
    RANDOM = "random"
    CONSISTENT_HASH = "consistent_hash"


class NodeState(str, Enum):
    """Execution node state enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    MAINTENANCE = "maintenance"
    OFFLINE = "offline"


@dataclass
class NodeMetrics:
    """Metrics for an execution node."""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    active_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    average_response_time: float = 0.0
    last_response_time: float = 0.0
    error_rate: float = 0.0
    throughput: float = 0.0  # tasks per second
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ExecutionNode:
    """Represents an execution node in the cluster."""
    node_id: str
    node_name: str
    endpoint: str
    weight: float = 1.0
    max_concurrent_tasks: int = 10
    capabilities: Set[str] = field(default_factory=set)
    state: NodeState = NodeState.HEALTHY
    metrics: NodeMetrics = field(default_factory=NodeMetrics)
    last_health_check: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoadBalancerConfig:
    """Configuration for load balancer."""
    strategy: LoadBalancingStrategy = LoadBalancingStrategy.LEAST_CONNECTIONS
    health_check_interval: float = 30.0
    health_check_timeout: float = 5.0
    failure_threshold: int = 3
    recovery_threshold: int = 2
    enable_sticky_sessions: bool = False
    session_timeout: float = 3600.0  # 1 hour
    enable_circuit_breaker: bool = True
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 60.0


class LoadBalancer:
    """Load balancer for distributing tasks across execution nodes."""
    
    def __init__(self, config: LoadBalancerConfig):
        """Initialize load balancer."""
        self.config = config
        self.logger = StructuredLogger("load_balancer")
        
        # Node management
        self.nodes: Dict[str, ExecutionNode] = {}
        self.healthy_nodes: Set[str] = set()
        self.degraded_nodes: Set[str] = set()
        self.unhealthy_nodes: Set[str] = set()
        
        # Load balancing state
        self.round_robin_index = 0
        self.node_connections: Dict[str, int] = {}
        self.response_times: Dict[str, List[float]] = {}
        
        # Sticky sessions
        self.session_assignments: Dict[str, str] = {}  # session_id -> node_id
        self.session_last_activity: Dict[str, datetime] = {}
        
        # Circuit breaker state
        self.circuit_breaker_state: Dict[str, bool] = {}  # node_id -> is_open
        self.circuit_breaker_failures: Dict[str, int] = {}
        self.circuit_breaker_last_failure: Dict[str, datetime] = {}
        
        # Health monitoring
        self.health_check_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        # Statistics
        self.total_requests = 0
        self.total_failures = 0
        self.total_response_time = 0.0
    
    async def start(self) -> None:
        """Start the load balancer."""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start health monitoring
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        
        self.logger.info(
            "Load balancer started",
            strategy=self.config.strategy.value,
            node_count=len(self.nodes)
        )
    
    async def stop(self) -> None:
        """Stop the load balancer."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Stop health monitoring
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Load balancer stopped")
    
    def add_node(self, node: ExecutionNode) -> None:
        """Add an execution node to the load balancer."""
        
        self.nodes[node.node_id] = node
        self.healthy_nodes.add(node.node_id)
        self.node_connections[node.node_id] = 0
        self.response_times[node.node_id] = []
        self.circuit_breaker_state[node.node_id] = False
        self.circuit_breaker_failures[node.node_id] = 0
        
        self.logger.info(
            "Node added to load balancer",
            node_id=node.node_id,
            node_name=node.node_name,
            endpoint=node.endpoint,
            weight=node.weight,
            capabilities=list(node.capabilities)
        )
    
    def remove_node(self, node_id: str) -> None:
        """Remove an execution node from the load balancer."""
        
        if node_id not in self.nodes:
            return
        
        # Remove from all sets
        self.healthy_nodes.discard(node_id)
        self.degraded_nodes.discard(node_id)
        self.unhealthy_nodes.discard(node_id)
        
        # Clean up state
        del self.nodes[node_id]
        self.node_connections.pop(node_id, None)
        self.response_times.pop(node_id, None)
        self.circuit_breaker_state.pop(node_id, None)
        self.circuit_breaker_failures.pop(node_id, None)
        self.circuit_breaker_last_failure.pop(node_id, None)
        
        # Remove session assignments
        sessions_to_remove = [
            session_id for session_id, assigned_node_id in self.session_assignments.items()
            if assigned_node_id == node_id
        ]
        for session_id in sessions_to_remove:
            del self.session_assignments[session_id]
            self.session_last_activity.pop(session_id, None)
        
        self.logger.info(
            "Node removed from load balancer",
            node_id=node_id
        )
    
    async def select_node(
        self,
        session_id: Optional[str] = None,
        required_capabilities: Optional[Set[str]] = None,
        exclude_nodes: Optional[Set[str]] = None
    ) -> Optional[ExecutionNode]:
        """Select the best node for task execution."""
        
        # Check sticky sessions
        if session_id and self.config.enable_sticky_sessions:
            if session_id in self.session_assignments:
                assigned_node_id = self.session_assignments[session_id]
                if (assigned_node_id in self.nodes and 
                    assigned_node_id in self.healthy_nodes and
                    not self._is_circuit_breaker_open(assigned_node_id)):
                    
                    # Update session activity
                    self.session_last_activity[session_id] = datetime.utcnow()
                    return self.nodes[assigned_node_id]
                else:
                    # Remove invalid session assignment
                    del self.session_assignments[session_id]
                    self.session_last_activity.pop(session_id, None)
        
        # Filter available nodes
        available_nodes = self._get_available_nodes(required_capabilities, exclude_nodes)
        
        if not available_nodes:
            self.logger.warning(
                "No available nodes for task execution",
                required_capabilities=list(required_capabilities) if required_capabilities else None,
                exclude_nodes=list(exclude_nodes) if exclude_nodes else None
            )
            return None
        
        # Select node based on strategy
        selected_node = await self._select_node_by_strategy(available_nodes)
        
        # Create sticky session if enabled
        if session_id and self.config.enable_sticky_sessions and selected_node:
            self.session_assignments[session_id] = selected_node.node_id
            self.session_last_activity[session_id] = datetime.utcnow()
        
        return selected_node
    
    def _get_available_nodes(
        self,
        required_capabilities: Optional[Set[str]] = None,
        exclude_nodes: Optional[Set[str]] = None
    ) -> List[ExecutionNode]:
        """Get list of available nodes based on criteria."""
        
        available_nodes = []
        
        for node_id in self.healthy_nodes:
            node = self.nodes[node_id]
            
            # Check if node is excluded
            if exclude_nodes and node_id in exclude_nodes:
                continue
            
            # Check circuit breaker
            if self._is_circuit_breaker_open(node_id):
                continue
            
            # Check capabilities
            if required_capabilities and not required_capabilities.issubset(node.capabilities):
                continue
            
            # Check capacity
            if node.metrics.active_tasks >= node.max_concurrent_tasks:
                continue
            
            available_nodes.append(node)
        
        return available_nodes
    
    async def _select_node_by_strategy(self, available_nodes: List[ExecutionNode]) -> Optional[ExecutionNode]:
        """Select node based on configured strategy."""
        
        if not available_nodes:
            return None
        
        if self.config.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._select_round_robin(available_nodes)
        
        elif self.config.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._select_least_connections(available_nodes)
        
        elif self.config.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._select_weighted_round_robin(available_nodes)
        
        elif self.config.strategy == LoadBalancingStrategy.LEAST_RESPONSE_TIME:
            return self._select_least_response_time(available_nodes)
        
        elif self.config.strategy == LoadBalancingStrategy.RESOURCE_BASED:
            return self._select_resource_based(available_nodes)
        
        elif self.config.strategy == LoadBalancingStrategy.RANDOM:
            return random.choice(available_nodes)
        
        elif self.config.strategy == LoadBalancingStrategy.CONSISTENT_HASH:
            return self._select_consistent_hash(available_nodes)
        
        else:
            return available_nodes[0]  # Fallback to first available
    
    def _select_round_robin(self, available_nodes: List[ExecutionNode]) -> ExecutionNode:
        """Select node using round-robin strategy."""
        
        node = available_nodes[self.round_robin_index % len(available_nodes)]
        self.round_robin_index += 1
        return node
    
    def _select_least_connections(self, available_nodes: List[ExecutionNode]) -> ExecutionNode:
        """Select node with least active connections."""
        
        return min(available_nodes, key=lambda n: self.node_connections.get(n.node_id, 0))
    
    def _select_weighted_round_robin(self, available_nodes: List[ExecutionNode]) -> ExecutionNode:
        """Select node using weighted round-robin strategy."""
        
        # Calculate weighted selection
        total_weight = sum(node.weight for node in available_nodes)
        if total_weight == 0:
            return available_nodes[0]
        
        # Generate random number and select based on weight
        rand_val = random.uniform(0, total_weight)
        current_weight = 0
        
        for node in available_nodes:
            current_weight += node.weight
            if rand_val <= current_weight:
                return node
        
        return available_nodes[-1]  # Fallback
    
    def _select_least_response_time(self, available_nodes: List[ExecutionNode]) -> ExecutionNode:
        """Select node with least average response time."""
        
        def get_avg_response_time(node: ExecutionNode) -> float:
            response_times = self.response_times.get(node.node_id, [])
            if not response_times:
                return 0.0  # Prefer nodes with no history
            return statistics.mean(response_times[-10:])  # Last 10 responses
        
        return min(available_nodes, key=get_avg_response_time)
    
    def _select_resource_based(self, available_nodes: List[ExecutionNode]) -> ExecutionNode:
        """Select node based on resource utilization."""
        
        def get_resource_score(node: ExecutionNode) -> float:
            # Lower score is better
            cpu_score = node.metrics.cpu_usage
            memory_score = node.metrics.memory_usage
            task_score = node.metrics.active_tasks / node.max_concurrent_tasks
            
            return (cpu_score + memory_score + task_score) / 3
        
        return min(available_nodes, key=get_resource_score)
    
    def _select_consistent_hash(self, available_nodes: List[ExecutionNode]) -> ExecutionNode:
        """Select node using consistent hashing."""
        
        # Simple hash-based selection (in practice, would use proper consistent hashing)
        node_hashes = [(hash(node.node_id), node) for node in available_nodes]
        node_hashes.sort(key=lambda x: x[0])
        
        # Select based on current time hash
        time_hash = hash(int(time.time() / 60))  # Change every minute
        
        for node_hash, node in node_hashes:
            if time_hash <= node_hash:
                return node
        
        return node_hashes[0][1]  # Wrap around
    
    async def record_request_start(self, node_id: str) -> None:
        """Record the start of a request to a node."""
        
        if node_id in self.nodes:
            self.node_connections[node_id] = self.node_connections.get(node_id, 0) + 1
            self.nodes[node_id].metrics.active_tasks += 1
            self.total_requests += 1
    
    async def record_request_end(
        self,
        node_id: str,
        success: bool,
        response_time: float,
        error: Optional[Exception] = None
    ) -> None:
        """Record the end of a request to a node."""
        
        if node_id not in self.nodes:
            return
        
        node = self.nodes[node_id]
        
        # Update connection count
        self.node_connections[node_id] = max(0, self.node_connections.get(node_id, 0) - 1)
        node.metrics.active_tasks = max(0, node.metrics.active_tasks - 1)
        
        # Update metrics
        node.metrics.last_response_time = response_time
        self.response_times[node_id].append(response_time)
        
        # Keep only recent response times
        if len(self.response_times[node_id]) > 100:
            self.response_times[node_id] = self.response_times[node_id][-50:]
        
        # Update average response time
        if self.response_times[node_id]:
            node.metrics.average_response_time = statistics.mean(self.response_times[node_id])
        
        self.total_response_time += response_time
        
        if success:
            node.metrics.completed_tasks += 1
            node.consecutive_successes += 1
            node.consecutive_failures = 0
            
            # Reset circuit breaker on success
            if self.circuit_breaker_failures.get(node_id, 0) > 0:
                self.circuit_breaker_failures[node_id] = max(0, self.circuit_breaker_failures[node_id] - 1)
                
                if self.circuit_breaker_failures[node_id] == 0:
                    self.circuit_breaker_state[node_id] = False
        
        else:
            node.metrics.failed_tasks += 1
            node.consecutive_failures += 1
            node.consecutive_successes = 0
            self.total_failures += 1
            
            # Update circuit breaker
            if self.config.enable_circuit_breaker:
                self.circuit_breaker_failures[node_id] = self.circuit_breaker_failures.get(node_id, 0) + 1
                self.circuit_breaker_last_failure[node_id] = datetime.utcnow()
                
                if self.circuit_breaker_failures[node_id] >= self.config.circuit_breaker_threshold:
                    self.circuit_breaker_state[node_id] = True
                    
                    self.logger.warning(
                        "Circuit breaker opened for node",
                        node_id=node_id,
                        failure_count=self.circuit_breaker_failures[node_id]
                    )
        
        # Update error rate
        total_requests = node.metrics.completed_tasks + node.metrics.failed_tasks
        if total_requests > 0:
            node.metrics.error_rate = node.metrics.failed_tasks / total_requests
        
        # Update node state based on health
        await self._update_node_state(node_id)
    
    def _is_circuit_breaker_open(self, node_id: str) -> bool:
        """Check if circuit breaker is open for a node."""
        
        if not self.config.enable_circuit_breaker:
            return False
        
        if not self.circuit_breaker_state.get(node_id, False):
            return False
        
        # Check if timeout has passed
        last_failure = self.circuit_breaker_last_failure.get(node_id)
        if last_failure:
            time_since_failure = (datetime.utcnow() - last_failure).total_seconds()
            if time_since_failure >= self.config.circuit_breaker_timeout:
                # Reset circuit breaker
                self.circuit_breaker_state[node_id] = False
                self.circuit_breaker_failures[node_id] = 0
                return False
        
        return True
    
    async def _update_node_state(self, node_id: str) -> None:
        """Update node state based on health metrics."""
        
        if node_id not in self.nodes:
            return
        
        node = self.nodes[node_id]
        old_state = node.state
        
        # Determine new state based on metrics
        if node.consecutive_failures >= self.config.failure_threshold:
            new_state = NodeState.UNHEALTHY
        elif node.metrics.error_rate > 0.1:  # 10% error rate
            new_state = NodeState.DEGRADED
        elif node.consecutive_successes >= self.config.recovery_threshold:
            new_state = NodeState.HEALTHY
        else:
            new_state = node.state  # Keep current state
        
        # Update state and node sets
        if new_state != old_state:
            node.state = new_state
            
            # Remove from old state set
            if old_state == NodeState.HEALTHY:
                self.healthy_nodes.discard(node_id)
            elif old_state == NodeState.DEGRADED:
                self.degraded_nodes.discard(node_id)
            elif old_state == NodeState.UNHEALTHY:
                self.unhealthy_nodes.discard(node_id)
            
            # Add to new state set
            if new_state == NodeState.HEALTHY:
                self.healthy_nodes.add(node_id)
            elif new_state == NodeState.DEGRADED:
                self.degraded_nodes.add(node_id)
            elif new_state == NodeState.UNHEALTHY:
                self.unhealthy_nodes.add(node_id)
            
            self.logger.info(
                "Node state changed",
                node_id=node_id,
                old_state=old_state.value,
                new_state=new_state.value,
                consecutive_failures=node.consecutive_failures,
                consecutive_successes=node.consecutive_successes,
                error_rate=node.metrics.error_rate
            )
    
    async def _health_check_loop(self) -> None:
        """Background health check loop."""
        
        while self.is_running:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                if not self.is_running:
                    break
                
                await self._perform_health_checks()
                await self._cleanup_expired_sessions()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    "Health check loop error",
                    error=str(e)
                )
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all nodes."""
        
        # This would be implemented to actually check node health
        # For now, just update last health check time
        current_time = datetime.utcnow()
        
        for node_id, node in self.nodes.items():
            node.last_health_check = current_time
    
    async def _cleanup_expired_sessions(self) -> None:
        """Clean up expired sticky sessions."""
        
        if not self.config.enable_sticky_sessions:
            return
        
        current_time = datetime.utcnow()
        expired_sessions = []
        
        for session_id, last_activity in self.session_last_activity.items():
            if (current_time - last_activity).total_seconds() > self.config.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.session_assignments[session_id]
            del self.session_last_activity[session_id]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get load balancer statistics."""
        
        return {
            "total_nodes": len(self.nodes),
            "healthy_nodes": len(self.healthy_nodes),
            "degraded_nodes": len(self.degraded_nodes),
            "unhealthy_nodes": len(self.unhealthy_nodes),
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "success_rate": (self.total_requests - self.total_failures) / max(self.total_requests, 1),
            "average_response_time": self.total_response_time / max(self.total_requests, 1),
            "active_sessions": len(self.session_assignments),
            "strategy": self.config.strategy.value,
            "circuit_breaker_enabled": self.config.enable_circuit_breaker,
            "sticky_sessions_enabled": self.config.enable_sticky_sessions
        }
    
    def get_node_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all nodes."""
        
        return {
            node_id: {
                "node_name": node.node_name,
                "endpoint": node.endpoint,
                "state": node.state.value,
                "weight": node.weight,
                "capabilities": list(node.capabilities),
                "active_tasks": node.metrics.active_tasks,
                "completed_tasks": node.metrics.completed_tasks,
                "failed_tasks": node.metrics.failed_tasks,
                "error_rate": node.metrics.error_rate,
                "average_response_time": node.metrics.average_response_time,
                "consecutive_failures": node.consecutive_failures,
                "consecutive_successes": node.consecutive_successes,
                "circuit_breaker_open": self._is_circuit_breaker_open(node_id),
                "last_health_check": node.last_health_check.isoformat() if node.last_health_check else None
            }
            for node_id, node in self.nodes.items()
        }
