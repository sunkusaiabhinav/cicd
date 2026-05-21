"""
FILE: app/models.py
PURPOSE: Defines the data shapes (schemas) for API requests and responses.

WHAT IS PYDANTIC?
  Pydantic is a Python library that validates data automatically.
  When a user sends JSON to your API, Pydantic checks:
    - Are all required fields present?
    - Are the types correct (e.g., is 'title' really a string)?
    - Do values pass any custom rules (e.g., title can't be empty)?
  If validation fails, FastAPI automatically returns a 422 error with details.

WHAT IS A BaseModel?
  Every Pydantic model inherits from BaseModel.
  Think of it as a smart dictionary with type-checking built in.

WHY SEPARATE CREATE / UPDATE / RESPONSE?
  - TaskCreate  : what the CLIENT sends when creating a task (no ID yet)
  - TaskUpdate  : what the CLIENT sends when editing a task (all fields optional)
  - TaskResponse: what the SERVER sends back (includes ID + timestamps)
  This separation keeps the API clean and prevents clients from spoofing IDs.
"""

from datetime import datetime

# Field adds extra validation metadata (min length, description, etc.)
from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    """
    Schema for creating a new task.
    The client must provide 'title'; 'description' and 'completed' are optional.
    """

    # Field(min_length=1) ensures the title is NOT an empty string
    title: str = Field(..., min_length=1, max_length=100, description="Task title")

    # Optional field — defaults to empty string if not provided
    description: str = Field(default="", max_length=500, description="Task details")

    # New tasks are not completed by default
    completed: bool = Field(default=False, description="Completion status")


class TaskUpdate(BaseModel):
    """
    Schema for updating an existing task.
    ALL fields are optional — client can update just the title, just completed, etc.
    'None' means 'not provided' (don't change this field).
    """

    title: str | None = Field(
        default=None, min_length=1, max_length=100, description="New title"
    )
    description: str | None = Field(default=None, max_length=500)
    completed: bool | None = Field(default=None)


class TaskResponse(BaseModel):
    """
    Schema for API responses — what the server sends back to clients.
    Includes the server-generated 'id' and timestamps.
    """

    id: int = Field(description="Unique task identifier")
    title: str
    description: str
    completed: bool
    created_at: datetime = Field(description="When the task was created")
    updated_at: datetime = Field(description="When the task was last modified")
