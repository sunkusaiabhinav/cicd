# Task Manager API

A simple **FastAPI REST API** for managing tasks, built as a demonstration project for a
full **GitHub Actions CI/CD pipeline**. All source code is heavily commented for beginners.

---

## Project Structure

```
github actions (cicd)/
├── app/
│   ├── __init__.py     # Package marker
│   ├── models.py       # Pydantic request/response schemas
│   ├── service.py      # Business logic (in-memory CRUD)
│   └── routes.py       # FastAPI router (all endpoints)
├── tests/
│   ├── __init__.py
│   ├── test_routes.py  # Integration tests (TestClient)
│   └── test_service.py # Unit tests for service layer
├── main.py             # FastAPI app entry point
├── requirements.txt    # Runtime deps (fastapi, uvicorn, pydantic)
├── requirements-dev.txt# Dev/CI deps (pytest, black, isort, etc.)
├── Dockerfile          # Containerizes the service
├── .bandit             # Bandit security scan config
├── setup.cfg           # flake8, isort, mypy, coverage config
├── pyproject.toml      # Black config + build metadata
└── .github/
    └── workflows/
        └── ci-cd.yml   # GitHub Actions CI/CD pipeline
```

---

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/` | Welcome message |
| GET | `/health` | Health check (used by Docker/K8s) |
| GET | `/tasks` | List all tasks |
| POST | `/tasks` | Create a new task |
| GET | `/tasks/{id}` | Get a single task by ID |
| PUT | `/tasks/{id}` | Update a task (partial) |
| DELETE | `/tasks/{id}` | Delete a task |

Interactive docs available at **`/docs`** (Swagger UI) when running locally.

---

## Quick Start (Local Development)

### 1. Create and activate a virtual environment
```powershell
# Create venv
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies
```powershell
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Run the API server
```powershell
uvicorn main:app --reload
```
Open **http://localhost:8000/docs** to see the interactive Swagger UI.

---

## Running Tests

```powershell
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=app --cov-report=term-missing -v
```

---

## CI/CD Pipeline (GitHub Actions)

The pipeline runs automatically on push to `main` or `develop`, and on PRs to `main`.

### Jobs

| Job | Depends On | What It Does |
|-----|-----------|--------------|
| `validation` | - | Runs all 6 quality tools |
| `testing` | `validation` | Runs pytest with coverage |
| `verify-docker-config` | `validation`, `testing` | Checks Docker secrets exist |
| `containerize` | All above | Builds & pushes Docker image |

### Quality Tools Used

| Stage | Tool | Command | What It Checks |
|-------|------|---------|----------------|
| Formatting | black | `black --check app/ tests/ main.py` | Consistent code style |
| Imports | isort | `isort --check-only app/ tests/ main.py` | Import order |
| Linting | flake8 | `flake8 app/ tests/` | Code errors & style violations |
| Types | mypy | `mypy app/` | Type annotation correctness |
| Security | bandit | `bandit -r app/ -c .bandit` | Security vulnerabilities in source |
| Packages | pip-audit | `pip-audit -r requirements.txt` | Known CVEs in dependencies |

### Auto-Fix Commands (when tools fail)

```powershell
# Fix formatting automatically
black app/ tests/ main.py

# Fix import order automatically
isort app/ tests/ main.py

# View flake8 errors (manual fix required)
flake8 app/ tests/

# View mypy errors (manual fix required)
mypy app/

# View security issues (manual fix required)
bandit -r app/ -c .bandit
```

---

## Docker

### Build the image
```bash
docker build -t fastapi-service .
```

### Run the container
```bash
docker run -p 8000:8000 fastapi-service
```

### Push to Docker Hub (GitHub Actions does this automatically)
```bash
docker tag fastapi-service yourusername/fastapi-service:latest
docker push yourusername/fastapi-service:latest
```

---

## Setting Up Docker Hub Secrets (for GitHub Actions)

To enable the `containerize` job, add these secrets to your GitHub repository:

1. Go to **GitHub repo → Settings → Secrets and variables → Actions**
2. Add:
   - `DOCKER_HUB_USERNAME` — your Docker Hub username
   - `DOCKER_HUB_TOKEN` — your Docker Hub access token (from hub.docker.com → Security)

---

## Example API Usage

```python
import httpx

base = "http://localhost:8000"

# Create a task
r = httpx.post(f"{base}/tasks", json={"title": "Learn FastAPI", "description": "Build something!"})
task = r.json()
print(task)  # {"id": 1, "title": "Learn FastAPI", ...}

# Mark it as completed
httpx.put(f"{base}/tasks/{task['id']}", json={"completed": True})

# List all tasks
all_tasks = httpx.get(f"{base}/tasks").json()

# Delete a task
httpx.delete(f"{base}/tasks/{task['id']}")
```
