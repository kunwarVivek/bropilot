"""
Test Management Services

High-level services for test management operations.
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone

from .models import TestCase, TestSuite, TestExecution, TestType, TestPriority
from .managers import TestCaseManager, TestSuiteManager, TestExecutionManager
from src.infrastructure.logging.logger import StructuredLogger


class TestCaseService:
    """High-level service for test case operations."""
    
    def __init__(self, test_case_manager: TestCaseManager):
        self.test_case_manager = test_case_manager
        self.logger = StructuredLogger("test_case_service")
    
    async def create_test_case_from_requirements(
        self,
        requirements: str,
        llm_provider,
        **kwargs
    ) -> TestCase:
        """Create test case from requirements document."""
        # This would implement requirements-to-test-case conversion
        # For now, delegate to the existing natural language method
        return await self.test_case_manager.create_from_natural_language(
            description=requirements,
            llm_provider=llm_provider,
            **kwargs
        )
    
    async def bulk_create_test_cases(
        self,
        test_definitions: List[Dict[str, Any]],
        llm_provider
    ) -> List[TestCase]:
        """Create multiple test cases in bulk."""
        test_cases = []
        
        for definition in test_definitions:
            try:
                if "description" in definition:
                    # Create from natural language
                    test_case = await self.test_case_manager.create_from_natural_language(
                        description=definition["description"],
                        llm_provider=llm_provider,
                        **{k: v for k, v in definition.items() if k != "description"}
                    )
                else:
                    # Create manually
                    test_case = await self.test_case_manager.create_test_case(**definition)
                
                test_cases.append(test_case)
                
            except Exception as e:
                self.logger.error(
                    "Failed to create test case in bulk operation",
                    error=str(e),
                    definition=definition
                )
        
        return test_cases


class TestSuiteService:
    """High-level service for test suite operations."""
    
    def __init__(self, test_suite_manager: TestSuiteManager):
        self.test_suite_manager = test_suite_manager
        self.logger = StructuredLogger("test_suite_service")
    
    async def create_suite_from_template(
        self,
        template_name: str,
        name: str,
        description: str,
        **kwargs
    ) -> TestSuite:
        """Create test suite from predefined template."""
        templates = {
            "regression": {
                "parallel_execution": True,
                "max_parallel_workers": 4,
                "stop_on_failure": False
            },
            "smoke": {
                "parallel_execution": True,
                "max_parallel_workers": 2,
                "stop_on_failure": True
            },
            "integration": {
                "parallel_execution": False,
                "stop_on_failure": True
            }
        }
        
        if template_name not in templates:
            raise ValueError(f"Unknown template: {template_name}")
        
        template_config = templates[template_name]
        template_config.update(kwargs)
        
        return await self.test_suite_manager.create_test_suite(
            name=name,
            description=description,
            **template_config
        )


class TestExecutionService:
    """High-level service for test execution operations."""
    
    def __init__(self, test_execution_manager: TestExecutionManager):
        self.test_execution_manager = test_execution_manager
        self.logger = StructuredLogger("test_execution_service")
    
    async def schedule_execution(
        self,
        test_suite_id: str,
        schedule_time: datetime,
        llm_provider,
        **kwargs
    ) -> str:
        """Schedule a test execution for future time."""
        # This would implement scheduling logic
        # For now, return a mock schedule ID
        schedule_id = f"schedule_{test_suite_id}_{int(schedule_time.timestamp())}"
        
        self.logger.info(
            "Test execution scheduled",
            schedule_id=schedule_id,
            test_suite_id=test_suite_id,
            schedule_time=schedule_time.isoformat()
        )
        
        return schedule_id
    
    async def execute_with_retry(
        self,
        test_case_id: str,
        llm_provider,
        max_retries: int = 3,
        **kwargs
    ) -> TestExecution:
        """Execute test case with automatic retry on failure."""
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                execution = await self.test_execution_manager.execute_test_case(
                    test_case_id=test_case_id,
                    llm_provider=llm_provider,
                    **kwargs
                )
                
                # If execution was successful, return it
                if execution.status.value in ["passed", "skipped"]:
                    return execution
                
                # If this was the last attempt, return the failed execution
                if attempt == max_retries:
                    return execution
                
                self.logger.warning(
                    "Test execution failed, retrying",
                    test_case_id=test_case_id,
                    attempt=attempt + 1,
                    max_retries=max_retries
                )
                
            except Exception as e:
                last_exception = e
                if attempt == max_retries:
                    raise
                
                self.logger.warning(
                    "Test execution exception, retrying",
                    test_case_id=test_case_id,
                    attempt=attempt + 1,
                    error=str(e)
                )
        
        # This should not be reached, but just in case
        if last_exception:
            raise last_exception


class TestImportExportService:
    """Service for importing and exporting test data."""
    
    def __init__(
        self,
        test_case_manager: TestCaseManager,
        test_suite_manager: TestSuiteManager
    ):
        self.test_case_manager = test_case_manager
        self.test_suite_manager = test_suite_manager
        self.logger = StructuredLogger("test_import_export_service")
    
    async def export_test_cases(
        self,
        test_case_ids: List[str],
        format: str = "json"
    ) -> Dict[str, Any]:
        """Export test cases to specified format."""
        exported_data = {
            "format": format,
            "export_time": datetime.now(timezone.utc).isoformat(),
            "test_cases": []
        }
        
        for test_case_id in test_case_ids:
            test_case = await self.test_case_manager.get_test_case(test_case_id)
            if test_case:
                exported_data["test_cases"].append(test_case.to_dict())
        
        return exported_data
    
    async def import_test_cases(
        self,
        import_data: Dict[str, Any],
        llm_provider=None
    ) -> List[TestCase]:
        """Import test cases from exported data."""
        imported_cases = []
        
        for case_data in import_data.get("test_cases", []):
            try:
                # Create new test case from imported data
                test_case = await self.test_case_manager.create_test_case(
                    name=case_data.get("name", "Imported Test"),
                    description=case_data.get("description", ""),
                    test_type=TestType(case_data.get("test_type", "functional")),
                    priority=TestPriority(case_data.get("priority", "medium")),
                    target_url=case_data.get("target_url"),
                    tags=case_data.get("tags", []),
                    environment=case_data.get("environment", "default")
                )
                
                imported_cases.append(test_case)
                
            except Exception as e:
                self.logger.error(
                    "Failed to import test case",
                    error=str(e),
                    case_data=case_data
                )
        
        return imported_cases
    
    async def export_test_suite(
        self,
        test_suite_id: str,
        include_test_cases: bool = True,
        format: str = "json"
    ) -> Dict[str, Any]:
        """Export test suite with optional test cases."""
        test_suite = await self.test_suite_manager.get_test_suite(test_suite_id)
        if not test_suite:
            raise ValueError(f"Test suite {test_suite_id} not found")
        
        exported_data = {
            "format": format,
            "export_time": datetime.now(timezone.utc).isoformat(),
            "test_suite": test_suite.to_dict()
        }
        
        if include_test_cases:
            test_cases = []
            for case_id in test_suite.test_case_ids:
                test_case = await self.test_case_manager.get_test_case(case_id)
                if test_case:
                    test_cases.append(test_case.to_dict())
            
            exported_data["test_cases"] = test_cases
        
        return exported_data
    
    async def import_test_suite(
        self,
        import_data: Dict[str, Any],
        llm_provider=None
    ) -> TestSuite:
        """Import test suite from exported data."""
        suite_data = import_data.get("test_suite", {})
        
        # Import test cases first if included
        test_case_ids = []
        if "test_cases" in import_data:
            imported_cases = await self.import_test_cases(import_data, llm_provider)
            test_case_ids = [case.id for case in imported_cases]
        
        # Create test suite
        test_suite = await self.test_suite_manager.create_test_suite(
            name=suite_data.get("name", "Imported Suite"),
            description=suite_data.get("description", ""),
            test_case_ids=test_case_ids,
            parallel_execution=suite_data.get("parallel_execution", False),
            max_parallel_workers=suite_data.get("max_parallel_workers", 4),
            stop_on_failure=suite_data.get("stop_on_failure", False),
            environment=suite_data.get("environment", "default")
        )
        
        return test_suite
