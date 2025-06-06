"""
LLM Validator

Validates LLM understanding, responses, and task interpretation using AI.
"""

import json
import re
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone

from .base_validator import BaseValidator
from ..core.validation_config import ValidationConfig
from ..core.validation_result import ValidationSeverity
from ..core.evidence_collector import EvidenceCollector


class LLMValidator(BaseValidator):
    """Validates LLM understanding and responses using AI-powered analysis."""
    
    def __init__(self, config: ValidationConfig):
        super().__init__(config)
        self.llm_provider = None  # Will be injected during validation
        self.validation_prompts = {
            "task_understanding": """
            Analyze if the LLM correctly understood the given task.
            
            Original Task: {original_task}
            LLM Interpretation: {llm_interpretation}
            
            Evaluate:
            1. Did the LLM understand the main objective?
            2. Are all key requirements captured?
            3. Are there any misinterpretations?
            4. Is the interpretation complete?
            
            Respond with JSON:
            {{
                "understanding_score": 0.0-1.0,
                "main_objective_understood": true/false,
                "requirements_captured": ["req1", "req2"],
                "missing_requirements": ["missing1"],
                "misinterpretations": ["issue1"],
                "completeness_score": 0.0-1.0,
                "overall_assessment": "explanation"
            }}
            """,
            
            "response_quality": """
            Evaluate the quality of the LLM's response for the given task.
            
            Task: {task}
            LLM Response: {response}
            Expected Outcome: {expected_outcome}
            
            Evaluate:
            1. Relevance to the task
            2. Accuracy of information
            3. Completeness of response
            4. Clarity and coherence
            5. Adherence to instructions
            
            Respond with JSON:
            {{
                "relevance_score": 0.0-1.0,
                "accuracy_score": 0.0-1.0,
                "completeness_score": 0.0-1.0,
                "clarity_score": 0.0-1.0,
                "instruction_adherence": 0.0-1.0,
                "overall_quality": 0.0-1.0,
                "strengths": ["strength1", "strength2"],
                "weaknesses": ["weakness1"],
                "suggestions": ["suggestion1"]
            }}
            """,
            
            "execution_validation": """
            Validate if the LLM's execution plan matches the task requirements.
            
            Task: {task}
            Execution Plan: {execution_plan}
            Actual Results: {actual_results}
            
            Evaluate:
            1. Does the plan address all task requirements?
            2. Are the execution steps logical and complete?
            3. Do the results match the expected outcomes?
            4. Are there any gaps or errors in execution?
            
            Respond with JSON:
            {{
                "plan_completeness": 0.0-1.0,
                "step_logic_score": 0.0-1.0,
                "result_alignment": 0.0-1.0,
                "execution_gaps": ["gap1"],
                "execution_errors": ["error1"],
                "improvement_suggestions": ["suggestion1"],
                "overall_execution_score": 0.0-1.0
            }}
            """
        }
    
    async def validate(self, context: Dict[str, Any], 
                      evidence_collector: Optional[EvidenceCollector] = None) -> None:
        """Validate LLM performance and understanding."""
        if not self.config.enable_llm_validation:
            self.add_info("LLM validation disabled", "config_check")
            return
        
        # Get LLM provider from context
        self.llm_provider = context.get("llm_provider")
        if not self.llm_provider:
            self.add_warning(
                "No LLM provider available for validation",
                "no_llm_provider",
                {},
                "Provide LLM provider in context for AI-powered validation"
            )
            return
        
        # Validate task understanding
        await self._validate_task_understanding(context, evidence_collector)
        
        # Validate response quality
        await self._validate_response_quality(context, evidence_collector)
        
        # Validate execution alignment
        await self._validate_execution_alignment(context, evidence_collector)
        
        # Self-validation if enabled
        if self.config.llm_self_validation:
            await self._perform_self_validation(context, evidence_collector)
        
        # Cross-validation if enabled
        if self.config.llm_cross_validation:
            await self._perform_cross_validation(context, evidence_collector)
    
    async def _validate_task_understanding(self, context: Dict[str, Any], 
                                         evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate LLM's understanding of the task."""
        task_definition = context.get("task_definition", {})
        original_task = task_definition.get("description", "")
        llm_interpretation = context.get("llm_interpretation", "")
        
        if not original_task or not llm_interpretation:
            self.add_info(
                "Insufficient data for task understanding validation",
                "insufficient_data",
                {"has_task": bool(original_task), "has_interpretation": bool(llm_interpretation)}
            )
            return
        
        try:
            # Use LLM to validate understanding
            prompt = self.validation_prompts["task_understanding"].format(
                original_task=original_task,
                llm_interpretation=llm_interpretation
            )
            
            validation_response = await self._query_llm(prompt)
            understanding_analysis = self._parse_llm_response(validation_response)
            
            if understanding_analysis:
                await self._process_understanding_analysis(understanding_analysis, evidence_collector)
            
        except Exception as e:
            self.add_error(
                f"Failed to validate task understanding: {str(e)}",
                "understanding_validation_failed",
                {"error": str(e)},
                "Check LLM provider connectivity and prompt format"
            )
    
    async def _validate_response_quality(self, context: Dict[str, Any], 
                                       evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate quality of LLM responses."""
        task_definition = context.get("task_definition", {})
        task = task_definition.get("description", "")
        
        task_result = context.get("task_result", {})
        llm_response = task_result.get("llm_response", "")
        expected_outcome = task_definition.get("expected_outcome", "")
        
        if not task or not llm_response:
            self.add_info(
                "Insufficient data for response quality validation",
                "insufficient_response_data",
                {"has_task": bool(task), "has_response": bool(llm_response)}
            )
            return
        
        try:
            prompt = self.validation_prompts["response_quality"].format(
                task=task,
                response=llm_response,
                expected_outcome=expected_outcome or "Not specified"
            )
            
            validation_response = await self._query_llm(prompt)
            quality_analysis = self._parse_llm_response(validation_response)
            
            if quality_analysis:
                await self._process_quality_analysis(quality_analysis, evidence_collector)
            
        except Exception as e:
            self.add_error(
                f"Failed to validate response quality: {str(e)}",
                "quality_validation_failed",
                {"error": str(e)},
                "Check LLM provider and validation prompt"
            )
    
    async def _validate_execution_alignment(self, context: Dict[str, Any], 
                                          evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate alignment between execution plan and results."""
        task_definition = context.get("task_definition", {})
        task = task_definition.get("description", "")
        
        execution_plan = context.get("execution_plan", "")
        task_result = context.get("task_result", {})
        
        if not task or not execution_plan:
            self.add_info(
                "Insufficient data for execution alignment validation",
                "insufficient_execution_data",
                {"has_task": bool(task), "has_plan": bool(execution_plan)}
            )
            return
        
        try:
            prompt = self.validation_prompts["execution_validation"].format(
                task=task,
                execution_plan=execution_plan,
                actual_results=json.dumps(task_result, default=str)[:1000]  # Limit size
            )
            
            validation_response = await self._query_llm(prompt)
            execution_analysis = self._parse_llm_response(validation_response)
            
            if execution_analysis:
                await self._process_execution_analysis(execution_analysis, evidence_collector)
            
        except Exception as e:
            self.add_error(
                f"Failed to validate execution alignment: {str(e)}",
                "execution_validation_failed",
                {"error": str(e)},
                "Check execution data and validation logic"
            )
    
    async def _perform_self_validation(self, context: Dict[str, Any], 
                                     evidence_collector: Optional[EvidenceCollector]) -> None:
        """Perform LLM self-validation."""
        task_result = context.get("task_result", {})
        llm_response = task_result.get("llm_response", "")
        
        if not llm_response:
            return
        
        try:
            self_validation_prompt = f"""
            Review your own response and identify any potential issues:
            
            Your Response: {llm_response}
            
            Evaluate:
            1. Are there any factual errors?
            2. Is the response complete?
            3. Are there any inconsistencies?
            4. Could the response be improved?
            
            Respond with JSON:
            {{
                "self_assessment_score": 0.0-1.0,
                "identified_errors": ["error1"],
                "completeness_issues": ["issue1"],
                "inconsistencies": ["inconsistency1"],
                "improvement_suggestions": ["suggestion1"],
                "confidence_level": 0.0-1.0
            }}
            """
            
            self_validation_response = await self._query_llm(self_validation_prompt)
            self_analysis = self._parse_llm_response(self_validation_response)
            
            if self_analysis:
                await self._process_self_analysis(self_analysis, evidence_collector)
            
        except Exception as e:
            self.add_warning(
                f"Self-validation failed: {str(e)}",
                "self_validation_failed",
                {"error": str(e)}
            )
    
    async def _perform_cross_validation(self, context: Dict[str, Any], 
                                      evidence_collector: Optional[EvidenceCollector]) -> None:
        """Perform cross-validation with secondary LLM."""
        # This would require a secondary LLM provider
        # For now, we'll log that cross-validation is requested
        self.add_info(
            "Cross-validation requested but not implemented",
            "cross_validation_pending",
            {},
            "Implement secondary LLM provider for cross-validation"
        )
    
    async def _query_llm(self, prompt: str) -> str:
        """Query the LLM provider with validation prompt."""
        try:
            if hasattr(self.llm_provider, 'invoke'):
                response = await self.llm_provider.invoke(
                    prompt,
                    temperature=0.1,  # Low temperature for consistent validation
                    max_tokens=1000
                )
                return response
            else:
                self.add_warning(
                    "LLM provider does not support invoke method",
                    "llm_provider_incompatible",
                    {"provider_type": type(self.llm_provider).__name__}
                )
                return ""
        except Exception as e:
            self.add_error(
                f"LLM query failed: {str(e)}",
                "llm_query_failed",
                {"error": str(e), "prompt_length": len(prompt)}
            )
            return ""
    
    def _parse_llm_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse LLM response as JSON."""
        if not response:
            return None
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                # If no JSON found, try parsing the entire response
                return json.loads(response)
        except json.JSONDecodeError as e:
            self.add_warning(
                f"Failed to parse LLM validation response as JSON: {str(e)}",
                "json_parse_failed",
                {"response_preview": response[:200], "error": str(e)},
                "Ensure LLM returns valid JSON format"
            )
            return None
    
    async def _process_understanding_analysis(self, analysis: Dict[str, Any], 
                                            evidence_collector: Optional[EvidenceCollector]) -> None:
        """Process task understanding analysis results."""
        understanding_score = analysis.get("understanding_score", 0.0)
        
        if understanding_score < 0.7:
            self.add_error(
                f"Poor task understanding: {understanding_score:.2%}",
                "poor_task_understanding",
                {
                    "score": understanding_score,
                    "missing_requirements": analysis.get("missing_requirements", []),
                    "misinterpretations": analysis.get("misinterpretations", [])
                },
                "Review task description clarity and LLM prompt engineering"
            )
        elif understanding_score < 0.9:
            self.add_warning(
                f"Moderate task understanding: {understanding_score:.2%}",
                "moderate_task_understanding",
                {"score": understanding_score, "assessment": analysis.get("overall_assessment", "")},
                "Consider improving task description or LLM guidance"
            )
        else:
            self.add_info(
                f"Good task understanding: {understanding_score:.2%}",
                "good_task_understanding",
                {"score": understanding_score}
            )
        
        # Collect understanding evidence
        if evidence_collector:
            await self.collect_evidence(
                evidence_collector,
                "task_understanding_analysis",
                analysis,
                "task_understanding_analysis.json"
            )
    
    async def _process_quality_analysis(self, analysis: Dict[str, Any], 
                                      evidence_collector: Optional[EvidenceCollector]) -> None:
        """Process response quality analysis results."""
        overall_quality = analysis.get("overall_quality", 0.0)
        
        if overall_quality < 0.6:
            self.add_error(
                f"Poor response quality: {overall_quality:.2%}",
                "poor_response_quality",
                {
                    "score": overall_quality,
                    "weaknesses": analysis.get("weaknesses", []),
                    "suggestions": analysis.get("suggestions", [])
                },
                "Improve LLM prompting or consider different model"
            )
        elif overall_quality < 0.8:
            self.add_warning(
                f"Moderate response quality: {overall_quality:.2%}",
                "moderate_response_quality",
                {
                    "score": overall_quality,
                    "strengths": analysis.get("strengths", []),
                    "weaknesses": analysis.get("weaknesses", [])
                },
                "Fine-tune prompts to improve response quality"
            )
        else:
            self.add_info(
                f"Good response quality: {overall_quality:.2%}",
                "good_response_quality",
                {"score": overall_quality, "strengths": analysis.get("strengths", [])}
            )
        
        # Check individual quality dimensions
        dimensions = ["relevance_score", "accuracy_score", "completeness_score", "clarity_score"]
        for dimension in dimensions:
            score = analysis.get(dimension, 0.0)
            if score < 0.7:
                self.add_warning(
                    f"Low {dimension.replace('_score', '')}: {score:.2%}",
                    f"low_{dimension}",
                    {"score": score, "dimension": dimension},
                    f"Focus on improving {dimension.replace('_score', '')} in responses"
                )
        
        # Collect quality evidence
        if evidence_collector:
            await self.collect_evidence(
                evidence_collector,
                "response_quality_analysis",
                analysis,
                "response_quality_analysis.json"
            )
    
    async def _process_execution_analysis(self, analysis: Dict[str, Any], 
                                        evidence_collector: Optional[EvidenceCollector]) -> None:
        """Process execution alignment analysis results."""
        execution_score = analysis.get("overall_execution_score", 0.0)
        
        if execution_score < 0.7:
            self.add_error(
                f"Poor execution alignment: {execution_score:.2%}",
                "poor_execution_alignment",
                {
                    "score": execution_score,
                    "gaps": analysis.get("execution_gaps", []),
                    "errors": analysis.get("execution_errors", [])
                },
                "Review execution logic and task-to-action mapping"
            )
        elif execution_score < 0.9:
            self.add_warning(
                f"Moderate execution alignment: {execution_score:.2%}",
                "moderate_execution_alignment",
                {"score": execution_score, "suggestions": analysis.get("improvement_suggestions", [])},
                "Fine-tune execution planning and validation"
            )
        else:
            self.add_info(
                f"Good execution alignment: {execution_score:.2%}",
                "good_execution_alignment",
                {"score": execution_score}
            )
        
        # Collect execution evidence
        if evidence_collector:
            await self.collect_evidence(
                evidence_collector,
                "execution_alignment_analysis",
                analysis,
                "execution_alignment_analysis.json"
            )
    
    async def _process_self_analysis(self, analysis: Dict[str, Any], 
                                   evidence_collector: Optional[EvidenceCollector]) -> None:
        """Process self-validation analysis results."""
        self_assessment_score = analysis.get("self_assessment_score", 0.0)
        confidence_level = analysis.get("confidence_level", 0.0)
        
        if self_assessment_score < 0.7 or confidence_level < 0.7:
            self.add_warning(
                f"LLM self-assessment indicates issues (score: {self_assessment_score:.2%}, confidence: {confidence_level:.2%})",
                "self_assessment_concerns",
                {
                    "self_score": self_assessment_score,
                    "confidence": confidence_level,
                    "identified_errors": analysis.get("identified_errors", []),
                    "completeness_issues": analysis.get("completeness_issues", [])
                },
                "Review LLM response based on self-identified issues"
            )
        else:
            self.add_info(
                f"LLM self-assessment positive (score: {self_assessment_score:.2%}, confidence: {confidence_level:.2%})",
                "self_assessment_positive",
                {"self_score": self_assessment_score, "confidence": confidence_level}
            )
        
        # Collect self-analysis evidence
        if evidence_collector:
            await self.collect_evidence(
                evidence_collector,
                "self_validation_analysis",
                analysis,
                "self_validation_analysis.json"
            )
    
    def get_validation_rules(self) -> List[str]:
        """Get list of validation rules this validator implements."""
        return [
            "no_llm_provider",
            "insufficient_data",
            "insufficient_response_data",
            "insufficient_execution_data",
            "understanding_validation_failed",
            "quality_validation_failed",
            "execution_validation_failed",
            "self_validation_failed",
            "cross_validation_pending",
            "llm_provider_incompatible",
            "llm_query_failed",
            "json_parse_failed",
            "poor_task_understanding",
            "moderate_task_understanding",
            "good_task_understanding",
            "poor_response_quality",
            "moderate_response_quality",
            "good_response_quality",
            "low_relevance_score",
            "low_accuracy_score",
            "low_completeness_score",
            "low_clarity_score",
            "poor_execution_alignment",
            "moderate_execution_alignment",
            "good_execution_alignment",
            "self_assessment_concerns",
            "self_assessment_positive"
        ]
