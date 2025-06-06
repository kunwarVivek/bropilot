"""
Browser-use library adapter for task execution.

This module provides an adapter that integrates the browser-use library
with the execution layer, handling browser automation tasks.
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone

from browser_use import Browser, Agent, BrowserConfig

from core.interfaces import TaskDefinition, ExecutionResult, TaskStatus
from core.exceptions import BrowserError, TaskExecutionError, ValidationError
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id


class BrowserUseAdapter:
    """
    Adapter for browser-use library integration.
    
    This adapter provides a clean interface between the execution layer
    and the browser-use library, handling browser automation tasks.
    """
    
    def __init__(
        self,
        default_config: Optional[Dict[str, Any]] = None,
        save_logs: bool = True,
        logs_base_path: str = "logs"
    ):
        """
        Initialize the browser-use adapter.
        
        Args:
            default_config: Default browser configuration
            save_logs: Whether to save execution logs
            logs_base_path: Base path for saving logs
        """
        self.default_config = default_config or self._get_default_config()
        self.save_logs = save_logs
        self.logs_base_path = logs_base_path
        
        # Active sessions tracking
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Initialize logger
        self.logger = StructuredLogger("browser_use_adapter")
        
        self.logger.info(
            "Browser-use adapter initialized",
            save_logs=save_logs,
            logs_base_path=logs_base_path,
            default_config=self.default_config
        )
    
    @with_correlation_id
    async def execute_task(
        self,
        task_definition: TaskDefinition,
        browser: Browser,
        llm_provider: Any,
        context: Dict[str, Any]
    ) -> ExecutionResult:
        """
        Execute a task using the browser-use library.
        
        Args:
            task_definition: The task to execute
            browser: Browser instance to use
            llm_provider: LLM provider for the agent
            context: Execution context
            
        Returns:
            ExecutionResult containing the task outcome
        """
        session_id = context.get("session_id", str(uuid.uuid4()))
        correlation_id = context.get("correlation_id", str(uuid.uuid4()))
        
        self.logger.info(
            "Executing task with browser-use",
            task_name=task_definition.name,
            session_id=session_id,
            correlation_id=correlation_id
        )
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Create agent configuration
            agent_config = await self._prepare_agent_config(
                task_definition, 
                context, 
                session_id
            )
            
            # Create browser-use agent
            agent = await self._create_agent(
                task_definition,
                browser,
                llm_provider,
                agent_config,
                session_id
            )
            
            # Track session
            self.active_sessions[session_id] = {
                "task_definition": task_definition,
                "agent": agent,
                "browser": browser,
                "start_time": start_time,
                "context": context
            }
            
            # Execute the task
            result = await self._execute_agent(agent, session_id, correlation_id)
            
            # Calculate execution time
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Create success result
            execution_result = ExecutionResult(
                status=TaskStatus.COMPLETED,
                result=result,
                execution_time=execution_time,
                metadata={
                    "session_id": session_id,
                    "task_name": task_definition.name,
                    "correlation_id": correlation_id,
                    "adapter": "browser_use",
                    "agent_config": agent_config
                }
            )
            
            self.logger.info(
                "Task execution completed successfully",
                task_name=task_definition.name,
                session_id=session_id,
                execution_time=execution_time,
                correlation_id=correlation_id
            )
            
            return execution_result
            
        except Exception as e:
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            error_msg = f"Browser-use task execution failed: {str(e)}"
            
            self.logger.error(
                "Task execution failed",
                task_name=task_definition.name,
                session_id=session_id,
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
                    "session_id": session_id,
                    "task_name": task_definition.name,
                    "correlation_id": correlation_id,
                    "adapter": "browser_use",
                    "error_type": type(e).__name__
                }
            )
            
        finally:
            # Cleanup session
            await self._cleanup_session(session_id)
    
    async def create_browser(self, config: Dict[str, Any]) -> Browser:
        """
        Create a browser instance using browser-use.
        
        Args:
            config: Browser configuration
            
        Returns:
            Browser instance
        """
        try:
            # Merge with default config
            merged_config = {**self.default_config, **config}
            
            # Create browser-use config
            browser_config = BrowserConfig(
                headless=merged_config.get("headless", True),
                browser_type=merged_config.get("browser_type", "chrome"),
                viewport_size=merged_config.get("viewport", {"width": 1920, "height": 1080}),
                user_agent=merged_config.get("user_agent"),
                extra_chromium_args=merged_config.get("args", [])
            )
            
            # Create browser
            browser = Browser(config=browser_config)
            
            self.logger.info(
                "Browser created via browser-use",
                headless=browser_config.headless,
                browser_type=browser_config.browser_type,
                viewport=browser_config.viewport_size
            )
            
            return browser
            
        except Exception as e:
            self.logger.error(
                "Failed to create browser via browser-use",
                error=str(e),
                config=config
            )
            raise BrowserError(f"Failed to create browser: {e}") from e
    
    async def close_browser(self, browser: Browser) -> None:
        """
        Close a browser instance safely.
        
        Args:
            browser: Browser instance to close
        """
        try:
            await browser.close()
            self.logger.debug("Browser closed via browser-use")
            
        except Exception as e:
            self.logger.warning(
                "Failed to close browser via browser-use",
                error=str(e)
            )
            # Don't raise exception for cleanup operations
    
    def get_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get information about active browser-use sessions."""
        return {
            session_id: {
                "task_name": info["task_definition"].name,
                "start_time": info["start_time"].isoformat(),
                "context": info["context"]
            }
            for session_id, info in self.active_sessions.items()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the browser-use adapter."""
        try:
            # Test browser creation
            test_config = {"headless": True, "browser_type": "chrome"}
            browser = await self.create_browser(test_config)
            await self.close_browser(browser)
            
            return {
                "status": "healthy",
                "adapter": "browser_use",
                "active_sessions": len(self.active_sessions),
                "can_create_browser": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "adapter": "browser_use",
                "error": str(e),
                "active_sessions": len(self.active_sessions),
                "can_create_browser": False,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    # Private helper methods
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default browser configuration."""
        return {
            "headless": True,
            "browser_type": "chrome",
            "viewport": {"width": 1920, "height": 1080},
            "args": [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor"
            ],
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    async def _prepare_agent_config(
        self,
        task_definition: TaskDefinition,
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """Prepare configuration for the browser-use agent."""
        # Prepare initial actions
        initial_actions = context.get("initial_actions", [])
        
        # Add default navigation if target URL is provided
        if "target_url" in context and not initial_actions:
            initial_actions = [
                {"open_tab": {"url": context["target_url"]}}
            ]
        
        # Prepare save path for logs
        save_path = None
        if self.save_logs:
            save_path = f"{self.logs_base_path}/{task_definition.name}_{session_id}"
        
        return {
            "initial_actions": initial_actions,
            "save_conversation_path": save_path,
            "use_vision": context.get("use_vision", True),
            "max_actions": context.get("max_actions", 100),
            "include_attributes": context.get("include_attributes", ["title", "placeholder", "value"])
        }
    
    async def _create_agent(
        self,
        task_definition: TaskDefinition,
        browser: Browser,
        llm_provider: Any,
        agent_config: Dict[str, Any],
        session_id: str
    ) -> Agent:
        """Create a browser-use agent."""
        try:
            agent = Agent(
                task=task_definition.prompt_template,
                llm=llm_provider,
                browser=browser,
                initial_actions=agent_config["initial_actions"],
                save_conversation_path=agent_config["save_conversation_path"],
                use_vision=agent_config["use_vision"],
                max_actions=agent_config["max_actions"],
                include_attributes=agent_config["include_attributes"]
            )
            
            self.logger.debug(
                "Browser-use agent created",
                session_id=session_id,
                task_name=task_definition.name,
                use_vision=agent_config["use_vision"],
                max_actions=agent_config["max_actions"]
            )
            
            return agent
            
        except Exception as e:
            self.logger.error(
                "Failed to create browser-use agent",
                session_id=session_id,
                error=str(e)
            )
            raise TaskExecutionError(f"Failed to create agent: {e}") from e
    
    async def _execute_agent(
        self,
        agent: Agent,
        session_id: str,
        correlation_id: str
    ) -> Any:
        """Execute the browser-use agent."""
        try:
            # Run the agent
            agent_history = await agent.run()
            
            # Save logs if enabled
            if self.save_logs and hasattr(agent_history, 'save_to_file'):
                save_path = f"{self.logs_base_path}/{session_id}"
                agent_history.save_to_file(save_path)
            
            # Extract result
            if hasattr(agent_history, 'final_result'):
                result = agent_history.final_result()
            else:
                result = str(agent_history)
            
            self.logger.debug(
                "Agent execution completed",
                session_id=session_id,
                correlation_id=correlation_id,
                result_type=type(result).__name__
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Agent execution failed",
                session_id=session_id,
                correlation_id=correlation_id,
                error=str(e)
            )
            raise TaskExecutionError(f"Agent execution failed: {e}") from e
    
    async def _cleanup_session(self, session_id: str) -> None:
        """Clean up a browser-use session."""
        try:
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
                
            self.logger.debug(
                "Session cleanup completed",
                session_id=session_id
            )
            
        except Exception as e:
            self.logger.warning(
                "Session cleanup failed",
                session_id=session_id,
                error=str(e)
            )
