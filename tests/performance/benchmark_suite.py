"""
Performance benchmarking suite for the browser automation framework.

Comprehensive performance testing including load testing, stress testing,
and performance regression detection.
"""

import pytest
import asyncio
import time
import statistics
import psutil
import gc
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import json

from src.intelligence.advanced_orchestrator import (
    AdvancedOrchestrator, 
    IntelligentWorkflowConfig
)
from src.orchestration.parallel_executor import ParallelExecutor, ExecutionConfig
from src.orchestration.dependency_graph import DependencyGraph, TaskNode, TaskPriority
from src.infrastructure.resources.pool_manager import ResourcePool, PoolConfig
from src.analytics.reporting_engine import AnalyticsEngine, MetricsCollector
from tests.e2e.test_complete_workflows import E2ETestExecutor, E2ETestLLMProvider


@dataclass
class PerformanceMetrics:
    """Performance metrics for benchmarking."""
    execution_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    throughput_ops_per_sec: float
    error_rate: float
    p95_response_time: float
    p99_response_time: float
    concurrent_tasks: int
    total_operations: int


@dataclass
class BenchmarkConfig:
    """Configuration for performance benchmarks."""
    duration_seconds: int = 60
    concurrent_users: int = 10
    ramp_up_time: int = 10
    target_throughput: float = 100.0  # operations per second
    max_error_rate: float = 0.01  # 1%
    memory_limit_mb: int = 1024
    cpu_limit_percent: float = 80.0


