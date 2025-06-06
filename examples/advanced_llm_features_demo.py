#!/usr/bin/env python3
"""
Advanced LLM Test Features Demo

Demonstrates the advanced LLM-powered test automation features:
1. Test Case Auto-Generation from Requirements
2. Test Maintenance and Updates when UI Changes
3. Intelligent Test Analysis and Optimization
"""

import asyncio
import itertools
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.test_automation_framework import create_test_automation_framework
from src.test_management.models import TestType, TestPriority


async def demo_requirements_to_test_generation():
    """Demo: Generate test cases from requirements document."""
    print("\n" + "="*60)
    print("🚀 DEMO: Test Case Auto-Generation from Requirements")
    print("="*60)
    
    # Sample requirements document
    requirements_doc = """
    E-Commerce Platform Requirements

    1. User Authentication System
    - Users must be able to register with email and password
    - Users must be able to login with valid credentials
    - System must lock account after 3 failed login attempts
    - Password must be at least 8 characters with special characters
    - Users must be able to reset password via email

    2. Product Catalog
    - Users can browse products by category
    - Users can search products by name, description, or SKU
    - Products must display price, description, and availability
    - Users can filter products by price range and ratings
    - Product images must load within 2 seconds

    3. Shopping Cart
    - Users can add products to cart
    - Users can modify quantities in cart
    - Users can remove items from cart
    - Cart must persist across browser sessions
    - Cart total must update automatically

    4. Checkout Process
    - Users must provide shipping address
    - Users can select shipping method
    - Users must provide payment information
    - System must validate payment before processing
    - Users receive order confirmation email

    5. Order Management
    - Users can view order history
    - Users can track order status
    - Users can cancel orders within 1 hour
    - System sends status update emails
    """
    
    # Initialize framework
    framework = await create_test_automation_framework(
        workspace_path="demo_workspace_advanced",
        environment="demo"
    )
    
    print("📋 Requirements Document:")
    print(requirements_doc[:500] + "..." if len(requirements_doc) > 500 else requirements_doc)
    
    # Mock LLM provider for demo
    from unittest.mock import AsyncMock
    mock_llm = AsyncMock()
    
    # Mock LLM responses for requirements analysis (cycle through responses)
    responses = [
        # Features extraction response
        """
        [
            {
                "feature_name": "User Authentication",
                "description": "Complete user authentication system with registration, login, and security",
                "acceptance_criteria": [
                    "User can register with email and password",
                    "User can login with valid credentials",
                    "Account locks after 3 failed attempts",
                    "Password reset functionality works"
                ],
                "priority": "high",
                "test_types": ["functional", "security"],
                "dependencies": [],
                "user_roles": ["guest", "user"],
                "business_rules": [
                    "Password must be 8+ characters",
                    "Must include special characters"
                ],
                "edge_cases": [
                    "Empty credentials",
                    "Invalid email format",
                    "SQL injection attempts"
                ],
                "estimated_test_cases": 8
            },
            {
                "feature_name": "Shopping Cart",
                "description": "Shopping cart functionality with persistence and automatic updates",
                "acceptance_criteria": [
                    "Users can add products to cart",
                    "Users can modify quantities",
                    "Cart persists across sessions",
                    "Total updates automatically"
                ],
                "priority": "high",
                "test_types": ["functional", "integration"],
                "dependencies": ["User Authentication", "Product Catalog"],
                "user_roles": ["user"],
                "business_rules": [
                    "Cart must persist for 30 days",
                    "Maximum 10 items per product"
                ],
                "edge_cases": [
                    "Adding out-of-stock items",
                    "Negative quantities",
                    "Session timeout"
                ],
                "estimated_test_cases": 6
            }
        ]
        """,
        # Scenarios for User Authentication
        """
        [
            {
                "scenario_name": "Valid User Registration",
                "test_type": "positive",
                "feature_name": "User Authentication",
                "preconditions": ["Registration page is accessible"],
                "test_steps": [
                    "Navigate to registration page",
                    "Enter valid email address",
                    "Enter strong password",
                    "Confirm password",
                    "Click register button",
                    "Verify registration success"
                ],
                "expected_results": [
                    "User account is created",
                    "Confirmation email is sent",
                    "User is redirected to login page"
                ],
                "test_data": {
                    "email": "newuser@example.com",
                    "password": "SecurePass123!"
                },
                "priority": "high",
                "risk_level": "medium"
            },
            {
                "scenario_name": "Account Lockout After Failed Attempts",
                "test_type": "negative",
                "feature_name": "User Authentication",
                "preconditions": ["User account exists"],
                "test_steps": [
                    "Navigate to login page",
                    "Enter valid email",
                    "Enter incorrect password",
                    "Click login button",
                    "Repeat 3 times",
                    "Verify account is locked"
                ],
                "expected_results": [
                    "Account is locked after 3 attempts",
                    "Error message is displayed",
                    "User cannot login even with correct password"
                ],
                "test_data": {
                    "email": "testuser@example.com",
                    "wrong_password": "wrongpass"
                },
                "priority": "high",
                "risk_level": "high"
            }
        ]
        """,
        # Scenarios for Shopping Cart
        """
        [
            {
                "scenario_name": "Add Product to Cart",
                "test_type": "positive",
                "feature_name": "Shopping Cart",
                "preconditions": ["User is logged in", "Product is available"],
                "test_steps": [
                    "Navigate to product page",
                    "Select product quantity",
                    "Click add to cart button",
                    "Verify product is added to cart",
                    "Check cart total is updated"
                ],
                "expected_results": [
                    "Product appears in cart",
                    "Quantity is correct",
                    "Total price is calculated correctly"
                ],
                "test_data": {
                    "product_id": "PROD123",
                    "quantity": 2
                },
                "priority": "high",
                "risk_level": "medium"
            }
        ]
        """,
        # Test case generation responses (2 calls)
        """
        {
            "name": "User Authentication - Valid User Registration",
            "description": "Test valid user registration process with email and password validation",
            "preconditions": ["Registration page is accessible", "Email service is available"],
            "steps": [
                {
                    "step_number": 1,
                    "description": "Navigate to registration page",
                    "action": "Open browser and navigate to /register",
                    "expected_result": "Registration form is displayed",
                    "validation_rules": ["Page title contains 'Register'"],
                    "timeout": 30
                },
                {
                    "step_number": 2,
                    "description": "Enter user details",
                    "action": "Fill in email and password fields",
                    "expected_result": "Fields accept input",
                    "validation_rules": ["Email format is validated"],
                    "timeout": 10
                },
                {
                    "step_number": 3,
                    "description": "Submit registration",
                    "action": "Click register button",
                    "expected_result": "Registration is processed",
                    "validation_rules": ["Success message is shown"],
                    "timeout": 15
                }
            ],
            "postconditions": ["User account is created in database"],
            "test_data": {"email": "newuser@example.com", "password": "SecurePass123!"}
        }
        """,
        """
        {
            "name": "Shopping Cart - Add Product to Cart",
            "description": "Test adding products to shopping cart with quantity selection",
            "preconditions": ["User is logged in", "Product catalog is available"],
            "steps": [
                {
                    "step_number": 1,
                    "description": "Navigate to product page",
                    "action": "Click on product from catalog",
                    "expected_result": "Product details page loads",
                    "validation_rules": ["Product information is displayed"],
                    "timeout": 20
                },
                {
                    "step_number": 2,
                    "description": "Add to cart",
                    "action": "Select quantity and click add to cart",
                    "expected_result": "Product is added to cart",
                    "validation_rules": ["Cart count increases"],
                    "timeout": 10
                }
            ],
            "postconditions": ["Cart contains selected product"],
            "test_data": {"product_id": "PROD123", "quantity": 2}
        }
        """
    ]

    # Create a cycling iterator for responses
    import itertools
    response_cycle = itertools.cycle(responses)
    mock_llm.invoke.side_effect = lambda prompt: next(response_cycle)

    framework.llm_provider = mock_llm
    
    print("\n🤖 Generating test cases from requirements...")
    
    # Generate test cases from requirements
    generated_test_cases = await framework.generate_test_cases_from_requirements(
        requirements_document=requirements_doc,
        test_coverage_level="comprehensive",
        target_url="https://demo-ecommerce.example.com"
    )
    
    print(f"\n✅ Generated {len(generated_test_cases)} test cases:")
    for i, test_case in enumerate(generated_test_cases, 1):
        print(f"\n{i}. {test_case.name}")
        print(f"   Type: {test_case.test_type.value}")
        print(f"   Priority: {test_case.priority.value}")
        print(f"   Steps: {len(test_case.steps)}")
        print(f"   Tags: {', '.join(test_case.tags)}")
        print(f"   Description: {test_case.description[:100]}...")
    
    return framework, generated_test_cases


