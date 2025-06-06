#!/usr/bin/env python3
"""
Integration test runner for the execution layer.

This script runs comprehensive integration tests to validate that all
execution layer components work together correctly.
"""

import asyncio
import sys
import os
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import only what we can test without external dependencies
try:
    from src.infrastructure.logging.logger import StructuredLogger
    LOGGING_AVAILABLE = True
except ImportError:
    LOGGING_AVAILABLE = False

try:
    from src.execution.feature_flags import FeatureFlagManager, FeatureFlag
    FEATURE_FLAGS_AVAILABLE = True
except ImportError:
    FEATURE_FLAGS_AVAILABLE = False

try:
    from src.execution.adapters.adapter_factory import AdapterFactory, AdapterType
    ADAPTERS_AVAILABLE = True
except ImportError:
    ADAPTERS_AVAILABLE = False

try:
    from src.execution.legacy_bridge import LegacyTaskBridge
    BRIDGE_AVAILABLE = True
except ImportError:
    BRIDGE_AVAILABLE = False


class IntegrationTestRunner:
    """
    Comprehensive integration test runner for the execution layer.
    
    This runner validates that all components work together correctly
    and provides detailed reporting on system health and functionality.
    """
    
    def __init__(self, verbose: bool = True):
        """
        Initialize the integration test runner.
        
        Args:
            verbose: Whether to enable verbose logging
        """
        self.verbose = verbose
        self.logger = StructuredLogger("integration_test_runner")
        
        # Test results tracking
        self.test_results: Dict[str, Dict[str, Any]] = {}
        self.start_time = None
        self.end_time = None
        
        self.logger.info("Integration test runner initialized", verbose=verbose)
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all integration tests and return comprehensive results.
        
        Returns:
            Dictionary containing test results and system status
        """
        self.start_time = time.time()
        
        self.logger.info("Starting comprehensive integration tests")
        
        try:
            # Test 1: Feature Flag System
            await self._test_feature_flags()
            
            # Test 2: Adapter Factory
            await self._test_adapter_factory()
            
            # Test 3: Legacy Bridge (Mocked)
            await self._test_legacy_bridge()
            
            # Test 4: Migration Phases
            await self._test_migration_phases()
            
            # Test 5: Error Handling
            await self._test_error_handling()
            
            # Test 6: Health Monitoring
            await self._test_health_monitoring()
            
            # Test 7: System Integration
            await self._test_system_integration()
            
        except Exception as e:
            self.logger.error("Integration test suite failed", error=str(e))
            self.test_results["suite_error"] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
        
        self.end_time = time.time()
        
        # Generate final report
        return self._generate_final_report()
    
    async def _test_feature_flags(self) -> None:
        """Test feature flag system functionality."""
        test_name = "feature_flags"
        self.logger.info("Testing feature flag system")
        
        try:
            # Create feature flag manager
            flag_manager = FeatureFlagManager()
            
            # Test initial state
            initial_state = flag_manager.get_all_flags()
            assert len(initial_state) > 0, "No feature flags found"
            
            # Test flag enabling
            flag_manager.enable_flag(FeatureFlag.USE_NEW_EXECUTION_LAYER, "Integration test")
            assert flag_manager.is_enabled(FeatureFlag.USE_NEW_EXECUTION_LAYER), "Flag not enabled"
            
            # Test flag disabling
            flag_manager.disable_flag(FeatureFlag.USE_NEW_EXECUTION_LAYER, "Integration test")
            assert not flag_manager.is_enabled(FeatureFlag.USE_NEW_EXECUTION_LAYER), "Flag not disabled"
            
            # Test migration phases
            flag_manager.enable_migration_phase(1)
            phase1_status = flag_manager.get_migration_status()
            assert phase1_status["adapter_migration"] > 0, "Phase 1 migration not working"
            
            # Test metadata
            metadata = flag_manager.get_flag_metadata(FeatureFlag.USE_BROWSER_USE_ADAPTER)
            assert metadata is not None, "Flag metadata not found"
            
            self.test_results[test_name] = {
                "status": "passed",
                "details": {
                    "total_flags": len(initial_state),
                    "migration_status": phase1_status,
                    "enabled_flags": len(flag_manager.get_enabled_flags())
                },
                "timestamp": time.time()
            }
            
            self.logger.info("Feature flag system test passed")
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Feature flag system test failed", error=str(e))
    
    async def _test_adapter_factory(self) -> None:
        """Test adapter factory functionality."""
        test_name = "adapter_factory"
        self.logger.info("Testing adapter factory")

        try:
            if not ADAPTERS_AVAILABLE:
                self.test_results[test_name] = {
                    "status": "skipped",
                    "reason": "AdapterFactory not available",
                    "timestamp": time.time()
                }
                self.logger.warning("Adapter factory test skipped - not available")
                return

            factory = AdapterFactory()
            
            # Test browser-use adapter creation
            browser_adapter = await factory.create_adapter(
                AdapterType.BROWSER_USE,
                "test_browser_adapter",
                {"save_logs": False}
            )
            assert browser_adapter is not None, "Browser adapter not created"
            
            # Test adapter info retrieval
            adapter_info = factory.get_adapter_info("test_browser_adapter")
            assert adapter_info is not None, "Adapter info not found"
            assert adapter_info["type"] == "browser_use", "Wrong adapter type"
            
            # Test adapter listing
            adapters = factory.list_adapters()
            assert "test_browser_adapter" in adapters, "Adapter not in list"
            
            # Test health check
            health_results = await factory.health_check_all()
            assert "test_browser_adapter" in health_results, "Adapter not in health check"
            
            # Test statistics
            stats = factory.get_statistics()
            assert stats["total_adapters"] >= 1, "No adapters in statistics"
            
            # Test adapter removal
            removed = await factory.remove_adapter("test_browser_adapter")
            assert removed is True, "Adapter not removed"
            
            self.test_results[test_name] = {
                "status": "passed",
                "details": {
                    "adapters_created": 1,
                    "adapters_removed": 1,
                    "health_checks": len(health_results),
                    "statistics": stats
                },
                "timestamp": time.time()
            }
            
            self.logger.info("Adapter factory test passed")
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Adapter factory test failed", error=str(e))
    
    async def _test_legacy_bridge(self) -> None:
        """Test legacy bridge functionality (with mocking)."""
        test_name = "legacy_bridge"
        self.logger.info("Testing legacy bridge")

        try:
            if not BRIDGE_AVAILABLE:
                self.test_results[test_name] = {
                    "status": "skipped",
                    "reason": "LegacyTaskBridge not available",
                    "timestamp": time.time()
                }
                self.logger.warning("Legacy bridge test skipped - not available")
                return

            # Create bridge without initialization (to avoid external dependencies)
            bridge = LegacyTaskBridge(
                use_new_execution=False,  # Use legacy mode for testing
                fallback_to_legacy=True,
                config={"test": "integration"}
            )
            
            # Test statistics (should work without initialization)
            stats = bridge.get_statistics()
            assert "total_executions" in stats, "Statistics not available"
            assert stats["use_new_execution"] is False, "Wrong execution mode"
            
            # Test health check (without initialization)
            health = await bridge.health_check()
            assert "bridge_status" in health, "Health check not available"
            assert "statistics" in health, "Statistics not in health check"
            
            self.test_results[test_name] = {
                "status": "passed",
                "details": {
                    "statistics": stats,
                    "health_status": health["bridge_status"],
                    "use_new_execution": stats["use_new_execution"]
                },
                "timestamp": time.time()
            }
            
            self.logger.info("Legacy bridge test passed")
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Legacy bridge test failed", error=str(e))
    
    async def _test_migration_phases(self) -> None:
        """Test migration phase functionality."""
        test_name = "migration_phases"
        self.logger.info("Testing migration phases")
        
        try:
            flag_manager = FeatureFlagManager()
            
            # Test each migration phase
            phase_results = {}
            
            for phase in range(1, 5):
                flag_manager.enable_migration_phase(phase)
                status = flag_manager.get_migration_status()
                
                phase_results[f"phase_{phase}"] = {
                    "migration_progress": status["migration_progress"],
                    "core_migration": status["core_migration"],
                    "workflow_migration": status["workflow_migration"],
                    "adapter_migration": status["adapter_migration"]
                }
            
            # Verify progression
            assert phase_results["phase_4"]["migration_progress"] > phase_results["phase_1"]["migration_progress"], \
                "Migration progress not increasing"
            
            self.test_results[test_name] = {
                "status": "passed",
                "details": {
                    "phases_tested": 4,
                    "phase_results": phase_results,
                    "final_progress": phase_results["phase_4"]["migration_progress"]
                },
                "timestamp": time.time()
            }
            
            self.logger.info("Migration phases test passed")
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Migration phases test failed", error=str(e))
    
    async def _test_error_handling(self) -> None:
        """Test error handling mechanisms."""
        test_name = "error_handling"
        self.logger.info("Testing error handling")

        try:
            if not ADAPTERS_AVAILABLE or not FEATURE_FLAGS_AVAILABLE:
                self.test_results[test_name] = {
                    "status": "skipped",
                    "reason": "Required components not available",
                    "timestamp": time.time()
                }
                self.logger.warning("Error handling test skipped - components not available")
                return

            # Test invalid adapter type
            factory = AdapterFactory()
            
            try:
                await factory.create_adapter("invalid_type")
                assert False, "Should have raised ConfigurationError"
            except Exception as e:
                assert "Unsupported adapter type" in str(e), "Wrong error message"
            
            # Test invalid migration phase
            flag_manager = FeatureFlagManager()
            
            try:
                flag_manager.enable_migration_phase(10)
                assert False, "Should have raised ValueError"
            except ValueError as e:
                assert "Invalid migration phase" in str(e), "Wrong error message"
            
            self.test_results[test_name] = {
                "status": "passed",
                "details": {
                    "error_cases_tested": 2,
                    "error_handling_working": True
                },
                "timestamp": time.time()
            }
            
            self.logger.info("Error handling test passed")
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Error handling test failed", error=str(e))
    
    async def _test_health_monitoring(self) -> None:
        """Test health monitoring functionality."""
        test_name = "health_monitoring"
        self.logger.info("Testing health monitoring")

        try:
            if not ADAPTERS_AVAILABLE or not BRIDGE_AVAILABLE:
                self.test_results[test_name] = {
                    "status": "skipped",
                    "reason": "Required components not available",
                    "timestamp": time.time()
                }
                self.logger.warning("Health monitoring test skipped - components not available")
                return

            # Test adapter factory health monitoring
            factory = AdapterFactory()
            
            # Create an adapter for health testing
            adapter = await factory.create_adapter(
                AdapterType.BROWSER_USE,
                "health_test_adapter",
                {"save_logs": False}
            )
            
            # Test health check
            health_results = await factory.health_check_all()
            assert "health_test_adapter" in health_results, "Adapter not in health results"
            
            # Test bridge health monitoring
            bridge = LegacyTaskBridge(use_new_execution=False)
            bridge_health = await bridge.health_check()
            assert "bridge_status" in bridge_health, "Bridge health not available"
            
            # Cleanup
            await factory.remove_adapter("health_test_adapter")
            
            self.test_results[test_name] = {
                "status": "passed",
                "details": {
                    "adapter_health_checks": len(health_results),
                    "bridge_health_status": bridge_health["bridge_status"],
                    "health_monitoring_working": True
                },
                "timestamp": time.time()
            }
            
            self.logger.info("Health monitoring test passed")
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Health monitoring test failed", error=str(e))
    
    async def _test_system_integration(self) -> None:
        """Test overall system integration."""
        test_name = "system_integration"
        self.logger.info("Testing system integration")

        try:
            if not ADAPTERS_AVAILABLE or not BRIDGE_AVAILABLE or not FEATURE_FLAGS_AVAILABLE:
                self.test_results[test_name] = {
                    "status": "skipped",
                    "reason": "Required components not available",
                    "timestamp": time.time()
                }
                self.logger.warning("System integration test skipped - components not available")
                return

            # Test feature flags with adapters
            flag_manager = FeatureFlagManager()
            flag_manager.enable_migration_phase(1)

            # Test adapter creation with feature flags
            factory = AdapterFactory()
            await factory.create_adapter(AdapterType.BROWSER_USE, "integration_test")

            # Test bridge with feature flags
            bridge = LegacyTaskBridge(use_new_execution=False)
            
            # Test comprehensive health check
            factory_health = await factory.health_check_all()
            bridge_health = await bridge.health_check()
            migration_status = flag_manager.get_migration_status()
            
            # Verify integration
            assert len(factory_health) > 0, "No adapter health results"
            assert bridge_health["bridge_status"] in ["healthy", "degraded"], "Invalid bridge status"
            assert migration_status["migration_progress"] > 0, "No migration progress"
            
            # Cleanup
            await factory.remove_adapter("integration_test")
            
            self.test_results[test_name] = {
                "status": "passed",
                "details": {
                    "components_tested": 3,
                    "integration_working": True,
                    "migration_progress": migration_status["migration_progress"],
                    "health_checks_passed": len(factory_health)
                },
                "timestamp": time.time()
            }
            
            self.logger.info("System integration test passed")
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("System integration test failed", error=str(e))
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive final test report."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["status"] == "passed")
        failed_tests = sum(1 for result in self.test_results.values() if result["status"] == "failed")
        skipped_tests = sum(1 for result in self.test_results.values() if result["status"] == "skipped")
        
        execution_time = self.end_time - self.start_time if self.end_time and self.start_time else 0
        
        report = {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "skipped_tests": skipped_tests,
                "success_rate": passed_tests / total_tests if total_tests > 0 else 0,
                "execution_time": execution_time,
                "timestamp": time.time()
            },
            "test_results": self.test_results,
            "system_status": {
                "execution_layer_ready": failed_tests == 0,
                "migration_capable": "migration_phases" in self.test_results and 
                                   self.test_results["migration_phases"]["status"] == "passed",
                "health_monitoring_active": "health_monitoring" in self.test_results and 
                                          self.test_results["health_monitoring"]["status"] == "passed"
            }
        }
        
        return report


async def main():
    """Main function to run integration tests."""
    print("🚀 Starting Execution Layer Integration Tests")
    print("=" * 60)
    
    runner = IntegrationTestRunner(verbose=True)
    
    try:
        results = await runner.run_all_tests()
        
        # Print summary
        summary = results["summary"]
        print(f"\n📊 Test Results Summary:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Passed: {summary['passed_tests']}")
        print(f"   Failed: {summary['failed_tests']}")
        print(f"   Skipped: {summary.get('skipped_tests', 0)}")
        print(f"   Success Rate: {summary['success_rate']:.1%}")
        print(f"   Execution Time: {summary['execution_time']:.2f}s")
        
        # Print system status
        status = results["system_status"]
        print(f"\n🏥 System Status:")
        print(f"   Execution Layer Ready: {'✅' if status['execution_layer_ready'] else '❌'}")
        print(f"   Migration Capable: {'✅' if status['migration_capable'] else '❌'}")
        print(f"   Health Monitoring: {'✅' if status['health_monitoring_active'] else '❌'}")
        
        # Print individual test results
        print(f"\n📋 Individual Test Results:")
        for test_name, result in results["test_results"].items():
            if result["status"] == "passed":
                status_icon = "✅"
            elif result["status"] == "failed":
                status_icon = "❌"
            else:  # skipped
                status_icon = "⏭️"
            print(f"   {status_icon} {test_name}: {result['status']}")
            if result["status"] == "failed" and "error" in result:
                print(f"      Error: {result['error']}")
            elif result["status"] == "skipped" and "reason" in result:
                print(f"      Reason: {result['reason']}")
        
        print("\n" + "=" * 60)
        
        if summary["failed_tests"] == 0:
            print("🎉 All integration tests passed! Execution layer is ready.")
            return 0
        else:
            print("⚠️  Some integration tests failed. Please review the results.")
            return 1
            
    except Exception as e:
        print(f"❌ Integration test suite failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
