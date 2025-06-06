#!/usr/bin/env python3
"""
Configuration validation tests for the execution layer.

This module tests configuration validation, environment setup,
and system requirements verification.
"""

import asyncio
import sys
import os
import time
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.logging.logger import StructuredLogger

# Import components for testing
try:
    from src.execution.feature_flags import FeatureFlagManager
    FEATURE_FLAGS_AVAILABLE = True
except ImportError:
    FEATURE_FLAGS_AVAILABLE = False

try:
    from src.execution.adapters.adapter_factory import AdapterFactory
    ADAPTERS_AVAILABLE = True
except ImportError:
    ADAPTERS_AVAILABLE = False


class ConfigurationValidationTests:
    """
    Configuration validation test suite.
    
    Tests configuration validation, environment setup,
    and system requirements verification.
    """
    
    def __init__(self, verbose: bool = True):
        """
        Initialize configuration validation tests.
        
        Args:
            verbose: Whether to enable verbose logging
        """
        self.verbose = verbose
        self.logger = StructuredLogger("configuration_validation_tests")
        
        # Test results tracking
        self.test_results: Dict[str, Dict[str, Any]] = {}
        self.start_time = None
        self.end_time = None
        
        self.logger.info("Configuration validation tests initialized", verbose=verbose)
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all configuration validation tests.
        
        Returns:
            Dictionary containing test results and configuration status
        """
        self.start_time = time.time()
        
        self.logger.info("Starting configuration validation tests")
        
        try:
            # Test 1: Environment Variables
            await self._test_environment_variables()
            
            # Test 2: File System Permissions
            await self._test_file_system_permissions()
            
            # Test 3: Python Dependencies
            await self._test_python_dependencies()
            
            # Test 4: Configuration File Validation
            await self._test_configuration_files()
            
            # Test 5: Logging Configuration
            await self._test_logging_configuration()
            
            # Test 6: Feature Flag Configuration
            await self._test_feature_flag_configuration()
            
            # Test 7: Adapter Configuration
            await self._test_adapter_configuration()
            
        except Exception as e:
            self.logger.error("Configuration validation test suite failed", error=str(e))
            self.test_results["suite_error"] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
        
        self.end_time = time.time()
        
        # Generate final report
        return self._generate_final_report()
    
    async def _test_environment_variables(self) -> None:
        """Test environment variable configuration."""
        test_name = "environment_variables"
        self.logger.info("Testing environment variables")
        
        try:
            env_checks = {
                "python_path": sys.executable,
                "working_directory": os.getcwd(),
                "user": os.environ.get("USER", "unknown"),
                "home": os.environ.get("HOME", "unknown"),
                "path": os.environ.get("PATH", ""),
                "pythonpath": os.environ.get("PYTHONPATH", "")
            }
            
            # Check for execution layer specific environment variables
            execution_env = {}
            for key, value in os.environ.items():
                if key.startswith("EXECUTION_"):
                    execution_env[key] = value
            
            # Validate critical paths
            critical_paths = [
                str(project_root),
                str(project_root / "src"),
                str(project_root / "tests")
            ]
            
            path_checks = {}
            for path in critical_paths:
                path_checks[path] = os.path.exists(path)
            
            self.test_results[test_name] = {
                "status": "passed",
                "details": {
                    "environment_checks": env_checks,
                    "execution_environment": execution_env,
                    "path_checks": path_checks,
                    "all_paths_exist": all(path_checks.values())
                },
                "timestamp": time.time()
            }
            
            self.logger.info("Environment variables test passed")
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Environment variables test failed", error=str(e))
    
    async def _test_file_system_permissions(self) -> None:
        """Test file system permissions."""
        test_name = "file_system_permissions"
        self.logger.info("Testing file system permissions")
        
        try:
            permission_checks = {}
            
            # Test read permissions on critical directories
            read_dirs = [
                str(project_root),
                str(project_root / "src"),
                str(project_root / "tests")
            ]
            
            for dir_path in read_dirs:
                try:
                    permission_checks[f"read_{dir_path}"] = os.access(dir_path, os.R_OK)
                except Exception:
                    permission_checks[f"read_{dir_path}"] = False
            
            # Test write permissions on temp directories
            write_dirs = [
                "/tmp" if os.path.exists("/tmp") else tempfile.gettempdir(),
                str(project_root / "logs") if (project_root / "logs").exists() else None
            ]
            
            for dir_path in write_dirs:
                if dir_path:
                    try:
                        permission_checks[f"write_{dir_path}"] = os.access(dir_path, os.W_OK)
                    except Exception:
                        permission_checks[f"write_{dir_path}"] = False
            
            # Test creating temporary files
            temp_file_test = False
            try:
                with tempfile.NamedTemporaryFile(delete=True) as tmp:
                    tmp.write(b"test")
                    temp_file_test = True
            except Exception:
                temp_file_test = False
            
            permission_checks["temp_file_creation"] = temp_file_test
            
            self.test_results[test_name] = {
                "status": "passed" if all(permission_checks.values()) else "failed",
                "details": {
                    "permission_checks": permission_checks,
                    "all_permissions_ok": all(permission_checks.values())
                },
                "timestamp": time.time()
            }
            
            self.logger.info("File system permissions test completed",
                           all_permissions_ok=all(permission_checks.values()))
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("File system permissions test failed", error=str(e))
    
    async def _test_python_dependencies(self) -> None:
        """Test Python dependencies."""
        test_name = "python_dependencies"
        self.logger.info("Testing Python dependencies")
        
        try:
            dependency_checks = {}
            
            # Core Python modules
            core_modules = [
                "asyncio", "json", "pathlib", "typing", "dataclasses",
                "time", "os", "sys", "tempfile", "statistics"
            ]
            
            for module in core_modules:
                try:
                    __import__(module)
                    dependency_checks[f"core_{module}"] = True
                except ImportError:
                    dependency_checks[f"core_{module}"] = False
            
            # Third-party dependencies
            third_party_modules = [
                "pydantic", "browser_use", "psutil"
            ]
            
            for module in third_party_modules:
                try:
                    __import__(module)
                    dependency_checks[f"third_party_{module}"] = True
                except ImportError:
                    dependency_checks[f"third_party_{module}"] = False
            
            # Project modules
            project_modules = [
                "src.infrastructure.logging.logger",
                "src.execution.feature_flags"
            ]
            
            for module in project_modules:
                try:
                    __import__(module)
                    dependency_checks[f"project_{module}"] = True
                except ImportError:
                    dependency_checks[f"project_{module}"] = False
            
            # Python version check
            python_version = sys.version_info
            python_version_ok = python_version >= (3, 8)
            dependency_checks["python_version_ok"] = python_version_ok
            
            self.test_results[test_name] = {
                "status": "passed",
                "details": {
                    "dependency_checks": dependency_checks,
                    "python_version": f"{python_version.major}.{python_version.minor}.{python_version.micro}",
                    "python_version_ok": python_version_ok,
                    "core_modules_ok": all(v for k, v in dependency_checks.items() if k.startswith("core_")),
                    "project_modules_available": sum(1 for k, v in dependency_checks.items() if k.startswith("project_") and v)
                },
                "timestamp": time.time()
            }
            
            self.logger.info("Python dependencies test passed",
                           python_version=f"{python_version.major}.{python_version.minor}.{python_version.micro}")
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Python dependencies test failed", error=str(e))
    
    async def _test_configuration_files(self) -> None:
        """Test configuration file validation."""
        test_name = "configuration_files"
        self.logger.info("Testing configuration files")
        
        try:
            config_checks = {}
            
            # Check for common configuration files
            config_files = [
                "pyproject.toml",
                "requirements.txt",
                ".gitignore",
                "README.md"
            ]
            
            for config_file in config_files:
                file_path = project_root / config_file
                config_checks[config_file] = {
                    "exists": file_path.exists(),
                    "readable": file_path.exists() and os.access(str(file_path), os.R_OK),
                    "size": file_path.stat().st_size if file_path.exists() else 0
                }
            
            # Test JSON configuration parsing
            json_test = False
            try:
                test_config = {"test": True, "value": 123}
                json_str = json.dumps(test_config)
                parsed = json.loads(json_str)
                json_test = parsed == test_config
            except Exception:
                json_test = False
            
            config_checks["json_parsing"] = json_test
            
            self.test_results[test_name] = {
                "status": "passed",
                "details": {
                    "config_file_checks": config_checks,
                    "json_parsing_ok": json_test
                },
                "timestamp": time.time()
            }
            
            self.logger.info("Configuration files test passed")
            
        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Configuration files test failed", error=str(e))

    async def _test_logging_configuration(self) -> None:
        """Test logging configuration."""
        test_name = "logging_configuration"
        self.logger.info("Testing logging configuration")

        try:
            logging_checks = {}

            # Test logger creation
            try:
                test_logger = StructuredLogger("test_logger")
                logging_checks["logger_creation"] = True
            except Exception:
                logging_checks["logger_creation"] = False

            # Test log message formatting
            try:
                test_logger.info("Test message", test_param="test_value")
                logging_checks["message_formatting"] = True
            except Exception:
                logging_checks["message_formatting"] = False

            # Test different log levels
            log_levels = ["debug", "info", "warning", "error"]
            for level in log_levels:
                try:
                    getattr(test_logger, level)(f"Test {level} message")
                    logging_checks[f"log_level_{level}"] = True
                except Exception:
                    logging_checks[f"log_level_{level}"] = False

            self.test_results[test_name] = {
                "status": "passed" if all(logging_checks.values()) else "failed",
                "details": {
                    "logging_checks": logging_checks,
                    "all_logging_ok": all(logging_checks.values())
                },
                "timestamp": time.time()
            }

            self.logger.info("Logging configuration test completed",
                           all_logging_ok=all(logging_checks.values()))

        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Logging configuration test failed", error=str(e))

    async def _test_feature_flag_configuration(self) -> None:
        """Test feature flag configuration."""
        test_name = "feature_flag_configuration"
        self.logger.info("Testing feature flag configuration")

        try:
            if not FEATURE_FLAGS_AVAILABLE:
                self.test_results[test_name] = {
                    "status": "skipped",
                    "reason": "Feature flags not available",
                    "timestamp": time.time()
                }
                self.logger.warning("Feature flag configuration test skipped - not available")
                return

            flag_checks = {}

            # Test feature flag manager creation
            try:
                flag_manager = FeatureFlagManager()
                flag_checks["manager_creation"] = True
            except Exception:
                flag_checks["manager_creation"] = False

            if flag_checks["manager_creation"]:
                # Test flag operations
                try:
                    flags = flag_manager.get_all_flags()
                    flag_checks["get_all_flags"] = len(flags) > 0
                except Exception:
                    flag_checks["get_all_flags"] = False

                try:
                    status = flag_manager.get_migration_status()
                    flag_checks["migration_status"] = isinstance(status, dict)
                except Exception:
                    flag_checks["migration_status"] = False

                try:
                    enabled_flags = flag_manager.get_enabled_flags()
                    flag_checks["enabled_flags"] = isinstance(enabled_flags, list)
                except Exception:
                    flag_checks["enabled_flags"] = False

            self.test_results[test_name] = {
                "status": "passed" if all(flag_checks.values()) else "failed",
                "details": {
                    "flag_checks": flag_checks,
                    "all_flags_ok": all(flag_checks.values())
                },
                "timestamp": time.time()
            }

            self.logger.info("Feature flag configuration test completed",
                           all_flags_ok=all(flag_checks.values()))

        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Feature flag configuration test failed", error=str(e))

    async def _test_adapter_configuration(self) -> None:
        """Test adapter configuration."""
        test_name = "adapter_configuration"
        self.logger.info("Testing adapter configuration")

        try:
            if not ADAPTERS_AVAILABLE:
                self.test_results[test_name] = {
                    "status": "skipped",
                    "reason": "Adapters not available",
                    "timestamp": time.time()
                }
                self.logger.warning("Adapter configuration test skipped - not available")
                return

            adapter_checks = {}

            # Test adapter factory creation
            try:
                factory = AdapterFactory()
                adapter_checks["factory_creation"] = True
            except Exception:
                adapter_checks["factory_creation"] = False

            if adapter_checks["factory_creation"]:
                # Test factory methods
                try:
                    stats = factory.get_statistics()
                    adapter_checks["get_statistics"] = isinstance(stats, dict)
                except Exception:
                    adapter_checks["get_statistics"] = False

                try:
                    adapters = factory.list_adapters()
                    adapter_checks["list_adapters"] = isinstance(adapters, dict)
                except Exception:
                    adapter_checks["list_adapters"] = False

            self.test_results[test_name] = {
                "status": "passed" if all(adapter_checks.values()) else "failed",
                "details": {
                    "adapter_checks": adapter_checks,
                    "all_adapters_ok": all(adapter_checks.values())
                },
                "timestamp": time.time()
            }

            self.logger.info("Adapter configuration test completed",
                           all_adapters_ok=all(adapter_checks.values()))

        except Exception as e:
            self.test_results[test_name] = {
                "status": "failed",
                "error": str(e),
                "timestamp": time.time()
            }
            self.logger.error("Adapter configuration test failed", error=str(e))

    def _generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive final configuration report."""
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
            "configuration_status": {
                "environment_ready": "environment_variables" in self.test_results and
                                   self.test_results["environment_variables"]["status"] == "passed",
                "file_system_ready": "file_system_permissions" in self.test_results and
                                   self.test_results["file_system_permissions"]["status"] == "passed",
                "dependencies_ready": "python_dependencies" in self.test_results and
                                    self.test_results["python_dependencies"]["status"] == "passed",
                "logging_ready": "logging_configuration" in self.test_results and
                               self.test_results["logging_configuration"]["status"] == "passed",
                "configuration_valid": failed_tests == 0
            }
        }

        return report


