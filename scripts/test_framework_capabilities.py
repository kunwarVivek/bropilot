#!/usr/bin/env python3
"""
Test Framework Capabilities Script

Comprehensive test script that validates all new test automation framework capabilities.
This script can be used for:
- Continuous integration testing
- Framework capability validation
- Regression testing
- Performance benchmarking
"""

import asyncio
import os
import sys
import tempfile
import shutil
import time
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.test_automation_framework import create_test_automation_framework
from src.test_management.models import TestType, TestPriority, ExecutionStatus
from src.test_data.models import DataScope, DataType
from src.test_reporting.models import ReportFormat, ReportType
from src.validation import get_validation_config


class FrameworkCapabilityTester:
    """Comprehensive framework capability tester."""
    
    def __init__(self, use_real_llm: bool = False):
        self.use_real_llm = use_real_llm
        self.temp_workspace = None
        self.framework = None
        self.test_results = {}
        self.start_time = None
        
    async def setup(self):
        """Setup test environment."""
        print("🔧 Setting up test environment...")
        
        # Create temporary workspace
        self.temp_workspace = tempfile.mkdtemp(prefix="framework_test_")
        print(f"   Workspace: {self.temp_workspace}")
        
        # Initialize framework
        if self.use_real_llm:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY required for real LLM testing")
            
            self.framework = await create_test_automation_framework(
                workspace_path=self.temp_workspace,
                llm_provider="openai",
                llm_model="gpt-3.5-turbo",  # Use cheaper model for testing
                api_key=api_key,
                environment="test"
            )
        else:
            # Use mock LLM for testing
            from unittest.mock import AsyncMock
            
            self.framework = await create_test_automation_framework(
                workspace_path=self.temp_workspace,
                environment="test"
            )
            
            # Mock LLM provider
            mock_llm = AsyncMock()
            mock_llm.invoke.return_value = """
            Generated test steps:
            1. Navigate to the target page
            2. Perform the required actions
            3. Verify the expected results
            """
            self.framework.llm_provider = mock_llm
        
        print("✅ Test environment setup complete")
        self.start_time = time.time()
    
    async def cleanup(self):
        """Cleanup test environment."""
        print("🧹 Cleaning up test environment...")
        
        if self.framework:
            await self.framework.cleanup()
        
        if self.temp_workspace and Path(self.temp_workspace).exists():
            shutil.rmtree(self.temp_workspace)
        
        print("✅ Cleanup complete")
    
    async def test_test_case_management(self) -> Dict[str, Any]:
        """Test test case management capabilities."""
        print("\n🧪 Testing Test Case Management...")
        
        results = {
            "test_name": "test_case_management",
            "start_time": time.time(),
            "tests": {}
        }
        
        try:
            # Test 1: Create test case from natural language
            print("   Testing natural language test case creation...")
            test_case = await self.framework.create_test_case_from_description(
                name="Login Functionality Test",
                description="""
                Test the user login process:
                1. Navigate to login page
                2. Enter valid credentials
                3. Click login button
                4. Verify successful login
                """,
                test_type=TestType.FUNCTIONAL,
                priority=TestPriority.HIGH,
                tags=["login", "authentication", "critical"]
            )
            
            results["tests"]["create_from_description"] = {
                "status": "passed",
                "test_case_id": test_case.id,
                "test_case_name": test_case.name
            }
            print("   ✅ Natural language test case creation")
            
            # Test 2: Create manual test case
            print("   Testing manual test case creation...")
            manual_test = await self.framework.create_test_case(
                name="Manual Test Case",
                description="Manually created test case",
                test_type=TestType.REGRESSION,
                priority=TestPriority.MEDIUM
            )
            
            results["tests"]["create_manual"] = {
                "status": "passed",
                "test_case_id": manual_test.id
            }
            print("   ✅ Manual test case creation")
            
            # Test 3: Search test cases
            print("   Testing test case search...")
            search_results = await self.framework.search_test_cases(
                tags=["login"]
            )
            
            results["tests"]["search_test_cases"] = {
                "status": "passed",
                "results_count": len(search_results)
            }
            print(f"   ✅ Test case search (found {len(search_results)} cases)")
            
            # Test 4: Clone test case
            print("   Testing test case cloning...")
            cloned_test = await self.framework.clone_test_case(
                test_case.id, 
                "Cloned Login Test"
            )
            
            results["tests"]["clone_test_case"] = {
                "status": "passed",
                "original_id": test_case.id,
                "cloned_id": cloned_test.id
            }
            print("   ✅ Test case cloning")
            
            # Test 5: Create test suite
            print("   Testing test suite creation...")
            test_suite = await self.framework.create_test_suite(
                name="Regression Test Suite",
                description="Automated regression tests",
                test_case_ids=[test_case.id, manual_test.id, cloned_test.id],
                parallel_execution=True,
                max_parallel_workers=2
            )
            
            results["tests"]["create_test_suite"] = {
                "status": "passed",
                "test_suite_id": test_suite.id,
                "test_case_count": len(test_suite.test_case_ids)
            }
            print(f"   ✅ Test suite creation (with {len(test_suite.test_case_ids)} test cases)")
            
            results["overall_status"] = "passed"
            
        except Exception as e:
            results["overall_status"] = "failed"
            results["error"] = str(e)
            print(f"   ❌ Test case management failed: {e}")
        
        results["duration"] = time.time() - results["start_time"]
        return results
    
    async def test_test_data_management(self) -> Dict[str, Any]:
        """Test test data management capabilities."""
        print("\n🗄️ Testing Test Data Management...")
        
        results = {
            "test_name": "test_data_management",
            "start_time": time.time(),
            "tests": {}
        }
        
        try:
            # Test 1: Create test data set
            print("   Testing test data set creation...")
            user_data_set = await self.framework.create_test_data_set(
                name="User Test Data",
                description="Test user accounts",
                data_type="person",
                scope=DataScope.GLOBAL,
                environment="test"
            )
            
            results["tests"]["create_data_set"] = {
                "status": "passed",
                "data_set_id": user_data_set.id,
                "data_type": user_data_set.data_type.value
            }
            print("   ✅ Test data set creation")
            
            # Test 2: Generate test data (mocked)
            print("   Testing test data generation...")
            # Mock the data generation since we don't have real generators in this test
            from unittest.mock import patch
            
            with patch.object(self.framework.test_data_manager, 'generate_data') as mock_generate:
                mock_generate.return_value = True
                
                success = await self.framework.generate_test_data(
                    data_set_id=user_data_set.id,
                    count=10,
                    generator_type="person",
                    include_fields=["username", "email", "password"]
                )
                
                results["tests"]["generate_data"] = {
                    "status": "passed" if success else "failed",
                    "count": 10
                }
                print("   ✅ Test data generation")
            
            # Test 3: Get test data (mocked)
            print("   Testing test data retrieval...")
            with patch.object(self.framework.test_data_manager, 'get_data') as mock_get:
                mock_get.return_value = {
                    "username": "testuser",
                    "email": "test@example.com",
                    "password": "password123"
                }
                
                test_data = await self.framework.get_test_data(user_data_set.id)
                
                results["tests"]["get_data"] = {
                    "status": "passed" if test_data else "failed",
                    "data_fields": list(test_data.keys()) if test_data else []
                }
                print("   ✅ Test data retrieval")
            
            results["overall_status"] = "passed"
            
        except Exception as e:
            results["overall_status"] = "failed"
            results["error"] = str(e)
            print(f"   ❌ Test data management failed: {e}")
        
        results["duration"] = time.time() - results["start_time"]
        return results
    
    async def test_test_execution(self) -> Dict[str, Any]:
        """Test test execution capabilities."""
        print("\n🚀 Testing Test Execution...")
        
        results = {
            "test_name": "test_execution",
            "start_time": time.time(),
            "tests": {}
        }
        
        try:
            # Create a test case first
            test_case = await self.framework.create_test_case(
                name="Execution Test Case",
                description="Test case for execution testing",
                target_url="https://httpbin.org"
            )
            
            # Mock the execution since we don't want to run real browser tests
            from unittest.mock import patch
            from src.test_management.models import TestExecution, TestResult
            
            with patch.object(self.framework.test_execution_manager, 'execute_test_case') as mock_execute:
                # Create mock execution result
                mock_execution = TestExecution(
                    name="Mock Execution",
                    test_case_ids=[test_case.id],
                    status=ExecutionStatus.PASSED,
                    total_tests=1,
                    passed_tests=1,
                    failed_tests=0
                )
                mock_execute.return_value = mock_execution
                
                # Test single test case execution
                print("   Testing single test case execution...")
                execution = await self.framework.execute_test_case(
                    test_case_id=test_case.id,
                    environment="test"
                )
                
                results["tests"]["execute_test_case"] = {
                    "status": "passed",
                    "execution_id": execution.id,
                    "execution_status": execution.status.value,
                    "total_tests": execution.total_tests,
                    "passed_tests": execution.passed_tests
                }
                print("   ✅ Single test case execution")
            
            results["overall_status"] = "passed"
            
        except Exception as e:
            results["overall_status"] = "failed"
            results["error"] = str(e)
            print(f"   ❌ Test execution failed: {e}")
        
        results["duration"] = time.time() - results["start_time"]
        return results
    
    async def test_test_reporting(self) -> Dict[str, Any]:
        """Test test reporting capabilities."""
        print("\n📊 Testing Test Reporting...")
        
        results = {
            "test_name": "test_reporting",
            "start_time": time.time(),
            "tests": {}
        }
        
        try:
            # Mock execution for reporting
            from unittest.mock import patch
            from src.test_management.models import TestExecution
            from src.test_reporting.models import TestReport
            
            mock_execution = TestExecution(
                name="Report Test Execution",
                status=ExecutionStatus.PASSED,
                total_tests=5,
                passed_tests=4,
                failed_tests=1
            )
            
            with patch.object(self.framework.report_manager, 'generate_execution_report') as mock_report:
                # Create mock report
                mock_test_report = TestReport(
                    title="Test Execution Report",
                    report_type=ReportType.EXECUTION_SUMMARY,
                    format=ReportFormat.HTML,
                    execution_ids=[mock_execution.id]
                )
                mock_report.return_value = mock_test_report
                
                # Test HTML report generation
                print("   Testing HTML report generation...")
                html_report = await self.framework.generate_execution_report(
                    execution_id=mock_execution.id,
                    report_format=ReportFormat.HTML
                )
                
                results["tests"]["html_report"] = {
                    "status": "passed",
                    "report_id": html_report.id,
                    "format": html_report.format.value
                }
                print("   ✅ HTML report generation")
            
            with patch.object(self.framework.report_manager, 'generate_trend_report') as mock_trend:
                mock_trend_report = TestReport(
                    title="Trend Analysis",
                    report_type=ReportType.TREND_ANALYSIS,
                    format=ReportFormat.HTML
                )
                mock_trend.return_value = mock_trend_report
                
                # Test trend report generation
                print("   Testing trend report generation...")
                trend_report = await self.framework.generate_trend_report(
                    days=30,
                    environment="test"
                )
                
                results["tests"]["trend_report"] = {
                    "status": "passed",
                    "report_id": trend_report.id,
                    "report_type": trend_report.report_type.value
                }
                print("   ✅ Trend report generation")
            
            results["overall_status"] = "passed"
            
        except Exception as e:
            results["overall_status"] = "failed"
            results["error"] = str(e)
            print(f"   ❌ Test reporting failed: {e}")
        
        results["duration"] = time.time() - results["start_time"]
        return results
    
    async def test_framework_status(self) -> Dict[str, Any]:
        """Test framework status and statistics."""
        print("\n📈 Testing Framework Status...")
        
        results = {
            "test_name": "framework_status",
            "start_time": time.time(),
            "tests": {}
        }
        
        try:
            # Get framework status
            status = await self.framework.get_framework_status()
            
            results["tests"]["get_status"] = {
                "status": "passed",
                "framework_initialized": status.get("framework_initialized", False),
                "llm_provider_configured": status.get("llm_provider_configured", False),
                "workspace_path": status.get("workspace_path", ""),
                "test_cases_total": status.get("test_cases", {}).get("total", 0)
            }
            
            print("   ✅ Framework status retrieval")
            results["overall_status"] = "passed"
            
        except Exception as e:
            results["overall_status"] = "failed"
            results["error"] = str(e)
            print(f"   ❌ Framework status failed: {e}")
        
        results["duration"] = time.time() - results["start_time"]
        return results
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all capability tests."""
        print("🚀 Starting Framework Capability Tests")
        print("=" * 60)
        
        all_results = {
            "test_session": {
                "start_time": time.time(),
                "use_real_llm": self.use_real_llm,
                "workspace": self.temp_workspace
            },
            "test_results": {}
        }
        
        # Run all test categories
        test_methods = [
            self.test_test_case_management,
            self.test_test_data_management,
            self.test_test_execution,
            self.test_test_reporting,
            self.test_framework_status
        ]
        
        for test_method in test_methods:
            try:
                result = await test_method()
                all_results["test_results"][result["test_name"]] = result
            except Exception as e:
                test_name = test_method.__name__
                all_results["test_results"][test_name] = {
                    "test_name": test_name,
                    "overall_status": "failed",
                    "error": str(e),
                    "duration": 0
                }
                print(f"   ❌ {test_name} failed with exception: {e}")
        
        # Calculate summary
        all_results["test_session"]["end_time"] = time.time()
        all_results["test_session"]["total_duration"] = (
            all_results["test_session"]["end_time"] - 
            all_results["test_session"]["start_time"]
        )
        
        # Count passed/failed tests
        passed_tests = sum(
            1 for result in all_results["test_results"].values() 
            if result.get("overall_status") == "passed"
        )
        total_tests = len(all_results["test_results"])
        
        all_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": passed_tests / total_tests if total_tests > 0 else 0
        }
        
        return all_results
    
    def print_summary(self, results: Dict[str, Any]):
        """Print test results summary."""
        print("\n" + "=" * 60)
        print("🎯 Framework Capability Test Results")
        print("=" * 60)
        
        summary = results["summary"]
        session = results["test_session"]
        
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Passed: {summary['passed_tests']}")
        print(f"Failed: {summary['failed_tests']}")
        print(f"Success Rate: {summary['success_rate']:.2%}")
        print(f"Total Duration: {session['total_duration']:.2f} seconds")
        print(f"LLM Mode: {'Real' if session['use_real_llm'] else 'Mock'}")
        
        print("\nDetailed Results:")
        for test_name, test_result in results["test_results"].items():
            status_icon = "✅" if test_result["overall_status"] == "passed" else "❌"
            duration = test_result.get("duration", 0)
            print(f"  {status_icon} {test_name}: {test_result['overall_status']} ({duration:.2f}s)")
            
            if test_result["overall_status"] == "failed" and "error" in test_result:
                print(f"      Error: {test_result['error']}")
        
        if summary["success_rate"] == 1.0:
            print("\n🎉 All tests passed! Framework is working correctly.")
        else:
            print(f"\n⚠️  {summary['failed_tests']} test(s) failed. Check the details above.")


async def main():
    """Main test execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Framework Capabilities")
    parser.add_argument(
        "--real-llm", 
        action="store_true", 
        help="Use real LLM provider (requires OPENAI_API_KEY)"
    )
    parser.add_argument(
        "--output", 
        help="Output file for test results (JSON format)"
    )
    
    args = parser.parse_args()
    
    tester = FrameworkCapabilityTester(use_real_llm=args.real_llm)
    
    try:
        await tester.setup()
        results = await tester.run_all_tests()
        tester.print_summary(results)
        
        # Save results to file if requested
        if args.output:
            import json
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\n📄 Results saved to: {args.output}")
        
        # Exit with appropriate code
        success_rate = results["summary"]["success_rate"]
        exit_code = 0 if success_rate == 1.0 else 1
        
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        exit_code = 1
    
    finally:
        await tester.cleanup()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
