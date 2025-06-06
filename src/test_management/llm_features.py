"""
Advanced LLM Test Features

LLM-powered advanced test automation features including:
- Test case auto-generation from requirements
- Test maintenance and updates when UI changes
- Intelligent test optimization
"""

import json
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from pathlib import Path

from .models import TestCase, TestStep, TestType, TestPriority, TestCaseStatus
from .generators import TestCaseGenerator
from src.infrastructure.logging.logger import StructuredLogger


class RequirementsToTestGenerator:
    """LLM-powered generator that creates comprehensive test cases from requirements documents."""
    
    def __init__(self):
        self.logger = StructuredLogger("requirements_to_test_generator")
        self.test_case_generator = TestCaseGenerator()
    
    async def generate_test_cases_from_requirements(
        self,
        requirements_document: str,
        llm_provider,
        test_coverage_level: str = "comprehensive",
        **kwargs
    ) -> List[TestCase]:
        """Generate comprehensive test cases from requirements document."""
        try:
            # Step 1: Analyze requirements and extract testable features
            features = await self._extract_testable_features(requirements_document, llm_provider)
            
            # Step 2: Generate test scenarios for each feature
            test_scenarios = await self._generate_test_scenarios(features, llm_provider, test_coverage_level)
            
            # Step 3: Create detailed test cases from scenarios
            test_cases = []
            for scenario in test_scenarios:
                test_case = await self._create_test_case_from_scenario(
                    scenario, llm_provider, **kwargs
                )
                test_cases.append(test_case)
            
            self.logger.info(
                "Test cases generated from requirements",
                requirements_length=len(requirements_document),
                features_extracted=len(features),
                scenarios_generated=len(test_scenarios),
                test_cases_created=len(test_cases),
                coverage_level=test_coverage_level
            )
            
            return test_cases
            
        except Exception as e:
            self.logger.error(
                "Failed to generate test cases from requirements",
                error=str(e),
                requirements_length=len(requirements_document)
            )
            raise
    
    async def _extract_testable_features(
        self,
        requirements_document: str,
        llm_provider
    ) -> List[Dict[str, Any]]:
        """Extract testable features from requirements document."""
        prompt = f"""
Analyze the following requirements document and extract all testable features and functionalities.

Requirements Document:
{requirements_document}

For each testable feature, provide:
1. Feature name
2. Description
3. Acceptance criteria
4. Priority (high/medium/low)
5. Test type (functional/integration/e2e/performance/security)
6. Dependencies on other features
7. User roles involved
8. Business rules
9. Edge cases to consider

Format your response as JSON array:
[
    {{
        "feature_name": "User Login",
        "description": "Users can authenticate using email and password",
        "acceptance_criteria": [
            "User can login with valid credentials",
            "Invalid credentials show error message",
            "Account lockout after 3 failed attempts"
        ],
        "priority": "high",
        "test_types": ["functional", "security"],
        "dependencies": ["User Registration"],
        "user_roles": ["end_user", "admin"],
        "business_rules": [
            "Password must be at least 8 characters",
            "Email must be valid format"
        ],
        "edge_cases": [
            "Empty credentials",
            "SQL injection attempts",
            "Very long passwords"
        ],
        "estimated_test_cases": 8
    }}
]

Extract all testable features comprehensively:
"""
        
        response = await llm_provider.invoke(prompt)
        return self._parse_features_response(response)
    
    async def _generate_test_scenarios(
        self,
        features: List[Dict[str, Any]],
        llm_provider,
        coverage_level: str
    ) -> List[Dict[str, Any]]:
        """Generate test scenarios for extracted features."""
        scenarios = []
        
        for feature in features:
            feature_scenarios = await self._generate_scenarios_for_feature(
                feature, llm_provider, coverage_level
            )
            scenarios.extend(feature_scenarios)
        
        return scenarios
    
    async def _generate_scenarios_for_feature(
        self,
        feature: Dict[str, Any],
        llm_provider,
        coverage_level: str
    ) -> List[Dict[str, Any]]:
        """Generate test scenarios for a specific feature."""
        coverage_instructions = {
            "basic": "Generate 2-3 core positive test scenarios",
            "standard": "Generate 4-6 scenarios covering positive, negative, and edge cases",
            "comprehensive": "Generate 6-10 scenarios covering all paths, edge cases, and error conditions",
            "exhaustive": "Generate 10+ scenarios covering all possible combinations and boundary conditions"
        }
        
        instruction = coverage_instructions.get(coverage_level, coverage_instructions["standard"])
        
        prompt = f"""
Generate detailed test scenarios for the following feature:

Feature: {feature['feature_name']}
Description: {feature['description']}
Acceptance Criteria: {feature['acceptance_criteria']}
Business Rules: {feature.get('business_rules', [])}
Edge Cases: {feature.get('edge_cases', [])}

Coverage Level: {coverage_level}
Instructions: {instruction}

For each test scenario, provide:
1. Scenario name
2. Test type (positive/negative/edge_case/boundary)
3. Preconditions
4. Test steps (high-level)
5. Expected results
6. Test data requirements
7. Priority
8. Risk level

Format as JSON array:
[
    {{
        "scenario_name": "Valid User Login",
        "test_type": "positive",
        "feature_name": "{feature['feature_name']}",
        "preconditions": ["User account exists", "User is not logged in"],
        "test_steps": [
            "Navigate to login page",
            "Enter valid email and password",
            "Click login button",
            "Verify successful login"
        ],
        "expected_results": [
            "User is redirected to dashboard",
            "Welcome message is displayed",
            "User session is created"
        ],
        "test_data": {{
            "email": "valid_user@example.com",
            "password": "ValidPassword123"
        }},
        "priority": "high",
        "risk_level": "medium"
    }}
]

Generate comprehensive test scenarios:
"""
        
        response = await llm_provider.invoke(prompt)
        return self._parse_scenarios_response(response, feature['feature_name'])
    
    async def _create_test_case_from_scenario(
        self,
        scenario: Dict[str, Any],
        llm_provider,
        **kwargs
    ) -> TestCase:
        """Create detailed test case from scenario."""
        # Convert scenario to detailed description
        description = f"""
Feature: {scenario['feature_name']}
Scenario: {scenario['scenario_name']}
Type: {scenario['test_type']}

Preconditions:
{chr(10).join(f"- {pc}" for pc in scenario.get('preconditions', []))}

Test Steps:
{chr(10).join(f"{i+1}. {step}" for i, step in enumerate(scenario.get('test_steps', [])))}

Expected Results:
{chr(10).join(f"- {er}" for er in scenario.get('expected_results', []))}

Test Data: {json.dumps(scenario.get('test_data', {}), indent=2)}
"""
        
        # Determine test type and priority
        test_type = self._map_scenario_to_test_type(scenario)
        priority = self._map_scenario_to_priority(scenario)
        
        # Generate detailed test case
        test_case = await self.test_case_generator.generate_from_description(
            description=description,
            llm_provider=llm_provider,
            name=f"{scenario['feature_name']} - {scenario['scenario_name']}",
            test_type=test_type,
            priority=priority,
            tags=[scenario['feature_name'].lower().replace(' ', '_'), scenario['test_type']],
            **kwargs
        )
        
        return test_case
    
    def _parse_features_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response to extract features."""
        try:
            # Try to extract JSON array
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
            # Fallback to text parsing
            return self._parse_features_text(response)
            
        except json.JSONDecodeError:
            return self._parse_features_text(response)
    
    def _parse_scenarios_response(self, response: str, feature_name: str) -> List[Dict[str, Any]]:
        """Parse LLM response to extract scenarios."""
        try:
            # Try to extract JSON array
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                scenarios = json.loads(json_match.group())
                # Ensure feature_name is set
                for scenario in scenarios:
                    scenario['feature_name'] = feature_name
                return scenarios
            
            # Fallback to text parsing
            return self._parse_scenarios_text(response, feature_name)
            
        except json.JSONDecodeError:
            return self._parse_scenarios_text(response, feature_name)
    
    def _parse_features_text(self, response: str) -> List[Dict[str, Any]]:
        """Parse text response to extract features."""
        # Simple text parsing fallback
        features = []
        lines = response.strip().split('\n')
        
        current_feature = None
        for line in lines:
            line = line.strip()
            if line.startswith(('Feature:', 'feature:', 'FEATURE:')):
                if current_feature:
                    features.append(current_feature)
                current_feature = {
                    "feature_name": line.split(':', 1)[1].strip(),
                    "description": "",
                    "acceptance_criteria": [],
                    "priority": "medium",
                    "test_types": ["functional"],
                    "dependencies": [],
                    "user_roles": ["user"],
                    "business_rules": [],
                    "edge_cases": [],
                    "estimated_test_cases": 3
                }
            elif current_feature and line:
                if not current_feature["description"]:
                    current_feature["description"] = line
        
        if current_feature:
            features.append(current_feature)
        
        return features if features else [{
            "feature_name": "Extracted Feature",
            "description": "Feature extracted from requirements",
            "acceptance_criteria": ["Basic functionality works"],
            "priority": "medium",
            "test_types": ["functional"],
            "dependencies": [],
            "user_roles": ["user"],
            "business_rules": [],
            "edge_cases": [],
            "estimated_test_cases": 3
        }]
    
    def _parse_scenarios_text(self, response: str, feature_name: str) -> List[Dict[str, Any]]:
        """Parse text response to extract scenarios."""
        # Simple text parsing fallback
        scenarios = []
        lines = response.strip().split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line and not line.startswith(('#', '//', '/*')):
                scenarios.append({
                    "scenario_name": f"Scenario {i+1}",
                    "test_type": "positive",
                    "feature_name": feature_name,
                    "preconditions": [],
                    "test_steps": [line],
                    "expected_results": ["Test completes successfully"],
                    "test_data": {},
                    "priority": "medium",
                    "risk_level": "low"
                })
        
        return scenarios if scenarios else [{
            "scenario_name": "Basic Test",
            "test_type": "positive",
            "feature_name": feature_name,
            "preconditions": [],
            "test_steps": ["Execute basic test"],
            "expected_results": ["Test passes"],
            "test_data": {},
            "priority": "medium",
            "risk_level": "low"
        }]
    
    def _map_scenario_to_test_type(self, scenario: Dict[str, Any]) -> TestType:
        """Map scenario to TestType enum."""
        scenario_type = scenario.get('test_type', 'positive').lower()
        
        if 'integration' in scenario_type:
            return TestType.INTEGRATION
        elif 'e2e' in scenario_type or 'end-to-end' in scenario_type:
            return TestType.E2E
        elif 'performance' in scenario_type:
            return TestType.PERFORMANCE
        elif 'security' in scenario_type:
            return TestType.SECURITY
        elif 'regression' in scenario_type:
            return TestType.REGRESSION
        else:
            return TestType.FUNCTIONAL
    
    def _map_scenario_to_priority(self, scenario: Dict[str, Any]) -> TestPriority:
        """Map scenario to TestPriority enum."""
        priority = scenario.get('priority', 'medium').lower()
        risk = scenario.get('risk_level', 'medium').lower()
        
        if priority == 'high' or risk == 'high':
            return TestPriority.CRITICAL
        elif priority == 'medium':
            return TestPriority.HIGH
        else:
            return TestPriority.MEDIUM


class TestMaintenanceEngine:
    """LLM-powered engine for maintaining and updating test cases when UI/system changes."""
    
    def __init__(self):
        self.logger = StructuredLogger("test_maintenance_engine")
    
    async def analyze_ui_changes_impact(
        self,
        ui_changes_description: str,
        affected_test_cases: List[TestCase],
        llm_provider
    ) -> Dict[str, Any]:
        """Analyze how UI changes impact existing test cases."""
        try:
            prompt = f"""
