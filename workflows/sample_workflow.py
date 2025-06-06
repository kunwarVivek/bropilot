import asyncio
import time
import uuid
from fastapi import HTTPException
from tenacity import RetryError
from utils.task_runner import run_task, get_execution_status
from tasks.definitions import get_task_templates
from dotenv import dotenv_values, load_dotenv

# Import enhanced workflow if available
try:
    from workflows.enhanced_workflow import (
        run_workflow as enhanced_run_workflow,
        get_available_tasks as enhanced_get_available_tasks,
        get_workflow_engine
    )
    from src.execution.feature_flags import get_feature_flag_manager, FeatureFlag
    ENHANCED_WORKFLOW_AVAILABLE = True
except ImportError:
    ENHANCED_WORKFLOW_AVAILABLE = False

load_dotenv()

def get_llm():
    from langchain_google_genai import ChatGoogleGenerativeAI
    import os
    from langchain_core.rate_limiters import InMemoryRateLimiter

    rate_limiter = InMemoryRateLimiter(
    requests_per_second=1,
    check_every_n_seconds=0.1,
    max_bucket_size=10
    )
    return ChatGoogleGenerativeAI(
        # model="models/gemini-2.5-pro-exp-03-25",
        model="models/gemini-2.5-flash-preview-04-17",
        # model="models/gemini-2.0-pro-exp",
        google_api_key=os.environ["GEMINI_API_KEY"],
        rate_limiter=rate_limiter
    )

async def run_workflow(flow_sequence, **kwargs):
    """
    Execute a workflow using enhanced workflow engine when available.

    This function automatically chooses between the enhanced workflow engine
    and the legacy system based on feature flags and availability.
    """
    # Check if enhanced workflow should be used
    if ENHANCED_WORKFLOW_AVAILABLE:
        try:
            flag_manager = get_feature_flag_manager()

            # Check if enhanced workflow is enabled
            if flag_manager.is_enabled(FeatureFlag.USE_ENHANCED_WORKFLOW):
                print("Using enhanced workflow engine")
                result = await enhanced_run_workflow(flow_sequence, **kwargs)

                # Return in legacy format for backward compatibility
                if "task_results" in result:
                    return result["task_results"]
                else:
                    return {"error": result.get("error", "Unknown error")}

        except Exception as e:
            print(f"Enhanced workflow failed, falling back to legacy: {e}")

            # Check if fallback is enabled
            if flag_manager.is_enabled(FeatureFlag.FALLBACK_TO_LEGACY):
                pass  # Continue to legacy execution
            else:
                raise  # Re-raise if fallback is disabled

    # Use legacy workflow execution
    print("Using legacy workflow engine")
    return await _run_workflow_legacy(flow_sequence)


async def _run_workflow_legacy(flow_sequence):
    """Execute workflow using the original legacy system."""
    env_vars = dotenv_values(".env")
    task_templates = get_task_templates(env_vars)

    # Validate tasks
    invalid_tasks = [task for task in flow_sequence if task not in task_templates]
    if invalid_tasks:
        raise HTTPException(status_code=400, detail=f"Invalid tasks: {', '.join(invalid_tasks)}")

    # Test LLM
    llm = get_llm()
    try:
        response = llm.invoke("What is the capital of France?")
        print(response)
    except RetryError:
        raise HTTPException(status_code=503, detail="The AI model is currently overloaded. Please try again shortly.")

    # Generate a unique workflow id
    workflow_id = str(uuid.uuid4())
    print(f"Starting legacy workflow {workflow_id} with tasks: {flow_sequence}")

    results = {}

    # Get auth task content
    auth_task = task_templates["auth"]


    for task_index, task_name in enumerate(flow_sequence):

        task_content = task_templates[task_name]
        
        combined_task = f"""
# ======================================================
# AUTHENTICATION STEP (REQUIRED)
# ======================================================
# First, you must authenticate to the system:

{auth_task}

# ======================================================
# TASK: {task_name.upper()}
# ======================================================
# After successful authentication, complete this task:

{task_content}

# ======================================================
# END OF TASK
# ======================================================
"""
        
        start_time = time.time()
        task_log_dir = f"logs/{task_name}_{workflow_id}"
        
        try:
            task_result = await asyncio.wait_for(
                run_task(combined_task, llm, save_path=task_log_dir),
                timeout=400  
            )
            
            results[task_name] = {
                "status": "completed",
                "result": task_result
            }
            
        except asyncio.TimeoutError:
            print(f"Task {task_name} timed out")
            results[task_name] = {
                "status": "timeout",
                "result": f"Task timed out after 15 minutes"
            }
            
        except Exception as e:
            print(f"Error in task {task_name}: {str(e)}")
            results[task_name] = {
                "status": "error",
                "result": str(e)
            }
        
        time_range = time.time() - start_time
        print(f"Completed task {task_name} in {time_range:.2f} seconds with status {results[task_name]['status']}")
    
    print(f"Workflow {workflow_id} completed")
    return results

def get_available_tasks():
    """
    Get available tasks using enhanced workflow engine when available.

    This function automatically chooses between the enhanced workflow engine
    and the legacy system based on feature flags and availability.
    """
    # Check if enhanced workflow should be used
    if ENHANCED_WORKFLOW_AVAILABLE:
        try:
            flag_manager = get_feature_flag_manager()

            # Check if enhanced workflow is enabled
            if flag_manager.is_enabled(FeatureFlag.USE_ENHANCED_WORKFLOW):
                return enhanced_get_available_tasks()

        except Exception as e:
            print(f"Enhanced workflow failed, falling back to legacy: {e}")

    # Use legacy task retrieval
    env_vars = dotenv_values(".env")
    task_templates = get_task_templates(env_vars)
    return {"tasks": list(task_templates.keys())}


# Utility functions for migration and monitoring
def get_workflow_status():
    """Get the current workflow system status."""
    status = {
        "enhanced_workflow_available": ENHANCED_WORKFLOW_AVAILABLE,
        "current_mode": "legacy"
    }

    if ENHANCED_WORKFLOW_AVAILABLE:
        try:
            flag_manager = get_feature_flag_manager()

            if flag_manager.is_enabled(FeatureFlag.USE_ENHANCED_WORKFLOW):
                status["current_mode"] = "enhanced"

            status["migration_status"] = flag_manager.get_migration_status()
            status["enabled_flags"] = flag_manager.get_enabled_flags()

        except Exception as e:
            status["error"] = str(e)

    # Add execution status
    status["execution_status"] = get_execution_status()

    return status


def enable_enhanced_workflow() -> dict:
    """Enable enhanced workflow features."""
    if not ENHANCED_WORKFLOW_AVAILABLE:
        return {"error": "Enhanced workflow not available"}

    try:
        flag_manager = get_feature_flag_manager()
        flag_manager.enable_flag(FeatureFlag.USE_ENHANCED_WORKFLOW, "Manual enable via API")

        return {
            "success": True,
            "message": "Enhanced workflow enabled",
            "status": get_workflow_status()
        }

    except Exception as e:
        return {"error": str(e)}
