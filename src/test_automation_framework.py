"""
LLM & Browser-Use Test Automation Framework

Main framework class that integrates test case management, test data management,
and advanced reporting for comprehensive test automation.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from src.test_management import (
    TestCaseManager, TestSuiteManager, TestExecutionManager,
    TestCase, TestSuite, TestExecution, TestType, TestPriority
)
from src.test_management.llm_features import (
    RequirementsToTestGenerator, TestMaintenanceEngine
)
from src.test_data import (
    TestDataManager, TestDataSet, DataScope
)
from src.test_reporting import (
    ReportManager, TestReport, ReportType, ReportFormat
)
from src.execution.llm_provider import create_llm_provider
from src.validation import ValidationConfig, get_validation_config
from src.infrastructure.logging.logger import StructuredLogger


class TestAutomationFramework:
    """
    Main framework class for LLM-powered browser automation testing.
    
    This class provides a unified interface for:
    - Managing test cases and test suites
    - Managing test data across different scopes
    - Executing tests with LLM-powered browser automation
    - Generating comprehensive test reports
    """
    
    def __init__(
        self,
        workspace_path: str = "test_workspace",
        default_environment: str = "default"
    ):
        self.workspace_path = Path(workspace_path)
        self.default_environment = default_environment
        self.logger = StructuredLogger("test_automation_framework")
        
        # Initialize workspace
        self._initialize_workspace()
        
        # Initialize managers
        self.test_case_manager = None
        self.test_suite_manager = None
        self.test_execution_manager = None
        self.test_data_manager = None
        self.report_manager = None

        # Advanced LLM features
        self.requirements_generator = RequirementsToTestGenerator()
        self.test_maintenance_engine = TestMaintenanceEngine()
        
        # Framework state
        self.llm_provider = None
        self.default_validation_config = get_validation_config("standard")
        
        self.logger.info(
            "Test automation framework initialized",
            workspace_path=str(self.workspace_path),
            default_environment=self.default_environment
        )
    
    def _initialize_workspace(self) -> None:
        """Initialize the test workspace directory structure."""
        directories = [
            "test_cases",
            "test_suites", 
            "test_data",
            "test_executions",
            "reports",
            "logs",
            "artifacts",
            "screenshots",
            "evidence"
        ]
        
        for directory in directories:
            (self.workspace_path / directory).mkdir(parents=True, exist_ok=True)
        
        self.logger.debug("Test workspace initialized", directories=directories)
    
    async def initialize(self) -> None:
        """Initialize the framework components."""
        # Initialize repositories and managers
        # Note: In a real implementation, these would use actual database/file repositories
        from src.test_management.repositories import (
            TestCaseRepository, TestSuiteRepository, TestExecutionRepository
        )
        
        # Initialize repositories with workspace paths
        case_repo = TestCaseRepository(str(self.workspace_path / "test_cases"))
        suite_repo = TestSuiteRepository(str(self.workspace_path / "test_suites"))
        execution_repo = TestExecutionRepository(str(self.workspace_path / "test_executions"))
        
        # Initialize managers
        self.test_case_manager = TestCaseManager(case_repo)
        self.test_suite_manager = TestSuiteManager(suite_repo, case_repo)
        self.test_execution_manager = TestExecutionManager(execution_repo, case_repo, suite_repo)
        
        # Initialize test data manager
        self.test_data_manager = TestDataManager(str(self.workspace_path / "test_data"))
        
        # Initialize report manager
        self.report_manager = ReportManager(
            str(self.workspace_path / "reports"),
            execution_repo
        )
        
        self.logger.info("Framework components initialized successfully")
    
    async def setup_llm_provider(
        self,
        provider: str,
        model: str,
        api_key: str,
        **kwargs
    ) -> None:
        """Setup LLM provider for test execution."""
        try:
            self.llm_provider = await create_llm_provider(
                primary_provider=provider,
                primary_model=model,
                primary_config={"api_key": api_key, **kwargs}
            )
            
            self.logger.info(
                "LLM provider configured",
                provider=provider,
                model=model
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to setup LLM provider",
                provider=provider,
                model=model,
                error=str(e)
            )
            raise
    
    # Test Case Management Methods
    
    async def create_test_case_from_description(
        self,
        name: str,
        description: str,
        test_type: TestType = TestType.FUNCTIONAL,
        priority: TestPriority = TestPriority.MEDIUM,
        **kwargs
    ) -> TestCase:
        """Create a test case from natural language description."""
        if not self.llm_provider:
            raise ValueError("LLM provider not configured. Call setup_llm_provider() first.")
        
        return await self.test_case_manager.create_from_natural_language(
            description=description,
            llm_provider=self.llm_provider,
            name=name,
            test_type=test_type,
            priority=priority,
            **kwargs
        )
    
    async def create_test_case(
        self,
        name: str,
        description: str,
        test_type: TestType = TestType.FUNCTIONAL,
        priority: TestPriority = TestPriority.MEDIUM,
        **kwargs
    ) -> TestCase:
        """Create a test case manually."""
        return await self.test_case_manager.create_test_case(
            name=name,
            description=description,
            test_type=test_type,
            priority=priority,
            **kwargs
        )
    
    async def get_test_case(self, test_case_id: str) -> Optional[TestCase]:
        """Get a test case by ID."""
        return await self.test_case_manager.get_test_case(test_case_id)
    
    async def search_test_cases(self, **filters) -> List[TestCase]:
        """Search test cases with filters."""
        return await self.test_case_manager.search_test_cases(**filters)
    
    async def clone_test_case(self, test_case_id: str, new_name: str) -> TestCase:
        """Clone an existing test case."""
        return await self.test_case_manager.clone_test_case(test_case_id, new_name)

    # Advanced LLM Test Features

    async def generate_test_cases_from_requirements(
        self,
        requirements_document: str,
        test_coverage_level: str = "comprehensive",
        **kwargs
    ) -> List[TestCase]:
        """Generate comprehensive test cases from requirements document using LLM."""
        if not self.llm_provider:
            raise ValueError("LLM provider not configured. Call setup_llm_provider() first.")

        test_cases = await self.requirements_generator.generate_test_cases_from_requirements(
            requirements_document=requirements_document,
            llm_provider=self.llm_provider,
            test_coverage_level=test_coverage_level,
            environment=self.default_environment,
            **kwargs
        )

        # Save generated test cases
        for test_case in test_cases:
            await self.test_case_manager.repository.save(test_case)

        self.logger.info(
            "Test cases generated from requirements",
            requirements_length=len(requirements_document),
            test_cases_generated=len(test_cases),
            coverage_level=test_coverage_level
        )

        return test_cases

    async def analyze_ui_changes_impact(
        self,
        ui_changes_description: str,
        affected_test_case_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Analyze how UI changes impact existing test cases."""
        if not self.llm_provider:
            raise ValueError("LLM provider not configured. Call setup_llm_provider() first.")

        # Get affected test cases
        if affected_test_case_ids:
            affected_test_cases = []
            for case_id in affected_test_case_ids:
                test_case = await self.get_test_case(case_id)
                if test_case:
                    affected_test_cases.append(test_case)
        else:
            # If no specific cases provided, analyze all test cases
            affected_test_cases = await self.search_test_cases(limit=100)

        impact_analysis = await self.test_maintenance_engine.analyze_ui_changes_impact(
            ui_changes_description=ui_changes_description,
            affected_test_cases=affected_test_cases,
            llm_provider=self.llm_provider
        )

        self.logger.info(
            "UI changes impact analyzed",
            changes_length=len(ui_changes_description),
            affected_test_cases=len(affected_test_cases),
            overall_impact=impact_analysis.get("overall_impact")
        )

        return impact_analysis

    async def update_test_case_for_changes(
        self,
        test_case_id: str,
        change_description: str,
        update_strategy: str = "smart"
    ) -> TestCase:
        """Update a test case based on system/UI changes using LLM."""
        if not self.llm_provider:
            raise ValueError("LLM provider not configured. Call setup_llm_provider() first.")

        # Get original test case
        original_test_case = await self.get_test_case(test_case_id)
        if not original_test_case:
            raise ValueError(f"Test case {test_case_id} not found")

        # Update test case using LLM
        updated_test_case = await self.test_maintenance_engine.update_test_case_for_changes(
            test_case=original_test_case,
            change_description=change_description,
            llm_provider=self.llm_provider,
            update_strategy=update_strategy
        )

        # Save updated test case
        await self.test_case_manager.repository.save(updated_test_case)

        self.logger.info(
            "Test case updated for changes",
            test_case_id=test_case_id,
            original_version=original_test_case.version,
            updated_version=updated_test_case.version,
            update_strategy=update_strategy
        )

        return updated_test_case

    async def bulk_update_test_cases_for_changes(
        self,
        test_case_ids: List[str],
        change_description: str,
        update_strategy: str = "smart"
    ) -> List[TestCase]:
        """Update multiple test cases for changes in bulk."""
        updated_test_cases = []

        for test_case_id in test_case_ids:
            try:
                updated_case = await self.update_test_case_for_changes(
                    test_case_id=test_case_id,
                    change_description=change_description,
                    update_strategy=update_strategy
                )
                updated_test_cases.append(updated_case)

            except Exception as e:
                self.logger.error(
                    "Failed to update test case in bulk operation",
                    test_case_id=test_case_id,
                    error=str(e)
                )

        self.logger.info(
            "Bulk test case update completed",
            requested_updates=len(test_case_ids),
            successful_updates=len(updated_test_cases),
            change_description=change_description[:100]
        )

        return updated_test_cases
    
    # Test Suite Management Methods
    
    async def create_test_suite(
        self,
        name: str,
        description: str,
        test_case_ids: Optional[List[str]] = None,
        **kwargs
    ) -> TestSuite:
        """Create a test suite."""
        return await self.test_suite_manager.create_test_suite(
            name=name,
            description=description,
            test_case_ids=test_case_ids,
            **kwargs
        )
    
    async def get_test_suite(self, test_suite_id: str) -> Optional[TestSuite]:
        """Get a test suite by ID."""
        return await self.test_suite_manager.get_test_suite(test_suite_id)
    
    async def add_test_cases_to_suite(
        self,
        test_suite_id: str,
        test_case_ids: List[str]
    ) -> bool:
        """Add test cases to a suite."""
        return await self.test_suite_manager.add_test_cases_to_suite(
            test_suite_id, test_case_ids
        )
    
    # Test Data Management Methods
    
    async def create_test_data_set(
        self,
        name: str,
        description: str,
        data_type: str,
        scope: DataScope = DataScope.GLOBAL,
        **kwargs
    ) -> TestDataSet:
        """Create a test data set."""
        return await self.test_data_manager.create_data_set(
            name=name,
            description=description,
            data_type=data_type,
            scope=scope,
            **kwargs
        )
    
    async def generate_test_data(
        self,
        data_set_id: str,
        count: int,
        generator_type: str,
        **kwargs
    ) -> bool:
        """Generate test data for a data set."""
        return await self.test_data_manager.generate_data(
            data_set_id=data_set_id,
            count=count,
            generator_type=generator_type,
            **kwargs
        )
    
    async def get_test_data(
        self,
        data_set_id: str,
        criteria: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get test data from a data set."""
        return await self.test_data_manager.get_data(data_set_id, criteria)
    
    # Test Execution Methods
    
    async def execute_test_case(
        self,
        test_case_id: str,
        environment: Optional[str] = None,
        validation_config: Optional[ValidationConfig] = None,
        **kwargs
    ) -> TestExecution:
        """Execute a single test case."""
        if not self.llm_provider:
            raise ValueError("LLM provider not configured. Call setup_llm_provider() first.")
        
        return await self.test_execution_manager.execute_test_case(
            test_case_id=test_case_id,
            llm_provider=self.llm_provider,
            environment=environment or self.default_environment,
            validation_config=validation_config or self.default_validation_config,
            **kwargs
        )
    
    async def execute_test_suite(
        self,
        test_suite_id: str,
        environment: Optional[str] = None,
        validation_config: Optional[ValidationConfig] = None,
        **kwargs
    ) -> TestExecution:
        """Execute a test suite."""
        if not self.llm_provider:
            raise ValueError("LLM provider not configured. Call setup_llm_provider() first.")
        
        return await self.test_execution_manager.execute_test_suite(
            test_suite_id=test_suite_id,
            llm_provider=self.llm_provider,
            environment=environment or self.default_environment,
            validation_config=validation_config or self.default_validation_config,
            **kwargs
        )
    
    async def execute_test_cases_by_tags(
        self,
        tags: List[str],
        environment: Optional[str] = None,
        validation_config: Optional[ValidationConfig] = None,
        **kwargs
    ) -> TestExecution:
        """Execute test cases by tags."""
        # Find test cases with matching tags
        test_cases = await self.search_test_cases(tags=tags)
        test_case_ids = [tc.id for tc in test_cases]
        
        if not test_case_ids:
            raise ValueError(f"No test cases found with tags: {tags}")
        
        # Create temporary test suite
        temp_suite = await self.create_test_suite(
            name=f"Execution by tags: {', '.join(tags)}",
            description=f"Temporary suite for executing tests with tags: {', '.join(tags)}",
            test_case_ids=test_case_ids
        )
        
        # Execute the suite
        return await self.execute_test_suite(
            test_suite_id=temp_suite.id,
            environment=environment,
            validation_config=validation_config,
            **kwargs
        )
    
    # Reporting Methods
    
    async def generate_execution_report(
        self,
        execution_id: str,
        report_format: ReportFormat = ReportFormat.HTML,
        **kwargs
    ) -> TestReport:
        """Generate a report for a test execution."""
        return await self.report_manager.generate_execution_report(
            execution_id=execution_id,
            report_format=report_format,
            **kwargs
        )
    
    async def generate_trend_report(
        self,
        days: int = 30,
        environment: Optional[str] = None,
        report_format: ReportFormat = ReportFormat.HTML,
        **kwargs
    ) -> TestReport:
        """Generate a trend analysis report."""
        return await self.report_manager.generate_trend_report(
            days=days,
            environment=environment or self.default_environment,
            report_format=report_format,
            **kwargs
        )
    
    async def generate_dashboard(self, **kwargs) -> str:
        """Generate a test dashboard."""
        return await self.report_manager.generate_dashboard(**kwargs)
    
    # Utility Methods
    
    async def get_framework_status(self) -> Dict[str, Any]:
        """Get framework status and statistics."""
        status = {
            "framework_initialized": all([
                self.test_case_manager,
                self.test_suite_manager,
                self.test_execution_manager,
                self.test_data_manager,
                self.report_manager
            ]),
            "llm_provider_configured": self.llm_provider is not None,
            "workspace_path": str(self.workspace_path),
            "default_environment": self.default_environment
        }
        
        if self.test_case_manager:
            # Get test case statistics
            all_cases = await self.search_test_cases(limit=1000)
            status["test_cases"] = {
                "total": len(all_cases),
                "by_type": {},
                "by_priority": {},
                "by_status": {}
            }
            
            # Count by categories
            for case in all_cases:
                # By type
                type_key = case.test_type.value
                status["test_cases"]["by_type"][type_key] = status["test_cases"]["by_type"].get(type_key, 0) + 1
                
                # By priority
                priority_key = case.priority.value
                status["test_cases"]["by_priority"][priority_key] = status["test_cases"]["by_priority"].get(priority_key, 0) + 1
                
                # By status
                status_key = case.status.value
                status["test_cases"]["by_status"][status_key] = status["test_cases"]["by_status"].get(status_key, 0) + 1
        
        return status
    
    async def cleanup(self) -> None:
        """Cleanup framework resources."""
        if self.llm_provider:
            # Cleanup LLM provider if needed
            pass
        
        self.logger.info("Framework cleanup completed")


# Convenience function for quick framework setup
async def create_test_automation_framework(
    workspace_path: str = "test_workspace",
    llm_provider: str = "openai",
    llm_model: str = "gpt-4",
    api_key: str = "",
    environment: str = "default"
) -> TestAutomationFramework:
    """
    Create and initialize a test automation framework with LLM provider.
    
    Args:
        workspace_path: Path to test workspace
        llm_provider: LLM provider name (openai, anthropic, google)
        llm_model: LLM model name
        api_key: API key for LLM provider
        environment: Default test environment
    
    Returns:
        Initialized TestAutomationFramework instance
    """
    framework = TestAutomationFramework(workspace_path, environment)
    await framework.initialize()
    
    if api_key:
        await framework.setup_llm_provider(llm_provider, llm_model, api_key)
    
    return framework