Analyze the impact of the following UI changes on existing test cases:

UI Changes:
{ui_changes_description}

Existing Test Cases:
{self._format_test_cases_for_analysis(affected_test_cases)}

For each test case, determine:
1. Impact level (none/low/medium/high/critical)
2. Specific elements affected
3. Required updates
4. Risk of test failure
5. Recommended actions

Format response as JSON:
{{
    "overall_impact": "medium",
    "summary": "Changes affect login and navigation elements",
    "test_case_impacts": [
        {{
            "test_case_id": "tc_001",
            "test_case_name": "User Login Test",
            "impact_level": "high",
            "affected_elements": ["login_button", "email_field"],
            "required_updates": [
                "Update selector for login button",
                "Verify new email field validation"
            ],
            "failure_risk": "high",
            "recommended_actions": [
                "Update element selectors",
                "Add new validation steps",
                "Re-record test data"
            ],
            "estimated_effort": "2 hours"
        }}
    ],
    "global_recommendations": [
        "Update page object models",
        "Review all authentication tests"
    ]
}}

Analyze the impact:
"""
            
            response = await llm_provider.invoke(prompt)
            impact_analysis = self._parse_impact_analysis(response)
            
            self.logger.info(
                "UI changes impact analyzed",
                overall_impact=impact_analysis.get("overall_impact"),
                affected_test_cases=len(affected_test_cases),
                high_impact_cases=len([
                    tc for tc in impact_analysis.get("test_case_impacts", [])
                    if tc.get("impact_level") in ["high", "critical"]
                ])
            )
            
            return impact_analysis
            
        except Exception as e:
            self.logger.error(
                "Failed to analyze UI changes impact",
                error=str(e),
                changes_length=len(ui_changes_description),
                test_cases_count=len(affected_test_cases)
            )
            raise
    
    async def update_test_case_for_changes(
        self,
        test_case: TestCase,
        change_description: str,
        llm_provider,
        update_strategy: str = "smart"
    ) -> TestCase:
        """Update a test case based on system/UI changes."""
        try:
            prompt = f"""
