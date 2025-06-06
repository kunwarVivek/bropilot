"""
Test Case Generators

LLM-powered test case generation from natural language descriptions.
"""

import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from .models import TestCase, TestStep, TestType, TestPriority, TestCaseStatus
from src.infrastructure.logging.logger import StructuredLogger


class TestCaseGenerator:
    """LLM-powered test case generator."""
    
    def __init__(self):
        self.logger = StructuredLogger("test_case_generator")
    
    async def generate_from_description(
        self,
        description: str,
        llm_provider,
        name: Optional[str] = None,
        test_type: TestType = TestType.FUNCTIONAL,
        priority: TestPriority = TestPriority.MEDIUM,
        **kwargs
    ) -> TestCase:
        """Generate a test case from natural language description."""
        try:
            # Create prompt for LLM
            prompt = self._create_test_case_prompt(description, test_type, priority, **kwargs)
            
            # Get LLM response
            response = await llm_provider.invoke(prompt)
            
            # Parse LLM response
            parsed_data = self._parse_llm_response(response)
            
            # Create test case
            test_case = self._create_test_case_from_parsed_data(
                parsed_data, description, name, test_type, priority, **kwargs
            )
            
            self.logger.info(
                "Test case generated from description",
                test_case_id=test_case.id,
                description_length=len(description),
                steps_generated=len(test_case.steps)
            )
            
            return test_case
            
        except Exception as e:
            self.logger.error(
                "Failed to generate test case from description",
                error=str(e),
                description=description[:100]
            )
            raise
    
    def _create_test_case_prompt(
        self,
        description: str,
        test_type: TestType,
        priority: TestPriority,
        **kwargs
    ) -> str:
        """Create prompt for LLM test case generation."""
        target_url = kwargs.get("target_url", "")
        tags = kwargs.get("tags", [])
        environment = kwargs.get("environment", "default")
        
        prompt = f"""
You are an expert test automation engineer. Generate a detailed test case from the following description.

Test Description:
{description}

Test Type: {test_type.value}
Priority: {priority.value}
Target URL: {target_url}
Environment: {environment}
Tags: {', '.join(tags) if tags else 'None'}

Please generate a comprehensive test case with the following structure:

1. Test Case Name (if not provided, create a descriptive name)
2. Detailed Description
3. Preconditions (what needs to be set up before the test)
4. Test Steps (detailed step-by-step actions)
5. Expected Results for each step
6. Postconditions (cleanup or verification after test)
7. Test Data requirements
8. Validation Rules

Format your response as JSON with this structure:
{{
    "name": "Test case name",
    "description": "Detailed test description",
    "preconditions": ["precondition 1", "precondition 2"],
    "steps": [
        {{
            "step_number": 1,
            "description": "Step description",
            "action": "Detailed action to perform",
            "expected_result": "What should happen",
            "test_data": {{"key": "value"}},
            "validation_rules": ["rule1", "rule2"],
            "is_optional": false,
            "timeout": 30
        }}
    ],
    "postconditions": ["postcondition 1"],
    "test_data": {{"global_data": "value"}},
    "validation_criteria": ["criteria 1", "criteria 2"]
}}

Make sure the test steps are:
- Specific and actionable
- Include proper validation points
- Cover both positive and negative scenarios where appropriate
- Include realistic test data
- Have clear expected results

Generate a comprehensive test case now:
"""
        return prompt
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response to extract test case data."""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            
            # If no JSON found, try to parse structured text
            return self._parse_structured_text(response)
            
        except json.JSONDecodeError:
            # Fallback to text parsing
            return self._parse_structured_text(response)
    
    def _parse_structured_text(self, response: str) -> Dict[str, Any]:
        """Parse structured text response when JSON parsing fails."""
        lines = response.strip().split('\n')
        parsed_data = {
            "name": "Generated Test Case",
            "description": "",
            "preconditions": [],
            "steps": [],
            "postconditions": [],
            "test_data": {},
            "validation_criteria": []
        }
        
        current_section = None
        step_counter = 1
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect sections
            if "name:" in line.lower() or "test case name:" in line.lower():
                current_section = "name"
                parsed_data["name"] = line.split(":", 1)[1].strip()
            elif "description:" in line.lower():
                current_section = "description"
                parsed_data["description"] = line.split(":", 1)[1].strip()
            elif "precondition" in line.lower():
                current_section = "preconditions"
            elif "step" in line.lower() and ("action" in line.lower() or "perform" in line.lower()):
                current_section = "steps"
                # Extract step information
                step = {
                    "step_number": step_counter,
                    "description": f"Step {step_counter}",
                    "action": line,
                    "expected_result": "Verify step completion",
                    "test_data": {},
                    "validation_rules": [],
                    "is_optional": False,
                    "timeout": 30
                }
                parsed_data["steps"].append(step)
                step_counter += 1
            elif "postcondition" in line.lower():
                current_section = "postconditions"
            elif current_section == "preconditions" and line.startswith(("-", "•", "*")):
                parsed_data["preconditions"].append(line[1:].strip())
            elif current_section == "postconditions" and line.startswith(("-", "•", "*")):
                parsed_data["postconditions"].append(line[1:].strip())
            elif current_section == "description":
                parsed_data["description"] += " " + line
        
        # If no steps were parsed, create basic steps from description
        if not parsed_data["steps"]:
            basic_steps = self._create_basic_steps_from_description(parsed_data["description"])
            parsed_data["steps"] = basic_steps
        
        return parsed_data
    
    def _create_basic_steps_from_description(self, description: str) -> List[Dict[str, Any]]:
        """Create basic test steps from description when parsing fails."""
        # Simple heuristic to create steps
        sentences = [s.strip() for s in description.split('.') if s.strip()]
        steps = []
        
        for i, sentence in enumerate(sentences[:10], 1):  # Limit to 10 steps
            if len(sentence) > 10:  # Skip very short sentences
                step = {
                    "step_number": i,
                    "description": f"Step {i}",
                    "action": sentence,
                    "expected_result": "Step completes successfully",
                    "test_data": {},
                    "validation_rules": [],
                    "is_optional": False,
                    "timeout": 30
                }
                steps.append(step)
        
        # If no meaningful steps, create a default step
        if not steps:
            steps = [{
                "step_number": 1,
                "description": "Execute test",
                "action": description,
                "expected_result": "Test completes successfully",
                "test_data": {},
                "validation_rules": [],
                "is_optional": False,
                "timeout": 60
            }]
        
        return steps
    
    def _create_test_case_from_parsed_data(
        self,
        parsed_data: Dict[str, Any],
        original_description: str,
        name: Optional[str],
        test_type: TestType,
        priority: TestPriority,
        **kwargs
    ) -> TestCase:
        """Create TestCase object from parsed data."""
        # Use provided name or generated name
        test_case_name = name or parsed_data.get("name", "Generated Test Case")
        
        # Create test steps
        steps = []
        for step_data in parsed_data.get("steps", []):
            step = TestStep(
                step_number=step_data.get("step_number", len(steps) + 1),
                description=step_data.get("description", f"Step {len(steps) + 1}"),
                action=step_data.get("action", ""),
                expected_result=step_data.get("expected_result", ""),
                test_data=step_data.get("test_data", {}),
                validation_rules=step_data.get("validation_rules", []),
                is_optional=step_data.get("is_optional", False),
                timeout=step_data.get("timeout", 30),
                retry_count=step_data.get("retry_count", 0)
            )
            steps.append(step)
        
        # Create test case
        test_case = TestCase(
            name=test_case_name,
            description=parsed_data.get("description", original_description),
            test_type=test_type,
            priority=priority,
            status=TestCaseStatus.DRAFT,
            steps=steps,
            preconditions=parsed_data.get("preconditions", []),
            postconditions=parsed_data.get("postconditions", []),
            target_url=kwargs.get("target_url"),
            browser_config=kwargs.get("browser_config", {}),
            test_data=parsed_data.get("test_data", {}),
            environment=kwargs.get("environment", "default"),
            tags=kwargs.get("tags", []),
            labels=kwargs.get("labels", {}),
            requirements=kwargs.get("requirements", []),
            timeout=kwargs.get("timeout", 300),
            retry_count=kwargs.get("retry_count", 1),
            parallel_execution=kwargs.get("parallel_execution", True),
            created_by=kwargs.get("created_by", "llm_generator"),
            created_at=datetime.now(timezone.utc),
            updated_by=kwargs.get("created_by", "llm_generator"),
            updated_at=datetime.now(timezone.utc),
            version=1
        )
        
        return test_case


class TestStepGenerator:
    """Generator for individual test steps."""
    
    def __init__(self):
        self.logger = StructuredLogger("test_step_generator")
    
    async def generate_steps_for_action(
        self,
        action_description: str,
        llm_provider,
        context: Optional[Dict[str, Any]] = None
    ) -> List[TestStep]:
        """Generate detailed test steps for a high-level action."""
        try:
            prompt = self._create_step_generation_prompt(action_description, context)
            response = await llm_provider.invoke(prompt)
            
            # Parse response to extract steps
            steps_data = self._parse_steps_response(response)
            
            # Create TestStep objects
            steps = []
            for i, step_data in enumerate(steps_data, 1):
                step = TestStep(
                    step_number=i,
                    description=step_data.get("description", f"Step {i}"),
                    action=step_data.get("action", ""),
                    expected_result=step_data.get("expected_result", ""),
                    test_data=step_data.get("test_data", {}),
                    validation_rules=step_data.get("validation_rules", []),
                    is_optional=step_data.get("is_optional", False),
                    timeout=step_data.get("timeout", 30)
                )
                steps.append(step)
            
            return steps
            
        except Exception as e:
            self.logger.error(
                "Failed to generate steps for action",
                error=str(e),
                action=action_description
            )
            # Return a basic step as fallback
            return [TestStep(
                step_number=1,
                description="Execute action",
                action=action_description,
                expected_result="Action completes successfully"
            )]
    
    def _create_step_generation_prompt(
        self,
        action_description: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Create prompt for step generation."""
        context_info = ""
        if context:
            context_info = f"\nContext: {json.dumps(context, indent=2)}"
        
        return f"""
Break down the following high-level action into detailed, executable test steps:

Action: {action_description}{context_info}

Generate 3-7 specific, actionable steps that would accomplish this action.
Each step should be atomic and verifiable.

Format as JSON array:
[
    {{
        "description": "Brief step description",
        "action": "Detailed action to perform",
        "expected_result": "What should happen",
        "validation_rules": ["validation rule 1"],
        "timeout": 30
    }}
]
"""
    
    def _parse_steps_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response to extract step data."""
        try:
            # Try to extract JSON array
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            
            # Fallback to text parsing
            return self._parse_steps_text(response)
            
        except json.JSONDecodeError:
            return self._parse_steps_text(response)
    
    def _parse_steps_text(self, response: str) -> List[Dict[str, Any]]:
        """Parse text response to extract steps."""
        lines = response.strip().split('\n')
        steps = []
        
        for line in lines:
            line = line.strip()
            if line and (line.startswith(('-', '•', '*')) or line[0].isdigit()):
                # Clean up the line
                clean_line = re.sub(r'^[-•*\d\.\)]\s*', '', line)
                if clean_line:
                    steps.append({
                        "description": f"Step {len(steps) + 1}",
                        "action": clean_line,
                        "expected_result": "Step completes successfully",
                        "validation_rules": [],
                        "timeout": 30
                    })
        
        return steps if steps else [{"action": response, "description": "Execute action"}]
