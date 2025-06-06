#!/usr/bin/env python3
"""
Test suite for the Advanced Error Recovery System.

This module tests the execution layer error recovery capabilities
including pattern classification, recovery strategies, and analytics.
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.exceptions import TaskExecutionError, BrowserError, TimeoutError
from src.execution.error_recovery import (
    ExecutionErrorRecovery, RecoveryContext, RecoveryPriority,
    ExecutionErrorCategory
)
from src.infrastructure.logging.logger import StructuredLogger


class ErrorRecoveryTestSuite:
    """Test suite for execution error recovery system."""
    
    def __init__(self):
        """Initialize test suite."""
        self.logger = StructuredLogger("error_recovery_tests")
        self.recovery_system = ExecutionErrorRecovery(
            llm_provider=None,  # No LLM for testing
            enable_learning=True,
            max_recovery_attempts=3
        )
        
        self.test_results = {}
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all error recovery tests."""
        self.logger.info("Starting error recovery test suite")
        
        # Start background recovery processor
        await self.recovery_system.start_background_recovery()
        
        try:
            # Test 1: Error Classification
            await self._test_error_classification()
            
            # Test 2: Immediate Recovery
            await self._test_immediate_recovery()
            
            # Test 3: Background Recovery
            await self._test_background_recovery()
            
            # Test 4: Recovery Strategies
            await self._test_recovery_strategies()
            
            # Test 5: Metrics and Analytics
            await self._test_metrics_analytics()
            
            # Test 6: Recovery Report Generation
            await self._test_report_generation()
            
        finally:
            # Stop background processor
            await self.recovery_system.stop_background_recovery()
        
        return self._generate_test_report()
    
    async def _test_error_classification(self) -> None:
        """Test error classification functionality."""
        test_name = "error_classification"
        self.logger.info("Testing error classification")
        
        try:
            test_cases = [
                (TaskExecutionError("Adapter connection failed"), "adapter_failure"),
                (BrowserError("Browser crashed unexpectedly"), "browser_crash"),
                (TimeoutError("Operation timed out"), "task_timeout"),
                (Exception("Memory limit exceeded"), "resource_exhaustion"),
                (ImportError("Module not found"), "dependency_failure"),
                (ValueError("Invalid configuration"), "configuration_invalid")
            ]
            
            correct_classifications = 0
            total_tests = len(test_cases)
            
            for error, expected_category in test_cases:
                context = RecoveryContext(
                    task_id="test_task",
                    adapter_id="test_adapter"
                )
                
                classified_category = self.recovery_system._classify_execution_error(error, context)
                
                if expected_category in classified_category:
                    correct_classifications += 1
                    self.logger.info(
                        "Classification correct",
                        error_type=type(error).__name__,
                        expected=expected_category,
                        actual=classified_category
                    )
                else:
                    self.logger.warning(
                        "Classification mismatch",
                        error_type=type(error).__name__,
                        expected=expected_category,
                        actual=classified_category
                    )
            
            accuracy = correct_classifications / total_tests
            
            self.test_results[test_name] = {
                "status": "passed" if accuracy >= 0.8 else "failed",
                "accuracy": accuracy,
                "correct_classifications": correct_classifications,
                "total_tests": total_tests,
                "details": "Error classification accuracy test"
            }
            
            self.logger.info("Error classification test completed", accuracy=accuracy)
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "details": "Error classification test failed"
            }
            self.logger.error("Error classification test failed", error=str(e))
    
    async def _test_immediate_recovery(self) -> None:
        """Test immediate recovery for high-priority errors."""
        test_name = "immediate_recovery"
        self.logger.info("Testing immediate recovery")
        
        try:
            # Test immediate recovery
            error = TaskExecutionError("Test adapter failure")
            context = RecoveryContext(
                task_id="test_task_immediate",
                adapter_id="test_adapter",
                priority=RecoveryPriority.IMMEDIATE,
                max_retries=2
            )
            
            start_time = time.time()
            recovery_result = await self.recovery_system.handle_execution_error(
                error, context, "test_correlation_id"
            )
            recovery_time = time.time() - start_time
            
            # Verify immediate processing (not queued)
            is_immediate = not recovery_result.get("queued_for_background", False)
            
            self.test_results[test_name] = {
                "status": "passed" if is_immediate else "failed",
                "recovery_time": recovery_time,
                "is_immediate": is_immediate,
                "recovery_result": recovery_result,
                "details": "Immediate recovery processing test"
            }
            
            self.logger.info("Immediate recovery test completed", 
                           recovery_time=recovery_time,
                           is_immediate=is_immediate)
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "details": "Immediate recovery test failed"
            }
            self.logger.error("Immediate recovery test failed", error=str(e))
    
    async def _test_background_recovery(self) -> None:
        """Test background recovery for normal priority errors."""
        test_name = "background_recovery"
        self.logger.info("Testing background recovery")
        
        try:
            # Test background recovery
            error = BrowserError("Test browser issue")
            context = RecoveryContext(
                task_id="test_task_background",
                browser_session_id="test_session",
                priority=RecoveryPriority.NORMAL
            )
            
            initial_queue_size = self.recovery_system.recovery_queue.qsize()
            
            recovery_result = await self.recovery_system.handle_execution_error(
                error, context, "test_correlation_id"
            )
            
            # Verify background queuing
            is_queued = recovery_result.get("queued_for_background", False)
            queue_increased = self.recovery_system.recovery_queue.qsize() > initial_queue_size
            
            # Wait a bit for background processing
            await asyncio.sleep(0.5)
            
            self.test_results[test_name] = {
                "status": "passed" if is_queued and queue_increased else "failed",
                "is_queued": is_queued,
                "queue_increased": queue_increased,
                "recovery_result": recovery_result,
                "details": "Background recovery queuing test"
            }
            
            self.logger.info("Background recovery test completed",
                           is_queued=is_queued,
                           queue_increased=queue_increased)
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "details": "Background recovery test failed"
            }
            self.logger.error("Background recovery test failed", error=str(e))
    
    async def _test_recovery_strategies(self) -> None:
        """Test individual recovery strategies."""
        test_name = "recovery_strategies"
        self.logger.info("Testing recovery strategies")
        
        try:
            strategies_tested = 0
            strategies_successful = 0
            
            # Test different strategy types
            test_strategies = [
                ("restart_adapter", TaskExecutionError("Adapter failed")),
                ("retry_with_backoff", TimeoutError("Operation timeout")),
                ("cleanup_resources", Exception("Memory exhausted")),
                ("generic_retry", Exception("Unknown error"))
            ]
            
            for strategy_name, test_error in test_strategies:
                if strategy_name in self.recovery_system.recovery_strategies:
                    try:
                        context = RecoveryContext(
                            task_id=f"test_{strategy_name}",
                            adapter_id="test_adapter",
                            retry_count=0
                        )
                        
                        strategy_func = self.recovery_system.recovery_strategies[strategy_name]
                        success = await strategy_func(test_error, context, {})
                        
                        strategies_tested += 1
                        if success:
                            strategies_successful += 1
                        
                        self.logger.info(
                            "Strategy tested",
                            strategy=strategy_name,
                            success=success
                        )
                        
                    except Exception as e:
                        self.logger.error(
                            "Strategy test failed",
                            strategy=strategy_name,
                            error=str(e)
                        )
                        strategies_tested += 1
            
            success_rate = strategies_successful / strategies_tested if strategies_tested > 0 else 0
            
            self.test_results[test_name] = {
                "status": "passed" if success_rate >= 0.5 else "failed",
                "strategies_tested": strategies_tested,
                "strategies_successful": strategies_successful,
                "success_rate": success_rate,
                "details": "Individual recovery strategy tests"
            }
            
            self.logger.info("Recovery strategies test completed",
                           success_rate=success_rate,
                           strategies_tested=strategies_tested)
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "details": "Recovery strategies test failed"
            }
            self.logger.error("Recovery strategies test failed", error=str(e))
    
    async def _test_metrics_analytics(self) -> None:
        """Test metrics and analytics functionality."""
        test_name = "metrics_analytics"
        self.logger.info("Testing metrics and analytics")
        
        try:
            # Generate some test errors first
            for i in range(5):
                error = TaskExecutionError(f"Test error {i}")
                context = RecoveryContext(
                    task_id=f"test_metrics_{i}",
                    priority=RecoveryPriority.IMMEDIATE
                )
                await self.recovery_system.handle_execution_error(error, context)
            
            # Get metrics
            metrics = self.recovery_system.get_recovery_metrics()
            analytics = self.recovery_system.get_error_analytics()
            
            # Verify metrics structure
            required_metrics = [
                "total_errors", "total_recoveries", "recovery_success_rate",
                "average_recovery_time", "errors_by_category"
            ]
            
            metrics_complete = all(key in metrics for key in required_metrics)
            analytics_available = "total_errors_analyzed" in analytics
            
            self.test_results[test_name] = {
                "status": "passed" if metrics_complete and analytics_available else "failed",
                "metrics_complete": metrics_complete,
                "analytics_available": analytics_available,
                "total_errors": metrics.get("total_errors", 0),
                "details": "Metrics and analytics functionality test"
            }
            
            self.logger.info("Metrics and analytics test completed",
                           metrics_complete=metrics_complete,
                           analytics_available=analytics_available)
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "details": "Metrics and analytics test failed"
            }
            self.logger.error("Metrics and analytics test failed", error=str(e))
    
    async def _test_report_generation(self) -> None:
        """Test recovery report generation."""
        test_name = "report_generation"
        self.logger.info("Testing report generation")
        
        try:
            # Generate recovery report
            report = await self.recovery_system.generate_recovery_report()
            
            # Verify report structure
            required_sections = [
                "report_timestamp", "metrics", "analytics", 
                "pattern_analysis", "recommendations", "system_health"
            ]
            
            report_complete = all(section in report for section in required_sections)
            has_recommendations = len(report.get("recommendations", [])) >= 0
            
            self.test_results[test_name] = {
                "status": "passed" if report_complete else "failed",
                "report_complete": report_complete,
                "has_recommendations": has_recommendations,
                "report_sections": list(report.keys()),
                "details": "Recovery report generation test"
            }
            
            self.logger.info("Report generation test completed",
                           report_complete=report_complete,
                           sections=len(report.keys()))
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "details": "Report generation test failed"
            }
            self.logger.error("Report generation test failed", error=str(e))
    
    def _generate_test_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["status"] == "passed")
        failed_tests = total_tests - passed_tests
        
        return {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
                "timestamp": time.time()
            },
            "test_results": self.test_results,
            "error_recovery_status": {
                "system_operational": failed_tests == 0,
                "classification_working": self.test_results.get("error_classification", {}).get("status") == "passed",
                "immediate_recovery_working": self.test_results.get("immediate_recovery", {}).get("status") == "passed",
                "background_recovery_working": self.test_results.get("background_recovery", {}).get("status") == "passed",
                "strategies_functional": self.test_results.get("recovery_strategies", {}).get("status") == "passed",
                "analytics_available": self.test_results.get("metrics_analytics", {}).get("status") == "passed"
            }
        }


