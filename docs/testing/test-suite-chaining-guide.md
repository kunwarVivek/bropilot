# Test Suite Chaining Guide

## 🔗 Overview

This guide covers advanced test suite management, including chaining test suites together, managing complex dependencies, and orchestrating comprehensive testing workflows across multiple environments and scenarios.

## 📋 Table of Contents

- [Suite Chaining Fundamentals](#suite-chaining-fundamentals)
- [Creating Chained Test Suites](#creating-chained-test-suites)
- [Cross-Suite Dependencies](#cross-suite-dependencies)
- [Conditional Execution](#conditional-execution)
- [Environment-Specific Suites](#environment-specific-suites)
- [Advanced Orchestration](#advanced-orchestration)
- [Monitoring and Reporting](#monitoring-and-reporting)

## 🏗️ Suite Chaining Fundamentals

### Basic Suite Chain

```python
# tests/suites/chained_test_execution.py
from src.testing.test_framework import TestSuiteChain, TestSuite
from src.testing.orchestration import SuiteOrchestrator

class ComprehensiveTestChain(TestSuiteChain):
    """Comprehensive test execution chain."""
    
    def __init__(self):
        super().__init__(
            name="Comprehensive Test Chain",
            description="Full application testing from unit to production validation",
            execution_strategy="sequential_with_gates",
            failure_strategy="stop_on_critical_failure",
            
            # Global configuration
            global_timeout=14400,  # 4 hours
            global_retry_policy={
                "max_retries": 2,
                "retry_delay": 300,  # 5 minutes
                "retry_on": ["infrastructure_failure", "transient_error"]
            }
        )
        
        # Define the test execution chain
        self.chain = [
            self._create_unit_test_suite(),
            self._create_integration_test_suite(),
            self._create_smoke_test_suite(),
            self._create_regression_test_suite(),
            self._create_performance_test_suite(),
            self._create_security_test_suite(),
            self._create_acceptance_test_suite()
        ]
        
        # Define gates between suites
        self.gates = [
            {
                "after_suite": "unit_tests",
                "condition": "all_tests_pass",
                "action": "continue"
            },
            {
                "after_suite": "integration_tests", 
                "condition": "success_rate >= 0.95",
                "action": "continue_with_warning"
            },
            {
                "after_suite": "smoke_tests",
                "condition": "critical_tests_pass",
                "action": "continue",
                "failure_action": "stop_chain"
            }
        ]
    
    def _create_unit_test_suite(self):
        """Create unit test suite."""
        return TestSuite(
            name="Unit Tests",
            description="Fast unit tests for core functionality",
            tags=["unit", "fast"],
            execution_mode="parallel",
            max_workers=8,
            timeout=600,  # 10 minutes
            
            # Success criteria
            success_criteria={
                "min_pass_rate": 1.0,  # 100% pass rate required
                "max_execution_time": 600,
                "max_memory_usage": 1024  # 1GB
            },
            
            # Test discovery
            test_patterns=[
                "tests/unit/**/*test*.py",
                "tests/unit/**/test_*.py"
            ]
        )
    
    def _create_integration_test_suite(self):
        """Create integration test suite."""
        return TestSuite(
            name="Integration Tests",
            description="Integration tests for component interactions",
            tags=["integration", "medium"],
            execution_mode="parallel",
            max_workers=4,
            timeout=1800,  # 30 minutes
            
            # Dependencies
            depends_on=["Unit Tests"],
            
            # Environment requirements
            environment_setup={
                "database": "test_integration",
                "services": ["api", "cache", "queue"],
                "external_dependencies": ["mock_payment_service"]
            },
            
            # Success criteria
            success_criteria={
                "min_pass_rate": 0.95,  # 95% pass rate
                "max_execution_time": 1800,
                "critical_tests_pass": True
            }
        )
    
    def _create_smoke_test_suite(self):
        """Create smoke test suite."""
        return TestSuite(
            name="Smoke Tests",
            description="Critical functionality smoke tests",
            tags=["smoke", "critical"],
            execution_mode="sequential",  # Sequential for smoke tests
            timeout=900,  # 15 minutes
            
            # Dependencies
            depends_on=["Integration Tests"],
            
            # Critical suite - failure stops the chain
            is_critical=True,
            
            # Success criteria
            success_criteria={
                "min_pass_rate": 1.0,  # 100% pass rate required
                "max_execution_time": 900,
                "all_critical_tests_pass": True
            }
        )

class EnvironmentSpecificChain(TestSuiteChain):
    """Environment-specific test chain."""
    
    def __init__(self, environment: str):
        self.environment = environment
        
        super().__init__(
            name=f"{environment.title()} Test Chain",
            description=f"Test chain for {environment} environment",
            execution_strategy="adaptive",
            
            # Environment-specific configuration
            environment_config={
                "target_environment": environment,
                "base_url": self._get_base_url(environment),
                "database_config": self._get_database_config(environment),
                "service_endpoints": self._get_service_endpoints(environment)
            }
        )
        
        # Build environment-specific chain
        self.chain = self._build_environment_chain()
    
    def _build_environment_chain(self):
        """Build test chain based on environment."""
        if self.environment == "development":
            return [
                self._create_dev_smoke_tests(),
                self._create_dev_feature_tests(),
                self._create_dev_integration_tests()
            ]
        elif self.environment == "staging":
            return [
                self._create_staging_smoke_tests(),
                self._create_staging_regression_tests(),
                self._create_staging_performance_tests(),
                self._create_staging_security_tests()
            ]
        elif self.environment == "production":
            return [
                self._create_prod_health_checks(),
                self._create_prod_monitoring_tests(),
                self._create_prod_canary_tests()
            ]
        else:
            raise ValueError(f"Unknown environment: {self.environment}")
```

## 🎯 Cross-Suite Dependencies

### Complex Dependency Management

```python
# tests/suites/dependency_management.py
from src.testing.dependencies import SuiteDependencyManager, DependencyGraph

class AdvancedDependencyChain(TestSuiteChain):
    """Test chain with complex dependencies."""
    
    def __init__(self):
        super().__init__(
            name="Advanced Dependency Chain",
            description="Test chain with complex cross-suite dependencies"
        )
        
        # Create dependency manager
        self.dependency_manager = SuiteDependencyManager()
        
        # Define complex dependency graph
        self._setup_dependency_graph()
        
        # Create suites with dependencies
        self.suites = self._create_dependent_suites()
    
    def _setup_dependency_graph(self):
        """Setup complex dependency relationships."""
        
        # Define suite dependencies
        dependencies = [
            # Basic dependencies
            ("database_tests", [], ["database_ready"]),
            ("api_tests", ["database_tests"], ["api_endpoints_verified"]),
            ("auth_tests", ["api_tests"], ["authentication_working"]),
            
            # Parallel branches
            ("ui_tests", ["auth_tests"], ["ui_functional"]),
            ("mobile_tests", ["auth_tests"], ["mobile_functional"]),
            
            # Integration points
            ("integration_tests", ["ui_tests", "mobile_tests"], ["full_integration_verified"]),
            
            # Final validation
            ("e2e_tests", ["integration_tests"], ["e2e_scenarios_pass"]),
            ("performance_tests", ["e2e_tests"], ["performance_validated"]),
            
            # Conditional dependencies
            ("security_tests", ["performance_tests"], ["security_validated"], {
                "condition": "environment == 'production'",
                "optional": False
            }),
            ("load_tests", ["performance_tests"], ["load_validated"], {
                "condition": "run_load_tests == True",
                "optional": True
            })
        ]
        
        # Build dependency graph
        for dep in dependencies:
            suite_name, depends_on, provides = dep[:3]
            conditions = dep[3] if len(dep) > 3 else {}
            
            self.dependency_manager.add_dependency(
                suite_name=suite_name,
                depends_on=depends_on,
                provides=provides,
                **conditions
            )
    
    def _create_dependent_suites(self):
        """Create suites with proper dependency configuration."""
        suites = {}
        
        # Database tests (no dependencies)
        suites["database_tests"] = TestSuite(
            name="Database Tests",
            description="Database connectivity and schema validation",
            tags=["database", "infrastructure"],
            provides=["database_ready"]
        )
        
        # API tests (depends on database)
        suites["api_tests"] = TestSuite(
            name="API Tests",
            description="API endpoint testing",
            tags=["api", "backend"],
            depends_on=["database_tests"],
            requires=["database_ready"],
            provides=["api_endpoints_verified"]
        )
        
        # Authentication tests (depends on API)
        suites["auth_tests"] = TestSuite(
            name="Authentication Tests",
            description="User authentication and authorization",
            tags=["auth", "security"],
            depends_on=["api_tests"],
            requires=["api_endpoints_verified"],
            provides=["authentication_working"]
        )
        
        # Parallel UI and Mobile tests
        suites["ui_tests"] = TestSuite(
            name="UI Tests",
            description="Web user interface testing",
            tags=["ui", "frontend"],
            depends_on=["auth_tests"],
            requires=["authentication_working"],
            provides=["ui_functional"],
            parallel_group="frontend_tests"
        )
        
        suites["mobile_tests"] = TestSuite(
            name="Mobile Tests", 
            description="Mobile application testing",
            tags=["mobile", "frontend"],
            depends_on=["auth_tests"],
            requires=["authentication_working"],
            provides=["mobile_functional"],
            parallel_group="frontend_tests"
        )
        
        return suites
```

## 🔄 Conditional Execution

### Dynamic Suite Selection

```python
# tests/suites/conditional_execution.py
from src.testing.conditions import ExecutionCondition, EnvironmentCondition, TimeCondition

class ConditionalTestChain(TestSuiteChain):
    """Test chain with conditional execution logic."""
    
    def __init__(self):
        super().__init__(
            name="Conditional Test Chain",
            description="Test chain that adapts based on conditions"
        )
        
        # Define conditional suites
        self.conditional_suites = [
            {
                "suite": self._create_nightly_regression_suite(),
                "conditions": [
                    TimeCondition(schedule="nightly"),
                    EnvironmentCondition(environments=["staging", "production"])
                ]
            },
            {
                "suite": self._create_performance_suite(),
                "conditions": [
                    ExecutionCondition(lambda: self._should_run_performance_tests()),
                    EnvironmentCondition(environments=["staging"])
                ]
            },
            {
                "suite": self._create_security_suite(),
                "conditions": [
                    ExecutionCondition(lambda: self._is_security_scan_required()),
                    TimeCondition(schedule="weekly")
                ]
            },
            {
                "suite": self._create_compatibility_suite(),
                "conditions": [
                    ExecutionCondition(lambda: self._has_browser_updates()),
                    EnvironmentCondition(environments=["staging"])
                ]
            }
        ]
    
    async def execute_conditional_chain(self, context: dict):
        """Execute test chain based on conditions."""
        execution_plan = []
        
        # Evaluate conditions for each suite
        for conditional_suite in self.conditional_suites:
            suite = conditional_suite["suite"]
            conditions = conditional_suite["conditions"]
            
            # Check if all conditions are met
            should_execute = True
            for condition in conditions:
                if not await condition.evaluate(context):
                    should_execute = False
                    break
            
            if should_execute:
                execution_plan.append(suite)
                self.logger.info(f"Suite {suite.name} added to execution plan")
            else:
                self.logger.info(f"Suite {suite.name} skipped due to unmet conditions")
        
        # Execute the filtered suites
        return await self.execute_suite_chain(execution_plan)
    
    def _should_run_performance_tests(self) -> bool:
        """Determine if performance tests should run."""
        # Check if there were significant code changes
        code_changes = self._get_recent_code_changes()
        performance_critical_changes = any(
            change.affects_performance for change in code_changes
        )
        
        # Check if it's been too long since last performance test
        last_perf_test = self._get_last_performance_test_time()
        time_since_last = datetime.now() - last_perf_test
        
        return performance_critical_changes or time_since_last > timedelta(days=7)
    
    def _is_security_scan_required(self) -> bool:
        """Determine if security scan is required."""
        # Check for security-related changes
        recent_changes = self._get_recent_code_changes()
        security_changes = any(
            change.affects_security for change in recent_changes
        )
        
        # Check for new dependencies
        new_dependencies = self._check_for_new_dependencies()
        
        return security_changes or new_dependencies
```
