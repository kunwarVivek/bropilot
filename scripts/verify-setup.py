#!/usr/bin/env python3
"""
Verification script for browser-use-automation setup.

This script verifies that all components are properly installed and configured.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def print_status(message, status="INFO"):
    colors = {
        "INFO": "\033[0;34m",
        "SUCCESS": "\033[0;32m", 
        "WARNING": "\033[1;33m",
        "ERROR": "\033[0;31m",
        "NC": "\033[0m"
    }
    print(f"{colors.get(status, colors['INFO'])}[{status}]{colors['NC']} {message}")

def verify_uv_setup():
    """Verify UV setup and virtual environment."""
    print_status("Verifying UV setup...")
    
    # Check if we're in a UV environment
    if not os.environ.get("VIRTUAL_ENV"):
        print_status("Not running in virtual environment", "WARNING")
        print_status("Run: uv run python scripts/verify-setup.py", "INFO")
    else:
        print_status("Running in virtual environment", "SUCCESS")
    
    # Check for uv.lock
    if (project_root / "uv.lock").exists():
        print_status("uv.lock file found", "SUCCESS")
    else:
        print_status("uv.lock file missing", "WARNING")
    
    # Check for pyproject.toml
    if (project_root / "pyproject.toml").exists():
        print_status("pyproject.toml found", "SUCCESS")
    else:
        print_status("pyproject.toml missing", "ERROR")
        return False
    
    return True

def verify_core_components():
    """Verify core architecture components."""
    print_status("Verifying core components...")
    
    try:
        # Test enhanced error recovery
        from src.execution.enhanced_error_recovery import EnhancedErrorRecovery, ErrorSeverity
        error_recovery = EnhancedErrorRecovery()
        print_status("Enhanced error recovery system ✓", "SUCCESS")
        
        # Test cost management
        from src.infrastructure.cost_management import CostManager, AdvancedRateLimiter, CostBudget
        cost_manager = CostManager()
        rate_limiter = AdvancedRateLimiter()
        print_status("Cost management and rate limiting ✓", "SUCCESS")
        
        # Test LLM abstraction
        from src.execution.llm_abstraction import (
            UnifiedLLMProvider, 
            LLMProviderRegistry, 
            ProviderCapability
        )
        registry = LLMProviderRegistry()
        print_status("Unified LLM abstraction ✓", "SUCCESS")
        print_status(f"Available capabilities: {len(list(ProviderCapability))}", "INFO")
        
        # Test task runner
        from utils.task_runner import get_execution_status
        status = get_execution_status()
        print_status("Unified task runner ✓", "SUCCESS")
        print_status(f"Execution mode: {status.get('execution_mode')}", "INFO")
        
        return True
        
    except ImportError as e:
        print_status(f"Import error: {e}", "ERROR")
        return False
    except Exception as e:
        print_status(f"Component error: {e}", "ERROR")
        return False

def verify_optional_components():
    """Verify optional components."""
    print_status("Verifying optional components...")
    
    # Test browser components (may fail if browser-use not fully configured)
    try:
        from src.execution.browser_manager import EnhancedBrowserManager
        print_status("Enhanced browser manager ✓", "SUCCESS")
    except ImportError as e:
        print_status(f"Browser manager not available: {e}", "WARNING")
    
    # Test monitoring
    try:
        from src.monitoring.system_monitor import SystemMonitor, HealthStatus
        monitor = SystemMonitor()
        print_status("System monitor ✓", "SUCCESS")
    except ImportError as e:
        print_status(f"System monitor not available: {e}", "WARNING")
    
    # Test LLM providers
    providers_available = []
    
    try:
        from src.execution.providers.openai_provider import OpenAIProvider
        providers_available.append("OpenAI")
    except ImportError:
        pass
    
    try:
        from src.execution.providers.gemini_provider import GeminiProvider
        providers_available.append("Gemini")
    except ImportError:
        pass
    
    try:
        from src.execution.providers.anthropic_provider import AnthropicProvider
        providers_available.append("Anthropic")
    except ImportError:
        pass
    
    try:
        from src.execution.providers.local_provider import LocalProvider
        providers_available.append("Local")
    except ImportError:
        pass
    
    if providers_available:
        print_status(f"LLM providers available: {', '.join(providers_available)}", "SUCCESS")
    else:
        print_status("No LLM providers available", "WARNING")

def verify_configuration():
    """Verify configuration files."""
    print_status("Verifying configuration...")
    
    # Check for .env file
    env_file = project_root / ".env"
    if env_file.exists():
        print_status(".env file found", "SUCCESS")
        
        # Check for API keys (without revealing them)
        with open(env_file) as f:
            content = f.read()
            
        api_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
        configured_keys = []
        
        for key in api_keys:
            if key in content and "your_" not in content:
                configured_keys.append(key)
        
        if configured_keys:
            print_status(f"API keys configured: {len(configured_keys)}/{len(api_keys)}", "SUCCESS")
        else:
            print_status("No API keys configured", "WARNING")
            print_status("Edit .env file with your API keys", "INFO")
    else:
        print_status(".env file not found", "WARNING")
        print_status("Copy .env.example to .env and configure", "INFO")

def verify_dependencies():
    """Verify key dependencies."""
    print_status("Verifying dependencies...")
    
    key_deps = [
        ("playwright", "Browser automation"),
        ("pydantic", "Data validation"),
        ("fastapi", "Web framework"),
        ("psutil", "System monitoring"),
        ("tiktoken", "Token counting"),
    ]
    
    for dep, description in key_deps:
        try:
            __import__(dep)
            print_status(f"{dep} ✓ ({description})", "SUCCESS")
        except ImportError:
            print_status(f"{dep} ✗ ({description})", "WARNING")

def main():
    """Main verification function."""
    print_status("🔍 Browser Use Automation Setup Verification", "INFO")
    print_status("=" * 50, "INFO")
    
    success = True
    
    # Verify UV setup
    if not verify_uv_setup():
        success = False
    
    print()
    
    # Verify core components
    if not verify_core_components():
        success = False
    
    print()
    
    # Verify optional components
    verify_optional_components()
    
    print()
    
    # Verify configuration
    verify_configuration()
    
    print()
    
    # Verify dependencies
    verify_dependencies()
    
    print()
    print_status("=" * 50, "INFO")
    
    if success:
        print_status("🎉 Setup verification completed successfully!", "SUCCESS")
        print_status("", "INFO")
        print_status("Next steps:", "INFO")
        print_status("1. Configure API keys in .env file", "INFO")
        print_status("2. Run: uv run python main.py", "INFO")
        print_status("3. Check documentation in docs/", "INFO")
    else:
        print_status("❌ Setup verification failed", "ERROR")
        print_status("Please check the errors above and fix them", "ERROR")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
