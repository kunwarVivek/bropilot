"""
Integration Tests for Test Automation Framework

Tests the complete framework functionality including test case management,
test data management, and advanced reporting.
"""

import pytest
import asyncio
import tempfile
import shutil
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from src.test_automation_framework import TestAutomationFramework, create_test_automation_framework
from src.test_management.models import TestType, TestPriority, TestCaseStatus, ExecutionStatus
from src.test_data.models import DataScope, DataType
from src.test_reporting.models import ReportFormat, ReportType


class TestFrameworkIntegration:
    """Integration tests for the complete test automation framework."""
    
    @pytest.fixture
    async def temp_workspace(self):
        """Create temporary workspace for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    async def mock_llm_provider(self):
        """Mock LLM provider for testing."""
        mock_llm = AsyncMock()
        mock_llm.invoke.return_value = """
        Generated test case:
        1. Navigate to the login page
        2. Enter username and password
        3. Click login button
        4. Verify successful login
        """
        return mock_llm
    
    @pytest.fixture
    async def framework(self, temp_workspace, mock_llm_provider):
        """Initialize framework for testing."""
        framework = TestAutomationFramework(temp_workspace, "test")
        await framework.initialize()
        framework.llm_provider = mock_llm_provider
        return framework
    
    @pytest.mark.asyncio
    async def test_framework_initialization(self, temp_workspace):
        """Test framework initialization."""
        framework = TestAutomationFramework(temp_workspace, "test")
        await framework.initialize()
        
        # Check that all managers are initialized
        assert framework.test_case_manager is not None
        assert framework.test_suite_manager is not None
        assert framework.test_execution_manager is not None
        assert framework.test_data_manager is not None
        assert framework.report_manager is not None
        
        # Check workspace structure
        workspace_path = Path(temp_workspace)
        expected_dirs = [
            "test_cases", "test_suites", "test_data", 
            "test_executions", "reports", "logs", 
            "artifacts", "screenshots", "evidence"
        ]
        
        for dir_name in expected_dirs:
            assert (workspace_path / dir_name).exists()
    
    @pytest.mark.asyncio
    async def test_create_test_automation_framework(self, temp_workspace):
        """Test framework creation helper function."""
        with patch('src.execution.llm_provider.create_llm_provider') as mock_create_llm:
            mock_create_llm.return_value = AsyncMock()
            
            framework = await create_test_automation_framework(
                workspace_path=temp_workspace,
                llm_provider="openai",
                llm_model="gpt-4",
                api_key="test-key",
                environment="test"
            )
            
            assert framework is not None
            assert framework.llm_provider is not None
            mock_create_llm.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_test_case_management_workflow(self, framework):
        """Test complete test case management workflow."""
        # Create test case from natural language
        test_case = await framework.create_test_case_from_description(
            name="Login Test",
            description="Test user login functionality",
            test_type=TestType.FUNCTIONAL,
            priority=TestPriority.HIGH,
            target_url="https://example.com/login",
            tags=["login", "authentication"]
        )
        
        assert test_case is not None
        assert test_case.name == "Login Test"
        assert test_case.test_type == TestType.FUNCTIONAL
        assert test_case.priority == TestPriority.HIGH
        assert "login" in test_case.tags
        
        # Get test case
        retrieved_case = await framework.get_test_case(test_case.id)
        assert retrieved_case is not None
        assert retrieved_case.id == test_case.id
        
        # Search test cases
        search_results = await framework.search_test_cases(tags=["login"])
        assert len(search_results) >= 1
        assert any(tc.id == test_case.id for tc in search_results)
        
        # Clone test case
        cloned_case = await framework.clone_test_case(test_case.id, "Login Test Clone")
        assert cloned_case is not None
        assert cloned_case.name == "Login Test Clone"
        assert cloned_case.id != test_case.id
    
    @pytest.mark.asyncio
    async def test_test_suite_management_workflow(self, framework):
        """Test test suite management workflow."""
        # Create test cases first
        test_case_1 = await framework.create_test_case(
            name="Test Case 1",
            description="First test case",
            test_type=TestType.FUNCTIONAL
        )
        
        test_case_2 = await framework.create_test_case(
            name="Test Case 2", 
            description="Second test case",
            test_type=TestType.REGRESSION
        )
        
        # Create test suite
        test_suite = await framework.create_test_suite(
            name="Regression Suite",
            description="Regression test suite",
            test_case_ids=[test_case_1.id, test_case_2.id],
            parallel_execution=True,
            max_parallel_workers=2
        )
        
        assert test_suite is not None
        assert test_suite.name == "Regression Suite"
        assert len(test_suite.test_case_ids) == 2
        assert test_case_1.id in test_suite.test_case_ids
        assert test_case_2.id in test_suite.test_case_ids
        assert test_suite.parallel_execution is True
        
        # Get test suite
        retrieved_suite = await framework.get_test_suite(test_suite.id)
        assert retrieved_suite is not None
        assert retrieved_suite.id == test_suite.id
        
        # Add more test cases to suite
        test_case_3 = await framework.create_test_case(
            name="Test Case 3",
            description="Third test case"
        )
        
        success = await framework.add_test_cases_to_suite(
            test_suite.id, [test_case_3.id]
        )
        assert success is True
        
        # Verify test case was added
        updated_suite = await framework.get_test_suite(test_suite.id)
        assert len(updated_suite.test_case_ids) == 3
        assert test_case_3.id in updated_suite.test_case_ids
    
    @pytest.mark.asyncio
    async def test_test_data_management_workflow(self, framework):
        """Test test data management workflow."""
        # Create test data set
        data_set = await framework.create_test_data_set(
            name="User Data",
            description="Test user data",
            data_type="person",
            scope=DataScope.GLOBAL,
            environment="test"
        )
        
        assert data_set is not None
        assert data_set.name == "User Data"
        assert data_set.data_type == DataType.PERSON
        assert data_set.scope == DataScope.GLOBAL
        
        # Generate test data
        with patch.object(framework.test_data_manager, 'generate_data') as mock_generate:
            mock_generate.return_value = True
            
            success = await framework.generate_test_data(
                data_set_id=data_set.id,
                count=10,
                generator_type="person",
                include_fields=["username", "email", "password"]
            )
            
            assert success is True
            mock_generate.assert_called_once_with(
                data_set_id=data_set.id,
                count=10,
                generator_type="person",
                include_fields=["username", "email", "password"]
            )
        
        # Get test data
        with patch.object(framework.test_data_manager, 'get_data') as mock_get_data:
            mock_get_data.return_value = {
                "username": "testuser",
                "email": "test@example.com",
                "password": "password123"
            }
            
            test_data = await framework.get_test_data(data_set.id)
            
            assert test_data is not None
            assert "username" in test_data
            assert "email" in test_data
            mock_get_data.assert_called_once_with(data_set.id, None)
        
        # Get test data with criteria
        with patch.object(framework.test_data_manager, 'get_data') as mock_get_data:
            mock_get_data.return_value = {
                "username": "adminuser",
                "email": "admin@example.com",
                "role": "admin"
            }
            
            admin_data = await framework.get_test_data(
                data_set.id, 
                criteria={"role": "admin"}
            )
            
            assert admin_data is not None
            assert admin_data["role"] == "admin"
            mock_get_data.assert_called_once_with(data_set.id, {"role": "admin"})
    
    @pytest.mark.asyncio
    async def test_test_execution_workflow(self, framework):
        """Test test execution workflow."""
        # Create test case
        test_case = await framework.create_test_case(
            name="Execution Test",
            description="Test for execution",
            target_url="https://example.com"
        )
        
        # Mock the execution manager
        with patch.object(framework.test_execution_manager, 'execute_test_case') as mock_execute:
            from src.test_management.models import TestExecution, TestResult
            
            # Create mock execution result
            mock_execution = TestExecution(
                name="Test Execution",
                test_case_ids=[test_case.id],
                status=ExecutionStatus.PASSED,
                total_tests=1,
                passed_tests=1,
                failed_tests=0
            )
            
            mock_execute.return_value = mock_execution
            
            # Execute test case
            execution = await framework.execute_test_case(
                test_case_id=test_case.id,
                environment="test"
            )
            
            assert execution is not None
            assert execution.status == ExecutionStatus.PASSED
            assert execution.total_tests == 1
            assert execution.passed_tests == 1
            assert test_case.id in execution.test_case_ids
            
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_test_suite_execution_workflow(self, framework):
        """Test test suite execution workflow."""
        # Create test cases and suite
        test_case_1 = await framework.create_test_case(
            name="Suite Test 1",
            description="First test in suite"
        )
        
        test_case_2 = await framework.create_test_case(
            name="Suite Test 2",
            description="Second test in suite"
        )
        
        test_suite = await framework.create_test_suite(
            name="Execution Suite",
            description="Suite for execution testing",
            test_case_ids=[test_case_1.id, test_case_2.id]
        )
        
        # Mock the execution manager
        with patch.object(framework.test_execution_manager, 'execute_test_suite') as mock_execute:
            from src.test_management.models import TestExecution
            
            mock_execution = TestExecution(
                name="Suite Execution",
                test_suite_id=test_suite.id,
                test_case_ids=[test_case_1.id, test_case_2.id],
                status=ExecutionStatus.PASSED,
                total_tests=2,
                passed_tests=2,
                failed_tests=0
            )
            
            mock_execute.return_value = mock_execution
            
            # Execute test suite
            execution = await framework.execute_test_suite(
                test_suite_id=test_suite.id,
                environment="test"
            )
            
            assert execution is not None
            assert execution.status == ExecutionStatus.PASSED
            assert execution.total_tests == 2
            assert execution.passed_tests == 2
            assert execution.test_suite_id == test_suite.id
            
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_by_tags_workflow(self, framework):
        """Test execution by tags workflow."""
        # Create test cases with tags
        test_case_1 = await framework.create_test_case(
            name="Critical Test 1",
            description="Critical test case",
            tags=["critical", "smoke"]
        )
        
        test_case_2 = await framework.create_test_case(
            name="Critical Test 2", 
            description="Another critical test",
            tags=["critical", "regression"]
        )
        
        test_case_3 = await framework.create_test_case(
            name="Normal Test",
            description="Normal test case",
            tags=["regression"]
        )
        
        # Mock search and execution
        with patch.object(framework.test_case_manager, 'search_test_cases') as mock_search, \
             patch.object(framework, 'create_test_suite') as mock_create_suite, \
             patch.object(framework, 'execute_test_suite') as mock_execute_suite:
            
            # Mock search results
            mock_search.return_value = [test_case_1, test_case_2]
            
            # Mock suite creation
            from src.test_management.models import TestSuite
            mock_suite = TestSuite(
                name="Execution by tags: critical",
                test_case_ids=[test_case_1.id, test_case_2.id]
            )
            mock_create_suite.return_value = mock_suite
            
            # Mock execution
            from src.test_management.models import TestExecution
            mock_execution = TestExecution(
                name="Tag Execution",
                test_case_ids=[test_case_1.id, test_case_2.id],
                status=ExecutionStatus.PASSED,
                total_tests=2,
                passed_tests=2
            )
            mock_execute_suite.return_value = mock_execution
            
            # Execute by tags
            execution = await framework.execute_test_cases_by_tags(
                tags=["critical"],
                environment="test"
            )
            
            assert execution is not None
            assert execution.total_tests == 2
            assert execution.passed_tests == 2
            
            mock_search.assert_called_once_with(tags=["critical"])
            mock_create_suite.assert_called_once()
            mock_execute_suite.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reporting_workflow(self, framework):
        """Test reporting workflow."""
        # Mock execution for reporting
        from src.test_management.models import TestExecution
        mock_execution = TestExecution(
            name="Test Execution for Reporting",
            status=ExecutionStatus.PASSED,
            total_tests=5,
            passed_tests=4,
            failed_tests=1
        )
        
        # Mock the report manager
        with patch.object(framework.report_manager, 'generate_execution_report') as mock_generate:
            from src.test_reporting.models import TestReport
            
            mock_report = TestReport(
                title="Execution Report",
                report_type=ReportType.EXECUTION_SUMMARY,
                format=ReportFormat.HTML,
                execution_ids=[mock_execution.id]
            )
            
            mock_generate.return_value = mock_report
            
            # Generate HTML report
            html_report = await framework.generate_execution_report(
                execution_id=mock_execution.id,
                report_format=ReportFormat.HTML,
                title="Test Execution Report"
            )
            
            assert html_report is not None
            assert html_report.format == ReportFormat.HTML
            assert html_report.title == "Test Execution Report"
            
            mock_generate.assert_called_once()
        
        # Test trend report generation
        with patch.object(framework.report_manager, 'generate_trend_report') as mock_trend:
            from src.test_reporting.models import TestReport
            
            mock_trend_report = TestReport(
                title="Trend Analysis",
                report_type=ReportType.TREND_ANALYSIS,
                format=ReportFormat.HTML
            )
            
            mock_trend.return_value = mock_trend_report
            
            trend_report = await framework.generate_trend_report(
                days=30,
                environment="test"
            )
            
            assert trend_report is not None
            assert trend_report.report_type == ReportType.TREND_ANALYSIS
            
            mock_trend.assert_called_once()
        
        # Test dashboard generation
        with patch.object(framework.report_manager, 'generate_dashboard') as mock_dashboard:
            mock_dashboard.return_value = "http://localhost:8080/dashboard"
            
            dashboard_url = await framework.generate_dashboard(
                title="Test Dashboard"
            )
            
            assert dashboard_url == "http://localhost:8080/dashboard"
            mock_dashboard.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_framework_status(self, framework):
        """Test framework status reporting."""
        # Create some test data for status
        await framework.create_test_case(
            name="Status Test 1",
            description="Test case for status",
            test_type=TestType.FUNCTIONAL,
            priority=TestPriority.HIGH
        )
        
        await framework.create_test_case(
            name="Status Test 2",
            description="Another test case",
            test_type=TestType.REGRESSION,
            priority=TestPriority.MEDIUM
        )
        
        # Get framework status
        status = await framework.get_framework_status()
        
        assert status is not None
        assert status["framework_initialized"] is True
        assert status["llm_provider_configured"] is True
        assert "workspace_path" in status
        assert "default_environment" in status
        
        # Check test case statistics
        if "test_cases" in status:
            tc_stats = status["test_cases"]
            assert tc_stats["total"] >= 2
            assert "by_type" in tc_stats
            assert "by_priority" in tc_stats
            assert "by_status" in tc_stats
    
    @pytest.mark.asyncio
    async def test_framework_cleanup(self, framework):
        """Test framework cleanup."""
        # Test cleanup doesn't raise errors
        await framework.cleanup()
        
        # Framework should still be usable after cleanup
        assert framework.workspace_path is not None


@pytest.mark.integration
class TestFrameworkEndToEnd:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_complete_workflow(self, temp_workspace, mock_llm_provider):
        """Test complete end-to-end workflow."""
        # Initialize framework
        framework = TestAutomationFramework(temp_workspace, "e2e_test")
        await framework.initialize()
        framework.llm_provider = mock_llm_provider
        
        # 1. Create test cases
        login_test = await framework.create_test_case_from_description(
            name="E2E Login Test",
            description="End-to-end login test",
            test_type=TestType.E2E,
            priority=TestPriority.CRITICAL,
            tags=["e2e", "login", "critical"]
        )
        
        # 2. Create test data
        user_data_set = await framework.create_test_data_set(
            name="E2E User Data",
            description="User data for E2E testing",
            data_type="person",
            scope=DataScope.GLOBAL
        )
        
        # 3. Create test suite
        e2e_suite = await framework.create_test_suite(
            name="E2E Test Suite",
            description="End-to-end test suite",
            test_case_ids=[login_test.id],
            parallel_execution=False
        )
        
        # 4. Mock execution
        with patch.object(framework.test_execution_manager, 'execute_test_suite') as mock_execute:
            from src.test_management.models import TestExecution
            
            mock_execution = TestExecution(
                name="E2E Execution",
                test_suite_id=e2e_suite.id,
                status=ExecutionStatus.PASSED,
                total_tests=1,
                passed_tests=1
            )
            mock_execute.return_value = mock_execution
            
            execution = await framework.execute_test_suite(e2e_suite.id)
            
            assert execution.status == ExecutionStatus.PASSED
        
        # 5. Generate report
        with patch.object(framework.report_manager, 'generate_execution_report') as mock_report:
            from src.test_reporting.models import TestReport
            
            mock_test_report = TestReport(
                title="E2E Test Report",
                format=ReportFormat.HTML
            )
            mock_report.return_value = mock_test_report
            
            report = await framework.generate_execution_report(
                execution.id,
                ReportFormat.HTML
            )
            
            assert report.format == ReportFormat.HTML
        
        # 6. Check framework status
        status = await framework.get_framework_status()
        assert status["framework_initialized"] is True
        
        # 7. Cleanup
        await framework.cleanup()
    
    @pytest.fixture
    async def temp_workspace(self):
        """Create temporary workspace for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    async def mock_llm_provider(self):
        """Mock LLM provider for testing."""
        mock_llm = AsyncMock()
        mock_llm.invoke.return_value = "Generated test content"
        return mock_llm
