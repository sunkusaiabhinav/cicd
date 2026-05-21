"""
FILE: tests/test_service.py
PURPOSE: Unit tests for the TaskService business logic layer.

WHAT ARE UNIT TESTS?
  Unit tests test a small, isolated unit of code — here, we test
  the TaskService class methods directly without running the web server.
  We call service methods and assert that results match expectations.

PYTEST FIXTURES (@pytest.fixture):
  A fixture is a reusable setup function. Instead of creating a fresh
  TaskService in every test, we define it once as a fixture.
  pytest automatically calls it and injects the result into any test
  that lists it as a parameter.
"""

import pytest

from app.models import TaskCreate, TaskUpdate
from app.service import TaskNotFoundError, TaskService


# -----------------------------------------------------------------------
# FIXTURES
# -----------------------------------------------------------------------


@pytest.fixture
def service() -> TaskService:
    """
    Creates a fresh, empty TaskService for each test.
    Using a new instance per test ensures tests don't affect each other
    (tests must be independent and repeatable).
    """
    return TaskService()


@pytest.fixture
def service_with_task(service: TaskService) -> tuple[TaskService, int]:
    """
    Returns a service that already has one task, plus its ID.
    Used by tests that need to test operations on an existing task.
    """
    payload = TaskCreate(title="Existing Task", description="Pre-created", completed=False)
    task = service.create_task(payload)
    return service, task.id


# -----------------------------------------------------------------------
# CREATE TASK TESTS
# -----------------------------------------------------------------------


class TestCreateTask:
    """Tests for TaskService.create_task()"""

    def test_create_returns_task_response(self, service: TaskService) -> None:
        """Creating a task should return a TaskResponse with correct data."""
        payload = TaskCreate(title="Buy groceries", description="Milk and eggs")
        result = service.create_task(payload)

        assert result.title == "Buy groceries"
        assert result.description == "Milk and eggs"
        assert result.completed is False

    def test_create_assigns_unique_ids(self, service: TaskService) -> None:
        """Each new task should get a unique, incrementing ID."""
        t1 = service.create_task(TaskCreate(title="Task One"))
        t2 = service.create_task(TaskCreate(title="Task Two"))
        t3 = service.create_task(TaskCreate(title="Task Three"))

        assert t1.id != t2.id
        assert t2.id != t3.id
        # IDs should be sequential (1, 2, 3)
        assert t2.id == t1.id + 1
        assert t3.id == t2.id + 1

    def test_create_with_defaults(self, service: TaskService) -> None:
        """Optional fields (description, completed) should use defaults."""
        task = service.create_task(TaskCreate(title="Minimal Task"))

        assert task.description == ""
        assert task.completed is False

    def test_create_stores_timestamps(self, service: TaskService) -> None:
        """A new task should have valid created_at and updated_at timestamps."""
        task = service.create_task(TaskCreate(title="Timed Task"))

        assert task.created_at is not None
        assert task.updated_at is not None
        # On creation, both timestamps should be equal
        assert task.created_at == task.updated_at


# -----------------------------------------------------------------------
# GET TASK TESTS
# -----------------------------------------------------------------------


class TestGetTask:
    """Tests for TaskService.get_task()"""

    def test_get_existing_task(
        self, service_with_task: tuple[TaskService, int]
    ) -> None:
        """Getting a task by a valid ID should return the correct task."""
        service, task_id = service_with_task
        task = service.get_task(task_id)

        assert task.id == task_id
        assert task.title == "Existing Task"

    def test_get_nonexistent_raises_error(self, service: TaskService) -> None:
        """Getting a task that doesn't exist should raise TaskNotFoundError."""
        # pytest.raises() is how we assert that an exception is raised
        with pytest.raises(TaskNotFoundError):
            service.get_task(999)


# -----------------------------------------------------------------------
# LIST TASKS TESTS
# -----------------------------------------------------------------------


