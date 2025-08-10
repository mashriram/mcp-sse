import sys
sys.path.insert(0, "/app/workflow_engine")

import asyncio
from app.yaml_parser import load_workflow_from_yaml
from app.executor import WorkflowExecutor

async def main():
    # Load the MCP workflow
    try:
        workflow = load_workflow_from_yaml("/app/workflow_engine/mcp_workflow.yaml")
        print("MCP workflow loaded successfully.")

        # Create an executor instance
        executor = WorkflowExecutor(workflow)
        print("WorkflowExecutor instantiated.")

        # Define the initial data for the input node
        initial_data = {
            "input_args": {
                "latitude": 47.6587,
                "longitude": -117.4260
            }
        }

        # Execute the workflow
        print("\nExecuting MCP workflow...")
        print("NOTE: This test requires the weather.py MCP server to be running on http://localhost:8080")
        final_output = await executor.execute(initial_data)

        print("\nWorkflow execution finished.")
        print("Final Output:", final_output)

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
