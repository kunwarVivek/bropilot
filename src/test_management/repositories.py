"""
Test Management Repositories

Data persistence layer for test management components.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from .models import (
    TestCase, TestSuite, TestExecution, TestResult,
    TestCaseStatus, TestPriority, TestType, ExecutionStatus
)


class BaseRepository:
    """Base repository with common functionality."""
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, item_id: str) -> Path:
        """Get file path for an item."""
        return self.storage_path / f"{item_id}.json"
    
    def _save_to_file(self, item_id: str, data: Dict[str, Any]) -> None:
        """Save data to file."""
        file_path = self._get_file_path(item_id)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def _load_from_file(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Load data from file."""
        file_path = self._get_file_path(item_id)
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    
    def _list_all_files(self) -> List[str]:
        """List all item IDs."""
        return [
            f.stem for f in self.storage_path.glob("*.json")
            if f.is_file()
        ]
    
    def _delete_file(self, item_id: str) -> bool:
        """Delete file for an item."""
        file_path = self._get_file_path(item_id)
        if file_path.exists():
            file_path.unlink()
            return True
        return False


class TestCaseRepository(BaseRepository):
    """Repository for test case persistence."""
    
    async def save(self, test_case: TestCase) -> None:
        """Save a test case."""
        data = test_case.to_dict()
        self._save_to_file(test_case.id, data)
    
    async def get_by_id(self, test_case_id: str) -> Optional[TestCase]:
        """Get test case by ID."""
        data = self._load_from_file(test_case_id)
        if not data:
            return None
        
        return self._dict_to_test_case(data)
    
    async def delete(self, test_case_id: str) -> bool:
        """Delete a test case."""
        return self._delete_file(test_case_id)
    
    async def search(
        self,
        query: Optional[str] = None,
        test_type: Optional[TestType] = None,
        priority: Optional[TestPriority] = None,
        status: Optional[TestCaseStatus] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TestCase]:
        """Search test cases with filters."""
        all_ids = self._list_all_files()
        results = []
        
        for item_id in all_ids[offset:offset + limit]:
            test_case = await self.get_by_id(item_id)
            if not test_case:
                continue
            
            # Apply filters
            if test_type and test_case.test_type != test_type:
                continue
            
            if priority and test_case.priority != priority:
                continue
            
            if status and test_case.status != status:
                continue
            
            if tags and not any(tag in test_case.tags for tag in tags):
                continue
            
            if query and query.lower() not in test_case.name.lower() and query.lower() not in test_case.description.lower():
                continue
            
            results.append(test_case)
        
        return results
    
    def _dict_to_test_case(self, data: Dict[str, Any]) -> TestCase:
        """Convert dictionary to TestCase object."""
        from .models import TestStep
        
        # Convert steps
        steps = []
        for step_data in data.get("steps", []):
            step = TestStep(
                id=step_data.get("id", ""),
                step_number=step_data.get("step_number", 1),
                description=step_data.get("description", ""),
                action=step_data.get("action", ""),
                expected_result=step_data.get("expected_result", ""),
                test_data=step_data.get("test_data", {}),
                validation_rules=step_data.get("validation_rules", []),
                is_optional=step_data.get("is_optional", False),
                timeout=step_data.get("timeout"),
                retry_count=step_data.get("retry_count", 0)
            )
            steps.append(step)
        
        # Convert timestamps
        created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc)
        updated_at = datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(timezone.utc)
        
        return TestCase(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            test_type=TestType(data.get("test_type", "functional")),
            priority=TestPriority(data.get("priority", "medium")),
            status=TestCaseStatus(data.get("status", "draft")),
            steps=steps,
            preconditions=data.get("preconditions", []),
            postconditions=data.get("postconditions", []),
            target_url=data.get("target_url"),
            browser_config=data.get("browser_config", {}),
            test_data=data.get("test_data", {}),
            environment=data.get("environment", "default"),
            tags=data.get("tags", []),
            labels=data.get("labels", {}),
            requirements=data.get("requirements", []),
            timeout=data.get("timeout", 300),
            retry_count=data.get("retry_count", 1),
            parallel_execution=data.get("parallel_execution", True),
            created_by=data.get("created_by", "system"),
            created_at=created_at,
            updated_by=data.get("updated_by", "system"),
            updated_at=updated_at,
            version=data.get("version", 1)
        )


