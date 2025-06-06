#!/usr/bin/env python3
"""
Basic usage examples for Browser Use Automation platform.

This file demonstrates common usage patterns and basic automation tasks.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import platform components
from utils.task_runner import run_task
from src.execution.llm_provider import create_llm_provider
from src.infrastructure.cost_management import CostManager, CostBudget, CostPeriod


async def example_1_simple_navigation():
    """Example 1: Simple website navigation."""
    print("🌐 Example 1: Simple Navigation")
    
    # Create LLM provider
    llm = await create_llm_provider(
        primary_provider="openai",
        primary_model="gpt-4",
        primary_config={"api_key": os.getenv("OPENAI_API_KEY")}
    )
    
    # Define task
    task = """
    Navigate to https://httpbin.org
    Take a screenshot of the homepage
    Click on the 'GET' link
    Verify that the page loads successfully
    """
    
    # Execute task
    try:
        result = await run_task(task, llm, "logs/example_1")
        print(f"✅ Task completed: {result}")
    except Exception as e:
        print(f"❌ Task failed: {e}")


async def example_2_form_interaction():
    """Example 2: Form filling and interaction."""
    print("📝 Example 2: Form Interaction")
    
    # Create LLM provider with fallback
    llm = await create_llm_provider(
        primary_provider="openai",
        primary_model="gpt-4",
        primary_config={"api_key": os.getenv("OPENAI_API_KEY")},
        fallback_provider="anthropic",
        fallback_model="claude-3-sonnet",
        fallback_config={"api_key": os.getenv("ANTHROPIC_API_KEY")}
    )
    
    # Define task
    task = """
    Navigate to https://httpbin.org/forms/post
    Fill out the form with the following information:
    - Customer name: John Doe
    - Telephone: +1-555-123-4567
    - Email: john.doe@example.com
    - Size: Medium
    - Topping: Cheese
    - Delivery time: 1pm
    - Comments: Please ring the doorbell
    
    Submit the form and verify the response
    Take a screenshot of the result
    """
    
    # Execute task
    try:
        result = await run_task(task, llm, "logs/example_2")
        print(f"✅ Form submission completed: {result}")
    except Exception as e:
        print(f"❌ Form submission failed: {e}")


async def example_3_data_extraction():
    """Example 3: Data extraction from web pages."""
    print("📊 Example 3: Data Extraction")
    
    # Create LLM provider
    llm = await create_llm_provider(
        primary_provider="google",
        primary_model="gemini-pro",
        primary_config={"api_key": os.getenv("GOOGLE_API_KEY")}
    )
    
    # Define task
    task = """
    Navigate to https://httpbin.org/json
    Extract the JSON data from the page
    Parse the following information:
    - slideshow title
    - slideshow author
    - slideshow date
    - number of slides
    
    Format the extracted data as a structured summary
    """
    
    # Execute task
    try:
        result = await run_task(task, llm, "logs/example_3")
        print(f"✅ Data extraction completed: {result}")
    except Exception as e:
        print(f"❌ Data extraction failed: {e}")


async def example_4_cost_management():
    """Example 4: Cost management and monitoring."""
    print("💰 Example 4: Cost Management")
    
    # Setup cost management
    cost_manager = CostManager()
    
    # Set daily budget
    cost_manager.set_budget("daily", CostBudget(
        period=CostPeriod.DAILY,
        limit=10.0,  # $10 daily limit
        warning_threshold=0.8,  # Alert at 80%
        auto_suspend=False  # Don't auto-suspend for demo
    ))
    
    # Create LLM provider with cost tracking
    llm = await create_llm_provider(
        primary_provider="openai",
        primary_model="gpt-3.5-turbo",  # Cheaper model for demo
        primary_config={"api_key": os.getenv("OPENAI_API_KEY")},
        enable_cost_management=True
    )
    
    # Define task
    task = """
    Navigate to https://httpbin.org
    Explore the different endpoints available
    Test the /get endpoint with some query parameters
    Summarize the API capabilities
    """
    
    # Execute task
    try:
        result = await run_task(task, llm, "logs/example_4")
        print(f"✅ Task completed: {result}")
        
        # Check cost usage
        daily_usage = cost_manager.get_usage_summary("daily")
        print(f"💰 Daily usage: ${daily_usage.get('total_cost', 0):.4f}")
        
    except Exception as e:
        print(f"❌ Task failed: {e}")


async def example_5_error_handling():
    """Example 5: Error handling and recovery."""
    print("🚨 Example 5: Error Handling")
    
    # Create LLM provider
    llm = await create_llm_provider(
        primary_provider="openai",
        primary_model="gpt-4",
        primary_config={"api_key": os.getenv("OPENAI_API_KEY")}
    )
    
    # Define task that might fail
    task = """
    Navigate to https://nonexistent-website-12345.com
    If the website doesn't exist, navigate to https://httpbin.org instead
    Take a screenshot of whichever site loads successfully
    """
    
    # Execute task (should handle the error gracefully)
    try:
        result = await run_task(task, llm, "logs/example_5")
        print(f"✅ Task completed with error recovery: {result}")
    except Exception as e:
        print(f"❌ Task failed even with error handling: {e}")


async def example_6_multi_step_workflow():
    """Example 6: Multi-step workflow automation."""
    print("🔄 Example 6: Multi-step Workflow")
    
    # Create LLM provider
    llm = await create_llm_provider(
        primary_provider="anthropic",
        primary_model="claude-3-sonnet",
        primary_config={"api_key": os.getenv("ANTHROPIC_API_KEY")}
    )
    
    # Define complex multi-step task
    task = """
    Perform the following workflow:
    
    Step 1: Navigate to https://httpbin.org
    Step 2: Take a screenshot of the homepage
    Step 3: Click on the 'JSON' link
    Step 4: Extract the JSON data
    Step 5: Navigate back to the homepage
    Step 6: Click on the 'HTML' link
    Step 7: Take a screenshot of the HTML page
    Step 8: Create a summary report of both pages
    
    Provide a detailed log of each step completed.
    """
    
    # Execute workflow
    try:
        result = await run_task(task, llm, "logs/example_6")
        print(f"✅ Multi-step workflow completed: {result}")
    except Exception as e:
        print(f"❌ Workflow failed: {e}")


async def main():
    """Run all examples."""
    print("🚀 Browser Use Automation - Basic Examples")
    print("=" * 50)
    
    examples = [
        example_1_simple_navigation,
        example_2_form_interaction,
        example_3_data_extraction,
        example_4_cost_management,
        example_5_error_handling,
        example_6_multi_step_workflow
    ]
    
    for i, example in enumerate(examples, 1):
        try:
            await example()
            print(f"✅ Example {i} completed successfully")
        except Exception as e:
            print(f"❌ Example {i} failed: {e}")
        
        print("-" * 30)
    
    print("🎉 All examples completed!")


if __name__ == "__main__":
    # Check for required API keys
    required_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    
    if missing_keys:
        print("⚠️  Warning: Missing API keys:", ", ".join(missing_keys))
        print("Some examples may fail. Please set these in your .env file.")
        print()
    
    # Run examples
    asyncio.run(main())
