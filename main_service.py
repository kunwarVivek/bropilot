from typing import List
from fastapi import FastAPI , APIRouter, HTTPException
from pydantic import BaseModel
from workflows.sample_workflow import get_available_tasks, run_workflow
import asyncio
from tasks.definitions import get_task_templates

app = FastAPI()

class WorkflowRequest(BaseModel):
    flows : List[str]


@app.post("/run_workflow")
async def run_workflows(req: WorkflowRequest):
    try:
        print(f"Starting workflow with flows: {req.flows}")
        result = await run_workflow(req.flows)
        return {"status": "completed", "results": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/get_available_tasks")
def get_all_workflows():
    try:
        tasks =  get_available_tasks()
        return {"status":"completed" , "result": tasks}
    
    except Exception as ex:
        raise HTTPException(status_code=500, detail=str(ex))