Update the following test case based on the described changes:

Original Test Case:
Name: {test_case.name}
Description: {test_case.description}
Steps: {self._format_test_steps(test_case.steps)}

Changes Description:
{change_description}

Update Strategy: {update_strategy}

Please provide updated test case with:
1. Updated test steps
2. New element selectors (if applicable)
3. Modified validation points
4. Additional preconditions/postconditions
5. Updated test data requirements

Format response as JSON:
{{
    "updated_name": "Updated test name",
    "updated_description": "Updated description",
    "updated_steps": [
        {{
            "step_number": 1,
            "description": "Updated step description",
            "action": "Updated action",
            "expected_result": "Updated expected result",
            "validation_rules": ["new validation rule"],
            "timeout": 30
        }}
    ],
    "new_preconditions": ["new precondition"],
    "new_postconditions": ["new postcondition"],
    "updated_test_data": {{"key": "new_value"}},
    "change_summary": "Summary of changes made",
    "confidence_level": "high"
}}

Update the test case:
"""
            
            response = await llm_provider.invoke(prompt)
            update_data = self._parse_update_response(response)
            
            # Apply updates to test case
            updated_test_case = self._apply_updates_to_test_case(test_case, update_data)
            
            self.logger.info(
                "Test case updated for changes",
                test_case_id=test_case.id,
                original_steps=len(test_case.steps),
                updated_steps=len(updated_test_case.steps),
                confidence_level=update_data.get("confidence_level", "medium")
            )
            
            return updated_test_case
            
        except Exception as e:
            self.logger.error(
                "Failed to update test case for changes",
                error=str(e),
                test_case_id=test_case.id,
                change_description=change_description[:100]
            )
            raise
    
    def _format_test_cases_for_analysis(self, test_cases: List[TestCase]) -> str:
        """Format test cases for LLM analysis."""
        formatted = []
        for tc in test_cases:
            formatted.append(f"""