class TestSuiteRepository(BaseRepository):
    """Repository for test suite persistence."""
    
    async def save(self, test_suite: TestSuite) -> None:
        """Save a test suite."""
        data = test_suite.to_dict()
        self._save_to_file(test_suite.id, data)
    
    async def get_by_id(self, test_suite_id: str) -> Optional[TestSuite]:
        """Get test suite by ID."""
        data = self._load_from_file(test_suite_id)
        if not data:
            return None
        
        return self._dict_to_test_suite(data)
    
    async def delete(self, test_suite_id: str) -> bool:
        """Delete a test suite."""
        return self._delete_file(test_suite_id)
    
    def _dict_to_test_suite(self, data: Dict[str, Any]) -> TestSuite:
        """Convert dictionary to TestSuite object."""
        # Convert timestamps
        created_at = datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc)
        updated_at = datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(timezone.utc)
        
        return TestSuite(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            test_case_ids=data.get("test_case_ids", []),
            execution_order=data.get("execution_order", []),
            parallel_execution=data.get("parallel_execution", False),
            max_parallel_workers=data.get("max_parallel_workers", 4),
            stop_on_failure=data.get("stop_on_failure", False),
            timeout=data.get("timeout", 3600),
            environment=data.get("environment", "default"),
            browser_config=data.get("browser_config", {}),
            suite_data=data.get("suite_data", {}),
            tags=data.get("tags", []),
            labels=data.get("labels", {}),
            created_by=data.get("created_by", "system"),
            created_at=created_at,
            updated_by=data.get("updated_by", "system"),
            updated_at=updated_at,
            version=data.get("version", 1)
        )


class TestExecutionRepository(BaseRepository):
    """Repository for test execution persistence."""
    
    async def save(self, test_execution: TestExecution) -> None:
        """Save a test execution."""
        data = test_execution.to_dict()
        self._save_to_file(test_execution.id, data)
    
    async def get_by_id(self, test_execution_id: str) -> Optional[TestExecution]:
        """Get test execution by ID."""
        data = self._load_from_file(test_execution_id)
        if not data:
            return None
        
        return self._dict_to_test_execution(data)
    
    async def delete(self, test_execution_id: str) -> bool:
        """Delete a test execution."""
        return self._delete_file(test_execution_id)
    
    async def get_recent_executions(self, limit: int = 10) -> List[TestExecution]:
        """Get recent test executions."""
        all_ids = self._list_all_files()
        executions = []
        
        for item_id in all_ids:
            execution = await self.get_by_id(item_id)
            if execution:
                executions.append(execution)
        
        # Sort by creation time (most recent first)
        executions.sort(key=lambda x: x.created_at, reverse=True)
        return executions[:limit]
    
    def _dict_to_test_execution(self, data: Dict[str, Any]) -> TestExecution:
        """Convert dictionary to TestExecution object."""
        from .models import TestResult
        
        # Convert test results
        test_results = []
        for result_data in data.get("test_results", []):
            # Convert timestamps
            start_time = None
            end_time = None
            if result_data.get("start_time"):
                start_time = datetime.fromisoformat(result_data["start_time"])
            if result_data.get("end_time"):
                end_time = datetime.fromisoformat(result_data["end_time"])
            
            result = TestResult(
                id=result_data.get("id", ""),
                test_case_id=result_data.get("test_case_id", ""),
                test_step_id=result_data.get("test_step_id"),
                status=ExecutionStatus(result_data.get("status", "pending")),
                start_time=start_time,
                end_time=end_time,
                duration=result_data.get("duration", 0.0),
                actual_result=result_data.get("actual_result", ""),
                error_message=result_data.get("error_message"),
                stack_trace=result_data.get("stack_trace"),
                screenshots=result_data.get("screenshots", []),
                logs=result_data.get("logs", []),
                artifacts=result_data.get("artifacts", {}),
                environment=result_data.get("environment", "default"),
                browser_info=result_data.get("browser_info", {}),
                system_info=result_data.get("system_info", {})
            )
            test_results.append(result)
        
        # Convert timestamps
        start_time = None
        end_time = None
        created_at = datetime.now(timezone.utc)
        
        if data.get("start_time"):
            start_time = datetime.fromisoformat(data["start_time"])
        if data.get("end_time"):
            end_time = datetime.fromisoformat(data["end_time"])
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        
        execution = TestExecution(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            test_suite_id=data.get("test_suite_id"),
            test_case_ids=data.get("test_case_ids", []),
            status=ExecutionStatus(data.get("status", "pending")),
            start_time=start_time,
            end_time=end_time,
            duration=data.get("duration", 0.0),
            test_results=test_results,
            total_tests=data.get("total_tests", 0),
            passed_tests=data.get("passed_tests", 0),
            failed_tests=data.get("failed_tests", 0),
            skipped_tests=data.get("skipped_tests", 0),
            error_tests=data.get("error_tests", 0),
            environment=data.get("environment", "default"),
            browser_config=data.get("browser_config", {}),
            execution_config=data.get("execution_config", {}),
            triggered_by=data.get("triggered_by", "manual"),
            tags=data.get("tags", []),
            labels=data.get("labels", {}),
            created_by=data.get("created_by", "system"),
            created_at=created_at
        )
        
        return execution
