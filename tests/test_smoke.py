# tests/test_smoke.py
import uuid
import httpx

BASE = "http://localhost:8080"  # If your gateway maps 80:80, use "http://localhost"

def test_smoke_happy_path():
    # Health (gateway + services through gateway)
    assert httpx.get(f"{BASE}/health").status_code == 200
    assert httpx.get(f"{BASE}/users/health").status_code == 200
    assert httpx.get(f"{BASE}/tasks/health").status_code == 200

    # Create user (random email avoids collisions between runs)
    email = f"alice+{uuid.uuid4().hex[:6]}@example.com"
    u = httpx.post(f"{BASE}/users/users", json={"name": "Alice", "email": email})
    assert u.status_code == 201
    user_id = u.json()["id"]

    # Create a task for that user
    t = httpx.post(f"{BASE}/tasks/tasks", json={
        "userId": user_id,
        "title": "Buy milk",
        "description": "2% organic",
        "status": "pending"
    })
    assert t.status_code == 201
    task_id = t.json()["id"]

    # List tasks for the user
    lst = httpx.get(f"{BASE}/tasks/tasks", params={"userId": user_id})
    assert lst.status_code == 200
    print(lst.json())
    assert any(x["id"] == task_id for x in lst.json())

    # Combined view via User Service (calls Task Service under the hood)
    combo = httpx.get(f"{BASE}/users/users/{user_id}/tasks")
    assert combo.status_code == 200
    assert any(x["id"] == task_id for x in combo.json()["tasks"])

    # Update task to completed
    upd = httpx.put(f"{BASE}/tasks/tasks/{task_id}", json={"status": "completed"})
    assert upd.status_code == 200
    assert upd.json()["status"] == "completed"

    # Delete task (cleanup)
    d = httpx.delete(f"{BASE}/tasks/tasks/{task_id}")
    assert d.status_code == 204

    # (Optional) delete user (keep environment tidy)
    httpx.delete(f"{BASE}/users/users/{user_id}")