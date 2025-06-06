#!/usr/bin/env python3
"""
Validation Framework Demo

Demonstrates the comprehensive validation framework across all phases.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import platform components
from utils.task_runner import run_task
from src.execution.llm_provider import create_llm_provider
from src.validation import ValidationConfig, ValidationLevel, get_validation_config


async def demo_basic_validation():
    """Demo 1: Basic validation with minimal checks."""
    print("🔍 Demo 1: Basic Validation")
    print("=" * 50)
    
    # Create LLM provider
    llm = await create_llm_provider(
        primary_provider="openai",
        primary_model="gpt-4",
        primary_config={"api_key": os.getenv("OPENAI_API_KEY")}
    )
    
    # Basic validation config
    validation_config = get_validation_config("basic")
    
    # Define task
    task = """
    Navigate to https://httpbin.org
    Take a screenshot of the homepage
    Extract the main heading text
    Verify the page loaded successfully
    """
    
    # Execute task with basic validation
    try:
        result = await run_task(task, llm, "logs/demo_1_basic", validation_config)
        print(f"✅ Task completed with basic validation")
        print(f"Result: {result[:200]}...")
    except Exception as e:
        print(f"❌ Task failed: {e}")
    
    print()


async def demo_standard_validation():
    """Demo 2: Standard validation with comprehensive checks."""
    print("🔍 Demo 2: Standard Validation")
    print("=" * 50)
    
    # Create LLM provider
    llm = await create_llm_provider(
        primary_provider="openai",
        primary_model="gpt-4",
        primary_config={"api_key": os.getenv("OPENAI_API_KEY")}
    )
    
    # Standard validation config
    validation_config = get_validation_config("standard")
    
    # Define task with expected outcomes
    task = """
    Navigate to https://httpbin.org/json
    Extract the JSON data from the page
    Parse the slideshow information:
    - Title
    - Author
    - Date
    - Number of slides
    
    Expected outcome: Successfully extract structured slideshow data
    """
    
    # Execute task with standard validation
    try:
        result = await run_task(task, llm, "logs/demo_2_standard", validation_config)
        print(f"✅ Task completed with standard validation")
        print(f"Result: {result[:300]}...")
    except Exception as e:
        print(f"❌ Task failed: {e}")
    
    print()


async def demo_comprehensive_validation():
    """Demo 3: Comprehensive validation with all features."""
    print("🔍 Demo 3: Comprehensive Validation")
    print("=" * 50)
    
    # Create LLM provider
    llm = await create_llm_provider(
        primary_provider="anthropic",
        primary_model="claude-3-sonnet",
        primary_config={"api_key": os.getenv("ANTHROPIC_API_KEY")}
    )
    
    # Comprehensive validation config
    validation_config = get_validation_config("comprehensive")
    
    # Define complex task
    task = """
    Perform a comprehensive web analysis:
    
    1. Navigate to https://httpbin.org
    2. Take screenshots of key sections
    3. Test the /get endpoint with parameters
    4. Test the /post endpoint with form data
    5. Extract all available endpoints
    6. Analyze response times and performance
    7. Generate a summary report
    
    Expected outcomes:
    - All endpoints tested successfully
    - Performance metrics collected
    - Comprehensive report generated
    """
    
    # Execute task with comprehensive validation
    try:
        result = await run_task(task, llm, "logs/demo_3_comprehensive", validation_config)
        print(f"✅ Task completed with comprehensive validation")
        print(f"Result: {result[:400]}...")
    except Exception as e:
        print(f"❌ Task failed: {e}")
    
    print()


async def demo_custom_validation():
    """Demo 4: Custom validation configuration."""
    print("🔍 Demo 4: Custom Validation Configuration")
    print("=" * 50)
    
    # Create LLM provider
    llm = await create_llm_provider(
        primary_provider="google",
        primary_model="gemini-pro",
        primary_config={"api_key": os.getenv("GOOGLE_API_KEY")}
    )
    
    # Create custom validation config
    validation_config = ValidationConfig(
        validation_level=ValidationLevel.STANDARD,
        enabled_types=["functional", "data_quality", "performance"],
        collect_evidence=True,
        evidence_types=["screenshots", "execution_logs", "performance_metrics"],
        enable_llm_validation=True,
        llm_self_validation=True,
        data_quality_checks=True,
        data_completeness_threshold=0.90,
        data_accuracy_threshold=0.85,
        performance_monitoring=True,
        max_execution_time=60.0,
        memory_threshold=0.80
    )
    
    # Define task with specific validation requirements
    task = """
    E-commerce product analysis:
    
    1. Navigate to https://httpbin.org (simulating e-commerce site)
    2. Extract product information (simulate with JSON data)
    3. Validate data completeness (all required fields)
    4. Check data accuracy (format validation)
    5. Monitor performance metrics
    6. Generate quality report
    
    Data quality requirements:
    - 90% completeness threshold
    - 85% accuracy threshold
    - All fields properly formatted
    """
    
    # Execute task with custom validation
    try:
        result = await run_task(task, llm, "logs/demo_4_custom", validation_config)
        print(f"✅ Task completed with custom validation")
        print(f"Result: {result[:400]}...")
    except Exception as e:
        print(f"❌ Task failed: {e}")
    
    print()


async def demo_validation_with_errors():
    """Demo 5: Validation with intentional errors."""
    print("🔍 Demo 5: Validation Error Detection")
    print("=" * 50)
    
    # Create LLM provider
    llm = await create_llm_provider(
        primary_provider="openai",
        primary_model="gpt-3.5-turbo",
        primary_config={"api_key": os.getenv("OPENAI_API_KEY")}
    )
    
    # Paranoid validation config (maximum validation)
    validation_config = get_validation_config("paranoid")
    
    # Define task with potential issues
    task = """
    Problematic task simulation:
    
    1. Navigate to https://nonexistent-website-12345.com (will fail)
    2. If that fails, navigate to http://httpbin.org (insecure HTTP)
    3. Extract data that may be incomplete
    4. Perform operations that may be slow
    5. Generate report with potential quality issues
    
    This task is designed to trigger various validation errors
    to demonstrate the validation framework's error detection.
    """
    
    # Execute task expecting validation issues
    try:
        result = await run_task(task, llm, "logs/demo_5_errors", validation_config)
        print(f"⚠️  Task completed but validation issues detected")
        print(f"Result: {result[:400]}...")
    except Exception as e:
        print(f"❌ Task failed with validation errors: {e}")
    
    print()


async def demo_validation_phases():
    """Demo 6: Validation across all phases."""
    print("🔍 Demo 6: Multi-Phase Validation")
    print("=" * 50)
    
    # Create LLM provider
    llm = await create_llm_provider(
        primary_provider="openai",
        primary_model="gpt-4",
        primary_config={"api_key": os.getenv("OPENAI_API_KEY")}
    )
    
    # Configure validation for all phases
    validation_config = ValidationConfig.create_comprehensive_config()
    validation_config.pre_execution.enabled = True
    validation_config.during_execution.enabled = True
    validation_config.post_execution.enabled = True
    validation_config.continuous.enabled = True
    
    # Define multi-step task
    task = """
    Multi-phase validation demonstration:
    
    Phase 1 (Pre-execution): Validate task understanding and setup
    Phase 2 (During execution): Monitor each step and performance
    Phase 3 (Post-execution): Validate outcomes and data quality
    Phase 4 (Continuous): Monitor system resources throughout
    
    Steps:
    1. Navigate to https://httpbin.org
    2. Test multiple endpoints (/get, /post, /json)
    3. Extract and validate response data
    4. Measure performance metrics
    5. Generate comprehensive report
    
    This demonstrates validation at every phase of execution.
    """
    
    # Execute task with multi-phase validation
    try:
        result = await run_task(task, llm, "logs/demo_6_phases", validation_config)
        print(f"✅ Multi-phase validation completed")
        print(f"Result: {result[:400]}...")
    except Exception as e:
        print(f"❌ Multi-phase validation failed: {e}")
    
    print()


async def main():
    """Run all validation demos."""
    print("🚀 Browser Use Automation - Validation Framework Demo")
    print("=" * 60)
    print()
    
    demos = [
        demo_basic_validation,
        demo_standard_validation,
        demo_comprehensive_validation,
        demo_custom_validation,
        demo_validation_with_errors,
        demo_validation_phases
    ]
    
    for i, demo in enumerate(demos, 1):
        try:
            await demo()
            print(f"✅ Demo {i} completed successfully")
        except Exception as e:
            print(f"❌ Demo {i} failed: {e}")
        
        print("-" * 60)
        print()
    
    print("🎉 All validation demos completed!")
    print()
    print("📊 Validation Features Demonstrated:")
    print("• Basic validation with minimal overhead")
    print("• Standard validation with comprehensive checks")
    print("• Comprehensive validation with all features")
    print("• Custom validation configuration")
    print("• Error detection and reporting")
    print("• Multi-phase validation workflow")
    print()
    print("📁 Check the logs/ directory for detailed validation reports")
    print("📁 Check the evidence/ directory for collected evidence")


if __name__ == "__main__":
    # Check for required API keys
    required_keys = ["OPENAI_API_KEY"]
    optional_keys = ["ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
    
    missing_required = [key for key in required_keys if not os.getenv(key)]
    missing_optional = [key for key in optional_keys if not os.getenv(key)]
    
    if missing_required:
        print("❌ Error: Missing required API keys:", ", ".join(missing_required))
        print("Please set these in your .env file.")
        exit(1)
    
    if missing_optional:
        print("⚠️  Warning: Missing optional API keys:", ", ".join(missing_optional))
        print("Some demos may use fallback providers.")
        print()
    
    # Run demos
    asyncio.run(main())
