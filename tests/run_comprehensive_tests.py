#!/usr/bin/env python3
"""
Comprehensive test runner for the execution layer.

This script orchestrates all test suites including:
- Integration tests
- Browser integration tests  
- Performance regression tests
- Load testing infrastructure

Provides unified reporting and test management.
"""

import asyncio
import sys
import os
import time
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.logging.logger import StructuredLogger

# Import test runners
try:
    from tests.run_integration_tests import IntegrationTestRunner
    INTEGRATION_AVAILABLE = True
except ImportError:
    INTEGRATION_AVAILABLE = False

try:
    from tests.test_browser_integration import BrowserIntegrationTests
    BROWSER_AVAILABLE = True
except ImportError:
    BROWSER_AVAILABLE = False

try:
    from tests.test_performance_regression import PerformanceRegressionTests
    PERFORMANCE_AVAILABLE = True
except ImportError:
    PERFORMANCE_AVAILABLE = False

try:
    from tests.test_load_testing import LoadTestingInfrastructure
    LOAD_AVAILABLE = True
except ImportError:
    LOAD_AVAILABLE = False

try:
    from tests.test_configuration_validation import ConfigurationValidationTests
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False


class ComprehensiveTestRunner:
    """
    Comprehensive test runner that orchestrates all test suites.
    
    Manages execution of:
    - Integration tests (core functionality)
    - Browser integration tests (real browser automation)
    - Performance regression tests (performance monitoring)
    - Load testing (stress and concurrency testing)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, verbose: bool = True):
        """
        Initialize comprehensive test runner.
        
        Args:
            config: Test configuration options
            verbose: Whether to enable verbose logging
        """
        self.config = config or {}
        self.verbose = verbose
        self.logger = StructuredLogger("comprehensive_test_runner")
        
        # Test suite results
        self.suite_results: Dict[str, Dict[str, Any]] = {}
        self.start_time = None
        self.end_time = None
        
        # Test configuration
        self.run_integration = self.config.get("run_integration", True)
        self.run_browser = self.config.get("run_browser", True)
        self.run_performance = self.config.get("run_performance", True)
        self.run_load = self.config.get("run_load", True)
        self.run_config = self.config.get("run_config", True)
        self.save_performance_baseline = self.config.get("save_performance_baseline", False)
        self.headless_browser = self.config.get("headless_browser", True)
        self.max_load_workers = self.config.get("max_load_workers", 10)
        
        self.logger.info("Comprehensive test runner initialized", 
                        config=self.config, verbose=verbose)
    
    async def run_all_test_suites(self) -> Dict[str, Any]:
        """
        Run all available test suites.
        
        Returns:
            Dictionary containing comprehensive test results
        """
        self.start_time = time.time()
        
        self.logger.info("Starting comprehensive test suite execution")
        
        # Test Suite 1: Integration Tests
        if self.run_integration and INTEGRATION_AVAILABLE:
            await self._run_integration_tests()
        elif self.run_integration:
            self.logger.warning("Integration tests requested but not available")
        
        # Test Suite 2: Browser Integration Tests
        if self.run_browser and BROWSER_AVAILABLE:
            await self._run_browser_integration_tests()
        elif self.run_browser:
            self.logger.warning("Browser integration tests requested but not available")
        
        # Test Suite 3: Performance Regression Tests
        if self.run_performance and PERFORMANCE_AVAILABLE:
            await self._run_performance_regression_tests()
        elif self.run_performance:
            self.logger.warning("Performance regression tests requested but not available")
        
        # Test Suite 4: Load Testing
        if self.run_load and LOAD_AVAILABLE:
            await self._run_load_tests()
        elif self.run_load:
            self.logger.warning("Load tests requested but not available")

        # Test Suite 5: Configuration Validation
        if self.run_config and CONFIG_AVAILABLE:
            await self._run_configuration_tests()
        elif self.run_config:
            self.logger.warning("Configuration tests requested but not available")
        
        self.end_time = time.time()
        
        # Generate comprehensive report
        return self._generate_comprehensive_report()
    
    async def _run_integration_tests(self) -> None:
        """Run integration test suite."""
        suite_name = "integration_tests"
        self.logger.info("Running integration test suite")
        
        try:
            runner = IntegrationTestRunner(verbose=self.verbose)
            results = await runner.run_all_tests()
            
            self.suite_results[suite_name] = {
                "status": "passed" if results["summary"]["failed_tests"] == 0 else "failed",
                "results": results,
                "timestamp": time.time()
            }
            
            self.logger.info("Integration test suite completed",
                           success_rate=results["summary"]["success_rate"],
                           total_tests=results["summary"]["total_tests"])
            
        except Exception as e:
            self.suite_results[suite_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Integration test suite failed", error=str(e))
    
    async def _run_browser_integration_tests(self) -> None:
        """Run browser integration test suite."""
        suite_name = "browser_integration_tests"
        self.logger.info("Running browser integration test suite")
        
        try:
            runner = BrowserIntegrationTests(
                headless=self.headless_browser,
                verbose=self.verbose
            )
            results = await runner.run_all_tests()
            
            self.suite_results[suite_name] = {
                "status": "passed" if results["summary"]["failed_tests"] == 0 else "failed",
                "results": results,
                "timestamp": time.time()
            }
            
            self.logger.info("Browser integration test suite completed",
                           success_rate=results["summary"]["success_rate"],
                           total_tests=results["summary"]["total_tests"])
            
        except Exception as e:
            self.suite_results[suite_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Browser integration test suite failed", error=str(e))
    
    async def _run_performance_regression_tests(self) -> None:
        """Run performance regression test suite."""
        suite_name = "performance_regression_tests"
        self.logger.info("Running performance regression test suite")
        
        try:
            runner = PerformanceRegressionTests(verbose=self.verbose)
            results = await runner.run_all_tests(save_baseline=self.save_performance_baseline)
            
            # Determine status based on regressions
            analysis = results.get("performance_analysis", {})
            has_regressions = len(analysis.get("regressions", [])) > 0
            
            self.suite_results[suite_name] = {
                "status": "failed" if has_regressions else "passed",
                "results": results,
                "timestamp": time.time()
            }
            
            self.logger.info("Performance regression test suite completed",
                           success_rate=results["summary"]["success_rate"],
                           regressions=len(analysis.get("regressions", [])),
                           improvements=len(analysis.get("improvements", [])))
            
        except Exception as e:
            self.suite_results[suite_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Performance regression test suite failed", error=str(e))
    
    async def _run_load_tests(self) -> None:
        """Run load test suite."""
        suite_name = "load_tests"
        self.logger.info("Running load test suite")
        
        try:
            runner = LoadTestingInfrastructure(
                max_workers=self.max_load_workers,
                verbose=self.verbose
            )
            results = await runner.run_all_tests()
            
            self.suite_results[suite_name] = {
                "status": "passed" if results["summary"]["failed_tests"] == 0 else "failed",
                "results": results,
                "timestamp": time.time()
            }
            
            self.logger.info("Load test suite completed",
                           success_rate=results["summary"]["success_rate"],
                           total_operations=results["load_analysis"]["total_operations"])
            
        except Exception as e:
            self.suite_results[suite_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Load test suite failed", error=str(e))

    async def _run_configuration_tests(self) -> None:
        """Run configuration validation test suite."""
        suite_name = "configuration_tests"
        self.logger.info("Running configuration validation test suite")

        try:
            runner = ConfigurationValidationTests(verbose=self.verbose)
            results = await runner.run_all_tests()

            self.suite_results[suite_name] = {
                "status": "passed" if results["summary"]["failed_tests"] == 0 else "failed",
                "results": results,
                "timestamp": time.time()
            }

            self.logger.info("Configuration validation test suite completed",
                           success_rate=results["summary"]["success_rate"],
                           total_tests=results["summary"]["total_tests"])

        except Exception as e:
            self.suite_results[suite_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Configuration validation test suite failed", error=str(e))
    
    def _generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        total_suites = len(self.suite_results)
        passed_suites = sum(1 for result in self.suite_results.values() if result["status"] == "passed")
        failed_suites = total_suites - passed_suites
        
        execution_time = self.end_time - self.start_time if self.end_time and self.start_time else 0
        
        # Aggregate test counts
        total_tests = 0
        total_passed = 0
        total_failed = 0
        
        for suite_result in self.suite_results.values():
            if "results" in suite_result and "summary" in suite_result["results"]:
                summary = suite_result["results"]["summary"]
                total_tests += summary.get("total_tests", 0)
                total_passed += summary.get("passed_tests", 0)
                total_failed += summary.get("failed_tests", 0)
        
        # Determine overall system status
        system_ready = failed_suites == 0
        integration_ready = ("integration_tests" in self.suite_results and
                           self.suite_results["integration_tests"]["status"] == "passed")
        browser_ready = ("browser_integration_tests" in self.suite_results and
                        self.suite_results["browser_integration_tests"]["status"] == "passed")
        performance_stable = ("performance_regression_tests" in self.suite_results and
                            self.suite_results["performance_regression_tests"]["status"] == "passed")
        load_capable = ("load_tests" in self.suite_results and
                       self.suite_results["load_tests"]["status"] == "passed")
        config_valid = ("configuration_tests" in self.suite_results and
                       self.suite_results["configuration_tests"]["status"] == "passed")
        
        report = {
            "summary": {
                "total_suites": total_suites,
                "passed_suites": passed_suites,
                "failed_suites": failed_suites,
                "suite_success_rate": passed_suites / total_suites if total_suites > 0 else 0,
                "total_tests": total_tests,
                "total_passed": total_passed,
                "total_failed": total_failed,
                "overall_success_rate": total_passed / total_tests if total_tests > 0 else 0,
                "execution_time": execution_time,
                "timestamp": time.time()
            },
            "suite_results": self.suite_results,
            "system_status": {
                "system_ready": system_ready,
                "integration_ready": integration_ready,
                "browser_automation_ready": browser_ready,
                "performance_stable": performance_stable,
                "load_handling_capable": load_capable,
                "configuration_valid": config_valid,
                "production_ready": system_ready and integration_ready and performance_stable and config_valid
            },
            "availability": {
                "integration_tests": INTEGRATION_AVAILABLE,
                "browser_integration_tests": BROWSER_AVAILABLE,
                "performance_regression_tests": PERFORMANCE_AVAILABLE,
                "load_tests": LOAD_AVAILABLE,
                "configuration_tests": CONFIG_AVAILABLE
            }
        }
        
        return report


def parse_arguments() -> Dict[str, Any]:
    """Parse command line arguments."""
    config = {
        "run_integration": True,
        "run_browser": True,
        "run_performance": True,
        "run_load": True,
        "run_config": True,
        "save_performance_baseline": False,
        "headless_browser": True,
        "max_load_workers": 10,
        "output_file": None
    }

    # Parse command line arguments
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]

        if arg == "--skip-integration":
            config["run_integration"] = False
        elif arg == "--skip-browser":
            config["run_browser"] = False
        elif arg == "--skip-performance":
            config["run_performance"] = False
        elif arg == "--skip-load":
            config["run_load"] = False
        elif arg == "--skip-config":
            config["run_config"] = False
        elif arg == "--save-baseline":
            config["save_performance_baseline"] = True
        elif arg == "--no-headless":
            config["headless_browser"] = False
        elif arg == "--workers" and i + 1 < len(args):
            try:
                config["max_load_workers"] = int(args[i + 1])
                i += 1
            except ValueError:
                print(f"Invalid workers value: {args[i + 1]}")
        elif arg == "--output" and i + 1 < len(args):
            config["output_file"] = args[i + 1]
            i += 1
        elif arg == "--help":
            print_help()
            sys.exit(0)

        i += 1

    return config


def print_help():
    """Print help message."""
    print("""