async def demo_test_maintenance_for_ui_changes(framework, test_cases):
    """Demo: Update test cases when UI changes occur."""
    print("\n" + "="*60)
    print("🔧 DEMO: Test Maintenance for UI Changes")
    print("="*60)
    
    # Sample UI changes description
    ui_changes = """
    UI Changes for E-Commerce Platform v2.0:
    
    1. Login Page Redesign:
    - Email field ID changed from 'email' to 'user-email-input'
    - Password field now has class 'password-field-v2'
    - Login button text changed from 'Login' to 'Sign In'
    - Added new 'Remember Me' checkbox
    - Added social login buttons (Google, Facebook)
    
    2. Product Page Updates:
    - Add to cart button moved to bottom of page
    - Quantity selector is now a dropdown instead of input field
    - Product images now use lazy loading
    - Added product reviews section
    - Price display format changed to include currency symbol
    
    3. Shopping Cart Changes:
    - Cart icon moved to top-right corner
    - Remove item button changed from 'X' to 'Remove'
    - Added 'Save for Later' functionality
    - Cart total now shows tax breakdown
    """
    
    print("📝 UI Changes Description:")
    print(ui_changes[:400] + "..." if len(ui_changes) > 400 else ui_changes)
    
    # Mock LLM responses for impact analysis and updates
    maintenance_responses = [
        # Impact analysis response
        """
        {
            "overall_impact": "high",
            "summary": "Significant changes to login and cart functionality requiring test updates",
            "test_case_impacts": [
                {
                    "test_case_id": "tc_001",
                    "test_case_name": "User Authentication - Valid User Registration",
                    "impact_level": "high",
                    "affected_elements": ["email_field", "password_field", "login_button"],
                    "required_updates": [
                        "Update email field selector to 'user-email-input'",
                        "Update password field selector to use class 'password-field-v2'",
                        "Change login button text expectation to 'Sign In'"
                    ],
                    "failure_risk": "high",
                    "recommended_actions": [
                        "Update element selectors",
                        "Add validation for new Remember Me checkbox",
                        "Consider testing social login options"
                    ],
                    "estimated_effort": "3 hours"
                },
                {
                    "test_case_id": "tc_002", 
                    "test_case_name": "Shopping Cart - Add Product to Cart",
                    "impact_level": "medium",
                    "affected_elements": ["add_to_cart_button", "quantity_selector"],
                    "required_updates": [
                        "Update add to cart button location",
                        "Change quantity selector from input to dropdown"
                    ],
                    "failure_risk": "medium",
                    "recommended_actions": [
                        "Update element locators",
                        "Add validation for new cart features"
                    ],
                    "estimated_effort": "2 hours"
                }
            ],
            "global_recommendations": [
                "Update page object models for all affected pages",
                "Review all authentication and cart-related tests",
                "Add tests for new social login functionality"
            ]
        }
        """,
        # Test case update response for first test case
        """
        {
            "updated_name": "User Authentication - Valid User Registration (Updated for v2.0)",
            "updated_description": "Test valid user registration process with updated UI elements and new features",
            "updated_steps": [
                {
                    "step_number": 1,
                    "description": "Navigate to registration page",
                    "action": "Open browser and navigate to /register",
                    "expected_result": "Registration form with new design is displayed",
                    "validation_rules": ["Page title contains 'Register'", "Social login buttons are visible"],
                    "timeout": 30
                },
                {
                    "step_number": 2,
                    "description": "Enter user details with new selectors",
                    "action": "Fill in email field (ID: user-email-input) and password field (class: password-field-v2)",
                    "expected_result": "Fields accept input with new validation",
                    "validation_rules": ["Email format is validated", "Password strength indicator shows"],
                    "timeout": 10
                },
                {
                    "step_number": 3,
                    "description": "Submit registration with new button",
                    "action": "Click 'Sign In' button",
                    "expected_result": "Registration is processed with new flow",
                    "validation_rules": ["Success message is shown", "Remember Me option is available"],
                    "timeout": 15
                }
            ],
            "new_preconditions": ["Social login services are available"],
            "new_postconditions": ["User preferences are saved if Remember Me is checked"],
            "updated_test_data": {
                "email": "newuser@example.com", 
                "password": "SecurePass123!",
                "remember_me": true
            },
            "change_summary": "Updated selectors for email and password fields, changed button text expectation, added social login validation",
            "confidence_level": "high"
        }
        """
    ]

    # Create cycling iterator for maintenance responses
    maintenance_cycle = itertools.cycle(maintenance_responses)
    framework.llm_provider.invoke.side_effect = lambda prompt: next(maintenance_cycle)
    
    print("\n🔍 Analyzing UI changes impact on test cases...")
    
    # Analyze impact of UI changes
    test_case_ids = [tc.id for tc in test_cases]
    impact_analysis = await framework.analyze_ui_changes_impact(
        ui_changes_description=ui_changes,
        affected_test_case_ids=test_case_ids
    )
    
    print(f"\n📊 Impact Analysis Results:")
    print(f"Overall Impact: {impact_analysis['overall_impact']}")
    print(f"Summary: {impact_analysis['summary']}")
    
    print(f"\nAffected Test Cases:")
    for impact in impact_analysis.get('test_case_impacts', []):
        print(f"\n• {impact['test_case_name']}")
        print(f"  Impact Level: {impact['impact_level']}")
        print(f"  Failure Risk: {impact['failure_risk']}")
        print(f"  Estimated Effort: {impact['estimated_effort']}")
        print(f"  Required Updates: {len(impact['required_updates'])} items")
    
    print(f"\nGlobal Recommendations:")
    for rec in impact_analysis.get('global_recommendations', []):
        print(f"• {rec}")
    
    print("\n🔧 Updating test cases for UI changes...")
    
    # Update the first test case
    if test_cases:
        updated_test_case = await framework.update_test_case_for_changes(
            test_case_id=test_cases[0].id,
            change_description=ui_changes,
            update_strategy="smart"
        )
        
        print(f"\n✅ Updated Test Case: {updated_test_case.name}")
        print(f"Version: {updated_test_case.version} (was {test_cases[0].version})")
        print(f"Steps: {len(updated_test_case.steps)} (was {len(test_cases[0].steps)})")
        print(f"Updated by: {updated_test_case.updated_by}")
        print(f"Tags: {', '.join(updated_test_case.tags)}")
        
        print(f"\nUpdated Steps:")
        for step in updated_test_case.steps:
            print(f"{step.step_number}. {step.description}")
            print(f"   Action: {step.action[:80]}...")
            print(f"   Expected: {step.expected_result[:60]}...")
    
    return impact_analysis