class PerformanceBenchmark:
    """Performance benchmarking framework."""
    
    def __init__(self):
        self.metrics_history: List[PerformanceMetrics] = []
        self.baseline_metrics: Dict[str, PerformanceMetrics] = {}
        
    async def run_load_test(
        self,
        orchestrator: AdvancedOrchestrator,
        workflow_definition: Dict[str, Any],
        config: BenchmarkConfig
    ) -> PerformanceMetrics:
        """Run load test with specified configuration."""
        
        print(f"Starting load test: {config.concurrent_users} users, {config.duration_seconds}s duration")
        
        # Prepare test data
        test_tasks = []
        start_time = time.time()
        end_time = start_time + config.duration_seconds
        
        # Track metrics
        execution_times = []
        error_count = 0
        total_operations = 0
        
        # Monitor system resources
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        try:
            # Create concurrent tasks
            for user_id in range(config.concurrent_users):
                task = asyncio.create_task(
                    self._user_simulation(
                        orchestrator,
                        workflow_definition,
                        user_id,
                        end_time,
                        execution_times,
                        config
                    )
                )
                test_tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*test_tasks, return_exceptions=True)
            
            # Count errors
            for result in results:
                if isinstance(result, Exception):
                    error_count += 1
                elif isinstance(result, dict):
                    total_operations += result.get("operations", 0)
                    error_count += result.get("errors", 0)
            
            # Calculate final metrics
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_usage = final_memory - initial_memory
            
            cpu_usage = psutil.cpu_percent(interval=1)
            
            actual_duration = time.time() - start_time
            throughput = total_operations / actual_duration if actual_duration > 0 else 0
            error_rate = error_count / max(total_operations, 1)
            
            # Calculate percentiles
            if execution_times:
                p95_time = statistics.quantiles(execution_times, n=20)[18]  # 95th percentile
                p99_time = statistics.quantiles(execution_times, n=100)[98]  # 99th percentile
            else:
                p95_time = p99_time = 0
            
            metrics = PerformanceMetrics(
                execution_time=actual_duration,
                memory_usage_mb=memory_usage,
                cpu_usage_percent=cpu_usage,
                throughput_ops_per_sec=throughput,
                error_rate=error_rate,
                p95_response_time=p95_time,
                p99_response_time=p99_time,
                concurrent_tasks=config.concurrent_users,
                total_operations=total_operations
            )
            
            self.metrics_history.append(metrics)
            
            print(f"Load test completed:")
            print(f"  Throughput: {throughput:.2f} ops/sec")
            print(f"  Error rate: {error_rate:.2%}")
            print(f"  P95 response time: {p95_time:.3f}s")
            print(f"  Memory usage: {memory_usage:.1f} MB")
            print(f"  CPU usage: {cpu_usage:.1f}%")
            
            return metrics
            
        except Exception as e:
            print(f"Load test failed: {e}")
            raise
        
        finally:
            # Cleanup
            for task in test_tasks:
                if not task.done():
                    task.cancel()
            
            # Force garbage collection
            gc.collect()
    
    async def _user_simulation(
        self,
        orchestrator: AdvancedOrchestrator,
        workflow_definition: Dict[str, Any],
        user_id: int,
        end_time: float,
        execution_times: List[float],
        config: BenchmarkConfig
    ) -> Dict[str, Any]:
        """Simulate a single user's workflow executions."""
        
        operations = 0
        errors = 0
        
        # Ramp up delay
        ramp_delay = (config.ramp_up_time * user_id) / config.concurrent_users
        await asyncio.sleep(ramp_delay)
        
        intelligent_config = IntelligentWorkflowConfig(
            enable_llm_assistance=False,  # Disable for performance testing
            enable_multimodal=False,
            enable_error_recovery=True,
            enable_analytics=True,
            auto_optimize=False,
            learning_mode=False
        )
        
        while time.time() < end_time:
            try:
                start = time.time()
                
                # Execute workflow
                result = await orchestrator.execute_intelligent_workflow(
                    workflow_definition=workflow_definition,
                    config=intelligent_config,
                    context={"user_id": user_id, "operation": operations}
                )
                
                execution_time = time.time() - start
                execution_times.append(execution_time)
                operations += 1
                
                if not result.get("result", {}).get("success", False):
                    errors += 1
                
                # Small delay between operations
                await asyncio.sleep(0.1)
                
            except Exception as e:
                errors += 1
                print(f"User {user_id} error: {e}")
                await asyncio.sleep(1)  # Longer delay on error
        
        return {"operations": operations, "errors": errors}
    
    async def run_stress_test(
        self,
        orchestrator: AdvancedOrchestrator,
        workflow_definition: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run stress test to find breaking point."""
        
        print("Starting stress test to find system limits...")
        
        stress_results = {}
        concurrent_users = 1
        max_users = 100
        
        while concurrent_users <= max_users:
            print(f"Testing with {concurrent_users} concurrent users...")
            
            config = BenchmarkConfig(
                duration_seconds=30,
                concurrent_users=concurrent_users,
                ramp_up_time=5
            )
            
            try:
                metrics = await self.run_load_test(orchestrator, workflow_definition, config)
                
                stress_results[concurrent_users] = {
                    "throughput": metrics.throughput_ops_per_sec,
                    "error_rate": metrics.error_rate,
                    "p95_response_time": metrics.p95_response_time,
                    "memory_usage": metrics.memory_usage_mb,
                    "cpu_usage": metrics.cpu_usage_percent
                }
                
                # Check if we've hit limits
                if (metrics.error_rate > 0.05 or  # 5% error rate
                    metrics.p95_response_time > 10.0 or  # 10s response time
                    metrics.memory_usage_mb > 2048 or  # 2GB memory
                    metrics.cpu_usage_percent > 95):  # 95% CPU
                    
                    print(f"System limits reached at {concurrent_users} users")
                    break
                
                # Exponential increase
                if concurrent_users < 10:
                    concurrent_users += 1
                else:
                    concurrent_users = int(concurrent_users * 1.5)
                
            except Exception as e:
                print(f"Stress test failed at {concurrent_users} users: {e}")
                break
        
        return stress_results
    
    async def run_memory_leak_test(
        self,
        orchestrator: AdvancedOrchestrator,
        workflow_definition: Dict[str, Any],
        duration_minutes: int = 30
    ) -> Dict[str, Any]:
        """Run extended test to detect memory leaks."""
        
        print(f"Starting memory leak test for {duration_minutes} minutes...")
        
        process = psutil.Process()
        memory_samples = []
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        config = IntelligentWorkflowConfig(
            enable_llm_assistance=False,
            enable_multimodal=False,
            enable_error_recovery=True,
            enable_analytics=False,  # Reduce overhead
            auto_optimize=False,
            learning_mode=False
        )
        
        operation_count = 0
        
        while time.time() < end_time:
            try:
                # Execute workflow
                result = await orchestrator.execute_intelligent_workflow(
                    workflow_definition=workflow_definition,
                    config=config,
                    context={"operation": operation_count}
                )
                
                operation_count += 1
                
                # Sample memory every 10 operations
                if operation_count % 10 == 0:
                    memory_mb = process.memory_info().rss / 1024 / 1024
                    memory_samples.append({
                        "timestamp": time.time() - start_time,
                        "memory_mb": memory_mb,
                        "operations": operation_count
                    })
                    
                    if operation_count % 100 == 0:
                        print(f"Operations: {operation_count}, Memory: {memory_mb:.1f} MB")
                
                # Force garbage collection periodically
                if operation_count % 50 == 0:
                    gc.collect()
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"Memory leak test error: {e}")
                await asyncio.sleep(1)
        
        # Analyze memory trend
        if len(memory_samples) >= 2:
            initial_memory = memory_samples[0]["memory_mb"]
            final_memory = memory_samples[-1]["memory_mb"]
            memory_growth = final_memory - initial_memory
            
            # Calculate growth rate
            duration_hours = (memory_samples[-1]["timestamp"] - memory_samples[0]["timestamp"]) / 3600
            growth_rate_mb_per_hour = memory_growth / duration_hours if duration_hours > 0 else 0
        else:
            memory_growth = 0
            growth_rate_mb_per_hour = 0
        
        return {
            "total_operations": operation_count,
            "duration_minutes": duration_minutes,
            "memory_samples": memory_samples,
            "memory_growth_mb": memory_growth,
            "growth_rate_mb_per_hour": growth_rate_mb_per_hour,
            "potential_leak": growth_rate_mb_per_hour > 10  # More than 10MB/hour growth
        }
    
    def compare_with_baseline(self, current_metrics: PerformanceMetrics, test_name: str) -> Dict[str, Any]:
        """Compare current metrics with baseline."""
        
        if test_name not in self.baseline_metrics:
            self.baseline_metrics[test_name] = current_metrics
            return {"status": "baseline_set", "baseline": current_metrics}
        
        baseline = self.baseline_metrics[test_name]
        
        comparison = {
            "throughput_change": (current_metrics.throughput_ops_per_sec - baseline.throughput_ops_per_sec) / baseline.throughput_ops_per_sec,
            "response_time_change": (current_metrics.p95_response_time - baseline.p95_response_time) / baseline.p95_response_time,
            "memory_change": (current_metrics.memory_usage_mb - baseline.memory_usage_mb) / baseline.memory_usage_mb,
            "error_rate_change": current_metrics.error_rate - baseline.error_rate
        }
        
        # Determine if performance regressed
        regression_detected = (
            comparison["throughput_change"] < -0.1 or  # 10% throughput decrease
            comparison["response_time_change"] > 0.2 or  # 20% response time increase
            comparison["memory_change"] > 0.3 or  # 30% memory increase
            comparison["error_rate_change"] > 0.01  # 1% error rate increase
        )
        
        return {
            "status": "regression_detected" if regression_detected else "performance_maintained",
            "comparison": comparison,
            "baseline": baseline,
            "current": current_metrics
        }
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        
        if not self.metrics_history:
            return {"error": "No performance data available"}
        
        # Calculate trends
        recent_metrics = self.metrics_history[-10:]  # Last 10 runs
        
        avg_throughput = statistics.mean([m.throughput_ops_per_sec for m in recent_metrics])
        avg_response_time = statistics.mean([m.p95_response_time for m in recent_metrics])
        avg_memory = statistics.mean([m.memory_usage_mb for m in recent_metrics])
        avg_error_rate = statistics.mean([m.error_rate for m in recent_metrics])
        
        return {
            "summary": {
                "total_test_runs": len(self.metrics_history),
                "average_throughput": avg_throughput,
                "average_p95_response_time": avg_response_time,
                "average_memory_usage": avg_memory,
                "average_error_rate": avg_error_rate
            },
            "recent_trends": {
                "throughput_trend": self._calculate_trend([m.throughput_ops_per_sec for m in recent_metrics]),
                "response_time_trend": self._calculate_trend([m.p95_response_time for m in recent_metrics]),
                "memory_trend": self._calculate_trend([m.memory_usage_mb for m in recent_metrics])
            },
            "baselines": {name: metrics.__dict__ for name, metrics in self.baseline_metrics.items()},
            "recommendations": self._generate_recommendations(recent_metrics)
        }
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from values."""
        if len(values) < 2:
            return "insufficient_data"
        
        # Simple linear trend
        first_half = statistics.mean(values[:len(values)//2])
        second_half = statistics.mean(values[len(values)//2:])
        
        change = (second_half - first_half) / first_half if first_half > 0 else 0
        
        if change > 0.05:
            return "increasing"
        elif change < -0.05:
            return "decreasing"
        else:
            return "stable"
    
    def _generate_recommendations(self, metrics: List[PerformanceMetrics]) -> List[str]:
        """Generate performance recommendations."""
        
        recommendations = []
        
        avg_throughput = statistics.mean([m.throughput_ops_per_sec for m in metrics])
        avg_response_time = statistics.mean([m.p95_response_time for m in metrics])
        avg_memory = statistics.mean([m.memory_usage_mb for m in metrics])
        avg_error_rate = statistics.mean([m.error_rate for m in metrics])
        
        if avg_throughput < 50:
            recommendations.append("Consider optimizing task execution logic for better throughput")
        
        if avg_response_time > 5.0:
            recommendations.append("High response times detected - investigate bottlenecks")
        
        if avg_memory > 512:
            recommendations.append("High memory usage - consider implementing memory optimization")
        
        if avg_error_rate > 0.02:
            recommendations.append("Error rate above 2% - improve error handling and retry logic")
        
        return recommendations


# Test fixtures and test cases
@pytest.fixture
async def benchmark_orchestrator():
    """Create orchestrator optimized for benchmarking."""
    
    task_executor = E2ETestExecutor()
    task_executor.execution_delay = 0.01  # Faster execution for benchmarking
    
    llm_provider = E2ETestLLMProvider()
    
    from unittest.mock import Mock, AsyncMock
    workflow_engine = Mock()
    workflow_engine.execute_workflow = AsyncMock(return_value={"success": True})
    
    orchestrator = AdvancedOrchestrator(
        workflow_engine=workflow_engine,
        task_executor=task_executor,
        llm_provider=llm_provider
    )
    
    await orchestrator.start()
    yield orchestrator
    await orchestrator.stop()


@pytest.fixture
def benchmark_workflow():
    """Simple workflow for benchmarking."""
    return {
        "type": "benchmark_workflow",
        "name": "Performance Benchmark Workflow",
        "tasks": [
            {
                "id": "task_1",
                "name": "Quick Task 1",
                "type": "navigate",
                "priority": "normal",
                "definition": {"url": "https://example.com"}
            },
            {
                "id": "task_2",
                "name": "Quick Task 2",
                "type": "extract_data",
                "priority": "normal",
                "definition": {"selector": ".content"}
            }
        ],
        "dependencies": [
            {"from": "task_1", "to": "task_2", "type": "hard"}
        ],
        "execution_mode": "sequential"
    }


class TestPerformanceBenchmarks:
    """Performance benchmark test suite."""
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_load_performance(self, benchmark_orchestrator, benchmark_workflow):
        """Test system performance under normal load."""
        
        benchmark = PerformanceBenchmark()
        
        config = BenchmarkConfig(
            duration_seconds=30,
            concurrent_users=5,
            ramp_up_time=5
        )
        
        metrics = await benchmark.run_load_test(
            benchmark_orchestrator,
            benchmark_workflow,
            config
        )
        
        # Performance assertions
        assert metrics.throughput_ops_per_sec > 10  # At least 10 ops/sec
        assert metrics.error_rate < 0.05  # Less than 5% errors
        assert metrics.p95_response_time < 5.0  # Less than 5s response time
        assert metrics.memory_usage_mb < 500  # Less than 500MB memory
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.slow
    async def test_stress_limits(self, benchmark_orchestrator, benchmark_workflow):
        """Test system stress limits."""
        
        benchmark = PerformanceBenchmark()
        
        stress_results = await benchmark.run_stress_test(
            benchmark_orchestrator,
            benchmark_workflow
        )
        
        # Verify we found some limits
        assert len(stress_results) > 1
        
        # Find maximum successful load
        max_users = max(stress_results.keys())
        assert max_users >= 5  # Should handle at least 5 concurrent users
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    @pytest.mark.slow
    async def test_memory_leak_detection(self, benchmark_orchestrator, benchmark_workflow):
        """Test for memory leaks during extended operation."""
        
        benchmark = PerformanceBenchmark()
        
        # Run shorter test for CI
        leak_results = await benchmark.run_memory_leak_test(
            benchmark_orchestrator,
            benchmark_workflow,
            duration_minutes=2
        )
        
        # Verify no significant memory leaks
        assert leak_results["growth_rate_mb_per_hour"] < 50  # Less than 50MB/hour growth
        assert not leak_results["potential_leak"]
        assert leak_results["total_operations"] > 10


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "performance"])
