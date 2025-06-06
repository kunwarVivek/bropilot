"""
Test Case Management Managers

High-level managers for test case operations.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from .models import (
    TestCase, TestSuite, TestStep, TestResult, TestExecution,
    TestCaseStatus, TestPriority, TestType, ExecutionStatus
)
from .repositories import TestCaseRepository, TestSuiteRepository, TestExecutionRepository
from .generators import TestCaseGenerator
from src.infrastructure.logging.logger import StructuredLogger
from utils.task_runner import run_task
from src.validation import ValidationConfig, get_validation_config


class TestCaseManager:
    """Manager for test case operations."""
    
    def __init__(self, repository: TestCaseRepository):
        self.repository = repository
        self.generator = TestCaseGenerator()
        self.logger = StructuredLogger("test_case_manager")
    
    async def create_test_case(
        self,
        name: str,
        description: str,
        test_type: TestType = TestType.FUNCTIONAL,
        priority: TestPriority = TestPriority.MEDIUM,
        **kwargs
    ) -> TestCase:
        """Create a new test case."""
        test_case = TestCase(
            name=name,
            description=description,
            test_type=test_type,
            priority=priority,
            **kwargs
        )
        
        await self.repository.save(test_case)
        
        self.logger.info(
            "Test case created",
            test_case_id=test_case.id,
            name=name,
            test_type=test_type.value
        )
        
        return test_case
    
    async def create_from_natural_language(
        self,
        description: str,
        llm_provider,
        **kwargs
    ) -> TestCase:
        """Create test case from natural language description using LLM."""
        try:
            # Use LLM to generate structured test case
            test_case = await self.generator.generate_from_description(
                description, llm_provider, **kwargs
            )
            
            await self.repository.save(test_case)
            
            self.logger.info(
                "Test case generated from natural language",
                test_case_id=test_case.id,
                description=description[:100]
            )
            
            return test_case
            
        except Exception as e:
            self.logger.error(
                "Failed to generate test case from natural language",
                error=str(e),
                description=description[:100]
            )
            raise
    
    async def get_test_case(self, test_case_id: str) -> Optional[TestCase]:
        """Get test case by ID."""
        return await self.repository.get_by_id(test_case_id)
    
    async def update_test_case(self, test_case: TestCase) -> TestCase:
        """Update an existing test case."""
        test_case.updated_at = datetime.now(timezone.utc)
        test_case.version += 1
        
        await self.repository.save(test_case)
        
        self.logger.info(
            "Test case updated",
            test_case_id=test_case.id,
            version=test_case.version
        )
        
        return test_case
    
    async def delete_test_case(self, test_case_id: str) -> bool:
        """Delete a test case."""
        success = await self.repository.delete(test_case_id)
        
        if success:
            self.logger.info("Test case deleted", test_case_id=test_case_id)
        
        return success
    
    async def search_test_cases(
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
        return await self.repository.search(
            query=query,
            test_type=test_type,
            priority=priority,
            status=status,
            tags=tags,
            limit=limit,
            offset=offset
        )
    
    async def clone_test_case(
        self,
        test_case_id: str,
        new_name: Optional[str] = None
    ) -> TestCase:
        """Clone an existing test case."""
        original = await self.repository.get_by_id(test_case_id)
        if not original:
            raise ValueError(f"Test case {test_case_id} not found")
        
        # Create clone
        cloned = TestCase(
            name=new_name or f"{original.name} (Copy)",
            description=original.description,
            test_type=original.test_type,
            priority=original.priority,
            steps=original.steps.copy(),
            preconditions=original.preconditions.copy(),
            postconditions=original.postconditions.copy(),
            target_url=original.target_url,
            browser_config=original.browser_config.copy(),
            test_data=original.test_data.copy(),
            environment=original.environment,
            tags=original.tags.copy(),
            labels=original.labels.copy(),
            requirements=original.requirements.copy(),
            timeout=original.timeout,
            retry_count=original.retry_count,
            parallel_execution=original.parallel_execution
        )
        
        await self.repository.save(cloned)
        
        self.logger.info(
            "Test case cloned",
            original_id=test_case_id,
            cloned_id=cloned.id
        )
        
        return cloned


class TestSuiteManager:
    """Manager for test suite operations."""
    
    def __init__(
        self,
        suite_repository: TestSuiteRepository,
        case_repository: TestCaseRepository
    ):
        self.suite_repository = suite_repository
        self.case_repository = case_repository
        self.logger = StructuredLogger("test_suite_manager")
    
    async def create_test_suite(
        self,
        name: str,
        description: str,
        test_case_ids: Optional[List[str]] = None,
        **kwargs
    ) -> TestSuite:
        """Create a new test suite."""
        test_suite = TestSuite(
            name=name,
            description=description,
            test_case_ids=test_case_ids or [],
            execution_order=test_case_ids or [],
            **kwargs
        )
        
        await self.suite_repository.save(test_suite)
        
        self.logger.info(
            "Test suite created",
            test_suite_id=test_suite.id,
            name=name,
            test_case_count=len(test_suite.test_case_ids)
        )
        
        return test_suite
    
    async def get_test_suite(self, test_suite_id: str) -> Optional[TestSuite]:
        """Get test suite by ID."""
        return await self.suite_repository.get_by_id(test_suite_id)
    
    async def get_test_suite_with_cases(self, test_suite_id: str) -> Optional[Dict[str, Any]]:
        """Get test suite with populated test cases."""
        suite = await self.suite_repository.get_by_id(test_suite_id)
        if not suite:
            return None
        
        # Load test cases
        test_cases = []
        for case_id in suite.execution_order:
            case = await self.case_repository.get_by_id(case_id)
            if case:
                test_cases.append(case)
        
        return {
            "suite": suite,
            "test_cases": test_cases
        }
    
    async def add_test_cases_to_suite(
        self,
        test_suite_id: str,
        test_case_ids: List[str]
    ) -> bool:
        """Add test cases to a suite."""
        suite = await self.suite_repository.get_by_id(test_suite_id)
        if not suite:
            return False
        
        # Validate test cases exist
        for case_id in test_case_ids:
            case = await self.case_repository.get_by_id(case_id)
            if not case:
                self.logger.warning(
                    "Test case not found when adding to suite",
                    test_case_id=case_id,
                    test_suite_id=test_suite_id
                )
                continue
            
            suite.add_test_case(case_id)
        
        await self.suite_repository.save(suite)
        
        self.logger.info(
            "Test cases added to suite",
            test_suite_id=test_suite_id,
            added_count=len(test_case_ids)
        )
        
        return True
    
    async def remove_test_cases_from_suite(
        self,
        test_suite_id: str,
        test_case_ids: List[str]
    ) -> bool:
        """Remove test cases from a suite."""
        suite = await self.suite_repository.get_by_id(test_suite_id)
        if not suite:
            return False
        
        for case_id in test_case_ids:
            suite.remove_test_case(case_id)
        
        await self.suite_repository.save(suite)
        
        self.logger.info(
            "Test cases removed from suite",
            test_suite_id=test_suite_id,
            removed_count=len(test_case_ids)
        )
        
        return True
    
    async def reorder_suite_test_cases(
        self,
        test_suite_id: str,
        new_order: List[str]
    ) -> bool:
        """Reorder test cases in a suite."""
        suite = await self.suite_repository.get_by_id(test_suite_id)
        if not suite:
            return False
        
        if suite.reorder_test_cases(new_order):
            await self.suite_repository.save(suite)
            
            self.logger.info(
                "Test suite reordered",
                test_suite_id=test_suite_id,
                new_order=new_order
            )
            
            return True
        
        return False


class TestExecutionManager:
    """Manager for test execution operations."""
    
    def __init__(
        self,
        execution_repository: TestExecutionRepository,
        case_repository: TestCaseRepository,
        suite_repository: TestSuiteRepository
    ):
        self.execution_repository = execution_repository
        self.case_repository = case_repository
        self.suite_repository = suite_repository
        self.logger = StructuredLogger("test_execution_manager")
    
    async def execute_test_case(
        self,
        test_case_id: str,
        llm_provider,
        environment: str = "default",
        validation_config: Optional[ValidationConfig] = None,
        **kwargs
    ) -> TestExecution:
        """Execute a single test case."""
        test_case = await self.case_repository.get_by_id(test_case_id)
        if not test_case:
            raise ValueError(f"Test case {test_case_id} not found")
        
        # Create execution record
        execution = TestExecution(
            name=f"Execution of {test_case.name}",
            test_case_ids=[test_case_id],
            environment=environment,
            triggered_by="manual"
        )
        
        execution.status = ExecutionStatus.RUNNING
        execution.start_time = datetime.now(timezone.utc)
        
        await self.execution_repository.save(execution)
        
        try:
            # Execute test case using task runner
            result = await self._execute_single_test_case(
                test_case, llm_provider, validation_config, **kwargs
            )
            
            execution.add_result(result)
            execution.status = ExecutionStatus.PASSED if result.status == ExecutionStatus.PASSED else ExecutionStatus.FAILED
            
        except Exception as e:
            # Create error result
            error_result = TestResult(
                test_case_id=test_case_id,
                status=ExecutionStatus.ERROR,
                error_message=str(e),
                environment=environment
            )
            
            execution.add_result(error_result)
            execution.status = ExecutionStatus.ERROR
            
            self.logger.error(
                "Test case execution failed",
                test_case_id=test_case_id,
                error=str(e)
            )
        
        finally:
            execution.end_time = datetime.now(timezone.utc)
            if execution.start_time:
                execution.duration = (execution.end_time - execution.start_time).total_seconds()
            
            await self.execution_repository.save(execution)
        
        return execution
    
    async def execute_test_suite(
        self,
        test_suite_id: str,
        llm_provider,
        environment: str = "default",
        validation_config: Optional[ValidationConfig] = None,
        **kwargs
    ) -> TestExecution:
        """Execute a test suite."""
        suite = await self.suite_repository.get_by_id(test_suite_id)
        if not suite:
            raise ValueError(f"Test suite {test_suite_id} not found")
        
        # Create execution record
        execution = TestExecution(
            name=f"Execution of {suite.name}",
            test_suite_id=test_suite_id,
            test_case_ids=suite.execution_order,
            environment=environment,
            triggered_by="manual",
            execution_config={
                "parallel_execution": suite.parallel_execution,
                "max_parallel_workers": suite.max_parallel_workers,
                "stop_on_failure": suite.stop_on_failure
            }
        )
        
        execution.status = ExecutionStatus.RUNNING
        execution.start_time = datetime.now(timezone.utc)
        
        await self.execution_repository.save(execution)
        
        try:
            if suite.parallel_execution:
                await self._execute_suite_parallel(
                    suite, execution, llm_provider, validation_config, **kwargs
                )
            else:
                await self._execute_suite_sequential(
                    suite, execution, llm_provider, validation_config, **kwargs
                )
            
            # Determine overall status
            if execution.failed_tests > 0 or execution.error_tests > 0:
                execution.status = ExecutionStatus.FAILED
            else:
                execution.status = ExecutionStatus.PASSED
                
        except Exception as e:
            execution.status = ExecutionStatus.ERROR
            self.logger.error(
                "Test suite execution failed",
                test_suite_id=test_suite_id,
                error=str(e)
            )
        
        finally:
            execution.end_time = datetime.now(timezone.utc)
            if execution.start_time:
                execution.duration = (execution.end_time - execution.start_time).total_seconds()
            
            await self.execution_repository.save(execution)
        
        return execution
    
    async def _execute_single_test_case(
        self,
        test_case: TestCase,
        llm_provider,
        validation_config: Optional[ValidationConfig],
        **kwargs
    ) -> TestResult:
        """Execute a single test case and return result."""
        result = TestResult(
            test_case_id=test_case.id,
            environment=test_case.environment,
            start_time=datetime.now(timezone.utc)
        )
        
        try:
            # Convert test case to natural language task
            task_description = self._convert_test_case_to_task(test_case)
            
            # Execute using task runner
            execution_result = await run_task(
                task_description,
                llm_provider,
                f"logs/test_execution/{test_case.id}",
                validation_config or get_validation_config("standard")
            )
            
            result.status = ExecutionStatus.PASSED
            result.actual_result = execution_result
            
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error_message = str(e)
        
        finally:
            result.end_time = datetime.now(timezone.utc)
            if result.start_time:
                result.duration = (result.end_time - result.start_time).total_seconds()
        
        return result
    
    def _convert_test_case_to_task(self, test_case: TestCase) -> str:
        """Convert test case to natural language task description."""
        task_parts = []
        
        # Add target URL if specified
        if test_case.target_url:
            task_parts.append(f"Navigate to {test_case.target_url}")
        
        # Add preconditions
        if test_case.preconditions:
            task_parts.append("Preconditions:")
            task_parts.extend(f"- {condition}" for condition in test_case.preconditions)
        
        # Add test steps
        if test_case.steps:
            task_parts.append("Test Steps:")
            for step in test_case.steps:
                task_parts.append(f"{step.step_number}. {step.action}")
                if step.expected_result:
                    task_parts.append(f"   Expected: {step.expected_result}")
        
        # Add postconditions
        if test_case.postconditions:
            task_parts.append("Postconditions:")
            task_parts.extend(f"- {condition}" for condition in test_case.postconditions)
        
        return "\n".join(task_parts)
    
    async def _execute_suite_sequential(
        self,
        suite: TestSuite,
        execution: TestExecution,
        llm_provider,
        validation_config: Optional[ValidationConfig],
        **kwargs
    ) -> None:
        """Execute test suite sequentially."""
        for case_id in suite.execution_order:
            test_case = await self.case_repository.get_by_id(case_id)
            if not test_case:
                continue
            
            try:
                result = await self._execute_single_test_case(
                    test_case, llm_provider, validation_config, **kwargs
                )
                execution.add_result(result)
                
                # Stop on failure if configured
                if suite.stop_on_failure and result.status in [ExecutionStatus.FAILED, ExecutionStatus.ERROR]:
                    self.logger.info(
                        "Stopping suite execution due to failure",
                        test_suite_id=suite.id,
                        failed_test_case_id=case_id
                    )
                    break
                    
            except Exception as e:
                error_result = TestResult(
                    test_case_id=case_id,
                    status=ExecutionStatus.ERROR,
                    error_message=str(e)
                )
                execution.add_result(error_result)
                
                if suite.stop_on_failure:
                    break
    
    async def _execute_suite_parallel(
        self,
        suite: TestSuite,
        execution: TestExecution,
        llm_provider,
        validation_config: Optional[ValidationConfig],
        **kwargs
    ) -> None:
        """Execute test suite in parallel."""
        semaphore = asyncio.Semaphore(suite.max_parallel_workers)
        
        async def execute_with_semaphore(case_id: str):
            async with semaphore:
                test_case = await self.case_repository.get_by_id(case_id)
                if test_case:
                    return await self._execute_single_test_case(
                        test_case, llm_provider, validation_config, **kwargs
                    )
                return None
        
        # Execute all test cases in parallel
        tasks = [execute_with_semaphore(case_id) for case_id in suite.execution_order]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = TestResult(
                    test_case_id=suite.execution_order[i],
                    status=ExecutionStatus.ERROR,
                    error_message=str(result)
                )
                execution.add_result(error_result)
            elif result:
                execution.add_result(result)
