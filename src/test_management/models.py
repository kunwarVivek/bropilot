"""
Test Case Management Models

Core data models for test case management system.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field


class TestCaseStatus(str, Enum):
    """Test case status enumeration."""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class TestPriority(str, Enum):
    """Test priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TestType(str, Enum):
    """Test type enumeration."""
    FUNCTIONAL = "functional"
    REGRESSION = "regression"
    SMOKE = "smoke"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    SECURITY = "security"
    ACCESSIBILITY = "accessibility"
    VISUAL = "visual"
    API = "api"


class ExecutionStatus(str, Enum):
    """Test execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    ERROR = "error"


@dataclass
class TestStep:
    """Individual test step within a test case."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    step_number: int = 1
    description: str = ""
    action: str = ""  # Natural language action description
    expected_result: str = ""
    test_data: Dict[str, Any] = field(default_factory=dict)
    validation_rules: List[str] = field(default_factory=list)
    is_optional: bool = False
    timeout: Optional[int] = None
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "step_number": self.step_number,
            "description": self.description,
            "action": self.action,
            "expected_result": self.expected_result,
            "test_data": self.test_data,
            "validation_rules": self.validation_rules,
            "is_optional": self.is_optional,
            "timeout": self.timeout,
            "retry_count": self.retry_count
        }


@dataclass
class TestCase:
    """Test case model for natural language test automation."""
    
    # Core identification
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    
    # Test classification
    test_type: TestType = TestType.FUNCTIONAL
    priority: TestPriority = TestPriority.MEDIUM
    status: TestCaseStatus = TestCaseStatus.DRAFT
    
    # Test content
    steps: List[TestStep] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    
    # Test configuration
    target_url: Optional[str] = None
    browser_config: Dict[str, Any] = field(default_factory=dict)
    test_data: Dict[str, Any] = field(default_factory=dict)
    environment: str = "default"
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    requirements: List[str] = field(default_factory=list)  # Linked requirements
    
    # Execution settings
    timeout: int = 300  # 5 minutes default
    retry_count: int = 1
    parallel_execution: bool = True
    
    # Audit fields
    created_by: str = "system"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_by: str = "system"
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1
    
    def add_step(self, step: TestStep) -> None:
        """Add a test step."""
        step.step_number = len(self.steps) + 1
        self.steps.append(step)
        self.updated_at = datetime.now(timezone.utc)
    
    def remove_step(self, step_id: str) -> bool:
        """Remove a test step by ID."""
        for i, step in enumerate(self.steps):
            if step.id == step_id:
                self.steps.pop(i)
                # Renumber remaining steps
                for j, remaining_step in enumerate(self.steps[i:], i):
                    remaining_step.step_number = j + 1
                self.updated_at = datetime.now(timezone.utc)
                return True
        return False
    
    def get_step(self, step_id: str) -> Optional[TestStep]:
        """Get a test step by ID."""
        return next((step for step in self.steps if step.id == step_id), None)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "test_type": self.test_type.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "steps": [step.to_dict() for step in self.steps],
            "preconditions": self.preconditions,
            "postconditions": self.postconditions,
            "target_url": self.target_url,
            "browser_config": self.browser_config,
            "test_data": self.test_data,
            "environment": self.environment,
            "tags": self.tags,
            "labels": self.labels,
            "requirements": self.requirements,
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "parallel_execution": self.parallel_execution,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat(),
            "version": self.version
        }


