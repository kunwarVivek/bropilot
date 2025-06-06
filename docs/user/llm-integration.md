# LLM Integration Guide

Harness the power of AI to create intelligent, adaptive browser automation workflows with natural language interaction and smart error recovery.

## 🎯 Overview

The Browser Automation Framework integrates seamlessly with leading LLM providers to offer:

- **Conversational Workflows**: Natural language interaction during execution
- **Intelligent Error Recovery**: AI-guided diagnosis and automatic resolution
- **Dynamic Adaptation**: Real-time workflow optimization based on context
- **Multi-Modal Understanding**: Process text, images, and complex web content

## 🚀 Quick Start

### Basic LLM Configuration

```python
from src.intelligence.advanced_orchestrator import AdvancedOrchestrator, IntelligentWorkflowConfig

# Configure LLM integration
config = IntelligentWorkflowConfig(
    enable_llm_assistance=True,
    llm_provider="openai",  # or "anthropic", "azure", "local"
    model="gpt-4",
    temperature=0.1,
    max_tokens=2000
)

# Create orchestrator with AI capabilities
orchestrator = AdvancedOrchestrator()
```

### Your First AI-Powered Workflow

```python
# Define workflow with AI assistance
workflow = {
    "type": "intelligent_scraping",
    "name": "AI-Guided Data Extraction",
    "ai_config": {
        "enable_conversation": True,
        "auto_adapt": True,
        "error_recovery": True
    },
    "tasks": [
        {
            "id": "navigate",
            "type": "navigate",
            "definition": {"url": "https://example.com"},
            "ai_assistance": {
                "verify_page_load": True,
                "handle_popups": True
            }
        },
        {
            "id": "extract_data",
            "type": "ai_extract",
            "definition": {
                "instruction": "Extract all product information including prices, descriptions, and availability",
                "output_format": "structured_json"
            }
        }
    ]
}

# Execute with AI guidance
result = await orchestrator.execute_intelligent_workflow(workflow, config)
```

## 🤖 LLM Provider Configuration

### OpenAI Integration

```python
llm_config = {
    "provider": "openai",
    "api_key": "your-openai-api-key",
    "model": "gpt-4",
    "temperature": 0.1,
    "max_tokens": 2000,
    "timeout": 30,
    "retry_attempts": 3
}
```

### Anthropic Claude Integration

```python
llm_config = {
    "provider": "anthropic",
    "api_key": "your-anthropic-api-key", 
    "model": "claude-3-sonnet-20240229",
    "temperature": 0.1,
    "max_tokens": 2000,
    "timeout": 30
}
```

### Azure OpenAI Integration

```python
llm_config = {
    "provider": "azure",
    "api_key": "your-azure-api-key",
    "endpoint": "https://your-resource.openai.azure.com/",
    "deployment_name": "gpt-4",
    "api_version": "2024-02-15-preview"
}
```

### Local LLM Integration

```python
llm_config = {
    "provider": "local",
    "endpoint": "http://localhost:11434",  # Ollama endpoint
    "model": "llama2:13b",
    "temperature": 0.1,
    "context_length": 4096
}
```

## 🧠 AI-Powered Features

### Conversational Workflows

Enable natural language interaction during workflow execution:

```python
conversation_config = {
    "enable_conversation": True,
    "interaction_points": [
        "before_execution",
        "on_error", 
        "decision_points",
        "after_completion"
    ],
    "conversation_style": {
        "tone": "professional",
        "detail_level": "moderate",
        "include_suggestions": True
    }
}
```

### Intelligent Error Recovery

Let AI diagnose and fix issues automatically:

```python
error_recovery_config = {
    "enable_auto_recovery": True,
    "max_recovery_attempts": 3,
    "recovery_strategies": [
        "retry_with_delay",
        "alternative_approach", 
        "graceful_degradation",
        "human_intervention"
    ],
    "learning_enabled": True
}
```

### Dynamic Workflow Adaptation

Allow AI to optimize workflows in real-time:

```python
adaptation_config = {
    "enable_auto_optimization": True,
    "optimization_targets": ["speed", "reliability", "accuracy"],
    "adaptation_triggers": [
        "performance_degradation",
        "error_patterns",
        "context_changes"
    ],
    "learning_mode": "continuous"
}
```

## 🎨 Advanced AI Patterns

### Context-Aware Task Execution

```python
# AI analyzes page context and adapts extraction strategy
smart_extraction_task = {
    "id": "smart_extract",
    "type": "ai_context_extract",
    "definition": {
        "goal": "Extract product catalog data",
        "context_analysis": {
            "analyze_page_structure": True,
            "identify_data_patterns": True,
            "detect_pagination": True,
            "handle_dynamic_content": True
        },
        "extraction_strategy": "adaptive",
        "output_validation": {
            "required_fields": ["name", "price", "description"],
            "data_quality_checks": True
        }
    }
}
```