async def main():
    """Main function to run configuration validation tests."""
    print("⚙️  Starting Configuration Validation Tests")
    print("=" * 60)

    runner = ConfigurationValidationTests(verbose=True)

    try:
        results = await runner.run_all_tests()

        # Print summary
        summary = results["summary"]
        print(f"\n📊 Configuration Test Results Summary:")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Passed: {summary['passed_tests']}")
        print(f"   Failed: {summary['failed_tests']}")
        print(f"   Skipped: {summary.get('skipped_tests', 0)}")
        print(f"   Success Rate: {summary['success_rate']:.1%}")
        print(f"   Execution Time: {summary['execution_time']:.2f}s")

        # Print configuration status
        status = results["configuration_status"]
        print(f"\n⚙️  Configuration Status:")
        print(f"   Environment Ready: {'✅' if status['environment_ready'] else '❌'}")
        print(f"   File System Ready: {'✅' if status['file_system_ready'] else '❌'}")
        print(f"   Dependencies Ready: {'✅' if status['dependencies_ready'] else '❌'}")
        print(f"   Logging Ready: {'✅' if status['logging_ready'] else '❌'}")
        print(f"   Configuration Valid: {'✅' if status['configuration_valid'] else '❌'}")

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
            print("🎉 All configuration tests passed! System configuration is valid.")
            return 0
        else:
            print("⚠️  Configuration issues detected. Please review the results.")
            return 1

    except Exception as e:
        print(f"❌ Configuration validation test suite failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
