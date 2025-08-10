from fastapi import FastAPI, HTTPException, Body
from typing import Dict, Any

from .models import Workflow
from .executor import WorkflowExecutor, WorkflowExecutionError
from .yaml_parser import load_workflow_from_dict

app = FastAPI(
    title="Workflow Engine API",
    description="An API for defining and executing workflows.",
    version="0.1.0",
)

@app.post("/workflows/execute", tags=["Execution"])
async def execute_workflow(
    workflow_data: Workflow,
    initial_data: Dict[str, Any] = Body(None, description="Initial data for InputNodes")
):
    """
    Executes a given workflow and returns the final output.
    """
    try:
        print("Received workflow execution request:", workflow_data.name)
        executor = WorkflowExecutor(workflow_data)
        final_output = await executor.execute(initial_data)
        return {"status": "success", "output": final_output}
    except WorkflowExecutionError as e:
        raise HTTPException(status_code=400, detail=f"Workflow Error: {e}")
    except Exception as e:
        # Catch any other unexpected errors during execution
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

@app.get("/workflows", tags=["Management"])
async def list_workflows():
    """
    (Placeholder) Lists all saved workflows.
    """
    return {"message": "Listing workflows is not yet implemented."}

@app.post("/workflows", tags=["Management"])
async def save_workflow(workflow: Workflow):
    """
    (Placeholder) Saves a new workflow definition.
    """
    return {"message": f"Workflow '{workflow.name}' would be saved, but this is not yet implemented."}

@app.get("/", tags=["General"])
async def read_root():
    """
    Root endpoint with a welcome message.
    """
    return {"message": "Welcome to the Workflow Engine API!"}