Comprehensive Test Runner for Browser-Use Automation

Usage: python tests/run_comprehensive_tests.py [OPTIONS]

Options:
  --skip-integration     Skip integration tests
  --skip-browser         Skip browser integration tests
  --skip-performance     Skip performance regression tests
  --skip-load           Skip load tests
  --skip-config         Skip configuration validation tests
  --save-baseline       Save performance baseline
  --no-headless         Run browser tests in non-headless mode
  --workers N           Set max load test workers (default: 10)
  --output FILE         Save results to JSON file
  --help                Show this help message

Examples:
  # Run all tests
  python tests/run_comprehensive_tests.py

  # Run only integration and browser tests
  python tests/run_comprehensive_tests.py --skip-performance --skip-load

  # Run with performance baseline saving
  python tests/run_comprehensive_tests.py --save-baseline

  # Run with custom load test workers
  python tests/run_comprehensive_tests.py --workers 20
""")


async def main():
    """Main function to run comprehensive tests."""
    print("🚀 Starting Comprehensive Test Suite")
    print("=" * 80)

    # Parse configuration
    config = parse_arguments()

    # Show configuration
    print("📋 Test Configuration:")
    print(f"   Integration Tests: {'✅' if config['run_integration'] else '❌'}")
    print(f"   Browser Tests: {'✅' if config['run_browser'] else '❌'}")
    print(f"   Performance Tests: {'✅' if config['run_performance'] else '❌'}")
    print(f"   Load Tests: {'✅' if config['run_load'] else '❌'}")
    print(f"   Configuration Tests: {'✅' if config['run_config'] else '❌'}")
    print(f"   Headless Browser: {'✅' if config['headless_browser'] else '❌'}")
    print(f"   Load Workers: {config['max_load_workers']}")
    if config['save_performance_baseline']:
        print("   💾 Will save performance baseline")
    print()

    runner = ComprehensiveTestRunner(config=config, verbose=True)

    try:
        results = await runner.run_all_test_suites()

        # Print summary
        summary = results["summary"]
        print(f"\n📊 Comprehensive Test Results Summary:")
        print(f"   Total Test Suites: {summary['total_suites']}")
        print(f"   Passed Suites: {summary['passed_suites']}")
        print(f"   Failed Suites: {summary['failed_suites']}")
        print(f"   Suite Success Rate: {summary['suite_success_rate']:.1%}")
        print(f"   Total Individual Tests: {summary['total_tests']}")
        print(f"   Total Passed Tests: {summary['total_passed']}")
        print(f"   Total Failed Tests: {summary['total_failed']}")
        print(f"   Overall Success Rate: {summary['overall_success_rate']:.1%}")
        print(f"   Total Execution Time: {summary['execution_time']:.2f}s")

        # Print system status
        status = results["system_status"]
        print(f"\n🏥 System Status:")
        print(f"   System Ready: {'✅' if status['system_ready'] else '❌'}")
        print(f"   Integration Ready: {'✅' if status['integration_ready'] else '❌'}")
        print(f"   Browser Automation Ready: {'✅' if status['browser_automation_ready'] else '❌'}")
        print(f"   Performance Stable: {'✅' if status['performance_stable'] else '❌'}")
        print(f"   Load Handling Capable: {'✅' if status['load_handling_capable'] else '❌'}")
        print(f"   Configuration Valid: {'✅' if status['configuration_valid'] else '❌'}")
        print(f"   Production Ready: {'✅' if status['production_ready'] else '❌'}")

        # Print suite results
        print(f"\n📋 Test Suite Results:")
        for suite_name, suite_result in results["suite_results"].items():
            status_icon = "✅" if suite_result["status"] == "passed" else "❌"
            print(f"   {status_icon} {suite_name}: {suite_result['status']}")
            if suite_result["status"] == "failed" and "error" in suite_result:
                print(f"      Error: {suite_result['error']}")
            elif "results" in suite_result and "summary" in suite_result["results"]:
                suite_summary = suite_result["results"]["summary"]
                print(f"      Tests: {suite_summary.get('total_tests', 0)}, "
                      f"Success: {suite_summary.get('success_rate', 0):.1%}")

        # Save results if requested
        if config["output_file"]:
            try:
                with open(config["output_file"], 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                print(f"\n💾 Results saved to: {config['output_file']}")
            except Exception as e:
                print(f"\n❌ Failed to save results: {e}")

        print("\n" + "=" * 80)

        if status["production_ready"]:
            print("🎉 All critical tests passed! System is production ready.")
            return 0
        elif status["system_ready"]:
            print("✅ System is functional but may have performance or load issues.")
            return 0
        else:
            print("⚠️  Critical issues detected. System not ready for production.")
            return 1

    except Exception as e:
        print(f"❌ Comprehensive test suite failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
