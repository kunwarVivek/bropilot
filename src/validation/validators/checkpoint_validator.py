"""
Checkpoint Validator

Creates and validates execution checkpoints for rollback and recovery.
"""

import json
import hashlib
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from pathlib import Path

from .base_validator import BaseValidator
from ..core.validation_config import ValidationConfig
from ..core.validation_result import ValidationSeverity
from ..core.evidence_collector import EvidenceCollector


class CheckpointValidator(BaseValidator):
    """Creates and validates execution checkpoints."""
    
    def __init__(self, config: ValidationConfig):
        super().__init__(config)
        self.checkpoints: Dict[str, Dict[str, Any]] = {}
        self.checkpoint_dir = Path("checkpoints")
        self.checkpoint_dir.mkdir(exist_ok=True)
    
    async def validate(self, context: Dict[str, Any], 
                      evidence_collector: Optional[EvidenceCollector] = None) -> None:
        """Validate checkpoint operations."""
        checkpoint_action = context.get("checkpoint_action", "create")
        
        if checkpoint_action == "create":
            await self._create_checkpoint(context, evidence_collector)
        elif checkpoint_action == "validate":
            await self._validate_checkpoint(context, evidence_collector)
        elif checkpoint_action == "restore":
            await self._validate_restore(context, evidence_collector)
        elif checkpoint_action == "compare":
            await self._compare_checkpoints(context, evidence_collector)
        else:
            self.add_warning(
                f"Unknown checkpoint action: {checkpoint_action}",
                "unknown_action",
                {"action": checkpoint_action},
                "Use 'create', 'validate', 'restore', or 'compare'"
            )
    
    async def _create_checkpoint(self, context: Dict[str, Any], 
                               evidence_collector: Optional[EvidenceCollector]) -> None:
        """Create a new checkpoint."""
        checkpoint_id = context.get("checkpoint_id")
        if not checkpoint_id:
            checkpoint_id = f"checkpoint_{int(datetime.now().timestamp())}"
        
        # Gather checkpoint data
        checkpoint_data = await self._gather_checkpoint_data(context)
        
        # Validate checkpoint data
        if not self._validate_checkpoint_data(checkpoint_data):
            return
        
        # Create checkpoint
        checkpoint = {
            "id": checkpoint_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": checkpoint_data,
            "metadata": context.get("checkpoint_metadata", {}),
            "hash": self._calculate_checkpoint_hash(checkpoint_data)
        }
        
        # Store checkpoint
        await self._store_checkpoint(checkpoint, evidence_collector)
        
        # Register checkpoint
        self.checkpoints[checkpoint_id] = checkpoint
        
        self.add_info(
            f"Checkpoint created: {checkpoint_id}",
            "checkpoint_created",
            {
                "checkpoint_id": checkpoint_id,
                "data_size": len(str(checkpoint_data)),
                "hash": checkpoint["hash"][:8]
            }
        )
    
    async def _gather_checkpoint_data(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Gather data for checkpoint creation."""
        checkpoint_data = {}
        
        # System state
        system_state = context.get("system_state", {})
        if system_state:
            checkpoint_data["system_state"] = system_state
        
        # Browser state
        browser_state = context.get("browser_state", {})
        if browser_state:
            checkpoint_data["browser_state"] = {
                "url": browser_state.get("url"),
                "title": browser_state.get("title"),
                "cookies": browser_state.get("cookies", []),
                "local_storage": browser_state.get("local_storage", {}),
                "session_storage": browser_state.get("session_storage", {})
            }
        
        # Task state
        task_state = context.get("task_state", {})
        if task_state:
            checkpoint_data["task_state"] = task_state
        
        # Execution state
        execution_state = context.get("execution_state", {})
        if execution_state:
            checkpoint_data["execution_state"] = execution_state
        
        # Variables and data
        variables = context.get("variables", {})
        if variables:
            checkpoint_data["variables"] = variables
        
        # Custom data
        custom_data = context.get("custom_checkpoint_data", {})
        if custom_data:
            checkpoint_data["custom"] = custom_data
        
        return checkpoint_data
    
    def _validate_checkpoint_data(self, checkpoint_data: Dict[str, Any]) -> bool:
        """Validate checkpoint data before creation."""
        if not checkpoint_data:
            self.add_error(
                "Checkpoint data is empty",
                "empty_checkpoint_data",
                {},
                "Ensure checkpoint contains meaningful state data"
            )
            return False
        
        # Check data size
        data_size = len(json.dumps(checkpoint_data, default=str))
        max_size = 10 * 1024 * 1024  # 10MB limit
        
        if data_size > max_size:
            self.add_error(
                f"Checkpoint data too large: {data_size} bytes > {max_size} bytes",
                "checkpoint_too_large",
                {"data_size": data_size, "max_size": max_size},
                "Reduce checkpoint data size or implement data compression"
            )
            return False
        
        # Validate data structure
        try:
            json.dumps(checkpoint_data, default=str)
        except (TypeError, ValueError) as e:
            self.add_error(
                f"Checkpoint data not serializable: {str(e)}",
                "checkpoint_not_serializable",
                {"error": str(e)},
                "Ensure all checkpoint data is JSON serializable"
            )
            return False
        
        return True
    
    async def _store_checkpoint(self, checkpoint: Dict[str, Any], 
                              evidence_collector: Optional[EvidenceCollector]) -> None:
        """Store checkpoint to file."""
        checkpoint_id = checkpoint["id"]
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        
        try:
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, indent=2, default=str)
            
            # Collect evidence
            if evidence_collector:
                await self.collect_evidence(
                    evidence_collector,
                    "checkpoint_storage",
                    {
                        "checkpoint_id": checkpoint_id,
                        "file_path": str(checkpoint_file),
                        "file_size": checkpoint_file.stat().st_size,
                        "timestamp": checkpoint["timestamp"]
                    },
                    f"checkpoint_storage_{checkpoint_id}.json"
                )
            
        except Exception as e:
            self.add_error(
                f"Failed to store checkpoint {checkpoint_id}: {str(e)}",
                "checkpoint_storage_failed",
                {"checkpoint_id": checkpoint_id, "error": str(e)},
                "Check file system permissions and disk space"
            )
    
    def _calculate_checkpoint_hash(self, data: Dict[str, Any]) -> str:
        """Calculate hash for checkpoint data integrity."""
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    async def _validate_checkpoint(self, context: Dict[str, Any], 
                                 evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate an existing checkpoint."""
        checkpoint_id = context.get("checkpoint_id")
        if not checkpoint_id:
            self.add_error(
                "No checkpoint ID provided for validation",
                "missing_checkpoint_id",
                {},
                "Specify checkpoint_id in context"
            )
            return
        
        # Load checkpoint
        checkpoint = await self._load_checkpoint(checkpoint_id)
        if not checkpoint:
            return
        
        # Validate checkpoint integrity
        await self._validate_checkpoint_integrity(checkpoint, evidence_collector)
        
        # Validate checkpoint age
        await self._validate_checkpoint_age(checkpoint, evidence_collector)
        
        # Validate checkpoint completeness
        await self._validate_checkpoint_completeness(checkpoint, evidence_collector)
    
    async def _load_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Load checkpoint from storage."""
        # Check memory first
        if checkpoint_id in self.checkpoints:
            return self.checkpoints[checkpoint_id]
        
        # Load from file
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        
        if not checkpoint_file.exists():
            self.add_error(
                f"Checkpoint file not found: {checkpoint_id}",
                "checkpoint_not_found",
                {"checkpoint_id": checkpoint_id, "file_path": str(checkpoint_file)},
                "Ensure checkpoint was created and file exists"
            )
            return None
        
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)
            
            # Cache in memory
            self.checkpoints[checkpoint_id] = checkpoint
            
            return checkpoint
            
        except Exception as e:
            self.add_error(
                f"Failed to load checkpoint {checkpoint_id}: {str(e)}",
                "checkpoint_load_failed",
                {"checkpoint_id": checkpoint_id, "error": str(e)},
                "Check file integrity and format"
            )
            return None
    
    async def _validate_checkpoint_integrity(self, checkpoint: Dict[str, Any], 
                                           evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate checkpoint data integrity."""
        checkpoint_id = checkpoint["id"]
        stored_hash = checkpoint.get("hash")
        
        if not stored_hash:
            self.add_warning(
                f"Checkpoint {checkpoint_id} has no integrity hash",
                "missing_integrity_hash",
                {"checkpoint_id": checkpoint_id},
                "Consider adding integrity checks to checkpoints"
            )
            return
        
        # Recalculate hash
        current_hash = self._calculate_checkpoint_hash(checkpoint["data"])
        
        if current_hash != stored_hash:
            self.add_error(
                f"Checkpoint {checkpoint_id} integrity check failed",
                "integrity_check_failed",
                {
                    "checkpoint_id": checkpoint_id,
                    "stored_hash": stored_hash[:8],
                    "current_hash": current_hash[:8]
                },
                "Checkpoint data may be corrupted"
            )
        else:
            self.add_info(
                f"Checkpoint {checkpoint_id} integrity verified",
                "integrity_verified",
                {"checkpoint_id": checkpoint_id, "hash": current_hash[:8]}
            )
    
    async def _validate_checkpoint_age(self, checkpoint: Dict[str, Any], 
                                     evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate checkpoint age and freshness."""
        checkpoint_id = checkpoint["id"]
        timestamp_str = checkpoint.get("timestamp")
        
        if not timestamp_str:
            self.add_warning(
                f"Checkpoint {checkpoint_id} has no timestamp",
                "missing_timestamp",
                {"checkpoint_id": checkpoint_id},
                "Add timestamps to checkpoints for age validation"
            )
            return
        
        try:
            checkpoint_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            current_time = datetime.now(timezone.utc)
            age_seconds = (current_time - checkpoint_time).total_seconds()
            age_hours = age_seconds / 3600
            
            # Validate age thresholds
            if age_hours > 24:
                self.add_warning(
                    f"Checkpoint {checkpoint_id} is old: {age_hours:.1f} hours",
                    "old_checkpoint",
                    {
                        "checkpoint_id": checkpoint_id,
                        "age_hours": age_hours,
                        "timestamp": timestamp_str
                    },
                    "Consider creating a fresh checkpoint"
                )
            elif age_hours > 168:  # 1 week
                self.add_error(
                    f"Checkpoint {checkpoint_id} is very old: {age_hours:.1f} hours",
                    "very_old_checkpoint",
                    {
                        "checkpoint_id": checkpoint_id,
                        "age_hours": age_hours,
                        "timestamp": timestamp_str
                    },
                    "Checkpoint may be stale and unreliable"
                )
            else:
                self.add_info(
                    f"Checkpoint {checkpoint_id} age acceptable: {age_hours:.1f} hours",
                    "checkpoint_age_ok",
                    {"checkpoint_id": checkpoint_id, "age_hours": age_hours}
                )
                
        except ValueError as e:
            self.add_error(
                f"Invalid timestamp format in checkpoint {checkpoint_id}: {str(e)}",
                "invalid_timestamp",
                {"checkpoint_id": checkpoint_id, "timestamp": timestamp_str},
                "Use ISO format timestamps in checkpoints"
            )
    
    async def _validate_checkpoint_completeness(self, checkpoint: Dict[str, Any], 
                                              evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate checkpoint data completeness."""
        checkpoint_id = checkpoint["id"]
        data = checkpoint.get("data", {})
        
        # Check for essential data sections
        essential_sections = ["system_state", "task_state", "execution_state"]
        missing_sections = [section for section in essential_sections if section not in data]
        
        if missing_sections:
            self.add_warning(
                f"Checkpoint {checkpoint_id} missing sections: {', '.join(missing_sections)}",
                "incomplete_checkpoint",
                {
                    "checkpoint_id": checkpoint_id,
                    "missing_sections": missing_sections,
                    "available_sections": list(data.keys())
                },
                "Include all essential state sections in checkpoints"
            )
        
        # Check data depth
        empty_sections = [
            section for section, content in data.items() 
            if not content or (isinstance(content, dict) and not content)
        ]
        
        if empty_sections:
            self.add_info(
                f"Checkpoint {checkpoint_id} has empty sections: {', '.join(empty_sections)}",
                "empty_sections",
                {"checkpoint_id": checkpoint_id, "empty_sections": empty_sections}
            )
    
    async def _validate_restore(self, context: Dict[str, Any], 
                              evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate checkpoint restore operation."""
        checkpoint_id = context.get("checkpoint_id")
        restore_result = context.get("restore_result", {})
        
        if not checkpoint_id:
            self.add_error(
                "No checkpoint ID provided for restore validation",
                "missing_restore_checkpoint_id",
                {},
                "Specify checkpoint_id for restore validation"
            )
            return
        
        # Load original checkpoint
        checkpoint = await self._load_checkpoint(checkpoint_id)
        if not checkpoint:
            return
        
        # Validate restore success
        restore_status = restore_result.get("status", "unknown")
        
        if restore_status == "success":
            self.add_info(
                f"Checkpoint {checkpoint_id} restored successfully",
                "restore_success",
                {"checkpoint_id": checkpoint_id}
            )
            
            # Validate restored state
            await self._validate_restored_state(checkpoint, restore_result, evidence_collector)
            
        elif restore_status == "failed":
            error_message = restore_result.get("error", "Unknown error")
            self.add_error(
                f"Checkpoint {checkpoint_id} restore failed: {error_message}",
                "restore_failed",
                {
                    "checkpoint_id": checkpoint_id,
                    "error": error_message,
                    "restore_result": restore_result
                },
                "Check restore logic and checkpoint compatibility"
            )
        else:
            self.add_warning(
                f"Unknown restore status for checkpoint {checkpoint_id}: {restore_status}",
                "unknown_restore_status",
                {"checkpoint_id": checkpoint_id, "status": restore_status},
                "Ensure restore operation reports proper status"
            )
    
    async def _validate_restored_state(self, checkpoint: Dict[str, Any], 
                                     restore_result: Dict[str, Any],
                                     evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate that restored state matches checkpoint."""
        checkpoint_id = checkpoint["id"]
        original_data = checkpoint.get("data", {})
        restored_data = restore_result.get("restored_state", {})
        
        # Compare key sections
        for section_name, original_section in original_data.items():
            restored_section = restored_data.get(section_name, {})
            
            if not restored_section:
                self.add_warning(
                    f"Section '{section_name}' not restored from checkpoint {checkpoint_id}",
                    "section_not_restored",
                    {"checkpoint_id": checkpoint_id, "section": section_name},
                    f"Ensure restore logic handles '{section_name}' section"
                )
                continue
            
            # Simple comparison (can be enhanced)
            if original_section != restored_section:
                self.add_warning(
                    f"Section '{section_name}' differs after restore from checkpoint {checkpoint_id}",
                    "restore_state_mismatch",
                    {
                        "checkpoint_id": checkpoint_id,
                        "section": section_name,
                        "original_keys": list(original_section.keys()) if isinstance(original_section, dict) else None,
                        "restored_keys": list(restored_section.keys()) if isinstance(restored_section, dict) else None
                    },
                    "Review restore logic for state consistency"
                )
    
    async def _compare_checkpoints(self, context: Dict[str, Any], 
                                 evidence_collector: Optional[EvidenceCollector]) -> None:
        """Compare two checkpoints."""
        checkpoint_id_1 = context.get("checkpoint_id_1")
        checkpoint_id_2 = context.get("checkpoint_id_2")
        
        if not checkpoint_id_1 or not checkpoint_id_2:
            self.add_error(
                "Two checkpoint IDs required for comparison",
                "missing_comparison_checkpoints",
                {"checkpoint_id_1": checkpoint_id_1, "checkpoint_id_2": checkpoint_id_2},
                "Provide both checkpoint_id_1 and checkpoint_id_2"
            )
            return
        
        # Load checkpoints
        checkpoint_1 = await self._load_checkpoint(checkpoint_id_1)
        checkpoint_2 = await self._load_checkpoint(checkpoint_id_2)
        
        if not checkpoint_1 or not checkpoint_2:
            return
        
        # Compare checkpoints
        comparison_result = self._compare_checkpoint_data(
            checkpoint_1.get("data", {}),
            checkpoint_2.get("data", {})
        )
        
        # Report comparison results
        if comparison_result["identical"]:
            self.add_info(
                f"Checkpoints {checkpoint_id_1} and {checkpoint_id_2} are identical",
                "checkpoints_identical",
                {"checkpoint_id_1": checkpoint_id_1, "checkpoint_id_2": checkpoint_id_2}
            )
        else:
            self.add_info(
                f"Checkpoints {checkpoint_id_1} and {checkpoint_id_2} differ",
                "checkpoints_different",
                {
                    "checkpoint_id_1": checkpoint_id_1,
                    "checkpoint_id_2": checkpoint_id_2,
                    "differences": comparison_result["differences"]
                }
            )
        
        # Collect comparison evidence
        if evidence_collector:
            await self.collect_evidence(
                evidence_collector,
                "checkpoint_comparison",
                {
                    "checkpoint_id_1": checkpoint_id_1,
                    "checkpoint_id_2": checkpoint_id_2,
                    "comparison_result": comparison_result,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                f"checkpoint_comparison_{checkpoint_id_1}_{checkpoint_id_2}.json"
            )
    
    def _compare_checkpoint_data(self, data_1: Dict[str, Any], 
                               data_2: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two checkpoint data structures."""
        differences = []
        
        # Check all keys from both datasets
        all_keys = set(data_1.keys()) | set(data_2.keys())
        
        for key in all_keys:
            if key not in data_1:
                differences.append(f"Key '{key}' only in checkpoint 2")
            elif key not in data_2:
                differences.append(f"Key '{key}' only in checkpoint 1")
            elif data_1[key] != data_2[key]:
                differences.append(f"Key '{key}' values differ")
        
        return {
            "identical": len(differences) == 0,
            "differences": differences,
            "total_differences": len(differences)
        }
    
    def get_checkpoint_list(self) -> List[str]:
        """Get list of available checkpoints."""
        return list(self.checkpoints.keys())
    
    def cleanup_old_checkpoints(self, max_age_hours: int = 168) -> None:
        """Clean up old checkpoint files."""
        try:
            current_time = datetime.now(timezone.utc)
            
            for checkpoint_file in self.checkpoint_dir.glob("*.json"):
                try:
                    with open(checkpoint_file, 'r') as f:
                        checkpoint = json.load(f)
                    
                    timestamp_str = checkpoint.get("timestamp")
                    if timestamp_str:
                        checkpoint_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        age_hours = (current_time - checkpoint_time).total_seconds() / 3600
                        
                        if age_hours > max_age_hours:
                            checkpoint_file.unlink()
                            checkpoint_id = checkpoint.get("id")
                            if checkpoint_id in self.checkpoints:
                                del self.checkpoints[checkpoint_id]
                            
                            self.logger.info("Cleaned up old checkpoint", 
                                           checkpoint_id=checkpoint_id, 
                                           age_hours=age_hours)
                
                except Exception as e:
                    self.logger.warning("Failed to process checkpoint file", 
                                      file=str(checkpoint_file), error=str(e))
                    
        except Exception as e:
            self.logger.error("Failed to cleanup old checkpoints", error=str(e))
    
    def get_validation_rules(self) -> List[str]:
        """Get list of validation rules this validator implements."""
        return [
            "checkpoint_created",
            "empty_checkpoint_data",
            "checkpoint_too_large",
            "checkpoint_not_serializable",
            "checkpoint_storage_failed",
            "missing_checkpoint_id",
            "checkpoint_not_found",
            "checkpoint_load_failed",
            "missing_integrity_hash",
            "integrity_check_failed",
            "integrity_verified",
            "missing_timestamp",
            "old_checkpoint",
            "very_old_checkpoint",
            "checkpoint_age_ok",
            "invalid_timestamp",
            "incomplete_checkpoint",
            "empty_sections",
            "restore_success",
            "restore_failed",
            "unknown_restore_status",
            "section_not_restored",
            "restore_state_mismatch",
            "checkpoints_identical",
            "checkpoints_different"
        ]
