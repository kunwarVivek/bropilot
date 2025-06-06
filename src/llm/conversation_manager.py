"""
Advanced conversation management for LLM interactions.

This module provides sophisticated conversation management with context tracking,
memory management, and multi-turn dialogue capabilities.
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import uuid

from core.interfaces import ILLMProvider
from core.exceptions import LLMError, ValidationError
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id


class MessageRole(str, Enum):
    """Message role enumeration."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"


class ConversationState(str, Enum):
    """Conversation state enumeration."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


@dataclass
class Message:
    """Represents a message in a conversation."""
    message_id: str
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    function_call: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    attachments: List[Dict[str, Any]] = field(default_factory=list)  # For multi-modal content
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        result = {
            "message_id": self.message_id,
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
        
        if self.function_call:
            result["function_call"] = self.function_call
        
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        
        if self.attachments:
            result["attachments"] = self.attachments
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create message from dictionary."""
        return cls(
            message_id=data["message_id"],
            role=MessageRole(data["role"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {}),
            function_call=data.get("function_call"),
            tool_calls=data.get("tool_calls"),
            attachments=data.get("attachments", [])
        )


@dataclass
class ConversationContext:
    """Context information for a conversation."""
    task_context: Dict[str, Any] = field(default_factory=dict)
    browser_context: Dict[str, Any] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    session_variables: Dict[str, Any] = field(default_factory=dict)
    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def update(self, **kwargs) -> None:
        """Update context with new information."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                if isinstance(getattr(self, key), dict):
                    getattr(self, key).update(value)
                else:
                    setattr(self, key, value)


@dataclass
class ConversationConfig:
    """Configuration for conversation management."""
    max_messages: int = 100
    max_context_length: int = 8000
    memory_window: int = 20  # Number of recent messages to keep in active memory
    auto_summarize: bool = True
    summarize_threshold: int = 50  # Summarize when exceeding this many messages
    context_compression: bool = True
    enable_function_calling: bool = True
    enable_tool_use: bool = True
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None


class ConversationManager:
    """Advanced conversation manager for LLM interactions."""
    
    def __init__(
        self,
        llm_provider: ILLMProvider,
        config: ConversationConfig,
        conversation_id: Optional[str] = None
    ):
        """Initialize conversation manager."""
        self.llm_provider = llm_provider
        self.config = config
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.logger = StructuredLogger(f"conversation_manager.{self.conversation_id}")
        
        # Conversation state
        self.messages: List[Message] = []
        self.context = ConversationContext()
        self.state = ConversationState.ACTIVE
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        
        # Memory management
        self.summary: Optional[str] = None
        self.compressed_history: List[Message] = []
        self.active_memory: List[Message] = []
        
        # Function and tool management
        self.available_functions: Dict[str, Callable] = {}
        self.available_tools: Dict[str, Callable] = {}
        
        # Statistics
        self.total_messages = 0
        self.total_tokens_used = 0
        self.total_function_calls = 0
        self.total_tool_calls = 0
        
        # Initialize with system prompt if provided
        if self.config.system_prompt:
            self.add_system_message(self.config.system_prompt)
    
    async def send_message(
        self,
        content: str,
        role: MessageRole = MessageRole.USER,
        metadata: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Message:
        """Send a message and get LLM response."""
        
        # Add user message
        user_message = self.add_message(
            role=role,
            content=content,
            metadata=metadata or {},
            attachments=attachments or []
        )
        
        self.logger.info(
            "Sending message to LLM",
            conversation_id=self.conversation_id,
            message_id=user_message.message_id,
            role=role.value,
            content_length=len(content)
        )
        
        try:
            # Prepare messages for LLM
            llm_messages = await self._prepare_messages_for_llm()
            
            # Get LLM response
            response = await self.llm_provider.generate_response(
                messages=llm_messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                functions=list(self.available_functions.keys()) if self.config.enable_function_calling else None,
                tools=list(self.available_tools.keys()) if self.config.enable_tool_use else None
            )
            
            # Process response
            assistant_message = await self._process_llm_response(response)
            
            # Update activity timestamp
            self.last_activity = datetime.utcnow()
            
            # Check if conversation needs summarization
            if self.config.auto_summarize and len(self.messages) > self.config.summarize_threshold:
                await self._summarize_conversation()
            
            return assistant_message
            
        except Exception as e:
            self.logger.error(
                "Failed to get LLM response",
                conversation_id=self.conversation_id,
                error=str(e)
            )
            
            # Add error message to conversation
            error_message = self.add_message(
                role=MessageRole.ASSISTANT,
                content=f"I apologize, but I encountered an error: {str(e)}",
                metadata={"error": True, "original_error": str(e)}
            )
            
            raise LLMError(f"LLM response failed: {e}") from e
    
    def add_message(
        self,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        function_call: Optional[Dict[str, Any]] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Message:
        """Add a message to the conversation."""
        
        message = Message(
            message_id=str(uuid.uuid4()),
            role=role,
            content=content,
            metadata=metadata or {},
            function_call=function_call,
            tool_calls=tool_calls,
            attachments=attachments or []
        )
        
        self.messages.append(message)
        self.total_messages += 1
        
        # Update active memory
        self._update_active_memory()
        
        self.logger.debug(
            "Message added to conversation",
            conversation_id=self.conversation_id,
            message_id=message.message_id,
            role=role.value,
            content_length=len(content)
        )
        
        return message
    
    def add_system_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> Message:
        """Add a system message to the conversation."""
        return self.add_message(
            role=MessageRole.SYSTEM,
            content=content,
            metadata=metadata
        )
    
    def add_function(self, name: str, function: Callable, description: Optional[str] = None) -> None:
        """Add a function that can be called by the LLM."""
        self.available_functions[name] = function
        
        self.logger.info(
            "Function added to conversation",
            conversation_id=self.conversation_id,
            function_name=name,
            description=description
        )
    
    def add_tool(self, name: str, tool: Callable, description: Optional[str] = None) -> None:
        """Add a tool that can be used by the LLM."""
        self.available_tools[name] = tool
        
        self.logger.info(
            "Tool added to conversation",
            conversation_id=self.conversation_id,
            tool_name=name,
            description=description
        )
    
    async def _prepare_messages_for_llm(self) -> List[Dict[str, Any]]:
        """Prepare messages for LLM API call."""
        
        # Use active memory for recent context
        messages_to_send = []
        
        # Add summary if available
        if self.summary:
            messages_to_send.append({
                "role": "system",
                "content": f"Previous conversation summary: {self.summary}"
            })
        
        # Add compressed history if available
        for message in self.compressed_history[-10:]:  # Last 10 compressed messages
            messages_to_send.append({
                "role": message.role.value,
                "content": message.content
            })
        
        # Add active memory messages
        for message in self.active_memory:
            msg_dict = {
                "role": message.role.value,
                "content": message.content
            }
            
            # Add function call if present
            if message.function_call:
                msg_dict["function_call"] = message.function_call
            
            # Add tool calls if present
            if message.tool_calls:
                msg_dict["tool_calls"] = message.tool_calls
            
            # Add attachments for multi-modal content
            if message.attachments:
                msg_dict["attachments"] = message.attachments
            
            messages_to_send.append(msg_dict)
        
        # Ensure we don't exceed context length
        if self.config.context_compression:
            messages_to_send = await self._compress_context(messages_to_send)
        
        return messages_to_send
    
    async def _process_llm_response(self, response: Dict[str, Any]) -> Message:
        """Process LLM response and handle function/tool calls."""
        
        content = response.get("content", "")
        function_call = response.get("function_call")
        tool_calls = response.get("tool_calls")
        
        # Update token usage
        if "usage" in response:
            self.total_tokens_used += response["usage"].get("total_tokens", 0)
        
        # Handle function calls
        if function_call and self.config.enable_function_calling:
            await self._handle_function_call(function_call)
            self.total_function_calls += 1
        
        # Handle tool calls
        if tool_calls and self.config.enable_tool_use:
            for tool_call in tool_calls:
                await self._handle_tool_call(tool_call)
            self.total_tool_calls += len(tool_calls)
        
        # Add assistant message
        assistant_message = self.add_message(
            role=MessageRole.ASSISTANT,
            content=content,
            function_call=function_call,
            tool_calls=tool_calls,
            metadata={
                "model": response.get("model"),
                "usage": response.get("usage"),
                "finish_reason": response.get("finish_reason")
            }
        )
        
        return assistant_message
    
    async def _handle_function_call(self, function_call: Dict[str, Any]) -> None:
        """Handle function call from LLM."""
        
        function_name = function_call.get("name")
        function_args = function_call.get("arguments", {})
        
        if function_name not in self.available_functions:
            self.logger.warning(
                "Unknown function called",
                conversation_id=self.conversation_id,
                function_name=function_name
            )
            return
        
        try:
            # Parse arguments if they're a string
            if isinstance(function_args, str):
                function_args = json.loads(function_args)
            
            # Call the function
            function = self.available_functions[function_name]
            if asyncio.iscoroutinefunction(function):
                result = await function(**function_args)
            else:
                result = function(**function_args)
            
            # Add function result message
            self.add_message(
                role=MessageRole.FUNCTION,
                content=json.dumps(result) if not isinstance(result, str) else result,
                metadata={
                    "function_name": function_name,
                    "function_args": function_args
                }
            )
            
            self.logger.info(
                "Function call executed",
                conversation_id=self.conversation_id,
                function_name=function_name,
                success=True
            )
            
        except Exception as e:
            self.logger.error(
                "Function call failed",
                conversation_id=self.conversation_id,
                function_name=function_name,
                error=str(e)
            )
            
            # Add error message
            self.add_message(
                role=MessageRole.FUNCTION,
                content=f"Function call failed: {str(e)}",
                metadata={
                    "function_name": function_name,
                    "function_args": function_args,
                    "error": True
                }
            )
    
    async def _handle_tool_call(self, tool_call: Dict[str, Any]) -> None:
        """Handle tool call from LLM."""
        
        tool_name = tool_call.get("name")
        tool_args = tool_call.get("arguments", {})
        
        if tool_name not in self.available_tools:
            self.logger.warning(
                "Unknown tool called",
                conversation_id=self.conversation_id,
                tool_name=tool_name
            )
            return
        
        try:
            # Parse arguments if they're a string
            if isinstance(tool_args, str):
                tool_args = json.loads(tool_args)
            
            # Call the tool
            tool = self.available_tools[tool_name]
            if asyncio.iscoroutinefunction(tool):
                result = await tool(**tool_args)
            else:
                result = tool(**tool_args)
            
            # Add tool result message
            self.add_message(
                role=MessageRole.TOOL,
                content=json.dumps(result) if not isinstance(result, str) else result,
                metadata={
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                    "tool_call_id": tool_call.get("id")
                }
            )
            
            self.logger.info(
                "Tool call executed",
                conversation_id=self.conversation_id,
                tool_name=tool_name,
                success=True
            )
            
        except Exception as e:
            self.logger.error(
                "Tool call failed",
                conversation_id=self.conversation_id,
                tool_name=tool_name,
                error=str(e)
            )
            
            # Add error message
            self.add_message(
                role=MessageRole.TOOL,
                content=f"Tool call failed: {str(e)}",
                metadata={
                    "tool_name": tool_name,
                    "tool_args": tool_args,
                    "tool_call_id": tool_call.get("id"),
                    "error": True
                }
            )
    
    def _update_active_memory(self) -> None:
        """Update active memory with recent messages."""
        
        # Keep recent messages in active memory
        self.active_memory = self.messages[-self.config.memory_window:]
    
    async def _summarize_conversation(self) -> None:
        """Summarize the conversation to manage context length."""
        
        if len(self.messages) <= self.config.memory_window:
            return
        
        # Messages to summarize (exclude recent ones in active memory)
        messages_to_summarize = self.messages[:-self.config.memory_window]
        
        if not messages_to_summarize:
            return
        
        try:
            # Create summarization prompt
            conversation_text = "\n".join([
                f"{msg.role.value}: {msg.content}"
                for msg in messages_to_summarize
            ])
            
            summary_prompt = f"""
            Please provide a concise summary of the following conversation, focusing on:
            1. Key decisions made
            2. Important context established
            3. Tasks completed or in progress
            4. Any relevant state information
            
            Conversation:
            {conversation_text}
            
            Summary:
            """
            
            # Get summary from LLM
            summary_response = await self.llm_provider.generate_response(
                messages=[{"role": "user", "content": summary_prompt}],
                temperature=0.3,
                max_tokens=500
            )
            
            self.summary = summary_response.get("content", "")
            
            # Move summarized messages to compressed history
            self.compressed_history.extend(messages_to_summarize)
            
            # Remove summarized messages from main list
            self.messages = self.messages[-self.config.memory_window:]
            
            self.logger.info(
                "Conversation summarized",
                conversation_id=self.conversation_id,
                summarized_messages=len(messages_to_summarize),
                summary_length=len(self.summary)
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to summarize conversation",
                conversation_id=self.conversation_id,
                error=str(e)
            )
    
    async def _compress_context(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compress context to fit within limits."""
        
        # Simple compression: truncate if too long
        total_length = sum(len(msg.get("content", "")) for msg in messages)
        
        if total_length <= self.config.max_context_length:
            return messages
        
        # Keep system messages and recent messages
        compressed = []
        current_length = 0
        
        # Add system messages first
        for msg in messages:
            if msg.get("role") == "system":
                compressed.append(msg)
                current_length += len(msg.get("content", ""))
        
        # Add recent messages in reverse order
        for msg in reversed(messages):
            if msg.get("role") != "system":
                msg_length = len(msg.get("content", ""))
                if current_length + msg_length <= self.config.max_context_length:
                    compressed.insert(-len([m for m in compressed if m.get("role") == "system"]), msg)
                    current_length += msg_length
                else:
                    break
        
        return compressed
    
    def get_conversation_history(self, include_metadata: bool = False) -> List[Dict[str, Any]]:
        """Get conversation history."""
        
        if include_metadata:
            return [msg.to_dict() for msg in self.messages]
        else:
            return [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in self.messages
            ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get conversation statistics."""
        
        return {
            "conversation_id": self.conversation_id,
            "state": self.state.value,
            "total_messages": self.total_messages,
            "current_messages": len(self.messages),
            "total_tokens_used": self.total_tokens_used,
            "total_function_calls": self.total_function_calls,
            "total_tool_calls": self.total_tool_calls,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "has_summary": self.summary is not None,
            "compressed_messages": len(self.compressed_history),
            "active_memory_size": len(self.active_memory),
            "available_functions": list(self.available_functions.keys()),
            "available_tools": list(self.available_tools.keys())
        }
    
    def update_context(self, **kwargs) -> None:
        """Update conversation context."""
        self.context.update(**kwargs)
    
    def pause_conversation(self) -> None:
        """Pause the conversation."""
        self.state = ConversationState.PAUSED
        
    def resume_conversation(self) -> None:
        """Resume the conversation."""
        self.state = ConversationState.ACTIVE
        
    def complete_conversation(self) -> None:
        """Mark conversation as completed."""
        self.state = ConversationState.COMPLETED
        
    def archive_conversation(self) -> None:
        """Archive the conversation."""
        self.state = ConversationState.ARCHIVED
