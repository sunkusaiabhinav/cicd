"""
FILE: app/service.py
PURPOSE: Business logic layer — all task CRUD operations live here.

WHY A SEPARATE SERVICE LAYER?
  Instead of putting all the logic inside the route handlers (endpoints),
  we separate it into a 'service'. This means:
    1. Routes stay thin — they just receive requests and call the service.
    2. Tests can test the service logic without running the web server.
    3. If we later swap in-memory storage for a database, only this file changes.

HOW IS DATA STORED?
  We use a plain Python dictionary: { id -> TaskRecord }
  This is 'in-memory' storage — it resets when the server restarts.
  Perfect for learning; a real app would use a database (PostgreSQL, etc.)

WHAT IS TaskRecord?
  An internal dataclass that holds the full task data including timestamps.
  We intentionally separate internal records (TaskRecord) from API schemas
  (TaskResponse) — keeps API and storage concerns separate.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

# We import our Pydantic models to use in method signatures
from app.models import TaskCreate, TaskResponse, TaskUpdate


@dataclass
class TaskRecord:
    """
    Internal storage representation of a task.

    WHAT IS A DATACLASS?
      @dataclass auto-generates __init__, __repr__, __eq__ for us.
      We just declare the fields and their types.
    """

    id: int
    title: str
    description: str
    completed: bool
    # field(default_factory=...) is used for mutable defaults
    # We use timezone-aware UTC timestamps to avoid ambiguity
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_response(self) -> TaskResponse:
        """Convert internal record to the Pydantic response model."""
        return TaskResponse(
            id=self.id,
            title=self.title,
            description=self.description,
            completed=self.completed,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class TaskNotFoundError(Exception):
    """
    Custom exception raised when a task ID doesn't exist.

    WHY CUSTOM EXCEPTIONS?
      Rather than using generic Exception or returning None,
      a named exception makes error handling explicit and readable.
      The route layer catches this and returns a 404 HTTP response.
    """

    pass


class TaskService:
    """
    Service class that manages all task operations.

    WHAT IS self._tasks?
      A private dictionary mapping task IDs (int) to TaskRecord objects.
      The underscore prefix (_tasks) signals 'this is internal — don't
      access it directly from outside the class'.

    WHAT IS self._next_id?
      A simple auto-increment counter — just like a database primary key.
    """

    def __init__(self) -> None:
        # Private storage — key: task_id, value: TaskRecord
        self._tasks: dict[int, TaskRecord] = {}
        # Counter to generate unique IDs (starts at 1)
        self._next_id: int = 1

    def create_task(self, data: TaskCreate) -> TaskResponse:
        """
        Create a new task and store it.

        Steps:
          1. Assign the next available ID
          2. Build a TaskRecord from the incoming data
          3. Store it in our dictionary
          4. Return the public-facing TaskResponse
        """
        task_id = self._next_id
        self._next_id += 1  # Increment for the next task

        # Capture a single timestamp so created_at and updated_at are identical
        now = datetime.now(timezone.utc)

        record = TaskRecord(
            id=task_id,
            title=data.title,
            description=data.description,
            completed=data.completed,
            created_at=now,
            updated_at=now,
        )
        self._tasks[task_id] = record
        return record.to_response()

    def get_task(self, task_id: int) -> TaskResponse:
        """
        Retrieve a single task by ID.
        Raises TaskNotFoundError if the ID doesn't exist.
        """
        # _get_or_raise handles the lookup + error in one place
        record = self._get_or_raise(task_id)
        return record.to_response()

    def list_tasks(self) -> list[TaskResponse]:
        """
        Return all tasks, sorted by creation time (oldest first).

        LIST COMPREHENSION EXPLAINED:
          [record.to_response() for record in self._tasks.values()]
          = "For each record in our storage, convert it to a response"
          This is a compact and Pythonic way to transform a list.
        """
        sorted_records = sorted(self._tasks.values(), key=lambda r: r.created_at)
        return [record.to_response() for record in sorted_records]

    def update_task(self, task_id: int, data: TaskUpdate) -> TaskResponse:
        """
        Partially update a task — only change fields that were provided.

        PARTIAL UPDATE PATTERN:
          data.title is None means "client didn't send a new title — keep old one"
          data.title is not None means "client wants to change the title"
        """
        record = self._get_or_raise(task_id)

        # Only update fields that were explicitly provided (not None)
        if data.title is not None:
            record.title = data.title
        if data.description is not None:
            record.description = data.description
        if data.completed is not None:
            record.completed = data.completed

        # Always update the 'updated_at' timestamp when a change is made
        record.updated_at = datetime.now(timezone.utc)

        return record.to_response()

    def delete_task(self, task_id: int) -> None:
        """
        Delete a task by ID.
        Raises TaskNotFoundError if the ID doesn't exist.
        """
        self._get_or_raise(task_id)  # Validate existence first
        del self._tasks[task_id]

    # ----------------------------------------------------------------
    # Private helper
    # ----------------------------------------------------------------

    def _get_or_raise(self, task_id: int) -> TaskRecord:
        """
        Look up a task by ID. If not found, raise TaskNotFoundError.

        WHY A PRIVATE HELPER?
          get_task, update_task, and delete_task all need the same
          'find or raise' logic. We extract it here to avoid repetition
          (DRY = Don't Repeat Yourself).
        """
        record = self._tasks.get(task_id)
        if record is None:
            raise TaskNotFoundError(f"Task with ID {task_id} not found")
        return record


# -----------------------------------------------------------------------
# SINGLETON INSTANCE
# -----------------------------------------------------------------------
# We create ONE shared instance that all routes will use.
# FastAPI uses dependency injection, but for simplicity we use a module-level
# singleton here. The instance is imported directly in routes.py.
task_service = TaskService()
