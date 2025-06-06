# Quick Start Guide

Get up and running with the Browser Automation Framework in just 5 minutes!

## 🎯 What You'll Learn

- How to install and start the framework
- Create your first intelligent workflow
- Use AI-powered features
- Monitor execution and results

## 📋 Prerequisites

Before you begin, ensure you have:

- **Docker & Docker Compose** installed
- **4GB+ RAM** available
- **LLM API Key** (OpenAI, Anthropic, or similar)
- **Basic Python knowledge** (helpful but not required)

## 🚀 Step 1: Installation

### Clone and Setup
```bash
# Clone the repository
git clone https://github.com/your-org/browser-automation-framework.git
cd browser-automation-framework

# Copy environment template
cp .env.example .env
```

### Configure Environment
Edit the `.env` file with your settings:

```bash
# Basic Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO

# LLM Configuration (choose one)
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here

# OR use Anthropic
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Database Configuration (auto-configured with Docker)
DATABASE_URL=postgresql://automation:password@postgres:5432/automation_db
REDIS_URL=redis://redis:6379/0

# Feature Flags
ENABLE_LLM_INTEGRATION=true
ENABLE_MULTIMODAL=true
ENABLE_ERROR_RECOVERY=true
ENABLE_ANALYTICS=true
```

### Start the System
```bash
# Start all services
docker-compose up -d

# Check system health
curl http://localhost:8001/health
```

You should see a response like:
```json
{
  "status": "healthy",
  "timestamp": "2024-12-19T10:00:00Z",
  "components": {
    "database": {"status": "healthy"},
    "redis": {"status": "healthy"},
    "analytics": {"status": "healthy"},
    "orchestrator": {"status": "healthy"}
  }
}
```

## 🎨 Step 2: Access the Dashboard

Open your browser and navigate to:
- **Main Dashboard**: http://localhost:3000 (Grafana)
- **API Documentation**: http://localhost:8000/docs
- **Health Monitoring**: http://localhost:8001/health

### Dashboard Overview

```mermaid
graph LR
    subgraph "User Interface"
        DASH[Dashboard<br/>localhost:3000]
        API[API Docs<br/>localhost:8000/docs]
        HEALTH[Health Check<br/>localhost:8001/health]
    end
    
    subgraph "Core Services"
        MAIN[Main App<br/>Port 8000]
        MONITOR[Monitoring<br/>Port 8001]
        DB[(Database<br/>Port 5432)]
        REDIS[(Redis<br/>Port 6379)]
    end
    
    DASH --> MAIN
    API --> MAIN
    HEALTH --> MONITOR
    MAIN --> DB
    MAIN --> REDIS
```

## 🤖 Step 3: Create Your First Workflow

### Simple Web Scraping Workflow

Create a file called `my_first_workflow.py`:

```python
import asyncio
from src.intelligence.advanced_orchestrator import (
    AdvancedOrchestrator, 
    IntelligentWorkflowConfig
)
from src.implementations.mock_providers import MockWorkflowEngine, MockTaskExecutor, MockLLMProvider

async def main():
    # Initialize the orchestrator
    orchestrator = AdvancedOrchestrator(
        workflow_engine=MockWorkflowEngine(),
        task_executor=MockTaskExecutor(),
        llm_provider=MockLLMProvider()
    )
    
    await orchestrator.start()
    
    try:
        # Define your workflow
        workflow = {
            "type": "web_scraping",
            "name": "My First Workflow",
            "description": "Extract title from a webpage",
            "tasks": [
                {
                    "id": "navigate_to_site",
                    "name": "Navigate to Website",
                    "type": "navigate",
                    "priority": "high",
                    "definition": {
                        "url": "https://example.com",
                        "wait_for": "body"
                    }
                },
                {
                    "id": "take_screenshot",
                    "name": "Take Screenshot",
                    "type": "screenshot",
                    "priority": "normal",
                    "definition": {
                        "element": "body",
                        "full_page": True
                    }
                },
                {
                    "id": "extract_title",
                    "name": "Extract Page Title",
                    "type": "extract_data",
                    "priority": "high",
                    "definition": {
                        "selector": "title",
                        "attribute": "text"
                    }
                }
            ],
            "dependencies": [
                {"from": "navigate_to_site", "to": "take_screenshot", "type": "hard"},
                {"from": "navigate_to_site", "to": "extract_title", "type": "hard"}
            ],
            "execution_mode": "hybrid",
            "max_parallel": 2
        }
        
        # Configure AI-powered execution
        config = IntelligentWorkflowConfig(
            enable_llm_assistance=True,      # AI workflow analysis
            enable_multimodal=True,          # Image/audio processing
            enable_error_recovery=True,      # Automatic error recovery
            enable_analytics=True,           # Performance tracking
            auto_optimize=True,              # Automatic optimization
            learning_mode=True,              # Learn from execution
            conversation_context={
                "user": "first_time_user",
                "goal": "learn_web_scraping"
            }
        )
        
        # Execute the workflow
        print("🚀 Starting workflow execution...")
        result = await orchestrator.execute_intelligent_workflow(
            workflow_definition=workflow,
            config=config,
            context={"source": "quick_start_guide"}
        )
        
        # Display results
        print("\n✅ Workflow completed!")
        print(f"Success: {result['result']['success']}")
        print(f"Execution Time: {result['execution_time']:.2f} seconds")
        print(f"Workflow ID: {result['workflow_id']}")
        
        # Show AI insights
        insights = result['intelligence_insights']
        if insights.get('llm_analysis'):
            print("\n🤖 AI Analysis:")
            print(insights['llm_analysis']['analysis'][:200] + "...")
        
        # Show performance metrics
        perf_metrics = result['performance_metrics']
        if perf_metrics:
            print(f"\n📊 Performance:")
            print(f"Average Execution Time: {perf_metrics.get('average_execution_time', 0):.2f}s")
            print(f"Total Executions: {perf_metrics.get('total_executions', 0)}")
    
    finally:
        await orchestrator.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### Run Your Workflow
```bash
# Execute your first workflow
python my_first_workflow.py
```

Expected output:
```
🚀 Starting workflow execution...

