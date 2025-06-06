"""
Task executor implementation for browser automation tasks.

This module provides the core task execution functionality, integrating with
the browser-use library and providing comprehensive task lifecycle management.
"""

import asyncio
import uuid
from typing import Dict, Any, Optional, Set
from datetime import datetime, timezone
from browser_use import Browser, Agent, BrowserConfig

from core.interfaces import ITaskExecutor, TaskDefinition, ExecutionResult, TaskStatus
from core.exceptions import TaskExecutionError, BrowserError, OperationCancelledError
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id


class TaskExecutor(ITaskExecutor):
    """
    Concrete implementation of ITaskExecutor for browser automation tasks.
    
    This executor integrates with the browser-use library to execute tasks
    with proper lifecycle management, error handling, and logging.
    """
    
    def __init__(
        self,
        browser_manager=None,
        llm_provider=None,
        default_timeout: int = 300,
        save_logs: bool = True,
        logs_base_path: str = "logs"
    ):
        """
        Initialize the task executor.
        
        Args:
            browser_manager: Browser manager instance (optional, will create if None)
            llm_provider: LLM provider instance (optional, will create if None)
            default_timeout: Default timeout for task execution in seconds
            save_logs: Whether to save execution logs
            logs_base_path: Base path for saving logs
        """
        self.browser_manager = browser_manager
        self.llm_provider = llm_provider
        self.default_timeout = default_timeout
        self.save_logs = save_logs
        self.logs_base_path = logs_base_path
        
        # Task tracking
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        self.paused_tasks: Set[str] = set()
        self.cancelled_tasks: Set[str] = set()
        
        # Initialize logger
        self.logger = StructuredLogger("task_executor")
        
        self.logger.info(
            "Task executor initialized",
            default_timeout=default_timeout,
            save_logs=save_logs,
            logs_base_path=logs_base_path
        )
    
    @with_correlation_id
    async def execute_task(
        self,
        task_definition: TaskDefinition,
        context: Dict[str, Any]
    ) -> ExecutionResult:
        """
        Execute a single task with the given context.
        
        Args:
            task_definition: The task to execute
            context: Execution context with variables and metadata
            
        Returns:
            ExecutionResult containing the task outcome
            
        Raises:
            TaskExecutionError: If task execution fails
            TimeoutError: If task execution times out
        """
        task_id = context.get("task_id", str(uuid.uuid4()))
        correlation_id = context.get("correlation_id", str(uuid.uuid4()))
        
        self.logger.info(
            "Starting task execution",
            task_id=task_id,
            task_name=task_definition.name,
            correlation_id=correlation_id
        )
        
        start_time = datetime.now(timezone.utc)
        browser = None
        
        try:
            # Register active task
            self.active_tasks[task_id] = {
                "definition": task_definition,
                "context": context,
                "start_time": start_time,
                "status": TaskStatus.RUNNING,
                "browser": None,
                "agent": None
            }
            
            # Check if task is cancelled before starting
            if task_id in self.cancelled_tasks:
                raise OperationCancelledError(f"Task {task_id} was cancelled before execution")
            
            # Create browser instance
            browser = await self._create_browser(task_id, context)
            self.active_tasks[task_id]["browser"] = browser
            
            # Get LLM provider
            llm = await self._get_llm_provider(context)
            
            # Create browser-use agent
            agent = await self._create_agent(
                task_definition, 
                browser, 
                llm, 
                task_id, 
                context
            )
            self.active_tasks[task_id]["agent"] = agent
            
            # Execute task with timeout
            timeout = task_definition.timeout or self.default_timeout
            result = await asyncio.wait_for(
                self._execute_with_pause_support(agent, task_id),
                timeout=timeout
            )
            
            # Calculate execution time
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Create success result
            execution_result = ExecutionResult(
                status=TaskStatus.COMPLETED,
                result=result,
                execution_time=execution_time,
                metadata={
                    "task_id": task_id,
                    "task_name": task_definition.name,
                    "correlation_id": correlation_id,
                    "start_time": start_time.isoformat(),
                    "end_time": datetime.now(timezone.utc).isoformat()
                }
            )
            
            self.logger.info(
                "Task execution completed successfully",
                task_id=task_id,
                task_name=task_definition.name,
                execution_time=execution_time,
                correlation_id=correlation_id
            )
            
            return execution_result
            
        except asyncio.TimeoutError:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            error_msg = f"Task {task_definition.name} timed out after {timeout} seconds"
            
            self.logger.error(
                "Task execution timed out",
                task_id=task_id,
                task_name=task_definition.name,
                timeout=timeout,
                execution_time=execution_time,
                correlation_id=correlation_id
            )
            
            return ExecutionResult(
                status=TaskStatus.TIMEOUT,
                error_message=error_msg,
                execution_time=execution_time,
                metadata={
                    "task_id": task_id,
                    "task_name": task_definition.name,
                    "correlation_id": correlation_id,
                    "timeout": timeout
                }
            )
            
        except OperationCancelledError:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            error_msg = f"Task {task_definition.name} was cancelled"
            
            self.logger.warning(
                "Task execution cancelled",
                task_id=task_id,
                task_name=task_definition.name,
                execution_time=execution_time,
                correlation_id=correlation_id
            )
            
            return ExecutionResult(
                status=TaskStatus.CANCELLED,
                error_message=error_msg,
                execution_time=execution_time,
                metadata={
                    "task_id": task_id,
                    "task_name": task_definition.name,
                    "correlation_id": correlation_id
                }
            )
            
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            error_msg = f"Task {task_definition.name} failed: {str(e)}"
            
            self.logger.error(
                "Task execution failed",
                task_id=task_id,
                task_name=task_definition.name,
                error=str(e),
                error_type=type(e).__name__,
                execution_time=execution_time,
                correlation_id=correlation_id
            )
            
            return ExecutionResult(
                status=TaskStatus.FAILED,
                error_message=error_msg,
                execution_time=execution_time,
                metadata={
                    "task_id": task_id,
                    "task_name": task_definition.name,
                    "correlation_id": correlation_id,
                    "error_type": type(e).__name__
                }
            )
            
        finally:
            # Cleanup
            await self._cleanup_task(task_id, browser)
    
    async def pause_task(self, task_id: str) -> bool:
        """
        Pause a running task.
        
        Args:
            task_id: ID of the task to pause
            
        Returns:
            True if task was paused successfully, False otherwise
        """
        if task_id not in self.active_tasks:
            self.logger.warning(
                "Cannot pause task - task not found",
                task_id=task_id
            )
            return False
        
        if task_id in self.paused_tasks:
            self.logger.warning(
                "Task is already paused",
                task_id=task_id
            )
            return True
        
        self.paused_tasks.add(task_id)
        self.active_tasks[task_id]["status"] = TaskStatus.PAUSED
        
        self.logger.info(
            "Task paused",
            task_id=task_id
        )
        
        return True
    
    async def resume_task(self, task_id: str) -> bool:
        """
        Resume a paused task.
        
        Args:
            task_id: ID of the task to resume
            
        Returns:
            True if task was resumed successfully, False otherwise
        """
        if task_id not in self.active_tasks:
            self.logger.warning(
                "Cannot resume task - task not found",
                task_id=task_id
            )
            return False
        
        if task_id not in self.paused_tasks:
            self.logger.warning(
                "Task is not paused",
                task_id=task_id
            )
            return True

    # Private helper methods

    async def _create_browser(self, task_id: str, context: Dict[str, Any]) -> Browser:
        """Create a browser instance for task execution."""
        try:
            # Use browser manager if available, otherwise create directly
            if self.browser_manager:
                browser_config = context.get("browser_config", {})
                return await self.browser_manager.create_browser(browser_config)
            else:
                # Create browser directly using browser-use
                config = BrowserConfig(
                    headless=context.get("headless", False),
                    browser_type=context.get("browser_type", "chrome")
                )
                browser = Browser(config=config)

                self.logger.debug(
                    "Browser created directly",
                    task_id=task_id,
                    headless=config.headless,
                    browser_type=config.browser_type
                )

                return browser

        except Exception as e:
            self.logger.error(
                "Failed to create browser",
                task_id=task_id,
                error=str(e)
            )
            raise BrowserError(f"Failed to create browser: {e}") from e

    async def _get_llm_provider(self, context: Dict[str, Any]):
        """Get LLM provider for task execution."""
        if self.llm_provider:
            return self.llm_provider

        # Fallback: create a simple LLM provider
        # This will be replaced when we implement the LLM provider
        # Note: context parameter reserved for future use when we implement proper LLM provider selection
        from workflows.sample_workflow import get_llm
        return get_llm()

    async def _create_agent(
        self,
        task_definition: TaskDefinition,
        browser: Browser,
        llm,
        task_id: str,
        context: Dict[str, Any]
    ) -> Agent:
        """Create a browser-use agent for task execution."""
        try:
            # Prepare initial actions
            initial_actions = context.get("initial_actions", [
                {'open_tab': {'url': context.get("target_url", "https://dev.gotrust.tech")}}
            ])

            # Prepare save path for logs
            save_path = None
            if self.save_logs:
                save_path = f"{self.logs_base_path}/{task_definition.name}_{task_id}"

            # Create agent
            agent = Agent(
                task=task_definition.prompt_template,
                llm=llm,
                initial_actions=initial_actions,
                browser=browser,
                save_conversation_path=save_path,
                use_vision=context.get("use_vision", True)
            )

            self.logger.debug(
                "Agent created",
                task_id=task_id,
                task_name=task_definition.name,
                save_path=save_path,
                use_vision=context.get("use_vision", True)
            )

            return agent

        except Exception as e:
            self.logger.error(
                "Failed to create agent",
                task_id=task_id,
                error=str(e)
            )
            raise TaskExecutionError(f"Failed to create agent: {e}") from e

    async def _execute_with_pause_support(self, agent: Agent, task_id: str):
        """Execute agent with pause/resume support."""
        while True:
            # Check if task is cancelled
            if task_id in self.cancelled_tasks:
                raise OperationCancelledError(f"Task {task_id} was cancelled")

            # Check if task is paused
            if task_id in self.paused_tasks:
                self.logger.debug(
                    "Task is paused, waiting for resume",
                    task_id=task_id
                )
                # Wait for resume (check every second)
                while task_id in self.paused_tasks:
                    if task_id in self.cancelled_tasks:
                        raise OperationCancelledError(f"Task {task_id} was cancelled while paused")
                    await asyncio.sleep(1)

                self.logger.debug(
                    "Task resumed, continuing execution",
                    task_id=task_id
                )

            # Execute the agent
            try:
                agent_history = await agent.run()

                # Save logs if enabled
                if self.save_logs and hasattr(agent_history, 'save_to_file'):
                    save_path = f"{self.logs_base_path}/{task_id}"
                    agent_history.save_to_file(save_path)

                # Get final result
                if hasattr(agent_history, 'final_result'):
                    return agent_history.final_result()
                else:
                    return str(agent_history)

            except Exception as e:
                self.logger.error(
                    "Agent execution failed",
                    task_id=task_id,
                    error=str(e)
                )
                raise TaskExecutionError(f"Agent execution failed: {e}") from e

    async def _cleanup_task(self, task_id: str, browser: Optional[Browser] = None):
        """Clean up task resources."""
        try:
            # Close browser if it exists and we created it directly
            if browser and not self.browser_manager:
                try:
                    await browser.close()
                    self.logger.debug(
                        "Browser closed",
                        task_id=task_id
                    )
                except Exception as e:
                    self.logger.warning(
                        "Failed to close browser",
                        task_id=task_id,
                        error=str(e)
                    )

            # Remove from tracking sets
            self.paused_tasks.discard(task_id)
            self.cancelled_tasks.discard(task_id)

            # Remove from active tasks
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]

            self.logger.debug(
                "Task cleanup completed",
                task_id=task_id
            )

        except Exception as e:
            self.logger.error(
                "Task cleanup failed",
                task_id=task_id,
                error=str(e)
            )

    def get_active_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get information about currently active tasks."""
        return {
            task_id: {
                "task_name": info["definition"].name,
                "status": info["status"].value,
                "start_time": info["start_time"].isoformat(),
                "is_paused": task_id in self.paused_tasks,
                "is_cancelled": task_id in self.cancelled_tasks
            }
            for task_id, info in self.active_tasks.items()
        }

    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the task executor."""
        return {
            "status": "healthy",
            "active_tasks_count": len(self.active_tasks),
            "paused_tasks_count": len(self.paused_tasks),
            "cancelled_tasks_count": len(self.cancelled_tasks),
            "browser_manager_available": self.browser_manager is not None,
            "llm_provider_available": self.llm_provider is not None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running or paused task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if task was cancelled successfully, False otherwise
        """
        if task_id not in self.active_tasks:
            self.logger.warning(
                "Cannot cancel task - task not found",
                task_id=task_id
            )
            return False
        
        self.cancelled_tasks.add(task_id)
        self.paused_tasks.discard(task_id)  # Remove from paused if it was paused
        self.active_tasks[task_id]["status"] = TaskStatus.CANCELLED
        
        self.logger.info(
            "Task cancelled",
            task_id=task_id
        )
        
        return True
