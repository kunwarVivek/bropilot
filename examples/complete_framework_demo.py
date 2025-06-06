#!/usr/bin/env python3
"""
Complete Test Automation Framework Demo

Demonstrates the full capabilities of the LLM & browser-use test automation framework
including test case management, test data management, and advanced reporting.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.test_automation_framework import create_test_automation_framework
from src.test_management.models import TestType, TestPriority
from src.test_data.models import DataScope, DataType
from src.test_reporting.models import ReportFormat


async def demo_test_case_management(framework):
    """Demo 1: Test Case Management"""
    print("🧪 Demo 1: Test Case Management")
    print("=" * 50)
    
    # Create test cases from natural language
    login_test = await framework.create_test_case_from_description(
        name="User Login Test",
        description="""
        Test the user login functionality:
        1. Navigate to the login page
        2. Enter valid username and password
        3. Click the login button
        4. Verify successful login by checking for dashboard elements
        5. Take a screenshot of the logged-in state
        """,
        test_type=TestType.FUNCTIONAL,
        priority=TestPriority.HIGH,
        target_url="https://example.com/login",
        tags=["login", "authentication", "critical"]
    )
    
    search_test = await framework.create_test_case_from_description(
        name="Product Search Test",
        description="""
        Test the product search functionality:
        1. Navigate to the homepage
        2. Enter a product name in the search box
        3. Click search or press Enter
        4. Verify search results are displayed
        5. Check that results are relevant to the search term
        """,
        test_type=TestType.FUNCTIONAL,
        priority=TestPriority.MEDIUM,
        target_url="https://example.com",
        tags=["search", "products", "functionality"]
    )
    
    checkout_test = await framework.create_test_case_from_description(
        name="Checkout Process Test",
        description="""
        Test the complete checkout process:
        1. Add items to cart
        2. Navigate to checkout
        3. Fill in shipping information
        4. Select payment method
        5. Complete the purchase
        6. Verify order confirmation
        """,
        test_type=TestType.E2E,
        priority=TestPriority.CRITICAL,
        target_url="https://example.com/products",
        tags=["checkout", "e2e", "critical", "payment"]
    )
    
    print(f"✅ Created test case: {login_test.name} (ID: {login_test.id})")
    print(f"✅ Created test case: {search_test.name} (ID: {search_test.id})")
    print(f"✅ Created test case: {checkout_test.name} (ID: {checkout_test.id})")
    
    # Create test suite
    regression_suite = await framework.create_test_suite(
        name="Regression Test Suite",
        description="Core functionality regression tests",
        test_case_ids=[login_test.id, search_test.id, checkout_test.id],
        parallel_execution=True,
        max_parallel_workers=2,
        stop_on_failure=False
    )
    
    print(f"✅ Created test suite: {regression_suite.name} (ID: {regression_suite.id})")
    print(f"   Contains {len(regression_suite.test_case_ids)} test cases")
    print()
    
    return {
        "test_cases": [login_test, search_test, checkout_test],
        "test_suite": regression_suite
    }


async def demo_test_data_management(framework):
    """Demo 2: Test Data Management"""
    print("🗄️ Demo 2: Test Data Management")
    print("=" * 50)
    
    # Create test data sets
    user_data_set = await framework.create_test_data_set(
        name="User Test Data",
        description="Test user accounts for login testing",
        data_type="person",
        scope=DataScope.GLOBAL,
        environment="staging"
    )
    
    product_data_set = await framework.create_test_data_set(
        name="Product Test Data", 
        description="Test products for search and checkout testing",
        data_type="product",
        scope=DataScope.SUITE,
        environment="staging"
    )
    
    print(f"✅ Created data set: {user_data_set.name} (ID: {user_data_set.id})")
    print(f"✅ Created data set: {product_data_set.name} (ID: {product_data_set.id})")
    
    # Generate test data
    await framework.generate_test_data(
        data_set_id=user_data_set.id,
        count=10,
        generator_type="person",
        include_fields=["username", "email", "password", "first_name", "last_name"]
    )
    
    await framework.generate_test_data(
        data_set_id=product_data_set.id,
        count=20,
        generator_type="product",
        include_fields=["name", "description", "price", "category", "sku"]
    )
    
    print(f"✅ Generated 10 user records")
    print(f"✅ Generated 20 product records")
    
    # Get sample test data
    user_data = await framework.get_test_data(user_data_set.id)
    product_data = await framework.get_test_data(
        product_data_set.id, 
        criteria={"category": "electronics"}
    )
    
    if user_data:
        print(f"📋 Sample user data: {user_data.get('username', 'N/A')}")
    if product_data:
        print(f"📋 Sample product data: {product_data.get('name', 'N/A')}")
    
    print()
    
    return {
        "user_data_set": user_data_set,
        "product_data_set": product_data_set,
        "sample_user": user_data,
        "sample_product": product_data
    }


async def demo_test_execution(framework, test_data):
    """Demo 3: Test Execution"""
    print("🚀 Demo 3: Test Execution")
    print("=" * 50)
    
    test_cases = test_data["test_cases"]
    test_suite = test_data["test_suite"]
    
    # Execute individual test case
    print("Executing individual test case...")
    login_execution = await framework.execute_test_case(
        test_case_id=test_cases[0].id,  # Login test
        environment="staging"
    )
    
    print(f"✅ Executed test case: {test_cases[0].name}")
    print(f"   Status: {login_execution.status.value}")
    print(f"   Duration: {login_execution.duration:.2f} seconds")
    print(f"   Results: {login_execution.passed_tests} passed, {login_execution.failed_tests} failed")
    
    # Execute test suite
    print("\nExecuting test suite...")
    suite_execution = await framework.execute_test_suite(
        test_suite_id=test_suite.id,
        environment="staging"
    )
    
    print(f"✅ Executed test suite: {test_suite.name}")
    print(f"   Status: {suite_execution.status.value}")
    print(f"   Duration: {suite_execution.duration:.2f} seconds")
    print(f"   Results: {suite_execution.passed_tests} passed, {suite_execution.failed_tests} failed")
    print(f"   Success Rate: {suite_execution.get_success_rate():.2%}")
    
    # Execute tests by tags
    print("\nExecuting tests by tags...")
    tag_execution = await framework.execute_test_cases_by_tags(
        tags=["critical"],
        environment="staging"
    )
    
    print(f"✅ Executed tests with 'critical' tag")
    print(f"   Status: {tag_execution.status.value}")
    print(f"   Test Cases: {len(tag_execution.test_case_ids)}")
    print(f"   Results: {tag_execution.passed_tests} passed, {tag_execution.failed_tests} failed")
    
    print()
    
    return {
        "login_execution": login_execution,
        "suite_execution": suite_execution,
        "tag_execution": tag_execution
    }


async def demo_advanced_reporting(framework, execution_data):
    """Demo 4: Advanced Reporting"""
    print("📊 Demo 4: Advanced Reporting")
    print("=" * 50)
    
    suite_execution = execution_data["suite_execution"]
    
    # Generate HTML execution report
    html_report = await framework.generate_execution_report(
        execution_id=suite_execution.id,
        report_format=ReportFormat.HTML,
        title="Regression Test Suite Report",
        include_screenshots=True,
        include_performance_metrics=True,
        include_failure_analysis=True
    )
    
    print(f"✅ Generated HTML report: {html_report.title}")
    print(f"   Report ID: {html_report.id}")
    print(f"   File: {html_report.file_path}")
    print(f"   Sections: {len(html_report.sections)}")
    
    # Generate PDF report
    pdf_report = await framework.generate_execution_report(
        execution_id=suite_execution.id,
        report_format=ReportFormat.PDF,
        title="Executive Test Summary",
        include_screenshots=False,
        include_logs=False
    )
    
    print(f"✅ Generated PDF report: {pdf_report.title}")
    print(f"   Report ID: {pdf_report.id}")
    print(f"   File: {pdf_report.file_path}")
    
    # Generate JUnit XML report
    junit_report = await framework.generate_execution_report(
        execution_id=suite_execution.id,
        report_format=ReportFormat.JUNIT,
        title="CI/CD Integration Report"
    )
    
    print(f"✅ Generated JUnit report: {junit_report.title}")
    print(f"   Report ID: {junit_report.id}")
    print(f"   File: {junit_report.file_path}")
    
    # Generate trend analysis report
    trend_report = await framework.generate_trend_report(
        days=30,
        environment="staging",
        report_format=ReportFormat.HTML,
        title="30-Day Trend Analysis"
    )
    
    print(f"✅ Generated trend report: {trend_report.title}")
    print(f"   Report ID: {trend_report.id}")
    print(f"   Analysis Period: 30 days")
    
    # Generate dashboard
    dashboard_url = await framework.generate_dashboard(
        title="Test Automation Dashboard",
        environment="staging",
        auto_refresh=True
    )
    
    print(f"✅ Generated dashboard: {dashboard_url}")
    
    print()
    
    return {
        "html_report": html_report,
        "pdf_report": pdf_report,
        "junit_report": junit_report,
        "trend_report": trend_report,
        "dashboard_url": dashboard_url
    }


async def demo_framework_status(framework):
    """Demo 5: Framework Status and Statistics"""
    print("📈 Demo 5: Framework Status")
    print("=" * 50)
    
    status = await framework.get_framework_status()
    
    print(f"Framework Initialized: {status['framework_initialized']}")
    print(f"LLM Provider Configured: {status['llm_provider_configured']}")
    print(f"Workspace Path: {status['workspace_path']}")
    print(f"Default Environment: {status['default_environment']}")
    
    if "test_cases" in status:
        tc_stats = status["test_cases"]
        print(f"\nTest Cases: {tc_stats['total']} total")
        print(f"  By Type: {tc_stats['by_type']}")
        print(f"  By Priority: {tc_stats['by_priority']}")
        print(f"  By Status: {tc_stats['by_status']}")
    
    print()


async def main():
    """Run complete framework demonstration."""
    print("🚀 LLM & Browser-Use Test Automation Framework Demo")
    print("=" * 60)
    print()
    
    # Check for required API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        print("Please set your OpenAI API key in the .env file")
        return
    
    try:
        # Initialize framework
        print("🔧 Initializing Test Automation Framework...")
        framework = await create_test_automation_framework(
            workspace_path="demo_workspace",
            llm_provider="openai",
            llm_model="gpt-4",
            api_key=api_key,
            environment="staging"
        )
        print("✅ Framework initialized successfully")
        print()
        
        # Run demos
        test_mgmt_data = await demo_test_case_management(framework)
        data_mgmt_data = await demo_test_data_management(framework)
        execution_data = await demo_test_execution(framework, test_mgmt_data)
        reporting_data = await demo_advanced_reporting(framework, execution_data)
        await demo_framework_status(framework)
        
        # Summary
        print("🎉 Demo Completed Successfully!")
        print("=" * 60)
        print()
        print("📋 What was demonstrated:")
        print("• Natural language test case creation using LLM")
        print("• Test suite organization and management")
        print("• Comprehensive test data generation and management")
        print("• Automated test execution with browser automation")
        print("• Advanced reporting in multiple formats (HTML, PDF, JUnit)")
        print("• Trend analysis and dashboard generation")
        print("• Framework status monitoring and statistics")
        print()
        print("📁 Generated artifacts:")
        print(f"• Test workspace: demo_workspace/")
        print(f"• Test cases: {len(test_mgmt_data['test_cases'])} created")
        print(f"• Test data sets: 2 created with sample data")
        print(f"• Test executions: 3 completed")
        print(f"• Reports: {len([r for r in reporting_data.values() if hasattr(r, 'id')])} generated")
        print()
        print("🔗 Next steps:")
        print("• Explore the generated reports in demo_workspace/reports/")
        print("• Review test cases in demo_workspace/test_cases/")
        print("• Check test data in demo_workspace/test_data/")
        print("• Integrate with your CI/CD pipeline using JUnit reports")
        
        # Cleanup
        await framework.cleanup()
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