✅ Workflow completed!
Success: True
Execution Time: 3.45 seconds
Workflow ID: 550e8400-e29b-41d4-a716-446655440000

🤖 AI Analysis:
Workflow Analysis:
1. The workflow appears well-structured with clear task dependencies
2. Potential optimization: Tasks take_screenshot and extract_title could run in parallel...

📊 Performance:
Average Execution Time: 3.45s
Total Executions: 1
```

## 🎯 Step 4: Understanding the Workflow

### Workflow Structure

```mermaid
graph TD
    A[navigate_to_site] --> B[take_screenshot]
    A --> C[extract_title]
    
    subgraph "Task Details"
        A1["🌐 Navigate<br/>URL: example.com<br/>Priority: High"]
        B1["📸 Screenshot<br/>Element: body<br/>Priority: Normal"]
        C1["📝 Extract<br/>Selector: title<br/>Priority: High"]
    end
    
    A -.-> A1
    B -.-> B1
    C -.-> C1
    
    style A fill:#e1f5fe
    style B fill:#f3e5f5
    style C fill:#e8f5e8
```

### Execution Flow

```mermaid
sequenceDiagram
    participant U as User
    participant O as Orchestrator
    participant L as LLM
    participant E as Executor
    participant A as Analytics
    
    U->>O: Execute Workflow
    O->>L: Analyze Workflow
    L-->>O: Optimization Suggestions
    O->>E: Execute Tasks (Parallel)
    
    par Navigate Task
        E->>E: Navigate to URL
    and Screenshot Task
        E->>E: Wait for Navigate
        E->>E: Take Screenshot
    and Extract Task
        E->>E: Wait for Navigate
        E->>E: Extract Title
    end
    
    E-->>O: Task Results
    O->>A: Record Metrics
    O->>L: Post-execution Analysis
    L-->>O: Insights & Recommendations
    O-->>U: Complete Results
```

## 🔍 Step 5: Monitor Your Workflow

### View Real-time Metrics
1. Open Grafana: http://localhost:3000
2. Login with `admin/admin`
3. Navigate to "Automation Framework Dashboard"

### Check Execution Logs
```bash
# View application logs
docker-compose logs -f automation-framework

# View specific service logs
docker-compose logs -f postgres
docker-compose logs -f redis
```

### API Monitoring
```bash
# Check system status
curl http://localhost:8001/health | jq

# Get workflow statistics
curl http://localhost:8000/api/v1/workflows/stats | jq

# View recent executions
curl http://localhost:8000/api/v1/executions?limit=10 | jq
```

## 🎨 Step 6: Explore Advanced Features

### Multi-Modal Processing
```python
# Add image analysis to your workflow
{
    "id": "analyze_screenshot",
    "name": "Analyze Screenshot with AI",
    "type": "image_analysis",
    "definition": {
        "analysis_type": "ui",
        "extract_text": True,
        "identify_elements": True
    }
}
```

### Error Recovery
```python
# Configure intelligent error recovery
config = IntelligentWorkflowConfig(
    enable_error_recovery=True,
    recovery_strategies=["retry", "fallback", "repair"],
    max_recovery_attempts=3
)
```

### Conversation with AI
```python
# Enable conversational workflow assistance
config = IntelligentWorkflowConfig(
    enable_llm_assistance=True,
    conversation_context={
        "user_expertise": "beginner",
        "preferred_style": "detailed_explanations",
        "focus_areas": ["performance", "reliability"]
    }
)
```

## 🎯 Next Steps

Congratulations! You've successfully:
- ✅ Installed the framework
- ✅ Created your first intelligent workflow
- ✅ Executed it with AI assistance
- ✅ Monitored the results

### Continue Learning
- **[User Guide](user-guide.md)** - Comprehensive feature documentation
- **[Workflow Creation](workflow-creation.md)** - Advanced workflow patterns
- **[LLM Integration](llm-integration.md)** - AI-powered automation
- **[Multi-Modal Processing](multimodal.md)** - Working with media content
- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions

### Join the Community
- **GitHub**: [Report issues and contribute](https://github.com/your-org/browser-automation-framework)
- **Discussions**: [Ask questions and share experiences](https://github.com/your-org/browser-automation-framework/discussions)
- **Examples**: [Explore more workflow examples](https://github.com/your-org/browser-automation-framework/tree/main/examples)

## 🆘 Need Help?

If you encounter any issues:

1. **Check the logs**: `docker-compose logs -f automation-framework`
2. **Verify health**: `curl http://localhost:8001/health`
3. **Review configuration**: Ensure your `.env` file is correct
4. **Consult troubleshooting**: [Troubleshooting Guide](troubleshooting.md)
5. **Ask for help**: [GitHub Discussions](https://github.com/your-org/browser-automation-framework/discussions)

Happy automating! 🚀