### AI-Guided Navigation

```python
# Let AI figure out how to navigate complex sites
navigation_task = {
    "id": "ai_navigate",
    "type": "intelligent_navigation",
    "definition": {
        "goal": "Find and access the product catalog section",
        "navigation_strategy": {
            "analyze_site_structure": True,
            "follow_semantic_clues": True,
            "handle_authentication": True,
            "bypass_obstacles": True
        },
        "success_criteria": [
            "page_contains_products",
            "navigation_path_recorded"
        ]
    }
}
```

### Multi-Step Reasoning

```python
# AI performs complex multi-step analysis
reasoning_task = {
    "id": "ai_analysis",
    "type": "multi_step_reasoning",
    "definition": {
        "analysis_goal": "Competitive price analysis",
        "reasoning_steps": [
            "extract_competitor_prices",
            "identify_comparable_products", 
            "calculate_price_differences",
            "generate_insights"
        ],
        "output_format": "analytical_report"
    }
}
```

## 🔧 Configuration Reference

### LLM Provider Settings

```yaml
llm:
  provider: "openai"  # openai, anthropic, azure, local
  model: "gpt-4"
  temperature: 0.1
  max_tokens: 2000
  timeout: 30
  retry_attempts: 3
  
  # Provider-specific settings
  openai:
    api_key: "${OPENAI_API_KEY}"
    organization: "${OPENAI_ORG_ID}"
    
  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
    
  azure:
    api_key: "${AZURE_OPENAI_API_KEY}"
    endpoint: "${AZURE_OPENAI_ENDPOINT}"
    deployment_name: "gpt-4"
    api_version: "2024-02-15-preview"
    
  local:
    endpoint: "http://localhost:11434"
    model: "llama2:13b"
```

### Conversation Settings

```yaml
conversation:
  enabled: true
  interaction_points:
    - "before_execution"
    - "on_error"
    - "decision_points"
    - "after_completion"
  
  style:
    tone: "professional"  # casual, professional, technical
    detail_level: "moderate"  # brief, moderate, detailed
    include_suggestions: true
    include_explanations: true
  
  context:
    max_history: 10
    include_workflow_state: true
    include_performance_metrics: true
```

### Error Recovery Settings

```yaml
error_recovery:
  enabled: true
  max_attempts: 3
  strategies:
    - "retry_with_delay"
    - "alternative_approach"
    - "graceful_degradation"
    - "human_intervention"
  
  learning:
    enabled: true
    pattern_detection: true
    solution_caching: true
    improvement_suggestions: true
```

## 📊 Monitoring AI Performance

### LLM Usage Metrics

```python
# Monitor LLM API usage and costs
metrics = await orchestrator.get_llm_metrics()
print(f"Total tokens used: {metrics['total_tokens']}")
print(f"API calls made: {metrics['api_calls']}")
print(f"Estimated cost: ${metrics['estimated_cost']}")
print(f"Average response time: {metrics['avg_response_time']}ms")
```

### AI Decision Tracking

```python
# Track AI decisions and their outcomes
decisions = await orchestrator.get_ai_decisions()
for decision in decisions:
    print(f"Decision: {decision['type']}")
    print(f"Context: {decision['context']}")
    print(f"Outcome: {decision['outcome']}")
    print(f"Success: {decision['success']}")
```

## 🚀 Best Practices

### 1. Prompt Engineering

```python
# Use clear, specific prompts
good_prompt = """
Analyze this e-commerce product page and extract:
1. Product name (exact text)
2. Current price (numerical value only)
3. Availability status (in stock/out of stock)
4. Product description (first paragraph only)

Return as JSON with keys: name, price, availability, description
"""

# Avoid vague prompts
bad_prompt = "Get product info from this page"
```

### 2. Context Management

```python
# Provide relevant context
context = {
    "page_type": "product_listing",
    "site_structure": "e-commerce",
    "previous_actions": ["navigated_to_category", "applied_filters"],
    "current_goal": "extract_product_data"
}
```

### 3. Error Handling

```python
# Implement graceful fallbacks
try:
    result = await ai_task.execute()
except LLMTimeoutError:
    # Fallback to traditional extraction
    result = await fallback_extraction()
except LLMQuotaExceededError:
    # Switch to local model
    result = await local_llm_extraction()
```

## 🔗 Next Steps

- **[Multi-Modal Processing](multimodal.md)** - Work with images, audio, and documents
- **[Dashboard & Monitoring](dashboard.md)** - Monitor AI performance and costs
- **[Troubleshooting](troubleshooting.md)** - Solve AI-related issues

## 📚 Additional Resources

- **[LLM Provider Documentation](https://docs.automation-framework.com/llm-providers)**
- **[Prompt Engineering Guide](https://docs.automation-framework.com/prompt-engineering)**
- **[AI Performance Optimization](https://docs.automation-framework.com/ai-optimization)**
