## Microservices Task Manager

This repository contains a pair of FastAPI microservices that work together to create, store, and manage users and their tasks. A lightweight Nginx gateway fronts both services, Redis provides storage, and Docker Compose stitches everything together so you can spin up the full stack with a single command.

### Highlights
- User Service for creating and retrieving user profiles, plus an aggregated view into a user's tasks.
- Task Service for CRUD operations on tasks with user validation and Redis-backed persistence.
- Nginx API gateway offering a single entry point (`http://localhost:8080`) for both services.
- Redis 7 with append-only persistence to keep state between restarts.
- End-to-end smoke test (`tests/test_smoke.py`) that exercises the complete flow through the gateway.

### Architecture
```
┌──────────┐      ┌─────────────┐      ┌─────────────┐
│  Client  │ ---> │ Nginx (8080)│ ---> │ User Service│
└──────────┘      │             │      │ (FastAPI 8000)
                  │             │      └─────────────┘
                  │             │               │
                  │             │               │ HTTP (user lookups)
                  │             │      ┌────────▼────────┐
                  └────────────►│ Task Service (8002)    │
                                 └────────┬──────────────┘
                                          │
                                          │ Redis commands
                                   ┌──────▼──────┐
                                   │ Redis (6379)│
                                   └─────────────┘
```

Gateway routes:
- `/users/...` → User Service (`app.main`)
- `/tasks/...` → Task Service (`app.main`)
- `/health`    → Gateway health probe

### Repository Layout
- `user-service/` – FastAPI app for user profiles and combined user/task view.
- `task-service/` – FastAPI app for managing tasks scoped to users.
- `nginx/nginx.conf` – Reverse proxy that exposes both services under one host.
- `docker-compose.yml` – Orchestrates Redis, both services, and Nginx.
- `tests/test_smoke.py` – End-to-end regression covering the happy path.

---

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (only needed for running tests locally)

### Environment Variables
Environment values are already provided in `.env` files inside each service. Key settings:
- `REDIS_HOST`, `REDIS_PORT` – Connection info for Redis.
- `TASK_BASE` – Base URL the User Service uses to contact the Task Service.
- `USER_SERVICE_BASE` – Base URL the Task Service uses to validate users.

### Launch the Stack
```bash
docker compose up --build
```

Once the containers are healthy:
- Gateway health: `curl http://localhost:8080/health`
- User Service health: `curl http://localhost:8080/users/health`
- Task Service health: `curl http://localhost:8080/tasks/health`

Use `Ctrl+C` to stop; add `-d` if you want to run detached. Redis data persists in the `redis-data` Docker volume.

### Sample Workflow
```bash
# Create a user (note the doubled /users/ prefix introduced by the gateway)
USER_ID=$(curl -s -X POST http://localhost:8080/users/users \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "email": "alice@example.com"}' | jq -r '.id')

# Create a task for that user
TASK_ID=$(curl -s -X POST http://localhost:8080/tasks/tasks \
  -H "Content-Type: application/json" \
  -d "{\"userId\": \"$USER_ID\", \"title\": \"Buy milk\", \"description\": \"2% organic\"}" \
  | jq -r '.id')

# Fetch tasks directly from the Task Service
curl -s "http://localhost:8080/tasks/tasks?userId=$USER_ID" | jq

# Fetch the combined user + tasks view via the User Service
curl -s "http://localhost:8080/users/users/$USER_ID/tasks" | jq
```

---

## API Quick Reference (via Gateway)

### User Service (`/users/...`)
| Method | Path | Notes |
| --- | --- | --- |
| GET | `/users/health` | Service liveness probe |
| POST | `/users/users` | Create a user (`name`, `email`) |
| GET | `/users/users/{userId}` | Retrieve a user profile |
| PUT | `/users/users/{userId}` | Replace a user profile |
| DELETE | `/users/users/{userId}` | Delete a user (204 on success) |
| GET | `/users/users/{userId}/tasks` | Fetch user info plus their tasks via Task Service |

### Task Service (`/tasks/...`)
| Method | Path | Notes |
| --- | --- | --- |
| GET | `/tasks/health` | Service liveness probe |
| POST | `/tasks/tasks` | Create a task (`userId`, `title`, optional `description`, `status`) |
| GET | `/tasks/tasks/{taskId}` | Retrieve a task |
| GET | `/tasks/tasks?userId=...&status=...` | List tasks, optionally filter by status |
| PUT | `/tasks/tasks/{taskId}` | Update `title`, `description`, and/or `status` |
| DELETE | `/tasks/tasks/{taskId}` | Delete a task (also removes Redis index entry) |

> **Note:** Inside each FastAPI app the routes live under `/users` or `/tasks`. The Nginx gateway prepends `/users/` or `/tasks/` when forwarding, which is why public endpoints appear doubled.

---

## Testing

1. Start the stack (`docker compose up --build`) and wait for health checks to pass.
2. In a separate shell, install test dependencies and run the smoke test:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install pytest httpx
   pytest -q tests/test_smoke.py
   ```
   The test uses the gateway (`http://localhost:8080`) and covers user + task lifecycle.

Deactivate the virtual environment when you are done (`deactivate`).

---

## Local Development

- Run individual services with Uvicorn:
  ```bash
  uvicorn app.main:app --reload --port 8000  # inside user-service/
  uvicorn app.main:app --reload --port 8002  # inside task-service/
  ```
  Ensure Redis is available (e.g., `docker compose up redis`).
- Update dependencies via the respective `requirements.txt`.
- Keep gateway routes in sync with service port changes (`nginx/nginx.conf` + `docker-compose.yml`).

---

## Troubleshooting
- **Unable to reach `/users/...`** – Confirm Nginx is up (`docker compose ps`) and ports 8080/8005/8002 are free.
- **Task creation fails with 400** – The Task Service validates users through the User Service; make sure the user exists and services can reach each other.
- **Redis data missing after restart** – Verify the `redis-data` volume is not being pruned. The Compose file enables append-only persistence by default.

Happy hacking!
