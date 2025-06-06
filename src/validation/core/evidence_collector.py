"""
Evidence Collection System

Collects and manages validation evidence during task execution.
"""

import os
import json
import time
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from pathlib import Path
import base64
import hashlib

from playwright.async_api import Page, Browser
from src.infrastructure.logging.logger import StructuredLogger


class EvidenceCollector:
    """Collects various types of evidence during task execution."""
    
    def __init__(self, evidence_dir: str = "evidence", task_id: str = None):
        self.evidence_dir = Path(evidence_dir)
        self.task_id = task_id or f"task_{int(time.time())}"
        self.task_evidence_dir = self.evidence_dir / self.task_id
        self.logger = StructuredLogger("evidence_collector")
        
        # Create evidence directory
        self.task_evidence_dir.mkdir(parents=True, exist_ok=True)
        
        # Evidence storage
        self.evidence_registry: Dict[str, Dict[str, Any]] = {}
        self.screenshot_counter = 0
        self.network_logs: List[Dict[str, Any]] = []
        self.execution_logs: List[Dict[str, Any]] = []
        self.performance_metrics: List[Dict[str, Any]] = []
        
        self.logger.info("Evidence collector initialized", 
                        task_id=task_id, evidence_dir=str(self.task_evidence_dir))
    
    async def collect_screenshot(self, page: Page, name: str = None, 
                                full_page: bool = True) -> str:
        """Collect screenshot evidence."""
        try:
            self.screenshot_counter += 1
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = name or f"screenshot_{self.screenshot_counter:03d}_{timestamp}"
            
            if not filename.endswith('.png'):
                filename += '.png'
            
            screenshot_path = self.task_evidence_dir / "screenshots" / filename
            screenshot_path.parent.mkdir(exist_ok=True)
            
            # Take screenshot
            await page.screenshot(
                path=str(screenshot_path),
                full_page=full_page,
                type='png'
            )
            
            # Register evidence
            evidence_info = {
                "type": "screenshot",
                "path": str(screenshot_path),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "full_page": full_page,
                "page_url": page.url,
                "page_title": await page.title(),
                "viewport": await page.viewport_size(),
                "file_size": screenshot_path.stat().st_size
            }
            
            self.evidence_registry[f"screenshot_{self.screenshot_counter}"] = evidence_info
            
            self.logger.info("Screenshot collected", 
                           filename=filename, path=str(screenshot_path))
            
            return str(screenshot_path)
            
        except Exception as e:
            self.logger.error("Failed to collect screenshot", error=str(e))
            return ""
    
    async def collect_dom_snapshot(self, page: Page, name: str = None) -> str:
        """Collect DOM snapshot evidence."""
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = name or f"dom_snapshot_{timestamp}.html"
            
            if not filename.endswith('.html'):
                filename += '.html'
            
            dom_path = self.task_evidence_dir / "dom_snapshots" / filename
            dom_path.parent.mkdir(exist_ok=True)
            
            # Get page content
            content = await page.content()
            
            # Save DOM snapshot
            with open(dom_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Register evidence
            evidence_info = {
                "type": "dom_snapshot",
                "path": str(dom_path),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "page_url": page.url,
                "page_title": await page.title(),
                "content_length": len(content),
                "file_size": dom_path.stat().st_size
            }
            
            self.evidence_registry[f"dom_{timestamp}"] = evidence_info
            
            self.logger.info("DOM snapshot collected", 
                           filename=filename, path=str(dom_path))
            
            return str(dom_path)
            
        except Exception as e:
            self.logger.error("Failed to collect DOM snapshot", error=str(e))
            return ""
    
    def collect_network_log(self, request_data: Dict[str, Any]) -> None:
        """Collect network request/response evidence."""
        try:
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "url": request_data.get("url"),
                "method": request_data.get("method"),
                "status": request_data.get("status"),
                "headers": request_data.get("headers", {}),
                "response_time": request_data.get("response_time"),
                "size": request_data.get("size", 0)
            }
            
            self.network_logs.append(log_entry)
            
            # Save network logs periodically
            if len(self.network_logs) % 10 == 0:
                self._save_network_logs()
                
        except Exception as e:
            self.logger.error("Failed to collect network log", error=str(e))
    
    def collect_execution_log(self, step: str, action: str, result: Any, 
                            metadata: Dict[str, Any] = None) -> None:
        """Collect execution step evidence."""
        try:
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "step": step,
                "action": action,
                "result": str(result),
                "metadata": metadata or {},
                "success": metadata.get("success", True) if metadata else True
            }
            
            self.execution_logs.append(log_entry)
            
        except Exception as e:
            self.logger.error("Failed to collect execution log", error=str(e))
    
    def collect_performance_metric(self, metric_name: str, value: Union[int, float], 
                                 unit: str = "", metadata: Dict[str, Any] = None) -> None:
        """Collect performance metrics evidence."""
        try:
            metric_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metric_name": metric_name,
                "value": value,
                "unit": unit,
                "metadata": metadata or {}
            }
            
            self.performance_metrics.append(metric_entry)
            
        except Exception as e:
            self.logger.error("Failed to collect performance metric", error=str(e))
    
    async def collect_video_recording(self, page: Page, duration: float = 30.0) -> str:
        """Collect video recording evidence (if supported)."""
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.webm"
            
            video_path = self.task_evidence_dir / "videos" / filename
            video_path.parent.mkdir(exist_ok=True)
            
            # Note: Video recording requires browser context setup
            # This is a placeholder for video recording functionality
            
            evidence_info = {
                "type": "video_recording",
                "path": str(video_path),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "duration": duration,
                "page_url": page.url
            }
            
            self.evidence_registry[f"video_{timestamp}"] = evidence_info
            
            return str(video_path)
            
        except Exception as e:
            self.logger.error("Failed to collect video recording", error=str(e))
            return ""
    
    def collect_custom_evidence(self, evidence_type: str, data: Any, 
                              filename: str = None) -> str:
        """Collect custom evidence data."""
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = filename or f"{evidence_type}_{timestamp}.json"
            
            evidence_path = self.task_evidence_dir / "custom" / filename
            evidence_path.parent.mkdir(exist_ok=True)
            
            # Save data as JSON
            with open(evidence_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            # Register evidence
            evidence_info = {
                "type": evidence_type,
                "path": str(evidence_path),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data_type": type(data).__name__,
                "file_size": evidence_path.stat().st_size
            }
            
            self.evidence_registry[f"{evidence_type}_{timestamp}"] = evidence_info
            
            return str(evidence_path)
            
        except Exception as e:
            self.logger.error("Failed to collect custom evidence", 
                            evidence_type=evidence_type, error=str(e))
            return ""
    
    def _save_network_logs(self) -> None:
        """Save network logs to file."""
        try:
            network_log_path = self.task_evidence_dir / "network_logs.json"
            with open(network_log_path, 'w', encoding='utf-8') as f:
                json.dump(self.network_logs, f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error("Failed to save network logs", error=str(e))
    
    def save_all_evidence(self) -> Dict[str, str]:
        """Save all collected evidence to files."""
        try:
            evidence_paths = {}
            
            # Save network logs
            if self.network_logs:
                network_log_path = self.task_evidence_dir / "network_logs.json"
                with open(network_log_path, 'w', encoding='utf-8') as f:
                    json.dump(self.network_logs, f, indent=2, default=str)
                evidence_paths["network_logs"] = str(network_log_path)
            
            # Save execution logs
            if self.execution_logs:
                execution_log_path = self.task_evidence_dir / "execution_logs.json"
                with open(execution_log_path, 'w', encoding='utf-8') as f:
                    json.dump(self.execution_logs, f, indent=2, default=str)
                evidence_paths["execution_logs"] = str(execution_log_path)
            
            # Save performance metrics
            if self.performance_metrics:
                metrics_path = self.task_evidence_dir / "performance_metrics.json"
                with open(metrics_path, 'w', encoding='utf-8') as f:
                    json.dump(self.performance_metrics, f, indent=2, default=str)
                evidence_paths["performance_metrics"] = str(metrics_path)
            
            # Save evidence registry
            registry_path = self.task_evidence_dir / "evidence_registry.json"
            with open(registry_path, 'w', encoding='utf-8') as f:
                json.dump(self.evidence_registry, f, indent=2, default=str)
            evidence_paths["evidence_registry"] = str(registry_path)
            
            self.logger.info("All evidence saved", 
                           evidence_count=len(self.evidence_registry),
                           evidence_dir=str(self.task_evidence_dir))
            
            return evidence_paths
            
        except Exception as e:
            self.logger.error("Failed to save evidence", error=str(e))
            return {}
    
    def get_evidence_summary(self) -> Dict[str, Any]:
        """Get summary of collected evidence."""
        return {
            "task_id": self.task_id,
            "evidence_dir": str(self.task_evidence_dir),
            "total_evidence_items": len(self.evidence_registry),
            "screenshots_count": self.screenshot_counter,
            "network_logs_count": len(self.network_logs),
            "execution_logs_count": len(self.execution_logs),
            "performance_metrics_count": len(self.performance_metrics),
            "evidence_types": list(set(
                item["type"] for item in self.evidence_registry.values()
            )),
            "total_size_bytes": sum(
                item.get("file_size", 0) for item in self.evidence_registry.values()
            )
        }
    
    def cleanup_old_evidence(self, max_age_days: int = 7) -> None:
        """Clean up old evidence files."""
        try:
            cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
            
            for evidence_item in self.evidence_registry.values():
                evidence_path = Path(evidence_item["path"])
                if evidence_path.exists():
                    if evidence_path.stat().st_mtime < cutoff_time:
                        evidence_path.unlink()
                        self.logger.info("Cleaned up old evidence", 
                                       path=str(evidence_path))
                        
        except Exception as e:
            self.logger.error("Failed to cleanup old evidence", error=str(e))
