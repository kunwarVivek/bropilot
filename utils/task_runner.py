"""
Unified task runner for browser automation.

This module provides a simplified interface for task execution using
the consolidated execution layer with comprehensive validation framework.
"""

import time
from typing import Optional, Dict, Any
from src.execution.task_executor import TaskExecutor
from core.interfaces import TaskDefinition, TaskStatus
from core.exceptions import TaskExecutionError
from src.validation import ValidationEngine, ValidationConfig, ValidationPhase


async def run_task(task: str, llm, save_path: str = "logs/run",
                  validation_config: Optional[ValidationConfig] = None):
    """
    Execute a task using the unified execution layer with validation.

    This function provides a simplified interface that uses the new
    execution layer with comprehensive validation framework.

    Args:
        task: Task description/prompt to execute
        llm: LLM provider instance
        save_path: Path to save execution logs
        validation_config: Optional validation configuration

    Returns:
        Task execution result as string

    Raises:
        TaskExecutionError: If task execution fails
    """
    try:
        # Initialize validation if configured
        validation_engine = None
        validation_result = None

        if validation_config:
            validation_engine = ValidationEngine(validation_config)

        # Create task executor
        task_executor = TaskExecutor()

        # Create task definition
        task_definition = TaskDefinition(
            name="task_execution",
            description="Task execution via unified interface",
            prompt_template=task,
            timeout=300,
            retry_count=3,
            metadata={"save_path": save_path}
        )

        # Create execution context
        context = {
            "target_url": "https://dev.gotrust.tech",
            "headless": False,
            "use_vision": True,
            "save_logs": True,
            "logs_base_path": save_path,
            "llm_provider": llm,
            "task_definition": {
                "description": task,
                "save_path": save_path
            }
        }

        # Start validation if enabled
        if validation_engine:
            validation_result = await validation_engine.start_validation(
                task_id=f"task_{int(time.time())}",
                task_definition=context["task_definition"]
            )

            # Pre-execution validation
            await validation_engine.validate_phase(
                ValidationPhase.PRE_EXECUTION,
                context
            )

        # Execute task
        result = await task_executor.execute_task(task_definition, context)

        # Update context with results for validation
        context.update({
            "task_result": {
                "status": result.status.value if hasattr(result.status, 'value') else str(result.status),
                "result": result.result,
                "error_message": result.error_message,
                "execution_time": getattr(result, 'execution_time', 0)
            }
        })

        # Post-execution validation if enabled
        if validation_engine:
            await validation_engine.validate_phase(
                ValidationPhase.POST_EXECUTION,
                context
            )

            # Complete validation
            validation_result = await validation_engine.complete_validation()

        if result.status == TaskStatus.COMPLETED:
            task_result = str(result.result)

            # Include validation summary if available
            if validation_result:
                validation_summary = validation_result.get_summary()
                if not validation_result.is_successful:
                    task_result += f"\n\nValidation Issues Found: {validation_summary['total_issues']}"
                    task_result += f"\nValidation Status: {validation_summary['overall_status']}"

            return task_result
        else:
            raise TaskExecutionError(f"Task failed: {result.error_message}")

    except Exception as e:
        raise TaskExecutionError(f"Task execution failed: {e}") from e


def get_execution_status() -> dict:
    """
    Get the current execution system status.
    
    Returns:
        Dictionary containing execution system status
    """
    return {
        "execution_mode": "unified",
        "legacy_components": "removed",
        "dual_paths": "eliminated",
        "status": "active"
    }
