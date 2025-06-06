"""
Advanced orchestrator integrating all intelligent features.

This module provides a comprehensive orchestrator that combines LLM integration,
multi-modal processing, error recovery, and analytics for intelligent automation.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import uuid

from core.interfaces import IWorkflowEngine, ITaskExecutor, ILLMProvider
from core.exceptions import OrchestrationError, ValidationError
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id
from src.llm.conversation_manager import ConversationManager, ConversationConfig, MessageRole
from src.llm.multimodal_processor import MultiModalProcessor, MediaType, ProcessingMode
from src.intelligence.error_recovery import IntelligentErrorRecovery
from src.analytics.reporting_engine import AnalyticsEngine
from src.orchestration.dependency_graph import DependencyGraph, TaskNode, TaskPriority
from src.orchestration.parallel_executor import ParallelExecutor, ExecutionConfig
from src.orchestration.state_manager import StateManager


@dataclass
class IntelligentWorkflowConfig:
    """Configuration for intelligent workflow execution."""
    enable_llm_assistance: bool = True
    enable_multimodal: bool = True
    enable_error_recovery: bool = True
    enable_analytics: bool = True
    auto_optimize: bool = True
    learning_mode: bool = True
    conversation_context: Dict[str, Any] = field(default_factory=dict)
    recovery_strategies: List[str] = field(default_factory=list)
    performance_targets: Dict[str, float] = field(default_factory=dict)


@dataclass
class ExecutionContext:
    """Enhanced execution context with intelligence features."""
    workflow_id: str
    correlation_id: str
    config: IntelligentWorkflowConfig
    conversation_manager: Optional[ConversationManager] = None
    multimodal_processor: Optional[MultiModalProcessor] = None
    error_recovery: Optional[IntelligentErrorRecovery] = None
    analytics_engine: Optional[AnalyticsEngine] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AdvancedOrchestrator:
    """Advanced orchestrator with intelligent capabilities."""
    
    def __init__(
        self,
        workflow_engine: IWorkflowEngine,
        task_executor: ITaskExecutor,
        llm_provider: Optional[ILLMProvider] = None
    ):
        """Initialize advanced orchestrator."""
        self.workflow_engine = workflow_engine
        self.task_executor = task_executor
        self.llm_provider = llm_provider
        self.logger = StructuredLogger("advanced_orchestrator")
        
        # Intelligence components
        self.multimodal_processor = MultiModalProcessor(llm_provider) if llm_provider else None
        self.error_recovery = IntelligentErrorRecovery(llm_provider)
        self.analytics_engine = AnalyticsEngine()
        self.state_manager = StateManager()
        
        # Active executions
        self.active_executions: Dict[str, ExecutionContext] = {}
        
        # Learning and optimization
        self.execution_patterns: Dict[str, Dict[str, Any]] = {}
        self.optimization_suggestions: List[Dict[str, Any]] = []
        
        # Performance tracking
        self.performance_history: List[Dict[str, Any]] = []
    
    async def start(self) -> None:
        """Start the advanced orchestrator."""
        
        # Start analytics engine
        await self.analytics_engine.start()
        
        self.logger.info("Advanced orchestrator started")
    
    async def stop(self) -> None:
        """Stop the advanced orchestrator."""
        
        # Stop analytics engine
        await self.analytics_engine.stop()
        
        # Complete active executions
        for execution_context in self.active_executions.values():
            if execution_context.conversation_manager:
                execution_context.conversation_manager.complete_conversation()
        
        self.logger.info("Advanced orchestrator stopped")
    
    async def execute_intelligent_workflow(
        self,
        workflow_definition: Dict[str, Any],
        config: IntelligentWorkflowConfig,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a workflow with intelligent capabilities."""
        
        workflow_id = str(uuid.uuid4())
        correlation_id = str(uuid.uuid4())
        
        self.logger.info(
            "Starting intelligent workflow execution",
            workflow_id=workflow_id,
            correlation_id=correlation_id,
            config=config.__dict__
        )
        
        start_time = datetime.utcnow()
        
        try:
            # Create execution context
            execution_context = await self._create_execution_context(
                workflow_id, correlation_id, config, context or {}
            )
            
            self.active_executions[workflow_id] = execution_context
            
            # Pre-execution analysis
            if config.enable_llm_assistance:
                await self._analyze_workflow_with_llm(workflow_definition, execution_context)
            
            # Optimize workflow if enabled
            if config.auto_optimize:
                workflow_definition = await self._optimize_workflow(workflow_definition, execution_context)
            
            # Execute workflow with intelligence
            result = await self._execute_with_intelligence(workflow_definition, execution_context)
            
            # Post-execution analysis
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            await self._post_execution_analysis(result, execution_context, execution_time)
            
            # Record analytics
            if config.enable_analytics:
                self._record_execution_metrics(workflow_id, execution_time, result, execution_context)
            
            # Learn from execution
            if config.learning_mode:
                await self._learn_from_execution(workflow_definition, result, execution_context)
            
            self.logger.info(
                "Intelligent workflow execution completed",
                workflow_id=workflow_id,
                execution_time=execution_time,
                success=result.get("success", False)
            )
            
            return {
                "workflow_id": workflow_id,
                "correlation_id": correlation_id,
                "result": result,
                "execution_time": execution_time,
                "intelligence_insights": await self._generate_execution_insights(execution_context),
                "performance_metrics": await self._get_performance_metrics(workflow_id)
            }
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Handle error with intelligence
            if config.enable_error_recovery:
                recovery_result = await self.error_recovery.handle_error(
                    e, {"workflow_id": workflow_id, "context": context}, correlation_id
                )
                
                # Record error analytics
                if config.enable_analytics:
                    self.analytics_engine.record_error(
                        type(e).__name__,
                        recovery_result.get("pattern_id", "unknown"),
                        "high",
                        recovery_result.get("resolved", False)
                    )
                
                if recovery_result.get("resolved"):
                    # Retry execution after recovery
                    return await self.execute_intelligent_workflow(workflow_definition, config, context)
            
            self.logger.error(
                "Intelligent workflow execution failed",
                workflow_id=workflow_id,
                error=str(e),
                execution_time=execution_time
            )
            
            raise OrchestrationError(f"Intelligent workflow execution failed: {e}") from e
        
        finally:
            # Cleanup
            if workflow_id in self.active_executions:
                del self.active_executions[workflow_id]
    
    async def _create_execution_context(
        self,
        workflow_id: str,
        correlation_id: str,
        config: IntelligentWorkflowConfig,
        context: Dict[str, Any]
    ) -> ExecutionContext:
        """Create execution context with intelligence components."""
        
        execution_context = ExecutionContext(
            workflow_id=workflow_id,
            correlation_id=correlation_id,
            config=config,
            metadata=context
        )
        
        # Initialize conversation manager
        if config.enable_llm_assistance and self.llm_provider:
            conversation_config = ConversationConfig(
                system_prompt=f"""
                You are an intelligent automation assistant helping with workflow execution.
                Workflow ID: {workflow_id}
                Context: {json.dumps(config.conversation_context, indent=2)}
                
                Your role is to:
                1. Analyze workflow steps and suggest optimizations
                2. Help with error diagnosis and recovery
                3. Provide insights on execution patterns
                4. Assist with multi-modal content processing
                """
            )
            
            execution_context.conversation_manager = ConversationManager(
                self.llm_provider, conversation_config, f"workflow_{workflow_id}"
            )
        
        # Initialize multimodal processor
        if config.enable_multimodal:
            execution_context.multimodal_processor = self.multimodal_processor
        
        # Initialize error recovery
        if config.enable_error_recovery:
            execution_context.error_recovery = self.error_recovery
        
        # Initialize analytics
        if config.enable_analytics:
            execution_context.analytics_engine = self.analytics_engine
        
        return execution_context
    
    async def _analyze_workflow_with_llm(
        self,
        workflow_definition: Dict[str, Any],
        execution_context: ExecutionContext
    ) -> None:
        """Analyze workflow with LLM assistance."""
        
        if not execution_context.conversation_manager:
            return
        
        analysis_prompt = f"""
        Please analyze this workflow definition and provide insights:
        
        {json.dumps(workflow_definition, indent=2)}
        
        Consider:
        1. Potential optimization opportunities
        2. Risk factors and error-prone areas
        3. Resource requirements
        4. Execution time estimates
        5. Dependencies and bottlenecks
        
        Provide actionable recommendations.
        """
        
        try:
            response = await execution_context.conversation_manager.send_message(analysis_prompt)
            
            # Store analysis in context
            execution_context.metadata["llm_analysis"] = {
                "analysis": response.content,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.logger.info(
                "Workflow analysis completed",
                workflow_id=execution_context.workflow_id,
                analysis_length=len(response.content)
            )
            
        except Exception as e:
            self.logger.error(
                "Workflow analysis failed",
                workflow_id=execution_context.workflow_id,
                error=str(e)
            )
    
    async def _optimize_workflow(
        self,
        workflow_definition: Dict[str, Any],
        execution_context: ExecutionContext
    ) -> Dict[str, Any]:
        """Optimize workflow based on learned patterns."""
        
        # Check for known optimization patterns
        workflow_type = workflow_definition.get("type", "unknown")
        
        if workflow_type in self.execution_patterns:
            patterns = self.execution_patterns[workflow_type]
            
            # Apply optimizations based on patterns
            optimized_definition = workflow_definition.copy()
            
            # Example optimizations
            if patterns.get("parallel_execution_beneficial", False):
                optimized_definition["execution_mode"] = "parallel"
            
            if patterns.get("average_execution_time", 0) > 60:
                optimized_definition["timeout"] = patterns["average_execution_time"] * 1.5
            
            self.logger.info(
                "Workflow optimized based on patterns",
                workflow_id=execution_context.workflow_id,
                optimizations_applied=len(optimized_definition) - len(workflow_definition)
            )
            
            return optimized_definition
        
        return workflow_definition
    
    async def _execute_with_intelligence(
        self,
        workflow_definition: Dict[str, Any],
        execution_context: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute workflow with intelligent monitoring and assistance."""
        
        # Create dependency graph
        dependency_graph = DependencyGraph(execution_context.workflow_id)
        
        # Add tasks to graph
        for task_def in workflow_definition.get("tasks", []):
            task_node = TaskNode(
                task_id=task_def["id"],
                task_name=task_def["name"],
                task_definition=task_def,
                priority=TaskPriority(task_def.get("priority", "normal"))
            )
            dependency_graph.add_task(task_node)
        
        # Add dependencies
        for dep in workflow_definition.get("dependencies", []):
            from src.orchestration.dependency_graph import Dependency, DependencyType
            dependency = Dependency(
                from_task=dep["from"],
                to_task=dep["to"],
                dependency_type=DependencyType(dep.get("type", "hard"))
            )
            dependency_graph.add_dependency(dependency)
        
        # Execute with parallel executor
        execution_config = ExecutionConfig(
            max_parallel_tasks=workflow_definition.get("max_parallel", 5),
            execution_mode=workflow_definition.get("execution_mode", "hybrid")
        )
        
        parallel_executor = ParallelExecutor(execution_config)
        
        # Execute with intelligent monitoring
        try:
            results = await parallel_executor.execute_graph(dependency_graph, self.task_executor)
            
            # Process results with intelligence
            processed_results = await self._process_results_with_intelligence(results, execution_context)
            
            return {
                "success": True,
                "results": processed_results,
                "statistics": parallel_executor.get_execution_statistics(),
                "graph_statistics": dependency_graph.get_graph_statistics()
            }
            
        except Exception as e:
            # Handle with error recovery
            if execution_context.config.enable_error_recovery:
                recovery_result = await execution_context.error_recovery.handle_error(
                    e, {"workflow_definition": workflow_definition}, execution_context.correlation_id
                )
                
                if recovery_result.get("resolved"):
                    # Retry execution
                    return await self._execute_with_intelligence(workflow_definition, execution_context)
            
            raise
    
    async def _process_results_with_intelligence(
        self,
        results: Dict[str, Any],
        execution_context: ExecutionContext
    ) -> Dict[str, Any]:
        """Process execution results with intelligent analysis."""
        
        processed_results = {}
        
        for task_id, result in results.items():
            processed_result = result.__dict__.copy()
            
            # Analyze result with multimodal processor if applicable
            if (execution_context.config.enable_multimodal and 
                execution_context.multimodal_processor and
                result.success and result.result):
                
                # Check if result contains media content
                if isinstance(result.result, dict) and "screenshot" in result.result:
                    try:
                        # Process screenshot
                        screenshot_data = result.result["screenshot"]
                        if isinstance(screenshot_data, bytes):
                            analysis = await execution_context.multimodal_processor.process_content(
                                screenshot_data,
                                MediaType.IMAGE,
                                ProcessingMode.ANALYZE,
                                mime_type="image/png"
                            )
                            processed_result["screenshot_analysis"] = analysis.result_data
                    
                    except Exception as e:
                        self.logger.error(
                            "Screenshot analysis failed",
                            task_id=task_id,
                            error=str(e)
                        )
            
            processed_results[task_id] = processed_result
        
        return processed_results
    
    async def _post_execution_analysis(
        self,
        result: Dict[str, Any],
        execution_context: ExecutionContext,
        execution_time: float
    ) -> None:
        """Perform post-execution analysis."""
        
        if not execution_context.conversation_manager:
            return
        
        analysis_prompt = f"""
        Workflow execution completed. Please analyze the results:
        
        Execution Time: {execution_time:.2f} seconds
        Success: {result.get('success', False)}
        Results Summary: {json.dumps(result.get('statistics', {}), indent=2)}
        
        Provide insights on:
        1. Performance analysis
        2. Areas for improvement
        3. Success factors
        4. Recommendations for future executions
        """
        
        try:
            response = await execution_context.conversation_manager.send_message(analysis_prompt)
            
            execution_context.metadata["post_execution_analysis"] = {
                "analysis": response.content,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(
                "Post-execution analysis failed",
                workflow_id=execution_context.workflow_id,
                error=str(e)
            )
    
    def _record_execution_metrics(
        self,
        workflow_id: str,
        execution_time: float,
        result: Dict[str, Any],
        execution_context: ExecutionContext
    ) -> None:
        """Record execution metrics for analytics."""
        
        success = result.get("success", False)
        task_count = len(result.get("results", {}))
        
        # Record workflow execution
        self.analytics_engine.record_workflow_execution(
            workflow_id, execution_time, success, task_count
        )
        
        # Record performance metrics
        statistics = result.get("statistics", {})
        if statistics:
            for metric_name, value in statistics.items():
                if isinstance(value, (int, float)):
                    self.analytics_engine.metrics_collector.record_metric(
                        f"workflow_{metric_name}",
                        value,
                        self.analytics_engine.metrics_collector.MetricType.GAUGE,
                        tags={"workflow_id": workflow_id}
                    )
    
    async def _learn_from_execution(
        self,
        workflow_definition: Dict[str, Any],
        result: Dict[str, Any],
        execution_context: ExecutionContext
    ) -> None:
        """Learn from execution for future optimizations."""
        
        workflow_type = workflow_definition.get("type", "unknown")
        
        if workflow_type not in self.execution_patterns:
            self.execution_patterns[workflow_type] = {
                "execution_count": 0,
                "total_execution_time": 0.0,
                "success_count": 0,
                "parallel_execution_beneficial": False
            }
        
        patterns = self.execution_patterns[workflow_type]
        patterns["execution_count"] += 1
        
        execution_time = result.get("execution_time", 0)
        patterns["total_execution_time"] += execution_time
        
        if result.get("success", False):
            patterns["success_count"] += 1
        
        # Calculate averages
        patterns["average_execution_time"] = patterns["total_execution_time"] / patterns["execution_count"]
        patterns["success_rate"] = patterns["success_count"] / patterns["execution_count"]
        
        # Learn about parallel execution benefits
        statistics = result.get("statistics", {})
        if statistics.get("execution_mode") == "parallel":
            parallel_time = statistics.get("total_execution_time", execution_time)
            if parallel_time < patterns["average_execution_time"] * 0.8:
                patterns["parallel_execution_beneficial"] = True
    
    async def _generate_execution_insights(
        self,
        execution_context: ExecutionContext
    ) -> Dict[str, Any]:
        """Generate insights from execution."""
        
        insights = {
            "llm_analysis": execution_context.metadata.get("llm_analysis"),
            "post_execution_analysis": execution_context.metadata.get("post_execution_analysis"),
            "conversation_statistics": None,
            "multimodal_statistics": None,
            "error_recovery_statistics": None
        }
        
        # Get conversation statistics
        if execution_context.conversation_manager:
            insights["conversation_statistics"] = execution_context.conversation_manager.get_statistics()
        
        # Get multimodal statistics
        if execution_context.multimodal_processor:
            insights["multimodal_statistics"] = execution_context.multimodal_processor.get_statistics()
        
        # Get error recovery statistics
        if execution_context.error_recovery:
            insights["error_recovery_statistics"] = execution_context.error_recovery.get_error_statistics()
        
        return insights
    
    async def _get_performance_metrics(self, workflow_id: str) -> Dict[str, Any]:
        """Get performance metrics for the workflow."""
        
        # Get recent metrics for this workflow
        now = datetime.utcnow()
        last_hour = now - timedelta(hours=1)
        
        metrics = self.analytics_engine.metrics_collector.get_metrics(
            tags={"workflow_id": workflow_id},
            time_range=(last_hour, now)
        )
        
        if not metrics:
            return {}
        
        # Calculate performance metrics
        execution_times = [m.value for m in metrics if m.name == "workflow_execution_time"]
        
        if execution_times:
            return {
                "average_execution_time": sum(execution_times) / len(execution_times),
                "min_execution_time": min(execution_times),
                "max_execution_time": max(execution_times),
                "total_executions": len(execution_times)
            }
        
        return {}
    
    async def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """Get optimization suggestions based on learned patterns."""
        
        suggestions = []
        
        for workflow_type, patterns in self.execution_patterns.items():
            if patterns["execution_count"] >= 5:  # Enough data for suggestions
                
                # Suggest parallel execution if beneficial
                if patterns["parallel_execution_beneficial"] and patterns["success_rate"] > 0.8:
                    suggestions.append({
                        "type": "parallel_execution",
                        "workflow_type": workflow_type,
                        "description": f"Enable parallel execution for {workflow_type} workflows",
                        "expected_improvement": "20-50% faster execution",
                        "confidence": 0.8
                    })
                
                # Suggest timeout optimization
                if patterns["average_execution_time"] > 60:
                    suggestions.append({
                        "type": "timeout_optimization",
                        "workflow_type": workflow_type,
                        "description": f"Increase timeout for {workflow_type} workflows",
                        "expected_improvement": "Reduced timeout failures",
                        "confidence": 0.9
                    })
        
        return suggestions
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        
        return {
            "active_executions": len(self.active_executions),
            "learned_patterns": len(self.execution_patterns),
            "optimization_suggestions": len(self.optimization_suggestions),
            "performance_history_size": len(self.performance_history),
            "analytics_statistics": self.analytics_engine.get_statistics(),
            "error_recovery_statistics": self.error_recovery.get_error_statistics()
        }
