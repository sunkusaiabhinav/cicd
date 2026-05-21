"""
FILE: tests/test_routes.py
PURPOSE: Integration tests for FastAPI HTTP endpoints.

WHAT IS TestClient?
  FastAPI provides a test client (powered by httpx) that lets you
  send HTTP requests to your app WITHOUT starting a real server.
  It simulates a real HTTP call and gives you back the response.

WHY INTEGRATION TESTS?
  Unlike unit tests (which test service logic in isolation),
  integration tests verify the full stack:
    HTTP request → route handler → service → response
  This catches issues like wrong status codes, missing fields, etc.

IMPORTANT — TEST ISOLATION:
  The 'client' fixture creates a fresh FastAPI app with a fresh
  TaskService for EACH test. This prevents test data from leaking
  between tests.
"""

import pytest
from fastapi.testclient import TestClient

# We import the FastAPI app and the service to reset state between tests
from app.service import TaskService, task_service
from main import app


@pytest.fixture
def client() -> TestClient:
    """
    Creates a TestClient with a clean service state for each test.

    WHY RESET task_service._tasks?
      Our service uses a module-level singleton (task_service in service.py).
      If we don't reset it, tasks created in one test bleed into the next.
      We clear _tasks and reset _next_id before each test runs.
    """
    # Reset the shared singleton's state before each test
    task_service._tasks = {}
    task_service._next_id = 1
    return TestClient(app)


# -----------------------------------------------------------------------
# HEALTH CHECK
# -----------------------------------------------------------------------


class TestHealthCheck:
    """Tests for GET /health"""

    def test_health_returns_200(self, client: TestClient) -> None:
        """Health endpoint should return HTTP 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_status_healthy(self, client: TestClient) -> None:
        """Health response body should contain status=healthy."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "task-manager"


# -----------------------------------------------------------------------
# ROOT ENDPOINT
# -----------------------------------------------------------------------


class TestRoot:
    """Tests for GET /"""

    def test_root_returns_200(self, client: TestClient) -> None:
        """Root endpoint should be reachable."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_contains_docs_link(self, client: TestClient) -> None:
        """Root response should include a link to the docs."""
        response = client.get("/")
        assert "docs" in response.json()


# -----------------------------------------------------------------------
# CREATE TASK (POST /tasks)
# -----------------------------------------------------------------------


class TestCreateTask:
    """Tests for POST /tasks"""

    def test_create_task_returns_201(self, client: TestClient) -> None:
        """Creating a task should return HTTP 201 Created."""
        payload = {"title": "Buy groceries"}
        response = client.post("/tasks", json=payload)
        assert response.status_code == 201

    def test_create_task_returns_correct_data(self, client: TestClient) -> None:
        """Response should contain the task data we sent."""
        payload = {"title": "Write tests", "description": "Very important"}
        response = client.post("/tasks", json=payload)
        data = response.json()

        assert data["title"] == "Write tests"
        assert data["description"] == "Very important"
        assert data["completed"] is False

    def test_create_task_assigns_id(self, client: TestClient) -> None:
        """The server should assign a numeric ID to the new task."""
        response = client.post("/tasks", json={"title": "Test ID"})
        data = response.json()

        assert "id" in data
        assert isinstance(data["id"], int)

    def test_create_task_missing_title_returns_422(self, client: TestClient) -> None:
        """Sending a request without 'title' should return 422 Validation Error."""
        response = client.post("/tasks", json={"description": "No title here"})
        assert response.status_code == 422

    def test_create_task_empty_title_returns_422(self, client: TestClient) -> None:
        """An empty string title should fail Pydantic's min_length=1 validation."""
        response = client.post("/tasks", json={"title": ""})
        assert response.status_code == 422


# -----------------------------------------------------------------------
# LIST TASKS (GET /tasks)
# -----------------------------------------------------------------------


class TestListTasks:
    """Tests for GET /tasks"""

    def test_list_empty_returns_200(self, client: TestClient) -> None:
        """Listing tasks on an empty service should return 200 with empty list."""
        response = client.get("/tasks")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_returns_all_created_tasks(self, client: TestClient) -> None:
        """After creating N tasks, GET /tasks should return all N."""
        for i in range(3):
            client.post("/tasks", json={"title": f"Task {i}"})

        response = client.get("/tasks")
        assert len(response.json()) == 3

    def test_list_contains_correct_titles(self, client: TestClient) -> None:
        """The returned tasks should match what was created."""
        client.post("/tasks", json={"title": "Alpha"})
        client.post("/tasks", json={"title": "Beta"})

        data = client.get("/tasks").json()
        titles = [t["title"] for t in data]
        assert "Alpha" in titles
        assert "Beta" in titles


