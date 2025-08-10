import yaml
from typing import Dict, Any
from .models import Workflow

def load_workflow_from_yaml(file_path: str) -> Workflow:
    """
    Loads a workflow definition from a YAML file and returns a Workflow object.

    Args:
        file_path: The path to the YAML file.

    Returns:
        A Workflow object representing the workflow.
    """
    with open(file_path, 'r') as f:
        data = yaml.safe_load(f)
    return Workflow(**data)

def save_workflow_to_yaml(workflow: Workflow, file_path: str) -> None:
    """
    Saves a Workflow object to a YAML file.

    Args:
        workflow: The Workflow object to save.
        file_path: The path to the output YAML file.
    """
    with open(file_path, 'w') as f:
        yaml.dump(workflow.dict(), f, sort_keys=False)

def load_workflow_from_dict(data: Dict[str, Any]) -> Workflow:
    """
    Loads a workflow definition from a dictionary and returns a Workflow object.

    Args:
        data: The dictionary containing the workflow data.

    Returns:
        A Workflow object representing the workflow.
    """
    return Workflow(**data)
