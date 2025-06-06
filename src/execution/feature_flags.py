"""
Feature flags for gradual migration to the new execution layer.

This module provides feature flag management to enable gradual migration
from the legacy system to the new execution layer with safe rollback capabilities.
"""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from enum import Enum

from src.infrastructure.logging.logger import StructuredLogger


class FeatureFlag(str, Enum):
    """Available feature flags for the unified execution layer."""

    # Core execution features (always enabled in unified system)
    USE_UNIFIED_EXECUTION = "use_unified_execution"
    USE_UNIFIED_LLM_PROVIDER = "use_unified_llm_provider"
    USE_BROWSER_MANAGER = "use_browser_manager"

    # Workflow features
    USE_ENHANCED_WORKFLOW = "use_enhanced_workflow"
    USE_PARALLEL_EXECUTION = "use_parallel_execution"
    USE_TASK_SCHEDULING = "use_task_scheduling"

    # Infrastructure features
    USE_BROWSER_POOLING = "use_browser_pooling"
    USE_CONVERSATION_MANAGER = "use_conversation_manager"
    USE_ADVANCED_LOGGING = "use_advanced_logging"

    # Provider features
    ENABLE_PROVIDER_FALLBACK = "enable_provider_fallback"
    ENABLE_PROVIDER_HEALTH_CHECKS = "enable_provider_health_checks"
    ENABLE_PROVIDER_METRICS = "enable_provider_metrics"

    # Safety features
    ENABLE_HEALTH_CHECKS = "enable_health_checks"
    ENABLE_METRICS_COLLECTION = "enable_metrics_collection"
    ENABLE_ERROR_RECOVERY = "enable_error_recovery"