# -----------------------------------------------------------------------
# GET SINGLE TASK (GET /tasks/{id})
# -----------------------------------------------------------------------


class TestGetTask:
    """Tests for GET /tasks/{task_id}"""

    def test_get_existing_task_returns_200(self, client: TestClient) -> None:
        """Getting a task with a valid ID should return 200."""
        created = client.post("/tasks", json={"title": "Find me"}).json()
        response = client.get(f"/tasks/{created['id']}")
        assert response.status_code == 200

    def test_get_existing_task_returns_correct_data(self, client: TestClient) -> None:
        """The returned task should match the created task."""
        created = client.post(
            "/tasks", json={"title": "Specific Task", "description": "Details"}
        ).json()

        fetched = client.get(f"/tasks/{created['id']}").json()
        assert fetched["title"] == "Specific Task"
        assert fetched["description"] == "Details"

    def test_get_nonexistent_task_returns_404(self, client: TestClient) -> None:
        """Getting a task with an invalid ID should return HTTP 404."""
        response = client.get("/tasks/99999")
        assert response.status_code == 404

    def test_get_404_has_detail_message(self, client: TestClient) -> None:
        """The 404 response should include a 'detail' message."""
        response = client.get("/tasks/99999")
        assert "detail" in response.json()


# -----------------------------------------------------------------------
# UPDATE TASK (PUT /tasks/{id})
# -----------------------------------------------------------------------


class TestUpdateTask:
    """Tests for PUT /tasks/{task_id}"""

    def test_update_title_returns_200(self, client: TestClient) -> None:
        """Updating a task's title should return 200 with updated data."""
        created = client.post("/tasks", json={"title": "Old Title"}).json()
        response = client.put(
            f"/tasks/{created['id']}", json={"title": "New Title"}
        )
        assert response.status_code == 200
        assert response.json()["title"] == "New Title"

    def test_update_completed_flag(self, client: TestClient) -> None:
        """Marking a task as completed should change the completed field."""
        created = client.post("/tasks", json={"title": "Do this"}).json()
        response = client.put(
            f"/tasks/{created['id']}", json={"completed": True}
        )
        assert response.json()["completed"] is True

    def test_update_partial_keeps_other_fields(self, client: TestClient) -> None:
        """Partial update should not change fields not included in the payload."""
        created = client.post(
            "/tasks", json={"title": "Original", "description": "Keep me"}
        ).json()

        client.put(f"/tasks/{created['id']}", json={"completed": True})
        fetched = client.get(f"/tasks/{created['id']}").json()

        assert fetched["title"] == "Original"
        assert fetched["description"] == "Keep me"

    def test_update_nonexistent_task_returns_404(self, client: TestClient) -> None:
        """Updating a non-existent task should return 404."""
        response = client.put("/tasks/99999", json={"title": "Ghost"})
        assert response.status_code == 404


# -----------------------------------------------------------------------
# DELETE TASK (DELETE /tasks/{id})
# -----------------------------------------------------------------------


class TestDeleteTask:
    """Tests for DELETE /tasks/{task_id}"""

    def test_delete_existing_task_returns_204(self, client: TestClient) -> None:
        """Deleting a valid task should return HTTP 204 No Content."""
        created = client.post("/tasks", json={"title": "Delete me"}).json()
        response = client.delete(f"/tasks/{created['id']}")
        assert response.status_code == 204

    def test_delete_removes_task_from_list(self, client: TestClient) -> None:
        """After deletion, the task should no longer appear in GET /tasks."""
        created = client.post("/tasks", json={"title": "Gone"}).json()
        client.delete(f"/tasks/{created['id']}")

        all_tasks = client.get("/tasks").json()
        ids = [t["id"] for t in all_tasks]
        assert created["id"] not in ids

    def test_delete_then_get_returns_404(self, client: TestClient) -> None:
        """After deletion, fetching the task by ID should return 404."""
        created = client.post("/tasks", json={"title": "Temporary"}).json()
        client.delete(f"/tasks/{created['id']}")

        response = client.get(f"/tasks/{created['id']}")
        assert response.status_code == 404

    def test_delete_nonexistent_task_returns_404(self, client: TestClient) -> None:
        """Deleting a non-existent task should return 404."""
        response = client.delete("/tasks/99999")
        assert response.status_code == 404