@dataclass
class TestSuite:
    """Test suite containing multiple test cases."""
    
    # Core identification
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    
    # Suite configuration
    test_case_ids: List[str] = field(default_factory=list)
    execution_order: List[str] = field(default_factory=list)  # Ordered test case IDs
    
    # Execution settings
    parallel_execution: bool = False
    max_parallel_workers: int = 4
    stop_on_failure: bool = False
    timeout: int = 3600  # 1 hour default
    
    # Environment and configuration
    environment: str = "default"
    browser_config: Dict[str, Any] = field(default_factory=dict)
    suite_data: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    
    # Audit fields
    created_by: str = "system"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_by: str = "system"
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1
    
    def add_test_case(self, test_case_id: str, position: Optional[int] = None) -> None:
        """Add a test case to the suite."""
        if test_case_id not in self.test_case_ids:
            self.test_case_ids.append(test_case_id)
            
            if position is not None:
                # Insert at specific position in execution order
                self.execution_order.insert(position, test_case_id)
            else:
                # Add to end of execution order
                self.execution_order.append(test_case_id)
            
            self.updated_at = datetime.now(timezone.utc)
    
    def remove_test_case(self, test_case_id: str) -> bool:
        """Remove a test case from the suite."""
        if test_case_id in self.test_case_ids:
            self.test_case_ids.remove(test_case_id)
            if test_case_id in self.execution_order:
                self.execution_order.remove(test_case_id)
            self.updated_at = datetime.now(timezone.utc)
            return True
        return False
    
    def reorder_test_cases(self, new_order: List[str]) -> bool:
        """Reorder test case execution."""
        # Validate all test cases exist in suite
        if all(tc_id in self.test_case_ids for tc_id in new_order):
            self.execution_order = new_order
            self.updated_at = datetime.now(timezone.utc)
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "test_case_ids": self.test_case_ids,
            "execution_order": self.execution_order,
            "parallel_execution": self.parallel_execution,
            "max_parallel_workers": self.max_parallel_workers,
            "stop_on_failure": self.stop_on_failure,
            "timeout": self.timeout,
            "environment": self.environment,
            "browser_config": self.browser_config,
            "suite_data": self.suite_data,
            "tags": self.tags,
            "labels": self.labels,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_by": self.updated_by,
            "updated_at": self.updated_at.isoformat(),
            "version": self.version
        }


@dataclass
class TestResult:
    """Individual test step or test case result."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    test_case_id: str = ""
    test_step_id: Optional[str] = None
    
    # Execution details
    status: ExecutionStatus = ExecutionStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0
    
    # Result details
    actual_result: str = ""
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    
    # Evidence and artifacts
    screenshots: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    artifacts: Dict[str, str] = field(default_factory=dict)
    
    # Metadata
    environment: str = "default"
    browser_info: Dict[str, Any] = field(default_factory=dict)
    system_info: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "test_case_id": self.test_case_id,
            "test_step_id": self.test_step_id,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "actual_result": self.actual_result,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "screenshots": self.screenshots,
            "logs": self.logs,
            "artifacts": self.artifacts,
            "environment": self.environment,
            "browser_info": self.browser_info,
            "system_info": self.system_info
        }


@dataclass
class TestExecution:
    """Test execution session containing multiple test results."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    
    # Execution scope
    test_suite_id: Optional[str] = None
    test_case_ids: List[str] = field(default_factory=list)
    
    # Execution status
    status: ExecutionStatus = ExecutionStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: float = 0.0
    
    # Results
    test_results: List[TestResult] = field(default_factory=list)
    
    # Statistics
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    
    # Configuration
    environment: str = "default"
    browser_config: Dict[str, Any] = field(default_factory=dict)
    execution_config: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    triggered_by: str = "manual"
    tags: List[str] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)
    
    # Audit fields
    created_by: str = "system"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def add_result(self, result: TestResult) -> None:
        """Add a test result."""
        self.test_results.append(result)
        self._update_statistics()
    
    def _update_statistics(self) -> None:
        """Update execution statistics."""
        self.total_tests = len(self.test_results)
        self.passed_tests = sum(1 for r in self.test_results if r.status == ExecutionStatus.PASSED)
        self.failed_tests = sum(1 for r in self.test_results if r.status == ExecutionStatus.FAILED)
        self.skipped_tests = sum(1 for r in self.test_results if r.status == ExecutionStatus.SKIPPED)
        self.error_tests = sum(1 for r in self.test_results if r.status == ExecutionStatus.ERROR)
    
    def get_success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_tests == 0:
            return 0.0
        return self.passed_tests / self.total_tests
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "test_suite_id": self.test_suite_id,
            "test_case_ids": self.test_case_ids,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "test_results": [result.to_dict() for result in self.test_results],
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "skipped_tests": self.skipped_tests,
            "error_tests": self.error_tests,
            "success_rate": self.get_success_rate(),
            "environment": self.environment,
            "browser_config": self.browser_config,
            "execution_config": self.execution_config,
            "triggered_by": self.triggered_by,
            "tags": self.tags,
            "labels": self.labels,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat()
        }