class FeatureFlagManager:
    """
    Manager for feature flags with environment and configuration support.
    
    This manager allows for dynamic feature flag management with support for
    environment variables, configuration files, and runtime updates.
    """
    
    def __init__(
        self,
        config_file: Optional[str] = None,
        env_prefix: str = "EXECUTION_",
        default_flags: Optional[Dict[str, bool]] = None
    ):
        """
        Initialize the feature flag manager.
        
        Args:
            config_file: Path to feature flag configuration file
            env_prefix: Prefix for environment variable flags
            default_flags: Default flag values
        """
        self.config_file = config_file
        self.env_prefix = env_prefix
        self.logger = StructuredLogger("feature_flags")
        
        # Flag storage
        self.flags: Dict[str, bool] = {}
        self.flag_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Default flag values (unified system approach)
        self.default_flags = default_flags or {
            # Core unified features (always enabled)
            FeatureFlag.USE_UNIFIED_EXECUTION: True,
            FeatureFlag.USE_UNIFIED_LLM_PROVIDER: True,
            FeatureFlag.USE_BROWSER_MANAGER: True,

            # Workflow features (can be enabled)
            FeatureFlag.USE_ENHANCED_WORKFLOW: True,
            FeatureFlag.USE_PARALLEL_EXECUTION: False,
            FeatureFlag.USE_TASK_SCHEDULING: False,

            # Infrastructure features
            FeatureFlag.USE_BROWSER_POOLING: False,
            FeatureFlag.USE_CONVERSATION_MANAGER: True,
            FeatureFlag.USE_ADVANCED_LOGGING: True,

            # Provider features
            FeatureFlag.ENABLE_PROVIDER_FALLBACK: True,
            FeatureFlag.ENABLE_PROVIDER_HEALTH_CHECKS: True,
            FeatureFlag.ENABLE_PROVIDER_METRICS: True,

            # Safety features (always enabled)
            FeatureFlag.ENABLE_HEALTH_CHECKS: True,
            FeatureFlag.ENABLE_METRICS_COLLECTION: True,
            FeatureFlag.ENABLE_ERROR_RECOVERY: True,
        }
        
        # Load flags
        self._load_flags()
        
        self.logger.info(
            "Feature flag manager initialized",
            config_file=config_file,
            env_prefix=env_prefix,
            total_flags=len(self.flags),
            enabled_flags=sum(1 for v in self.flags.values() if v)
        )
    
    def is_enabled(self, flag: FeatureFlag) -> bool:
        """
        Check if a feature flag is enabled.
        
        Args:
            flag: Feature flag to check
            
        Returns:
            True if flag is enabled, False otherwise
        """
        return self.flags.get(flag.value, self.default_flags.get(flag.value, False))
    
    def enable_flag(self, flag: FeatureFlag, reason: str = "Manual enable") -> None:
        """
        Enable a feature flag.
        
        Args:
            flag: Feature flag to enable
            reason: Reason for enabling the flag
        """
        old_value = self.flags.get(flag.value, False)
        self.flags[flag.value] = True
        
        # Update metadata
        self.flag_metadata[flag.value] = {
            "enabled_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "previous_value": old_value
        }
        
        self.logger.info(
            "Feature flag enabled",
            flag=flag.value,
            reason=reason,
            previous_value=old_value
        )
        
        # Save to file if configured
        self._save_flags()
    
    def disable_flag(self, flag: FeatureFlag, reason: str = "Manual disable") -> None:
        """
        Disable a feature flag.
        
        Args:
            flag: Feature flag to disable
            reason: Reason for disabling the flag
        """
        old_value = self.flags.get(flag.value, True)
        self.flags[flag.value] = False
        
        # Update metadata
        self.flag_metadata[flag.value] = {
            "disabled_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "previous_value": old_value
        }
        
        self.logger.info(
            "Feature flag disabled",
            flag=flag.value,
            reason=reason,
            previous_value=old_value
        )
        
        # Save to file if configured
        self._save_flags()
    
    def get_all_flags(self) -> Dict[str, bool]:
        """Get all feature flags and their current values."""
        return self.flags.copy()
    
    def get_enabled_flags(self) -> List[str]:
        """Get list of enabled feature flags."""
        return [flag for flag, enabled in self.flags.items() if enabled]
    
    def get_flag_metadata(self, flag: FeatureFlag) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific flag."""
        return self.flag_metadata.get(flag.value)
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Get the current migration status based on feature flags."""
        core_flags = [
            FeatureFlag.USE_NEW_EXECUTION_LAYER,
            FeatureFlag.USE_NEW_BROWSER_MANAGER,
            FeatureFlag.USE_NEW_LLM_PROVIDER
        ]
        
        workflow_flags = [
            FeatureFlag.USE_ENHANCED_WORKFLOW,
            FeatureFlag.USE_PARALLEL_EXECUTION,
            FeatureFlag.USE_TASK_SCHEDULING
        ]
        
        adapter_flags = [
            FeatureFlag.USE_BROWSER_USE_ADAPTER,
            FeatureFlag.USE_GEMINI_ADAPTER,
            FeatureFlag.USE_OPENAI_ADAPTER
        ]
        
        core_enabled = sum(1 for flag in core_flags if self.is_enabled(flag))
        workflow_enabled = sum(1 for flag in workflow_flags if self.is_enabled(flag))
        adapter_enabled = sum(1 for flag in adapter_flags if self.is_enabled(flag))
        
        total_flags = len(self.flags)
        enabled_flags = sum(1 for v in self.flags.values() if v)
        
        return {
            "migration_progress": enabled_flags / total_flags if total_flags > 0 else 0,
            "core_migration": core_enabled / len(core_flags),
            "workflow_migration": workflow_enabled / len(workflow_flags),
            "adapter_migration": adapter_enabled / len(adapter_flags),
            "total_flags": total_flags,
            "enabled_flags": enabled_flags,
            "fallback_enabled": self.is_enabled(FeatureFlag.FALLBACK_TO_LEGACY),
            "health_checks_enabled": self.is_enabled(FeatureFlag.ENABLE_HEALTH_CHECKS)
        }
    
    def enable_migration_phase(self, phase: int) -> None:
        """
        Enable flags for a specific migration phase.
        
        Args:
            phase: Migration phase (1-4)
        """
        if phase == 1:
            # Phase 1: Enable adapters and safety features
            flags_to_enable = [
                FeatureFlag.USE_BROWSER_USE_ADAPTER,
                FeatureFlag.USE_GEMINI_ADAPTER,
                FeatureFlag.USE_OPENAI_ADAPTER,
                FeatureFlag.USE_ADVANCED_LOGGING,
                FeatureFlag.ENABLE_HEALTH_CHECKS,
                FeatureFlag.ENABLE_METRICS_COLLECTION,
                FeatureFlag.FALLBACK_TO_LEGACY
            ]
            
        elif phase == 2:
            # Phase 2: Enable core execution components
            flags_to_enable = [
                FeatureFlag.USE_NEW_LLM_PROVIDER,
                FeatureFlag.USE_NEW_BROWSER_MANAGER,
                FeatureFlag.USE_CONVERSATION_MANAGER
            ]
            
        elif phase == 3:
            # Phase 3: Enable new execution layer
            flags_to_enable = [
                FeatureFlag.USE_NEW_EXECUTION_LAYER,
                FeatureFlag.USE_ENHANCED_WORKFLOW
            ]
            
        elif phase == 4:
            # Phase 4: Enable advanced features
            flags_to_enable = [
                FeatureFlag.USE_PARALLEL_EXECUTION,
                FeatureFlag.USE_TASK_SCHEDULING,
                FeatureFlag.USE_BROWSER_POOLING
            ]
            
        else:
            raise ValueError(f"Invalid migration phase: {phase}")
        
        for flag in flags_to_enable:
            self.enable_flag(flag, f"Migration phase {phase}")
        
        self.logger.info(
            "Migration phase enabled",
            phase=phase,
            flags_enabled=len(flags_to_enable)
        )
    
    def _load_flags(self) -> None:
        """Load flags from environment variables and configuration file."""
        # Start with defaults
        self.flags = self.default_flags.copy()
        
        # Load from configuration file
        if self.config_file and os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    file_flags = json.load(f)
                    self.flags.update(file_flags.get("flags", {}))
                    self.flag_metadata.update(file_flags.get("metadata", {}))
                    
                self.logger.info(
                    "Loaded flags from configuration file",
                    config_file=self.config_file,
                    flags_loaded=len(file_flags.get("flags", {}))
                )
            except Exception as e:
                self.logger.warning(
                    "Failed to load flags from configuration file",
                    config_file=self.config_file,
                    error=str(e)
                )
        
        # Override with environment variables
        for flag in FeatureFlag:
            env_var = f"{self.env_prefix}{flag.value.upper()}"
            env_value = os.environ.get(env_var)
            
            if env_value is not None:
                # Convert string to boolean
                bool_value = env_value.lower() in ('true', '1', 'yes', 'on', 'enabled')
                self.flags[flag.value] = bool_value
                
                self.logger.debug(
                    "Flag overridden by environment variable",
                    flag=flag.value,
                    env_var=env_var,
                    value=bool_value
                )
    
    def _save_flags(self) -> None:
        """Save flags to configuration file."""
        if not self.config_file:
            return
        
        try:
            config_data = {
                "flags": self.flags,
                "metadata": self.flag_metadata,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
                
            self.logger.debug(
                "Flags saved to configuration file",
                config_file=self.config_file
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to save flags to configuration file",
                config_file=self.config_file,
                error=str(e)
            )


# Global feature flag manager
_global_manager: Optional[FeatureFlagManager] = None


def get_feature_flag_manager(
    config_file: Optional[str] = None,
    env_prefix: str = "EXECUTION_"
) -> FeatureFlagManager:
    """
    Get the global feature flag manager instance.
    
    Args:
        config_file: Path to configuration file (only used on first call)
        env_prefix: Environment variable prefix (only used on first call)
        
    Returns:
        FeatureFlagManager instance
    """
    global _global_manager
    
    if _global_manager is None:
        _global_manager = FeatureFlagManager(config_file, env_prefix)
    
    return _global_manager


def is_feature_enabled(flag: FeatureFlag) -> bool:
    """
    Convenience function to check if a feature flag is enabled.
    
    Args:
        flag: Feature flag to check
        
    Returns:
        True if flag is enabled, False otherwise
    """
    manager = get_feature_flag_manager()
    return manager.is_enabled(flag)