class TestListTasks:
    """Tests for TaskService.list_tasks()"""

    def test_list_empty_service(self, service: TaskService) -> None:
        """A fresh service should return an empty list."""
        result = service.list_tasks()
        assert result == []

    def test_list_returns_all_tasks(self, service: TaskService) -> None:
        """After adding N tasks, list should return all N."""
        for i in range(3):
            service.create_task(TaskCreate(title=f"Task {i}"))

        result = service.list_tasks()
        assert len(result) == 3

    def test_list_sorted_by_creation_time(self, service: TaskService) -> None:
        """Tasks should be returned in the order they were created."""
        titles = ["First", "Second", "Third"]
        for title in titles:
            service.create_task(TaskCreate(title=title))

        result = service.list_tasks()
        returned_titles = [t.title for t in result]
        assert returned_titles == titles


# -----------------------------------------------------------------------
# UPDATE TASK TESTS
# -----------------------------------------------------------------------


class TestUpdateTask:
    """Tests for TaskService.update_task()"""

    def test_update_title_only(
        self, service_with_task: tuple[TaskService, int]
    ) -> None:
        """Updating only title should not affect other fields."""
        service, task_id = service_with_task
        updated = service.update_task(task_id, TaskUpdate(title="New Title"))

        assert updated.title == "New Title"
        # description and completed should be unchanged
        assert updated.description == "Pre-created"
        assert updated.completed is False

    def test_update_completed_status(
        self, service_with_task: tuple[TaskService, int]
    ) -> None:
        """Marking a task as completed should update the completed field."""
        service, task_id = service_with_task
        updated = service.update_task(task_id, TaskUpdate(completed=True))

        assert updated.completed is True

    def test_update_refreshes_updated_at(
        self, service_with_task: tuple[TaskService, int]
    ) -> None:
        """updated_at timestamp should change after an update."""
        service, task_id = service_with_task
        original = service.get_task(task_id)

        # Small sleep not needed — updated_at is set to now() during update
        updated = service.update_task(task_id, TaskUpdate(title="Changed"))

        # updated_at should be >= created_at (updated later than creation)
        assert updated.updated_at >= original.created_at

    def test_update_nonexistent_raises_error(self, service: TaskService) -> None:
        """Updating a task that doesn't exist should raise TaskNotFoundError."""
        with pytest.raises(TaskNotFoundError):
            service.update_task(999, TaskUpdate(title="Ghost"))

    def test_update_empty_payload_changes_nothing(
        self, service_with_task: tuple[TaskService, int]
    ) -> None:
        """Sending an empty update payload should leave data unchanged."""
        service, task_id = service_with_task
        original = service.get_task(task_id)
        updated = service.update_task(task_id, TaskUpdate())

        assert updated.title == original.title
        assert updated.description == original.description
        assert updated.completed == original.completed


# -----------------------------------------------------------------------
# DELETE TASK TESTS
# -----------------------------------------------------------------------


class TestDeleteTask:
    """Tests for TaskService.delete_task()"""

    def test_delete_existing_task(
        self, service_with_task: tuple[TaskService, int]
    ) -> None:
        """Deleting a task should remove it from storage."""
        service, task_id = service_with_task
        service.delete_task(task_id)

        # Trying to get the deleted task should now raise an error
        with pytest.raises(TaskNotFoundError):
            service.get_task(task_id)

    def test_delete_reduces_list_count(
        self, service_with_task: tuple[TaskService, int]
    ) -> None:
        """After deletion, list_tasks should have one fewer item."""
        service, task_id = service_with_task
        service.create_task(TaskCreate(title="Extra Task"))

        assert len(service.list_tasks()) == 2
        service.delete_task(task_id)
        assert len(service.list_tasks()) == 1

    def test_delete_nonexistent_raises_error(self, service: TaskService) -> None:
        """Deleting a non-existent task should raise TaskNotFoundError."""
        with pytest.raises(TaskNotFoundError):
            service.delete_task(999)
