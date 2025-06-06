#!/usr/bin/env python3
"""
Performance regression tests for the execution layer.

This module tests performance characteristics and detects regressions
in execution speed, memory usage, and resource utilization.
"""

import asyncio
import sys
import os
import time
import psutil
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.logging.logger import StructuredLogger
from src.execution.adapters.adapter_factory import AdapterFactory, AdapterType
from src.execution.legacy_bridge import LegacyTaskBridge
from src.execution.feature_flags import FeatureFlagManager


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    test_name: str
    execution_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    operations_per_second: float
    peak_memory_mb: float
    timestamp: float


class PerformanceRegressionTests:
    """
    Performance regression test suite.
    
    Tests performance characteristics and detects regressions in:
    - Execution speed
    - Memory usage
    - CPU utilization
    - Resource cleanup
    - Concurrent operations
    """
    
    def __init__(self, baseline_file: Optional[str] = None, verbose: bool = True):
        """
        Initialize performance regression tests.
        
        Args:
            baseline_file: Path to baseline performance metrics file
            verbose: Whether to enable verbose logging
        """
        self.verbose = verbose
        self.logger = StructuredLogger("performance_regression_tests")
        self.baseline_file = baseline_file or "tests/performance_baseline.json"
        
        # Performance tracking
        self.metrics: List[PerformanceMetrics] = []
        self.baseline_metrics: Dict[str, PerformanceMetrics] = {}
        self.test_results: Dict[str, Dict[str, Any]] = {}
        
        # Load baseline if exists
        self._load_baseline()
        
        self.logger.info("Performance regression tests initialized", 
                        baseline_file=self.baseline_file, verbose=verbose)
    
    def _load_baseline(self) -> None:
        """Load baseline performance metrics."""
        try:
            if os.path.exists(self.baseline_file):
                with open(self.baseline_file, 'r') as f:
                    baseline_data = json.load(f)
                    for test_name, metrics_dict in baseline_data.items():
                        self.baseline_metrics[test_name] = PerformanceMetrics(**metrics_dict)
                self.logger.info("Baseline metrics loaded", 
                               tests_count=len(self.baseline_metrics))
            else:
                self.logger.info("No baseline file found, will create new baseline")
        except Exception as e:
            self.logger.error("Failed to load baseline metrics", error=str(e))
    
    def _save_baseline(self) -> None:
        """Save current metrics as baseline."""
        try:
            baseline_data = {}
            for metric in self.metrics:
                baseline_data[metric.test_name] = asdict(metric)
            
            os.makedirs(os.path.dirname(self.baseline_file), exist_ok=True)
            with open(self.baseline_file, 'w') as f:
                json.dump(baseline_data, f, indent=2)
            
            self.logger.info("Baseline metrics saved", 
                           tests_count=len(baseline_data))
        except Exception as e:
            self.logger.error("Failed to save baseline metrics", error=str(e))
    
    async def run_all_tests(self, save_baseline: bool = False) -> Dict[str, Any]:
        """
        Run all performance regression tests.
        
        Args:
            save_baseline: Whether to save current results as new baseline
            
        Returns:
            Dictionary containing test results and performance analysis
        """
        self.logger.info("Starting performance regression tests")
        
        try:
            # Test 1: Adapter Creation Performance
            await self._test_adapter_creation_performance()
            
            # Test 2: Feature Flag Performance
            await self._test_feature_flag_performance()
            
            # Test 3: Concurrent Operations Performance
            await self._test_concurrent_operations_performance()
            
            # Test 4: Memory Usage Performance
            await self._test_memory_usage_performance()
            
            # Test 5: Health Check Performance
            await self._test_health_check_performance()
            
            # Test 6: Bridge Performance
            await self._test_bridge_performance()
            
            # Test 7: Cleanup Performance
            await self._test_cleanup_performance()
            
        except Exception as e:
            self.logger.error("Performance test suite failed", error=str(e))
            self.test_results["suite_error"] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
        
        # Analyze results
        analysis = self._analyze_performance()
        
        # Save baseline if requested
        if save_baseline:
            self._save_baseline()
        
        return self._generate_final_report(analysis)
    
    async def _test_adapter_creation_performance(self) -> None:
        """Test adapter creation performance."""
        test_name = "adapter_creation_performance"
        self.logger.info("Testing adapter creation performance")
        
        try:
            # Measure performance
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            factory = AdapterFactory()
            
            # Create multiple adapters to test performance
            adapter_count = 10
            for i in range(adapter_count):
                await factory.create_adapter(
                    AdapterType.BROWSER_USE,
                    f"perf_test_{i}",
                    {"save_logs": False}
                )
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            execution_time = end_time - start_time
            memory_usage = end_memory - start_memory
            operations_per_second = adapter_count / execution_time
            
            # Cleanup
            for i in range(adapter_count):
                await factory.remove_adapter(f"perf_test_{i}")
            
            # Record metrics
            metrics = PerformanceMetrics(
                test_name=test_name,
                execution_time=execution_time,
                memory_usage_mb=memory_usage,
                cpu_usage_percent=psutil.cpu_percent(),
                operations_per_second=operations_per_second,
                peak_memory_mb=end_memory,
                timestamp=time.time()
            )
            self.metrics.append(metrics)
            
            self.test_results[test_name] = {
                "status": "passed",
                "metrics": asdict(metrics),
                "timestamp": time.time()
            }
            
            self.logger.info("Adapter creation performance test passed",
                           execution_time=execution_time,
                           operations_per_second=operations_per_second)
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Adapter creation performance test failed", error=str(e))
    
    async def _test_feature_flag_performance(self) -> None:
        """Test feature flag performance."""
        test_name = "feature_flag_performance"
        self.logger.info("Testing feature flag performance")
        
        try:
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            flag_manager = FeatureFlagManager()
            
            # Perform multiple flag operations
            operation_count = 1000
            for i in range(operation_count):
                flag_manager.get_all_flags()
                flag_manager.get_migration_status()
                if i % 100 == 0:
                    flag_manager.enable_migration_phase((i // 100) % 4 + 1)
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            execution_time = end_time - start_time
            memory_usage = end_memory - start_memory
            operations_per_second = operation_count / execution_time
            
            # Record metrics
            metrics = PerformanceMetrics(
                test_name=test_name,
                execution_time=execution_time,
                memory_usage_mb=memory_usage,
                cpu_usage_percent=psutil.cpu_percent(),
                operations_per_second=operations_per_second,
                peak_memory_mb=end_memory,
                timestamp=time.time()
            )
            self.metrics.append(metrics)
            
            self.test_results[test_name] = {
                "status": "passed",
                "metrics": asdict(metrics),
                "timestamp": time.time()
            }
            
            self.logger.info("Feature flag performance test passed",
                           execution_time=execution_time,
                           operations_per_second=operations_per_second)
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Feature flag performance test failed", error=str(e))
    
    async def _test_concurrent_operations_performance(self) -> None:
        """Test concurrent operations performance."""
        test_name = "concurrent_operations_performance"
        self.logger.info("Testing concurrent operations performance")
        
        try:
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            # Create multiple tasks to run concurrently
            async def create_and_remove_adapter(factory, adapter_id):
                await factory.create_adapter(
                    AdapterType.BROWSER_USE,
                    adapter_id,
                    {"save_logs": False}
                )
                await factory.remove_adapter(adapter_id)
            
            factory = AdapterFactory()
            concurrent_count = 5
            
            # Run concurrent operations
            tasks = [
                create_and_remove_adapter(factory, f"concurrent_{i}")
                for i in range(concurrent_count)
            ]
            await asyncio.gather(*tasks)
            
            end_time = time.time()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            execution_time = end_time - start_time
            memory_usage = end_memory - start_memory
            operations_per_second = concurrent_count / execution_time
            
            # Record metrics
            metrics = PerformanceMetrics(
                test_name=test_name,
                execution_time=execution_time,
                memory_usage_mb=memory_usage,
                cpu_usage_percent=psutil.cpu_percent(),
                operations_per_second=operations_per_second,
                peak_memory_mb=end_memory,
                timestamp=time.time()
            )
            self.metrics.append(metrics)
            
            self.test_results[test_name] = {
                "status": "passed",
                "metrics": asdict(metrics),
                "timestamp": time.time()
            }
            
            self.logger.info("Concurrent operations performance test passed",
                           execution_time=execution_time,
                           operations_per_second=operations_per_second)
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Concurrent operations performance test failed", error=str(e))

    async def _test_memory_usage_performance(self) -> None:
        """Test memory usage performance."""
        test_name = "memory_usage_performance"
        self.logger.info("Testing memory usage performance")

        try:
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024
            peak_memory = start_memory

            factory = AdapterFactory()

            # Create and monitor memory usage
            for i in range(20):
                await factory.create_adapter(
                    AdapterType.BROWSER_USE,
                    f"memory_test_{i}",
                    {"save_logs": False}
                )
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                peak_memory = max(peak_memory, current_memory)

            # Cleanup and measure memory recovery
            for i in range(20):
                await factory.remove_adapter(f"memory_test_{i}")

            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_usage = peak_memory - start_memory
            memory_recovery = peak_memory - end_memory

            # Record metrics
            metrics = PerformanceMetrics(
                test_name=test_name,
                execution_time=0.0,  # Not time-focused
                memory_usage_mb=memory_usage,
                cpu_usage_percent=psutil.cpu_percent(),
                operations_per_second=0.0,  # Not applicable
                peak_memory_mb=peak_memory,
                timestamp=time.time()
            )
            self.metrics.append(metrics)

            self.test_results[test_name] = {
                "status": "passed",
                "metrics": asdict(metrics),
                "memory_recovery_mb": memory_recovery,
                "timestamp": time.time()
            }

            self.logger.info("Memory usage performance test passed",
                           peak_memory=peak_memory,
                           memory_recovery=memory_recovery)

        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Memory usage performance test failed", error=str(e))

    async def _test_health_check_performance(self) -> None:
        """Test health check performance."""
        test_name = "health_check_performance"
        self.logger.info("Testing health check performance")

        try:
            start_time = time.time()

            factory = AdapterFactory()

            # Create adapters for health checking
            for i in range(5):
                await factory.create_adapter(
                    AdapterType.BROWSER_USE,
                    f"health_test_{i}",
                    {"save_logs": False}
                )

            # Perform multiple health checks
            health_check_count = 50
            for _ in range(health_check_count):
                await factory.health_check_all()

            end_time = time.time()
            execution_time = end_time - start_time
            operations_per_second = health_check_count / execution_time

            # Cleanup
            for i in range(5):
                await factory.remove_adapter(f"health_test_{i}")

            # Record metrics
            metrics = PerformanceMetrics(
                test_name=test_name,
                execution_time=execution_time,
                memory_usage_mb=0.0,  # Not memory-focused
                cpu_usage_percent=psutil.cpu_percent(),
                operations_per_second=operations_per_second,
                peak_memory_mb=psutil.Process().memory_info().rss / 1024 / 1024,
                timestamp=time.time()
            )
            self.metrics.append(metrics)

            self.test_results[test_name] = {
                "status": "passed",
                "metrics": asdict(metrics),
                "timestamp": time.time()
            }

            self.logger.info("Health check performance test passed",
                           execution_time=execution_time,
                           operations_per_second=operations_per_second)

        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Health check performance test failed", error=str(e))

    async def _test_bridge_performance(self) -> None:
        """Test bridge performance."""
        test_name = "bridge_performance"
        self.logger.info("Testing bridge performance")

        try:
            start_time = time.time()

            # Create multiple bridges and test operations
            bridge_count = 10
            bridges = []

            for i in range(bridge_count):
                bridge = LegacyTaskBridge(use_new_execution=False)
                bridges.append(bridge)
                await bridge.health_check()

            end_time = time.time()
            execution_time = end_time - start_time
            operations_per_second = bridge_count / execution_time

            # Record metrics
            metrics = PerformanceMetrics(
                test_name=test_name,
                execution_time=execution_time,
                memory_usage_mb=0.0,  # Not memory-focused
                cpu_usage_percent=psutil.cpu_percent(),
                operations_per_second=operations_per_second,
                peak_memory_mb=psutil.Process().memory_info().rss / 1024 / 1024,
                timestamp=time.time()
            )
            self.metrics.append(metrics)

            self.test_results[test_name] = {
                "status": "passed",
                "metrics": asdict(metrics),
                "timestamp": time.time()
            }

            self.logger.info("Bridge performance test passed",
                           execution_time=execution_time,
                           operations_per_second=operations_per_second)

        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Bridge performance test failed", error=str(e))

    async def _test_cleanup_performance(self) -> None:
        """Test cleanup performance."""
        test_name = "cleanup_performance"
        self.logger.info("Testing cleanup performance")

        try:
            factory = AdapterFactory()

            # Create many adapters
            adapter_count = 15
            for i in range(adapter_count):
                await factory.create_adapter(
                    AdapterType.BROWSER_USE,
                    f"cleanup_test_{i}",
                    {"save_logs": False}
                )

            # Measure cleanup time
            start_time = time.time()
            await factory.shutdown()
            end_time = time.time()

            execution_time = end_time - start_time
            operations_per_second = adapter_count / execution_time

            # Record metrics
            metrics = PerformanceMetrics(
                test_name=test_name,
                execution_time=execution_time,
                memory_usage_mb=0.0,  # Not memory-focused
                cpu_usage_percent=psutil.cpu_percent(),
                operations_per_second=operations_per_second,
                peak_memory_mb=psutil.Process().memory_info().rss / 1024 / 1024,
                timestamp=time.time()
            )
            self.metrics.append(metrics)

            self.test_results[test_name] = {
                "status": "passed",
                "metrics": asdict(metrics),
                "timestamp": time.time()
            }

            self.logger.info("Cleanup performance test passed",
                           execution_time=execution_time,
                           operations_per_second=operations_per_second)

        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Cleanup performance test failed", error=str(e))

    def _analyze_performance(self) -> Dict[str, Any]:
        """Analyze performance results against baseline."""
        analysis = {
            "regressions": [],
            "improvements": [],
            "new_tests": [],
            "overall_status": "unknown"
        }

        regression_threshold = 0.2  # 20% regression threshold
        improvement_threshold = 0.1  # 10% improvement threshold

        for metric in self.metrics:
            test_name = metric.test_name

            if test_name in self.baseline_metrics:
                baseline = self.baseline_metrics[test_name]

                # Analyze execution time
                if baseline.execution_time > 0:
                    time_change = (metric.execution_time - baseline.execution_time) / baseline.execution_time
                    if time_change > regression_threshold:
                        analysis["regressions"].append({
                            "test": test_name,
                            "metric": "execution_time",
                            "change_percent": time_change * 100,
                            "current": metric.execution_time,
                            "baseline": baseline.execution_time
                        })
                    elif time_change < -improvement_threshold:
                        analysis["improvements"].append({
                            "test": test_name,
                            "metric": "execution_time",
                            "improvement_percent": abs(time_change) * 100,
                            "current": metric.execution_time,
                            "baseline": baseline.execution_time
                        })

                # Analyze memory usage
                if baseline.memory_usage_mb > 0:
                    memory_change = (metric.memory_usage_mb - baseline.memory_usage_mb) / baseline.memory_usage_mb
                    if memory_change > regression_threshold:
                        analysis["regressions"].append({
                            "test": test_name,
                            "metric": "memory_usage",
                            "change_percent": memory_change * 100,
                            "current": metric.memory_usage_mb,
                            "baseline": baseline.memory_usage_mb
                        })

                # Analyze operations per second
                if baseline.operations_per_second > 0:
                    ops_change = (metric.operations_per_second - baseline.operations_per_second) / baseline.operations_per_second
                    if ops_change < -regression_threshold:
                        analysis["regressions"].append({
                            "test": test_name,
                            "metric": "operations_per_second",
                            "change_percent": ops_change * 100,
                            "current": metric.operations_per_second,
                            "baseline": baseline.operations_per_second
                        })
                    elif ops_change > improvement_threshold:
                        analysis["improvements"].append({
                            "test": test_name,
                            "metric": "operations_per_second",
                            "improvement_percent": ops_change * 100,
                            "current": metric.operations_per_second,
                            "baseline": baseline.operations_per_second
                        })
            else:
                analysis["new_tests"].append(test_name)

        # Determine overall status
        if len(analysis["regressions"]) == 0:
            analysis["overall_status"] = "passed"
        elif len(analysis["regressions"]) <= 2:
            analysis["overall_status"] = "warning"
        else:
            analysis["overall_status"] = "failed"

        return analysis

    def _generate_final_report(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive final performance report."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["status"] == "passed")
        failed_tests = total_tests - passed_tests

        report = {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
                "timestamp": time.time()
            },
            "performance_analysis": analysis,
            "test_results": self.test_results,
            "metrics": [asdict(metric) for metric in self.metrics],
            "performance_status": {
                "regression_detected": len(analysis["regressions"]) > 0,
                "improvements_detected": len(analysis["improvements"]) > 0,
                "overall_performance": analysis["overall_status"]
            }
        }

        return report


async def main():
    """Main function to run performance regression tests."""
    print("⚡ Starting Performance Regression Tests")
    print("=" * 60)

    # Check if we should save baseline
    save_baseline = "--save-baseline" in sys.argv

    runner = PerformanceRegressionTests(verbose=True)

    try:
        results = await runner.run_all_tests(save_baseline=save_baseline)

        # Print summary
        summary = results["summary"]
        print(f"\n📊 Performance Test Results Summary:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Passed: {summary['passed_tests']}")
        print(f"   Failed: {summary['failed_tests']}")
        print(f"   Success Rate: {summary['success_rate']:.1%}")

        # Print performance analysis
        analysis = results["performance_analysis"]
        print(f"\n⚡ Performance Analysis:")
        print(f"   Overall Status: {analysis['overall_status'].upper()}")
        print(f"   Regressions Detected: {len(analysis['regressions'])}")
        print(f"   Improvements Detected: {len(analysis['improvements'])}")
        print(f"   New Tests: {len(analysis['new_tests'])}")

        # Print regressions if any
        if analysis["regressions"]:
            print(f"\n🔴 Performance Regressions:")
            for regression in analysis["regressions"]:
                print(f"   - {regression['test']}.{regression['metric']}: "
                      f"{regression['change_percent']:+.1f}% change")

        # Print improvements if any
        if analysis["improvements"]:
            print(f"\n🟢 Performance Improvements:")
            for improvement in analysis["improvements"]:
                print(f"   + {improvement['test']}.{improvement['metric']}: "
                      f"{improvement['improvement_percent']:+.1f}% improvement")

        # Print individual test results
        print(f"\n📋 Individual Test Results:")
        for test_name, result in results["test_results"].items():
            status_icon = "✅" if result["status"] == "passed" else "❌"
            print(f"   {status_icon} {test_name}: {result['status']}")
            if result["status"] == "failed" and "error" in result:
                print(f"      Error: {result['error']}")

        print("\n" + "=" * 60)

        if save_baseline:
            print("💾 Baseline metrics saved for future comparisons.")

        if summary["failed_tests"] == 0 and analysis["overall_status"] != "failed":
            print("🎉 All performance tests passed! No significant regressions detected.")
            return 0
        else:
            print("⚠️  Performance issues detected. Please review the results.")
            return 1

    except Exception as e:
        print(f"❌ Performance test suite failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
