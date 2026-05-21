"""
FILE: app/routes.py
PURPOSE: Defines all HTTP endpoints (routes) for the Task Manager API.

WHAT IS A ROUTER?
  Instead of defining all routes directly on the FastAPI app,
  we use APIRouter — a mini-app that groups related routes together.
  In main.py we 'include' this router into the main app.
  This keeps large apps organized (e.g., one router per feature).

HTTP METHODS:
  - GET    : Read data (safe, no side effects)
  - POST   : Create new data
  - PUT    : Update existing data
  - DELETE : Remove data

STATUS CODES:
  - 200 OK           : Success (GET, PUT, DELETE)
  - 201 Created      : Successfully created a new resource (POST)
  - 204 No Content   : Success but nothing to return (DELETE)
  - 404 Not Found    : Resource doesn't exist
  - 422 Unprocessable: Validation error (Pydantic catches this automatically)
"""

from fastapi import APIRouter, HTTPException, status

from app.models import TaskCreate, TaskResponse, TaskUpdate

# We import the singleton service instance
from app.service import TaskNotFoundError, task_service

# All routes in this file will have /tasks or /health prefix
# (actually prefix is added in main.py — we use no prefix here for simplicity)
router = APIRouter()


# -----------------------------------------------------------------------
# HEALTH CHECK
# -----------------------------------------------------------------------


@router.get(
    "/health",
    summary="Health Check",
    description="Returns API status. Used by load balancers and monitoring tools.",
)
def health_check() -> dict[str, str]:
    """
    Simple liveness probe.

    WHY A HEALTH ENDPOINT?
      Docker, Kubernetes, and cloud platforms ping /health to know
      if your service is alive. If it returns 200, all is well.
    """
    return {"status": "healthy", "service": "task-manager"}


# -----------------------------------------------------------------------
# LIST ALL TASKS
# -----------------------------------------------------------------------


@router.get(
    "/tasks",
    response_model=list[TaskResponse],
    summary="List Tasks",
    description="Returns all tasks sorted by creation time.",
)
def list_tasks() -> list[TaskResponse]:
    """
    GET /tasks — Retrieve the full list of tasks.

    response_model=list[TaskResponse] tells FastAPI:
      "Filter and shape the response using TaskResponse schema."
    """
    return task_service.list_tasks()


# -----------------------------------------------------------------------
# CREATE A TASK
# -----------------------------------------------------------------------


@router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Task",
    description="Creates a new task. Title is required.",
)
def create_task(payload: TaskCreate) -> TaskResponse:
    """
    POST /tasks — Create a new task.

    FastAPI automatically:
      1. Reads the JSON body
      2. Validates it against TaskCreate (Pydantic)
      3. Passes the validated object as 'payload'
    """
    return task_service.create_task(payload)


# -----------------------------------------------------------------------
# GET A SINGLE TASK
# -----------------------------------------------------------------------


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="Get Task",
    description="Retrieve a single task by its ID.",
)
def get_task(task_id: int) -> TaskResponse:
    """
    GET /tasks/{task_id} — Fetch one task by ID.

    PATH PARAMETERS:
      {task_id} in the URL is automatically extracted and passed as
      the 'task_id' argument. FastAPI also validates it's an integer.
    """
    try:
        return task_service.get_task(task_id)
    except TaskNotFoundError:
        # Convert our domain exception into an HTTP 404 response
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )


# -----------------------------------------------------------------------
# UPDATE A TASK
# -----------------------------------------------------------------------


@router.put(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    summary="Update Task",
    description="Update one or more fields of an existing task.",
)
def update_task(task_id: int, payload: TaskUpdate) -> TaskResponse:
    """
    PUT /tasks/{task_id} — Partially update a task.

    Combines a PATH parameter (task_id) with a REQUEST BODY (payload).
    Only fields present in the body are changed.
    """
    try:
        return task_service.update_task(task_id, payload)
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )


# -----------------------------------------------------------------------
# DELETE A TASK
# -----------------------------------------------------------------------


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Task",
    description="Permanently delete a task by ID.",
)
def delete_task(task_id: int) -> None:
    """
    DELETE /tasks/{task_id} — Remove a task.

    Returns 204 No Content on success (nothing to return).
    Returns 404 if the ID doesn't exist.
    """
    try:
        task_service.delete_task(task_id)
    except TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
