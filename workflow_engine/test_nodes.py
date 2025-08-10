import sys
sys.path.insert(0, "/app/workflow_engine")

from app.yaml_parser import load_workflow_from_yaml
from app.executor import WorkflowExecutor

# Load the LLM workflow
try:
    workflow = load_workflow_from_yaml("/app/workflow_engine/llm_workflow.yaml")
    print("LLM workflow loaded successfully.")

    # Create an executor instance
    executor = WorkflowExecutor(workflow)
    print("WorkflowExecutor instantiated.")

    # Define the initial data for the input node
    initial_data = {
        "input_prompt": "Tell me a joke."
    }

    # Execute the workflow
    print("\nExecuting LLM workflow...")
    final_output = executor.execute(initial_data)

    print("\nWorkflow execution finished.")
    print("Final Output:", final_output)

except Exception as e:
    print(f"An error occurred: {e}")