Test Case ID: {tc.id}
Name: {tc.name}
Description: {tc.description}
Steps: {len(tc.steps)} steps
Target URL: {tc.target_url or 'Not specified'}
Tags: {', '.join(tc.tags)}
""")
        return '\n'.join(formatted)
    
    def _format_test_steps(self, steps: List[TestStep]) -> str:
        """Format test steps for LLM processing."""
        formatted = []
        for step in steps:
            formatted.append(f"{step.step_number}. {step.action} -> {step.expected_result}")
        return '\n'.join(formatted)
    
    def _parse_impact_analysis(self, response: str) -> Dict[str, Any]:
        """Parse LLM response for impact analysis."""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        
        # Fallback
        return {
            "overall_impact": "medium",
            "summary": "Impact analysis completed",
            "test_case_impacts": [],
            "global_recommendations": ["Review and update affected tests"]
        }
    
    def _parse_update_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response for test case updates."""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
        
        # Fallback
        return {
            "updated_name": "Updated Test Case",
            "updated_description": "Test case updated for changes",
            "updated_steps": [],
            "new_preconditions": [],
            "new_postconditions": [],
            "updated_test_data": {},
            "change_summary": "Test case updated",
            "confidence_level": "medium"
        }
    
    def _apply_updates_to_test_case(self, original: TestCase, updates: Dict[str, Any]) -> TestCase:
        """Apply updates to create new test case version."""
        # Create updated test case
        updated_case = TestCase(
            id=original.id,  # Keep same ID but increment version
            name=updates.get("updated_name", original.name),
            description=updates.get("updated_description", original.description),
            test_type=original.test_type,
            priority=original.priority,
            status=TestCaseStatus.DRAFT,  # Mark as draft for review
            steps=self._create_updated_steps(updates.get("updated_steps", [])),
            preconditions=original.preconditions + updates.get("new_preconditions", []),
            postconditions=original.postconditions + updates.get("new_postconditions", []),
            target_url=original.target_url,
            browser_config=original.browser_config,
            test_data={**original.test_data, **updates.get("updated_test_data", {})},
            environment=original.environment,
            tags=original.tags + ["updated_for_changes"],
            labels=original.labels,
            requirements=original.requirements,
            timeout=original.timeout,
            retry_count=original.retry_count,
            parallel_execution=original.parallel_execution,
            created_by=original.created_by,
            created_at=original.created_at,
            updated_by="llm_maintenance_engine",
            updated_at=datetime.now(timezone.utc),
            version=original.version + 1
        )
        
        return updated_case
    
    def _create_updated_steps(self, steps_data: List[Dict[str, Any]]) -> List[TestStep]:
        """Create TestStep objects from update data."""
        steps = []
        for step_data in steps_data:
            step = TestStep(
                step_number=step_data.get("step_number", len(steps) + 1),
                description=step_data.get("description", f"Step {len(steps) + 1}"),
                action=step_data.get("action", ""),
                expected_result=step_data.get("expected_result", ""),
                test_data=step_data.get("test_data", {}),
                validation_rules=step_data.get("validation_rules", []),
                is_optional=step_data.get("is_optional", False),
                timeout=step_data.get("timeout", 30)
            )
            steps.append(step)
        
        return steps
