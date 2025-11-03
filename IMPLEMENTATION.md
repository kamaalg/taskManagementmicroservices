## Implementation Notes

This document explains how the microservices task manager is assembled, what technology choices were made, and the key trade-offs that shaped the current solution.

---

## High-Level Architecture

- **User Service (`user-service/`)** – FastAPI app that manages user profiles and provides an aggregated user + tasks view. Persists user data in Redis and fans out to the Task Service using HTTP calls.
- **Task Service (`task-service/`)** – FastAPI app that manages CRUD lifecycle for tasks. Tasks are persisted in Redis with per-user index sets to support quick lookups.
- **Redis (`redis`)** – Shared backing store for both services. Data is stored as JSON strings keyed by predictable patterns.
- **Nginx Gateway (`nginx/`)** – Single entry point exposed on `http://localhost:8080`. Routes `/users/...` traffic to the User Service and `/tasks/...` traffic to the Task Service. Also exposes a gateway-level `/health` endpoint.
- **Docker Compose (`docker-compose.yml`)** – Orchestrates Redis, both FastAPI services, and the gateway. Each service defines health checks and restarts automatically on failure.

All external consumers hit the Nginx gateway. Internal service-to-service calls bypass the gateway and use the container DNS names (e.g., `http://task-service:8002`).

---

## Data Model & Persistence

Redis stores JSON blobs and simple index sets.

### User Service
- **Key pattern:** `user:{userId}`
- **Value:** JSON serialization of the `UserCreate` payload with an extra `createdAt` field stamped server-side.
- **Model classes:**
  - `UserCreate` – Incoming payload with `name` and `email`.
  - `UserResponse` – Outbound shape with `id`, `name`, `email`, `created_at`.

### Task Service
- **Key pattern:** `task:{taskId}`
- **Value:** JSON serialization of the `TaskCreate` payload plus a server-generated `createdAt`.
- **Secondary index:** `user:{userId}:tasks` – Redis Set storing task IDs for each user. Enables listing tasks for a user without scanning all task keys.
- **Model classes:**
  - `TaskCreate` – Incoming payload (`userId`, `title`, optional `description`, `status` defaulting to `"pending"`).
  - `TaskResponse` – Outbound representation used across endpoints.
  - `TaskUpdate` – Partial updates for `title`, `description`, and `status`.

---

## Service Behavior

### User Service (`app/main.py`)
- `POST /users` – Generates a UUID, stamps `createdAt`, writes a JSON blob to Redis, and returns a `UserResponse`.
- `GET /users/{user_id}` – Reads from Redis, returning 404 if the key is missing.
- `GET /users/{user_id}/tasks` – Validates the user exists, fetches tasks from the Task Service using the `TASK_BASE` URL, and returns a combined `UserTasksResponse`.
- `PUT /users/{user_id}` – Overwrites the existing user entry with the submitted payload.
- `DELETE /users/{user_id}` – Removes the Redis key and ensures deletion succeeded before returning `204`.
- `GET /health` – Liveness response consumed by Docker health checks.

#### Notable Implementation Details
- **Synchronous HTTP in async route:** Uses `httpx.get(...)` directly inside async path functions, which blocks the event loop. Switching to `httpx.AsyncClient` plus `await` would improve scalability.
- **Env naming mismatch:** The service expects `REDIS-HOST`/`REDIS-PORT` (dash) but Docker and `.env` files provide `REDIS_HOST`/`REDIS_PORT` (underscore). Defaults mask this in Docker but break local overrides.
- **PUT response fields:** Returns `created_at=user.createdAt`, but `UserCreate` does not define `createdAt`. A future fix should carry forward the original creation timestamp instead of relying on client input.

### Task Service (`app/main.py`)
- `POST /tasks` – Validates the user exists by calling the User Service (`USER_SERVICE_BASE`). Upon success, stores the task, adds the task ID to the user’s Redis set, and returns a `TaskResponse`.
- `GET /tasks/{task_id}` – Fetches a single task by key.
- `GET /tasks` – Loads all task IDs from the user-specific Redis set, filters by optional `status` query parameter, and returns a list of `TaskResponse` objects. Returns a 400 if the user has no tasks.
- `PUT /tasks/{task_id}` – Performs a shallow merge of updated fields into the stored JSON record.
- `DELETE /tasks/{task_id}` – Removes both the task record and the set membership within a Redis pipeline to keep the operations atomic.
- `GET /health` – Liveness endpoint for Compose health checks.

#### Notable Implementation Details
- **User validation:** Ensures referential integrity by synchronously calling the User Service before task creation. This prevents orphaned tasks at the cost of coupling and additional latency.
- **Redis connection parms:** Uses `REDIS_HOST`, `REDIS_PORT` and defaults to `redis`/`None`. A default port of `6379` would avoid implicit type conversion issues.
- **Status filtering:** Filters in application code after retrieving all tasks. For large task sets, switching to separate Redis sets per status or scan-based pagination would be more scalable.

---

## Cross-Service Communication

- **User → Task:** `GET {TASK_BASE}/tasks?userId={id}` when assembling the combined view.
- **Task → User:** `GET {USER_SERVICE_BASE}/users/{userId}` before creating a task.

Both services rely on synchronous HTTP calls from inside async route handlers. Under higher load, migrating to `httpx.AsyncClient` within an `async with` block would keep the event loop responsive.

---

## Deployment & Runtime Configuration

- **Dockerfiles:** Both services use `python:3.11-slim`, install dependencies from `requirements.txt`, copy the FastAPI app into `/app`, and run via `uvicorn`.
- **Compose stack:** 
  - Redis uses append-only mode for durability.
  - Services expose ports `8005:8000` (User) and `8002:8002` (Task) for optional direct access.
  - Nginx binds host port `8080` and depends on both services’ health checks.
- **Environment Variables:**
  - `USER_SERVICE_BASE` and `TASK_BASE` configure service-to-service calls.
  - `REDIS_HOST` / `REDIS_PORT` configure Redis connectivity.

For local development, running `docker compose up --build` brings up the entire stack with correct networking topology.

---

## Testing Strategy

- **Smoke Test (`tests/test_smoke.py`)** – Exercises the full flow through the Nginx gateway:
  1. Checks gateway and service health endpoints.
  2. Creates a new user with a randomized email.
  3. Creates a task for that user.
  4. Lists tasks and verifies the created task is present.
  5. Retrieves the aggregated user + tasks view.
  6. Updates the task status to `"completed"`.
  7. Deletes the task (and optionally cleans up the user).

The test uses `httpx` directly and assumes the Compose stack is running on `http://localhost:8080`.

No unit tests exist yet; all coverage comes from this end-to-end sanity check.

---

## Known Gaps & Future Work

- **Async correctness:** Replace blocking `httpx.get` calls in async endpoints with awaited async client calls.
- **Configuration consistency:** Align environment variable names (`REDIS_HOST` vs `REDIS-HOST`) and add type-safe parsing for ports.
- **User update semantics:** Preserve `createdAt` when updating users and consider partial (PATCH) support.
- **Error transparency:** Surface downstream failure reasons (e.g., pass through Task Service error messages) instead of generic 500s.
- **Security:** Currently there is no authentication/authorization layer. Add rate limiting and request validation before production use.
- **Observability:** Introduce structured logging and metrics to trace cross-service requests and Redis operations.
- **Testing depth:** Add unit tests for business logic, contract tests for Redis interactions, and negative-path coverage.

These improvements would enhance robustness while keeping the current architecture intact.
