#!/usr/bin/env python3
"""
Load testing infrastructure for the execution layer.

This module tests system behavior under various load conditions
including concurrent workflows, high-frequency operations, and
resource stress scenarios.
"""

import asyncio
import sys
import os
import time
import psutil
import statistics
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.logging.logger import StructuredLogger
from src.execution.adapters.adapter_factory import AdapterFactory, AdapterType
from src.execution.legacy_bridge import LegacyTaskBridge
from src.execution.feature_flags import FeatureFlagManager


@dataclass
class LoadTestMetrics:
    """Load test metrics data structure."""
    test_name: str
    concurrent_operations: int
    total_operations: int
    duration_seconds: float
    operations_per_second: float
    success_rate: float
    average_response_time: float
    p95_response_time: float
    p99_response_time: float
    peak_memory_mb: float
    peak_cpu_percent: float
    error_count: int
    timestamp: float


class LoadTestingInfrastructure:
    """
    Load testing infrastructure for the execution layer.
    
    Tests system behavior under various load conditions:
    - Concurrent adapter creation/removal
    - High-frequency feature flag operations
    - Stress testing with resource monitoring
    - Sustained load testing
    """
    
    def __init__(self, max_workers: int = 10, verbose: bool = True):
        """
        Initialize load testing infrastructure.
        
        Args:
            max_workers: Maximum number of concurrent workers
            verbose: Whether to enable verbose logging
        """
        self.max_workers = max_workers
        self.verbose = verbose
        self.logger = StructuredLogger("load_testing_infrastructure")
        
        # Load test tracking
        self.metrics: List[LoadTestMetrics] = []
        self.test_results: Dict[str, Dict[str, Any]] = {}
        
        self.logger.info("Load testing infrastructure initialized", 
                        max_workers=max_workers, verbose=verbose)
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all load tests.
        
        Returns:
            Dictionary containing test results and load analysis
        """
        self.logger.info("Starting load testing suite")
        
        try:
            # Test 1: Concurrent Adapter Load Test
            await self._test_concurrent_adapter_load()
            
            # Test 2: High-Frequency Operations Load Test
            await self._test_high_frequency_operations()
            
            # Test 3: Sustained Load Test
            await self._test_sustained_load()
            
            # Test 4: Memory Stress Test
            await self._test_memory_stress()
            
            # Test 5: CPU Stress Test
            await self._test_cpu_stress()
            
            # Test 6: Mixed Workload Test
            await self._test_mixed_workload()
            
        except Exception as e:
            self.logger.error("Load test suite failed", error=str(e))
            self.test_results["suite_error"] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
        
        return self._generate_final_report()
    
    async def _test_concurrent_adapter_load(self) -> None:
        """Test concurrent adapter creation and removal under load."""
        test_name = "concurrent_adapter_load"
        self.logger.info("Testing concurrent adapter load")
        
        try:
            concurrent_operations = 20
            total_operations = concurrent_operations * 3  # Create, use, remove
            
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            response_times = []
            errors = 0
            
            async def adapter_lifecycle(adapter_id: str) -> float:
                """Complete adapter lifecycle with timing."""
                operation_start = time.time()
                try:
                    factory = AdapterFactory()
                    
                    # Create adapter
                    await factory.create_adapter(
                        AdapterType.BROWSER_USE,
                        adapter_id,
                        {"save_logs": False}
                    )
                    
                    # Simulate usage
                    await factory.health_check_all()
                    
                    # Remove adapter
                    await factory.remove_adapter(adapter_id)
                    
                    return time.time() - operation_start
                    
                except Exception as e:
                    self.logger.error("Adapter lifecycle failed", 
                                    adapter_id=adapter_id, error=str(e))
                    return time.time() - operation_start
            
            # Run concurrent operations
            tasks = [
                adapter_lifecycle(f"load_test_{i}")
                for i in range(concurrent_operations)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for result in results:
                if isinstance(result, Exception):
                    errors += 1
                else:
                    response_times.append(result)
            
            end_time = time.time()
            peak_memory = psutil.Process().memory_info().rss / 1024 / 1024
            peak_cpu = psutil.cpu_percent()
            
            duration = end_time - start_time
            success_rate = (len(response_times) / concurrent_operations) * 100
            ops_per_second = total_operations / duration
            
            # Calculate percentiles
            avg_response_time = statistics.mean(response_times) if response_times else 0
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else 0
            p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else 0
            
            # Record metrics
            metrics = LoadTestMetrics(
                test_name=test_name,
                concurrent_operations=concurrent_operations,
                total_operations=total_operations,
                duration_seconds=duration,
                operations_per_second=ops_per_second,
                success_rate=success_rate,
                average_response_time=avg_response_time,
                p95_response_time=p95_response_time,
                p99_response_time=p99_response_time,
                peak_memory_mb=peak_memory,
                peak_cpu_percent=peak_cpu,
                error_count=errors,
                timestamp=time.time()
            )
            self.metrics.append(metrics)
            
            self.test_results[test_name] = {
                "status": "passed" if success_rate >= 90 else "failed",
                "metrics": asdict(metrics),
                "timestamp": time.time()
            }
            
            self.logger.info("Concurrent adapter load test completed",
                           success_rate=success_rate,
                           ops_per_second=ops_per_second,
                           avg_response_time=avg_response_time)
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Concurrent adapter load test failed", error=str(e))
    
    async def _test_high_frequency_operations(self) -> None:
        """Test high-frequency operations."""
        test_name = "high_frequency_operations"
        self.logger.info("Testing high-frequency operations")
        
        try:
            operations_count = 1000
            concurrent_workers = 5
            
            start_time = time.time()
            response_times = []
            errors = 0
            
            async def high_frequency_worker(worker_id: int) -> List[float]:
                """Worker performing high-frequency operations."""
                worker_times = []
                flag_manager = FeatureFlagManager()
                
                operations_per_worker = operations_count // concurrent_workers
                
                for i in range(operations_per_worker):
                    operation_start = time.time()
                    try:
                        # Perform rapid flag operations
                        flag_manager.get_all_flags()
                        flag_manager.get_migration_status()
                        if i % 10 == 0:
                            flag_manager.enable_migration_phase((i % 4) + 1)
                        
                        worker_times.append(time.time() - operation_start)
                        
                    except Exception as e:
                        self.logger.error("High-frequency operation failed", 
                                        worker_id=worker_id, operation=i, error=str(e))
                        worker_times.append(time.time() - operation_start)
                
                return worker_times
            
            # Run concurrent workers
            tasks = [
                high_frequency_worker(i)
                for i in range(concurrent_workers)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Aggregate results
            for result in results:
                if isinstance(result, Exception):
                    errors += 1
                else:
                    response_times.extend(result)
            
            end_time = time.time()
            duration = end_time - start_time
            success_rate = ((len(response_times) - errors) / len(response_times)) * 100 if response_times else 0
            ops_per_second = len(response_times) / duration
            
            # Calculate metrics
            avg_response_time = statistics.mean(response_times) if response_times else 0
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else 0
            p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else 0
            
            # Record metrics
            metrics = LoadTestMetrics(
                test_name=test_name,
                concurrent_operations=concurrent_workers,
                total_operations=len(response_times),
                duration_seconds=duration,
                operations_per_second=ops_per_second,
                success_rate=success_rate,
                average_response_time=avg_response_time,
                p95_response_time=p95_response_time,
                p99_response_time=p99_response_time,
                peak_memory_mb=psutil.Process().memory_info().rss / 1024 / 1024,
                peak_cpu_percent=psutil.cpu_percent(),
                error_count=errors,
                timestamp=time.time()
            )
            self.metrics.append(metrics)
            
            self.test_results[test_name] = {
                "status": "passed" if success_rate >= 95 else "failed",
                "metrics": asdict(metrics),
                "timestamp": time.time()
            }
            
            self.logger.info("High-frequency operations test completed",
                           success_rate=success_rate,
                           ops_per_second=ops_per_second)
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("High-frequency operations test failed", error=str(e))

    async def _test_sustained_load(self) -> None:
        """Test sustained load over time."""
        test_name = "sustained_load"
        self.logger.info("Testing sustained load")

        try:
            duration_seconds = 30  # 30 second sustained test
            operations_per_second_target = 10

            start_time = time.time()
            response_times = []
            errors = 0

            factory = AdapterFactory()

            async def sustained_operation():
                """Single sustained operation."""
                operation_start = time.time()
                try:
                    # Create, check, remove cycle
                    adapter_id = f"sustained_{int(time.time() * 1000000)}"
                    await factory.create_adapter(
                        AdapterType.BROWSER_USE,
                        adapter_id,
                        {"save_logs": False}
                    )
                    await factory.health_check_all()
                    await factory.remove_adapter(adapter_id)

                    return time.time() - operation_start

                except Exception as e:
                    self.logger.error("Sustained operation failed", error=str(e))
                    return time.time() - operation_start

            # Run sustained operations
            while time.time() - start_time < duration_seconds:
                try:
                    response_time = await sustained_operation()
                    response_times.append(response_time)

                    # Control rate
                    await asyncio.sleep(1.0 / operations_per_second_target)

                except Exception:
                    errors += 1

            end_time = time.time()
            actual_duration = end_time - start_time
            success_rate = ((len(response_times) - errors) / len(response_times)) * 100 if response_times else 0
            ops_per_second = len(response_times) / actual_duration

            # Calculate metrics
            avg_response_time = statistics.mean(response_times) if response_times else 0
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else 0
            p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else 0

            # Record metrics
            metrics = LoadTestMetrics(
                test_name=test_name,
                concurrent_operations=1,  # Sequential operations
                total_operations=len(response_times),
                duration_seconds=actual_duration,
                operations_per_second=ops_per_second,
                success_rate=success_rate,
                average_response_time=avg_response_time,
                p95_response_time=p95_response_time,
                p99_response_time=p99_response_time,
                peak_memory_mb=psutil.Process().memory_info().rss / 1024 / 1024,
                peak_cpu_percent=psutil.cpu_percent(),
                error_count=errors,
                timestamp=time.time()
            )
            self.metrics.append(metrics)

            self.test_results[test_name] = {
                "status": "passed" if success_rate >= 90 else "failed",
                "metrics": asdict(metrics),
                "timestamp": time.time()
            }

            self.logger.info("Sustained load test completed",
                           duration=actual_duration,
                           success_rate=success_rate,
                           ops_per_second=ops_per_second)

        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Sustained load test failed", error=str(e))

    async def _test_memory_stress(self) -> None:
        """Test memory stress scenarios."""
        test_name = "memory_stress"
        self.logger.info("Testing memory stress")

        try:
            max_adapters = 50
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024
            peak_memory = start_memory

            factory = AdapterFactory()
            created_adapters = []

            start_time = time.time()

            # Create many adapters to stress memory
            for i in range(max_adapters):
                try:
                    adapter_id = f"memory_stress_{i}"
                    await factory.create_adapter(
                        AdapterType.BROWSER_USE,
                        adapter_id,
                        {"save_logs": False}
                    )
                    created_adapters.append(adapter_id)

                    current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                    peak_memory = max(peak_memory, current_memory)

                    # Check if we're hitting memory limits
                    if current_memory > start_memory + 1000:  # 1GB increase limit
                        self.logger.warning("Memory limit reached",
                                          current_memory=current_memory,
                                          adapters_created=len(created_adapters))
                        break

                except Exception as e:
                    self.logger.error("Memory stress adapter creation failed",
                                    adapter_id=f"memory_stress_{i}", error=str(e))
                    break

            # Cleanup all adapters
            cleanup_start = time.time()
            for adapter_id in created_adapters:
                try:
                    await factory.remove_adapter(adapter_id)
                except Exception as e:
                    self.logger.error("Memory stress cleanup failed",
                                    adapter_id=adapter_id, error=str(e))

            cleanup_time = time.time() - cleanup_start
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024

            duration = end_time - start_time
            memory_usage = peak_memory - start_memory
            memory_recovery = peak_memory - end_memory
            success_rate = (len(created_adapters) / max_adapters) * 100

            # Record metrics
            metrics = LoadTestMetrics(
                test_name=test_name,
                concurrent_operations=1,
                total_operations=len(created_adapters),
                duration_seconds=duration,
                operations_per_second=len(created_adapters) / duration,
                success_rate=success_rate,
                average_response_time=cleanup_time / len(created_adapters) if created_adapters else 0,
                p95_response_time=0,  # Not applicable
                p99_response_time=0,  # Not applicable
                peak_memory_mb=peak_memory,
                peak_cpu_percent=psutil.cpu_percent(),
                error_count=max_adapters - len(created_adapters),
                timestamp=time.time()
            )
            self.metrics.append(metrics)

            self.test_results[test_name] = {
                "status": "passed" if success_rate >= 80 else "failed",
                "metrics": asdict(metrics),
                "memory_usage_mb": memory_usage,
                "memory_recovery_mb": memory_recovery,
                "cleanup_time": cleanup_time,
                "timestamp": time.time()
            }

            self.logger.info("Memory stress test completed",
                           adapters_created=len(created_adapters),
                           peak_memory=peak_memory,
                           memory_recovery=memory_recovery)

        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Memory stress test failed", error=str(e))

    async def _test_cpu_stress(self) -> None:
        """Test CPU stress scenarios."""
        test_name = "cpu_stress"
        self.logger.info("Testing CPU stress")

        try:
            concurrent_workers = 8
            operations_per_worker = 100

            start_time = time.time()
            response_times = []
            errors = 0

            async def cpu_intensive_worker(worker_id: int) -> List[float]:
                """Worker performing CPU-intensive operations."""
                worker_times = []

                for i in range(operations_per_worker):
                    operation_start = time.time()
                    try:
                        # CPU-intensive operations
                        flag_manager = FeatureFlagManager()

                        # Rapid flag operations
                        for _ in range(10):
                            flag_manager.get_all_flags()
                            flag_manager.get_migration_status()
                            flag_manager.enable_migration_phase((i % 4) + 1)

                        worker_times.append(time.time() - operation_start)

                    except Exception as e:
                        self.logger.error("CPU stress operation failed",
                                        worker_id=worker_id, operation=i, error=str(e))
                        worker_times.append(time.time() - operation_start)

                return worker_times

            # Run concurrent CPU-intensive workers
            tasks = [
                cpu_intensive_worker(i)
                for i in range(concurrent_workers)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Aggregate results
            for result in results:
                if isinstance(result, Exception):
                    errors += 1
                else:
                    response_times.extend(result)

            end_time = time.time()
            duration = end_time - start_time
            success_rate = ((len(response_times) - errors) / len(response_times)) * 100 if response_times else 0
            ops_per_second = len(response_times) / duration

            # Calculate metrics
            avg_response_time = statistics.mean(response_times) if response_times else 0
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else 0
            p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else 0

            # Record metrics
            metrics = LoadTestMetrics(
                test_name=test_name,
                concurrent_operations=concurrent_workers,
                total_operations=len(response_times),
                duration_seconds=duration,
                operations_per_second=ops_per_second,
                success_rate=success_rate,
                average_response_time=avg_response_time,
                p95_response_time=p95_response_time,
                p99_response_time=p99_response_time,
                peak_memory_mb=psutil.Process().memory_info().rss / 1024 / 1024,
                peak_cpu_percent=psutil.cpu_percent(),
                error_count=errors,
                timestamp=time.time()
            )
            self.metrics.append(metrics)

            self.test_results[test_name] = {
                "status": "passed" if success_rate >= 90 else "failed",
                "metrics": asdict(metrics),
                "timestamp": time.time()
            }

            self.logger.info("CPU stress test completed",
                           success_rate=success_rate,
                           ops_per_second=ops_per_second)

        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("CPU stress test failed", error=str(e))

    async def _test_mixed_workload(self) -> None:
        """Test mixed workload scenarios."""
        test_name = "mixed_workload"
        self.logger.info("Testing mixed workload")

        try:
            duration_seconds = 20
            start_time = time.time()

            response_times = []
            errors = 0

            async def mixed_worker(worker_type: str, worker_id: int):
                """Worker performing mixed operations based on type."""
                worker_times = []

                while time.time() - start_time < duration_seconds:
                    operation_start = time.time()
                    try:
                        if worker_type == "adapter":
                            # Adapter operations
                            factory = AdapterFactory()
                            adapter_id = f"mixed_{worker_id}_{int(time.time() * 1000000)}"
                            await factory.create_adapter(
                                AdapterType.BROWSER_USE,
                                adapter_id,
                                {"save_logs": False}
                            )
                            await factory.remove_adapter(adapter_id)

                        elif worker_type == "flags":
                            # Flag operations
                            flag_manager = FeatureFlagManager()
                            flag_manager.get_all_flags()
                            flag_manager.get_migration_status()

                        elif worker_type == "bridge":
                            # Bridge operations
                            bridge = LegacyTaskBridge(use_new_execution=False)
                            await bridge.health_check()

                        worker_times.append(time.time() - operation_start)
                        await asyncio.sleep(0.1)  # Small delay

                    except Exception as e:
                        self.logger.error("Mixed workload operation failed",
                                        worker_type=worker_type, worker_id=worker_id, error=str(e))
                        worker_times.append(time.time() - operation_start)

                return worker_times

            # Create mixed workload
            tasks = []
            for i in range(3):
                tasks.append(mixed_worker("adapter", i))
                tasks.append(mixed_worker("flags", i))
                tasks.append(mixed_worker("bridge", i))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Aggregate results
            for result in results:
                if isinstance(result, Exception):
                    errors += 1
                else:
                    response_times.extend(result)

            end_time = time.time()
            actual_duration = end_time - start_time
            success_rate = ((len(response_times) - errors) / len(response_times)) * 100 if response_times else 0
            ops_per_second = len(response_times) / actual_duration

            # Calculate metrics
            avg_response_time = statistics.mean(response_times) if response_times else 0
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else 0
            p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else 0

            # Record metrics
            metrics = LoadTestMetrics(
                test_name=test_name,
                concurrent_operations=9,  # 3 types × 3 workers
                total_operations=len(response_times),
                duration_seconds=actual_duration,
                operations_per_second=ops_per_second,
                success_rate=success_rate,
                average_response_time=avg_response_time,
                p95_response_time=p95_response_time,
                p99_response_time=p99_response_time,
                peak_memory_mb=psutil.Process().memory_info().rss / 1024 / 1024,
                peak_cpu_percent=psutil.cpu_percent(),
                error_count=errors,
                timestamp=time.time()
            )
            self.metrics.append(metrics)

            self.test_results[test_name] = {
                "status": "passed" if success_rate >= 85 else "failed",
                "metrics": asdict(metrics),
                "timestamp": time.time()
            }

            self.logger.info("Mixed workload test completed",
                           success_rate=success_rate,
                           ops_per_second=ops_per_second)

        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Mixed workload test failed", error=str(e))

    def _generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive final load test report."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["status"] == "passed")
        failed_tests = total_tests - passed_tests

        # Aggregate metrics
        total_operations = sum(metric.total_operations for metric in self.metrics)
        avg_ops_per_second = statistics.mean([metric.operations_per_second for metric in self.metrics]) if self.metrics else 0
        avg_success_rate = statistics.mean([metric.success_rate for metric in self.metrics]) if self.metrics else 0
        peak_memory = max([metric.peak_memory_mb for metric in self.metrics]) if self.metrics else 0
        peak_cpu = max([metric.peak_cpu_percent for metric in self.metrics]) if self.metrics else 0

        report = {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
                "timestamp": time.time()
            },
            "load_analysis": {
                "total_operations": total_operations,
                "average_ops_per_second": avg_ops_per_second,
                "average_success_rate": avg_success_rate,
                "peak_memory_mb": peak_memory,
                "peak_cpu_percent": peak_cpu,
                "max_concurrent_operations": max([metric.concurrent_operations for metric in self.metrics]) if self.metrics else 0
            },
            "test_results": self.test_results,
            "metrics": [asdict(metric) for metric in self.metrics],
            "load_status": {
                "load_handling_capable": failed_tests == 0,
                "high_concurrency_supported": avg_success_rate >= 90,
                "resource_efficient": peak_memory < 1000,  # Less than 1GB peak
                "performance_stable": avg_ops_per_second > 5  # At least 5 ops/sec average
            }
        }

        return report


async def main():
    """Main function to run load tests."""
    print("🔥 Starting Load Testing Infrastructure")
    print("=" * 60)

    # Parse command line arguments
    max_workers = 10
    if "--workers" in sys.argv:
        try:
            worker_index = sys.argv.index("--workers") + 1
            max_workers = int(sys.argv[worker_index])
        except (IndexError, ValueError):
            print("Invalid --workers argument, using default: 10")

    runner = LoadTestingInfrastructure(max_workers=max_workers, verbose=True)

    try:
        results = await runner.run_all_tests()

        # Print summary
        summary = results["summary"]
        print(f"\n📊 Load Test Results Summary:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Passed: {summary['passed_tests']}")
        print(f"   Failed: {summary['failed_tests']}")
        print(f"   Success Rate: {summary['success_rate']:.1%}")

        # Print load analysis
        analysis = results["load_analysis"]
        print(f"\n🔥 Load Analysis:")
        print(f"   Total Operations: {analysis['total_operations']:,}")
        print(f"   Average Ops/Second: {analysis['average_ops_per_second']:.1f}")
        print(f"   Average Success Rate: {analysis['average_success_rate']:.1f}%")
        print(f"   Peak Memory Usage: {analysis['peak_memory_mb']:.1f} MB")
        print(f"   Peak CPU Usage: {analysis['peak_cpu_percent']:.1f}%")
        print(f"   Max Concurrent Ops: {analysis['max_concurrent_operations']}")

        # Print load status
        status = results["load_status"]
        print(f"\n🏋️ Load Status:")
        print(f"   Load Handling Capable: {'✅' if status['load_handling_capable'] else '❌'}")
        print(f"   High Concurrency Supported: {'✅' if status['high_concurrency_supported'] else '❌'}")
        print(f"   Resource Efficient: {'✅' if status['resource_efficient'] else '❌'}")
        print(f"   Performance Stable: {'✅' if status['performance_stable'] else '❌'}")

        # Print individual test results
        print(f"\n📋 Individual Test Results:")
        for test_name, result in results["test_results"].items():
            status_icon = "✅" if result["status"] == "passed" else "❌"
            print(f"   {status_icon} {test_name}: {result['status']}")
            if result["status"] == "failed" and "error" in result:
                print(f"      Error: {result['error']}")
            elif "metrics" in result:
                metrics = result["metrics"]
                print(f"      Ops/sec: {metrics.get('operations_per_second', 0):.1f}, "
                      f"Success: {metrics.get('success_rate', 0):.1f}%")

        print("\n" + "=" * 60)

        if summary["failed_tests"] == 0 and status["load_handling_capable"]:
            print("🎉 All load tests passed! System can handle expected load.")
            return 0
        else:
            print("⚠️  Load testing issues detected. Please review the results.")
            return 1

    except Exception as e:
        print(f"❌ Load test suite failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
