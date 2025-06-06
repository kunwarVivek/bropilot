# Framework Usage Guide

## 🚀 Overview

This comprehensive guide demonstrates how to use the Browser Automation Framework in practice, covering everything from basic workflow creation to advanced AI-powered automation scenarios.

## 📋 Table of Contents

- [Getting Started](#getting-started)
- [Basic Usage](#basic-usage)
- [Advanced Features](#advanced-features)
- [Real-World Examples](#real-world-examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## 🏁 Getting Started

### Installation and Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-org/browser-automation-framework.git
cd browser-automation-framework

# 2. Set up environment
cp .env.example .env
# Edit .env with your configuration

# 3. Start the system
docker-compose up -d

# 4. Verify installation
curl http://localhost:8001/health
```

### Basic Configuration

```python
# config.py - Basic framework configuration
from src.intelligence.advanced_orchestrator import AdvancedOrchestrator
from src.intelligence.config import IntelligentWorkflowConfig

# Create orchestrator instance
orchestrator = AdvancedOrchestrator(
    workflow_engine=workflow_engine,
    task_executor=task_executor,
    llm_provider=llm_provider  # Optional for AI features
)

# Basic configuration
config = IntelligentWorkflowConfig(
    enable_llm_assistance=True,
    enable_multimodal=True,
    enable_error_recovery=True,
    enable_analytics=True
)
```

## 🎯 Basic Usage

### 1. Simple Web Scraping

```python
# simple_scraping.py
import asyncio
from src.intelligence.advanced_orchestrator import AdvancedOrchestrator
from src.intelligence.config import IntelligentWorkflowConfig

async def simple_web_scraping():
    """Basic web scraping example."""
    
    # Define workflow
    workflow = {
        "type": "web_scraping",
        "name": "Simple Product Scraping",
        "tasks": [
            {
                "id": "navigate",
                "name": "Navigate to Product Page",
                "type": "navigate",
                "definition": {
                    "url": "https://example-store.com/products",
                    "wait_for": "h1"
                }
            },
            {
                "id": "extract_products",
                "name": "Extract Product Information",
                "type": "extract_data",
                "definition": {
                    "selectors": {
                        "title": ".product-title",
                        "price": ".product-price",
                        "description": ".product-description"
                    },
                    "multiple": True
                }
            }
        ],
        "dependencies": [
            {"from": "navigate", "to": "extract_products", "type": "hard"}
        ]
    }
    
    # Configure execution
    config = IntelligentWorkflowConfig(
        enable_llm_assistance=False,  # Simple scraping doesn't need AI
        enable_error_recovery=True,
        enable_analytics=True
    )
    
    # Execute workflow
    result = await orchestrator.execute_intelligent_workflow(workflow, config)
    
    if result["success"]:
        products = result["results"]["extract_products"]["data"]
        print(f"Extracted {len(products)} products")
        for product in products:
            print(f"- {product['title']}: {product['price']}")
    else:
        print(f"Workflow failed: {result.get('error')}")

# Run the example
if __name__ == "__main__":
    asyncio.run(simple_web_scraping())
```

### 2. Form Automation

```python
# form_automation.py
async def automated_form_filling():
    """Automated form filling example."""
    
    workflow = {
        "type": "form_automation",
        "name": "Contact Form Submission",
        "tasks": [
            {
                "id": "navigate_form",
                "name": "Navigate to Contact Form",
                "type": "navigate",
                "definition": {
                    "url": "https://example.com/contact",
                    "wait_for": "form#contact-form"
                }
            },
            {
                "id": "fill_form",
                "name": "Fill Contact Form",
                "type": "form_interaction",
                "definition": {
                    "form_selector": "#contact-form",
                    "fields": {
                        "name": "John Doe",
                        "email": "john.doe@example.com",
                        "subject": "Automated Inquiry",
                        "message": "This is an automated test message."
                    }
                }
            },
            {
                "id": "submit_form",
                "name": "Submit Form",
                "type": "click",
                "definition": {
                    "selector": "button[type='submit']",
                    "wait_for_navigation": True
                }
            },
            {
                "id": "verify_submission",
                "name": "Verify Submission",
                "type": "extract_data",
                "definition": {
                    "selector": ".success-message",
                    "expected_text": "Thank you for your message"
                }
            }
        ],
        "dependencies": [
            {"from": "navigate_form", "to": "fill_form", "type": "hard"},
            {"from": "fill_form", "to": "submit_form", "type": "hard"},
            {"from": "submit_form", "to": "verify_submission", "type": "hard"}
        ]
    }
    
    config = IntelligentWorkflowConfig(
        enable_error_recovery=True,
        enable_analytics=True,
        performance_targets={"max_execution_time": 60.0}
    )
    
    result = await orchestrator.execute_intelligent_workflow(workflow, config)
    return result

# Usage
result = await automated_form_filling()
print(f"Form submission {'successful' if result['success'] else 'failed'}")
```

## 🤖 Advanced Features

### 1. AI-Powered Workflow with Conversation

```python
# ai_powered_workflow.py
async def ai_powered_research():
    """AI-powered research workflow with conversation."""
    
    workflow = {
        "type": "ai_research",
        "name": "Intelligent Market Research",
        "tasks": [
            {
                "id": "search_products",
                "name": "Search for Products",
                "type": "navigate",
                "definition": {
                    "url": "https://marketplace.com/search",
                    "search_query": "wireless headphones"
                }
            },
            {
                "id": "analyze_results",
                "name": "Analyze Search Results",
                "type": "ai_analysis",
                "definition": {
                    "analysis_type": "market_research",
                    "extract_insights": True,
                    "conversation_prompt": "Analyze these search results and identify the top 3 most popular wireless headphone brands based on search ranking and customer reviews."
                }
            },
            {
                "id": "detailed_analysis",
                "name": "Detailed Product Analysis",
                "type": "ai_deep_dive",
                "definition": {
                    "conversation_prompt": "For each of the top 3 brands identified, extract detailed specifications, pricing, and customer sentiment analysis."
                }
            }
        ],
        "dependencies": [
            {"from": "search_products", "to": "analyze_results", "type": "hard"},
            {"from": "analyze_results", "to": "detailed_analysis", "type": "hard"}
        ]
    }
    
    # Advanced AI configuration
    config = IntelligentWorkflowConfig(
        enable_llm_assistance=True,
        enable_multimodal=True,
        enable_error_recovery=True,
        enable_analytics=True,
        auto_optimize=True,
        learning_mode=True,
        conversation_context={
            "research_domain": "consumer_electronics",
            "analysis_depth": "comprehensive",
            "output_format": "structured_report"
        }
    )
    
    # Execute with conversation capability
    result = await orchestrator.execute_intelligent_workflow(workflow, config)
    
    if result["success"]:
        # Access AI-generated insights
        insights = result["results"]["analyze_results"]["ai_insights"]
        detailed_analysis = result["results"]["detailed_analysis"]["ai_analysis"]
        
        print("=== Market Research Results ===")
        print(f"Key Insights: {insights}")
        print(f"Detailed Analysis: {detailed_analysis}")
    
    return result
```

### 2. Multi-Modal Content Processing

```python
# multimodal_processing.py
async def multimodal_content_analysis():
    """Multi-modal content processing example."""
    
    workflow = {
        "type": "multimodal_analysis",
        "name": "Website Content Analysis",
        "tasks": [
            {
                "id": "capture_screenshot",
                "name": "Capture Page Screenshot",
                "type": "screenshot",
                "definition": {
                    "url": "https://example-news.com",
                    "full_page": True,
                    "element": "main"
                }
            },
            {
                "id": "extract_text",
                "name": "Extract Text Content",
                "type": "extract_data",
                "definition": {
                    "selectors": {
                        "headlines": "h1, h2, h3",
                        "articles": ".article-content",
                        "metadata": ".article-meta"
                    }
                }
            },
            {
                "id": "analyze_image",
                "name": "Analyze Screenshot",
                "type": "image_analysis",
                "definition": {
                    "analysis_type": "ui_layout",
                    "extract_text": True,
                    "identify_elements": True
                }
            },
            {
                "id": "content_synthesis",
                "name": "Synthesize Multi-Modal Content",
                "type": "ai_synthesis",
                "definition": {
                    "combine_sources": ["text", "image", "metadata"],
                    "analysis_prompt": "Analyze the website's content strategy, visual design, and user experience based on both textual content and visual layout."
                }
            }
        ],
        "dependencies": [
            {"from": "capture_screenshot", "to": "analyze_image", "type": "hard"},
            {"from": "extract_text", "to": "content_synthesis", "type": "hard"},
            {"from": "analyze_image", "to": "content_synthesis", "type": "hard"}
        ],
        "execution_mode": "hybrid"  # Some tasks can run in parallel
    }
    
    config = IntelligentWorkflowConfig(
        enable_llm_assistance=True,
        enable_multimodal=True,
        enable_error_recovery=True,
        enable_analytics=True,
        conversation_context={
            "analysis_focus": "content_strategy",
            "output_detail": "comprehensive"
        }
    )
    
    result = await orchestrator.execute_intelligent_workflow(workflow, config)
    return result
```

### 3. Self-Healing Workflow

```python
# self_healing_workflow.py
async def self_healing_ecommerce_monitoring():
    """Self-healing e-commerce monitoring workflow."""
    
    workflow = {
        "type": "monitoring",
        "name": "E-commerce Site Monitoring",
        "tasks": [
            {
                "id": "health_check",
                "name": "Site Health Check",
                "type": "navigate",
                "definition": {
                    "url": "https://my-store.com",
                    "expected_elements": [".header", ".navigation", ".product-grid"],
                    "performance_thresholds": {
                        "load_time": 3.0,
                        "first_contentful_paint": 1.5
                    }
                }
            },
            {
                "id": "product_availability",
                "name": "Check Product Availability",
                "type": "extract_data",
                "definition": {
                    "selectors": {
                        "in_stock_products": ".product.in-stock",
                        "out_of_stock_products": ".product.out-of-stock",
                        "pricing_errors": ".product .price.error"
                    }
                }
            },
            {
                "id": "checkout_flow",
                "name": "Test Checkout Flow",
                "type": "user_journey",
                "definition": {
                    "steps": [
                        {"action": "click", "selector": ".product:first-child"},
                        {"action": "click", "selector": ".add-to-cart"},
                        {"action": "navigate", "url": "/cart"},
                        {"action": "verify", "selector": ".cart-item"}
                    ]
                }
            }
        ],
        "dependencies": [
            {"from": "health_check", "to": "product_availability", "type": "hard"},
            {"from": "product_availability", "to": "checkout_flow", "type": "soft"}
        ]
    }
    
    # Self-healing configuration
    config = IntelligentWorkflowConfig(
        enable_llm_assistance=True,
        enable_error_recovery=True,
        enable_analytics=True,
        auto_optimize=True,
        learning_mode=True,
        performance_targets={
            "max_execution_time": 120.0,
            "success_rate": 0.95
        },
        conversation_context={
            "monitoring_type": "ecommerce",
            "recovery_strategy": "adaptive",
            "alert_threshold": "medium"
        }
    )
    
    result = await orchestrator.execute_intelligent_workflow(workflow, config)
    
    # Handle monitoring results
    if not result["success"]:
        # AI will automatically attempt recovery
        print("Issues detected, AI recovery initiated...")
        recovery_result = await orchestrator.get_recovery_suggestions(result)
        print(f"Recovery suggestions: {recovery_result}")
    
    return result
```

## 🌍 Real-World Examples

### E-commerce Price Monitoring

```python
# price_monitoring.py
async def price_monitoring_workflow():
    """Real-world price monitoring example."""
    
    products_to_monitor = [
        {"name": "iPhone 15", "url": "https://store.com/iphone-15", "selector": ".price"},
        {"name": "Samsung Galaxy", "url": "https://store.com/galaxy", "selector": ".current-price"},
        {"name": "Google Pixel", "url": "https://store.com/pixel", "selector": ".price-now"}
    ]
    
    tasks = []
    dependencies = []
    
    for i, product in enumerate(products_to_monitor):
        task_id = f"monitor_{i}"
        tasks.append({
            "id": task_id,
            "name": f"Monitor {product['name']} Price",
            "type": "price_extraction",
            "definition": {
                "url": product["url"],
                "price_selector": product["selector"],
                "product_name": product["name"],
                "store_historical_data": True
            }
        })
    
    # Add analysis task
    tasks.append({
        "id": "price_analysis",
        "name": "Analyze Price Trends",
        "type": "ai_analysis",
        "definition": {
            "analysis_type": "price_trend",
            "conversation_prompt": "Analyze the current prices against historical data and identify any significant price changes or trends."
        }
    })
    
    # Create dependencies
    for i in range(len(products_to_monitor)):
        dependencies.append({
            "from": f"monitor_{i}",
            "to": "price_analysis",
            "type": "hard"
        })
    
    workflow = {
        "type": "price_monitoring",
        "name": "Daily Price Monitoring",
        "tasks": tasks,
        "dependencies": dependencies,
        "execution_mode": "parallel",
        "max_parallel": 3
    }
    
    config = IntelligentWorkflowConfig(
        enable_llm_assistance=True,
        enable_analytics=True,
        enable_error_recovery=True,
        conversation_context={
            "monitoring_frequency": "daily",
            "alert_on_change": True,
            "price_change_threshold": 0.05  # 5% change
        }
    )
    
    result = await orchestrator.execute_intelligent_workflow(workflow, config)
    return result
```

### Social Media Content Analysis

```python
# social_media_analysis.py
async def social_media_sentiment_analysis():
    """Social media content analysis workflow."""
    
    workflow = {
        "type": "social_media_analysis",
        "name": "Brand Sentiment Analysis",
        "tasks": [
            {
                "id": "collect_posts",
                "name": "Collect Social Media Posts",
                "type": "data_collection",
                "definition": {
                    "platforms": ["twitter", "instagram", "facebook"],
                    "search_terms": ["#mybrand", "@mybrand", "mybrand"],
                    "time_range": "24h",
                    "max_posts": 100
                }
            },
            {
                "id": "content_analysis",
                "name": "Analyze Content",
                "type": "ai_analysis",
                "definition": {
                    "analysis_types": ["sentiment", "topics", "engagement"],
                    "conversation_prompt": "Analyze the sentiment, key topics, and engagement patterns in these social media posts about our brand."
                }
            },
            {
                "id": "generate_report",
                "name": "Generate Insights Report",
                "type": "report_generation",
                "definition": {
                    "report_type": "social_media_insights",
                    "include_visualizations": True,
                    "conversation_prompt": "Create a comprehensive report with actionable insights and recommendations based on the social media analysis."
                }
            }
        ],
        "dependencies": [
            {"from": "collect_posts", "to": "content_analysis", "type": "hard"},
            {"from": "content_analysis", "to": "generate_report", "type": "hard"}
        ]
    }
    
    config = IntelligentWorkflowConfig(
        enable_llm_assistance=True,
        enable_multimodal=True,
        enable_analytics=True,
        conversation_context={
            "brand_name": "MyBrand",
            "analysis_focus": "sentiment_and_trends",
            "report_audience": "marketing_team"
        }
    )
    
    result = await orchestrator.execute_intelligent_workflow(workflow, config)
    return result
```

## 🎯 Best Practices

### 1. Workflow Design Principles

```python
# best_practices.py

# ✅ Good: Modular task design
def create_modular_workflow():
    return {
        "type": "modular_example",
        "name": "Well-Designed Workflow",
        "tasks": [
            {
                "id": "setup",
                "name": "Initialize Environment",
                "type": "setup",
                "definition": {"clear_cookies": True, "set_viewport": "1920x1080"}
            },
            {
                "id": "authenticate",
                "name": "User Authentication",
                "type": "auth",
                "definition": {"method": "oauth", "provider": "google"}
            },
            {
                "id": "main_task",
                "name": "Execute Main Task",
                "type": "business_logic",
                "definition": {"operation": "data_extraction"}
            },
            {
                "id": "cleanup",
                "name": "Cleanup Resources",
                "type": "cleanup",
                "definition": {"close_browser": True, "clear_temp_files": True}
            }
        ],
        "dependencies": [
            {"from": "setup", "to": "authenticate", "type": "hard"},
            {"from": "authenticate", "to": "main_task", "type": "hard"},
            {"from": "main_task", "to": "cleanup", "type": "soft"}
        ]
    }

# ❌ Bad: Monolithic task design
def create_monolithic_workflow():
    return {
        "tasks": [
            {
                "id": "do_everything",
                "name": "Do Everything",
                "type": "monolithic",
                "definition": {
                    "setup": True,
                    "auth": True,
                    "extract_data": True,
                    "cleanup": True
                }
            }
        ]
    }
```

### 2. Error Handling and Recovery

```python
# error_handling.py
async def robust_workflow_with_error_handling():
    """Example of robust error handling."""
    
    workflow = {
        "type": "robust_example",
        "name": "Error-Resilient Workflow",
        "tasks": [
            {
                "id": "critical_task",
                "name": "Critical Business Task",
                "type": "business_critical",
                "definition": {
                    "operation": "payment_processing",
                    "retry_count": 3,
                    "timeout": 30,
                    "fallback_strategy": "manual_review"
                }
            },
            {
                "id": "optional_task",
                "name": "Optional Enhancement",
                "type": "enhancement",
                "definition": {
                    "operation": "analytics_tracking",
                    "required": False,
                    "fail_silently": True
                }
            }
        ],
        "dependencies": [
            {"from": "critical_task", "to": "optional_task", "type": "soft"}
        ],
        "error_handling": {
            "global_retry_count": 2,
            "circuit_breaker_threshold": 5,
            "graceful_degradation": True
        }
    }
    
    config = IntelligentWorkflowConfig(
        enable_error_recovery=True,
        enable_analytics=True,
        performance_targets={
            "max_execution_time": 300.0,
            "success_rate": 0.99
        }
    )
    
    return await orchestrator.execute_intelligent_workflow(workflow, config)
```

### 3. Performance Optimization

```python
# performance_optimization.py
async def optimized_workflow():
    """Performance-optimized workflow example."""
    
    workflow = {
        "type": "performance_optimized",
        "name": "High-Performance Workflow",
        "tasks": [
            {
                "id": "parallel_task_1",
                "name": "Independent Task 1",
                "type": "data_extraction",
                "priority": "high",
                "definition": {"source": "api_endpoint_1"}
            },
            {
                "id": "parallel_task_2",
                "name": "Independent Task 2",
                "type": "data_extraction",
                "priority": "high",
                "definition": {"source": "api_endpoint_2"}
            },
            {
                "id": "parallel_task_3",
                "name": "Independent Task 3",
                "type": "data_extraction",
                "priority": "normal",
                "definition": {"source": "api_endpoint_3"}
            },
            {
                "id": "aggregation",
                "name": "Aggregate Results",
                "type": "data_processing",
                "priority": "high",
                "definition": {"operation": "merge_and_analyze"}
            }
        ],
        "dependencies": [
            {"from": "parallel_task_1", "to": "aggregation", "type": "hard"},
            {"from": "parallel_task_2", "to": "aggregation", "type": "hard"},
            {"from": "parallel_task_3", "to": "aggregation", "type": "hard"}
        ],
        "execution_mode": "parallel",
        "max_parallel": 3,
        "resource_optimization": {
            "browser_pool_size": 2,
            "memory_limit": "1GB",
            "cpu_limit": "2 cores"
        }
    }
    
    config = IntelligentWorkflowConfig(
        enable_analytics=True,
        auto_optimize=True,
        performance_targets={
            "max_execution_time": 60.0,
            "memory_usage": "500MB",
            "cpu_usage": "80%"
        }
    )
    
    return await orchestrator.execute_intelligent_workflow(workflow, config)
```

## 🔧 Troubleshooting

### Common Issues and Solutions

#### Issue 1: Workflow Execution Timeout

```python
# Solution: Optimize task timeouts and dependencies
workflow["tasks"][0]["definition"]["timeout"] = 60  # Increase timeout
config.performance_targets["max_execution_time"] = 300.0  # Increase overall timeout
```

#### Issue 2: Browser Resource Exhaustion

```python
# Solution: Implement proper resource management
config = IntelligentWorkflowConfig(
    enable_analytics=True,
    performance_targets={
        "browser_pool_size": 3,
        "max_concurrent_browsers": 2
    }
)
```

#### Issue 3: AI/LLM API Failures

```python
# Solution: Implement fallback strategies
config = IntelligentWorkflowConfig(
    enable_llm_assistance=True,
    enable_error_recovery=True,
    conversation_context={
        "fallback_mode": "rule_based",
        "api_timeout": 30,
        "retry_count": 3
    }
)
```

### Debug Mode Usage

```python
# Enable debug mode for troubleshooting
config = IntelligentWorkflowConfig(
    enable_llm_assistance=True,
    enable_analytics=True,
    debug_mode=True,  # Enable detailed logging
    conversation_context={
        "debug_level": "verbose",
        "log_ai_interactions": True
    }
)

# Execute with debug information
result = await orchestrator.execute_intelligent_workflow(workflow, config)

# Access debug information
if result.get("debug_info"):
    print("Debug Information:")
    print(f"Execution trace: {result['debug_info']['execution_trace']}")
    print(f"AI interactions: {result['debug_info']['ai_interactions']}")
    print(f"Performance metrics: {result['debug_info']['performance']}")
```

---

For more detailed information, see:
- [Quick Start Guide](quick-start.md)
- [Workflow Creation Guide](workflow-creation.md)
- [LLM Integration Guide](llm-integration.md)
- [Troubleshooting Guide](troubleshooting.md)