async def main():
    """Main function to run error recovery tests."""
    print("🔧 Starting Error Recovery System Tests")
    print("=" * 60)
    
    test_suite = ErrorRecoveryTestSuite()
    
    try:
        results = await test_suite.run_all_tests()
        
        # Print summary
        summary = results["summary"]
        print(f"\n📊 Error Recovery Test Results:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Passed: {summary['passed_tests']}")
        print(f"   Failed: {summary['failed_tests']}")
        print(f"   Success Rate: {summary['success_rate']:.1%}")
        
        # Print system status
        status = results["error_recovery_status"]
        print(f"\n🔧 Error Recovery System Status:")
        print(f"   System Operational: {'✅' if status['system_operational'] else '❌'}")
        print(f"   Classification Working: {'✅' if status['classification_working'] else '❌'}")
        print(f"   Immediate Recovery: {'✅' if status['immediate_recovery_working'] else '❌'}")
        print(f"   Background Recovery: {'✅' if status['background_recovery_working'] else '❌'}")
        print(f"   Strategies Functional: {'✅' if status['strategies_functional'] else '❌'}")
        print(f"   Analytics Available: {'✅' if status['analytics_available'] else '❌'}")
        
        # Print individual test results
        print(f"\n📋 Individual Test Results:")
        for test_name, result in results["test_results"].items():
            status_icon = "✅" if result["status"] == "passed" else "❌"
            print(f"   {status_icon} {test_name}: {result['status']}")
            if result["status"] == "failed" and "error" in result:
                print(f"      Error: {result['error']}")
        
        print("\n" + "=" * 60)
        
        if summary["failed_tests"] == 0:
            print("🎉 All error recovery tests passed! System is ready for production.")
            return 0
        else:
            print("⚠️  Some error recovery tests failed. Please review the results.")
            return 1
            
    except Exception as e:
        print(f"❌ Error recovery test suite failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