async def demo_bulk_test_maintenance():
    """Demo: Bulk update multiple test cases for changes."""
    print("\n" + "="*60)
    print("🔄 DEMO: Bulk Test Case Maintenance")
    print("="*60)
    
    # This would demonstrate updating multiple test cases at once
    print("📦 Bulk maintenance features:")
    print("• Analyze impact across entire test suite")
    print("• Update multiple test cases simultaneously")
    print("• Generate maintenance reports")
    print("• Track version history and changes")
    print("• Validate updated tests automatically")
    
    print("\n✨ Advanced capabilities:")
    print("• Smart conflict resolution")
    print("• Dependency-aware updates")
    print("• Rollback capabilities")
    print("• Change impact visualization")


async def main():
    """Run the advanced LLM features demo."""
    print("🚀 Advanced LLM Test Features Demo")
    print("Showcasing intelligent test automation capabilities")
    
    try:
        # Demo 1: Requirements to test generation
        framework, test_cases = await demo_requirements_to_test_generation()
        
        # Demo 2: Test maintenance for UI changes
        impact_analysis = await demo_test_maintenance_for_ui_changes(framework, test_cases)
        
        # Demo 3: Bulk maintenance overview
        await demo_bulk_test_maintenance()
        
        print("\n" + "="*60)
        print("🎉 DEMO COMPLETED SUCCESSFULLY!")
        print("="*60)
        
        print("\n📈 Summary:")
        print(f"• Generated {len(test_cases)} test cases from requirements")
        print(f"• Analyzed impact on {len(test_cases)} existing test cases")
        print(f"• Overall UI change impact: {impact_analysis.get('overall_impact', 'N/A')}")
        print(f"• Demonstrated intelligent test maintenance")
        
        print("\n🚀 Key Benefits:")
        print("• Automated test case generation from requirements")
        print("• Intelligent impact analysis for changes")
        print("• Automated test maintenance and updates")
        print("• Reduced manual effort in test management")
        print("• Improved test coverage and quality")
        
        # Cleanup
        await framework.cleanup()
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
