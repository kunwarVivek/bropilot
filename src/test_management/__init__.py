"""
Test Case Management System

Comprehensive test case management for LLM-powered browser automation testing.
This module provides the core infrastructure for organizing, managing, and executing
natural language test cases.
"""

from .models import (
    TestCase,
    TestSuite, 
    TestStep,
    TestResult,
    TestExecution,
    TestCaseStatus,
    TestPriority,
    TestType
)

from .managers import (
    TestCaseManager,
    TestSuiteManager,
    TestExecutionManager
)

from .repositories import (
    TestCaseRepository,
    TestSuiteRepository,
    TestExecutionRepository
)

from .services import (
    TestCaseService,
    TestSuiteService,
    TestExecutionService,
    TestImportExportService
)

from .generators import (
    TestCaseGenerator,
    TestStepGenerator
)

__all__ = [
    # Models
    "TestCase",
    "TestSuite",
    "TestStep", 
    "TestResult",
    "TestExecution",
    "TestCaseStatus",
    "TestPriority",
    "TestType",
    
    # Managers
    "TestCaseManager",
    "TestSuiteManager", 
    "TestExecutionManager",
    
    # Repositories
    "TestCaseRepository",
    "TestSuiteRepository",
    "TestExecutionRepository",
    
    # Services
    "TestCaseService",
    "TestSuiteService",
    "TestExecutionService",
    "TestImportExportService",
    
    # Generators
    "TestCaseGenerator",
    "TestStepGenerator"
]
