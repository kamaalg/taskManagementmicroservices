# CODE_PROVENANCE.md

## 1. Student info
- Name: Kamal Gurbanov
- NetID: 33597899
- Date: 11.03.2025

## 2. Tools used
- ChatGPT, GPT-5, web app, code + chat
- GitHub Copilot, VS Code extension, inline suggestions (minimal boilerplate suggestions only)

## 3. Prompts and outputs you used

### Interaction 1
- **Purpose:** Understand how to configure Nginx reverse proxy for multiple FastAPI microservices
- **Prompt:** "Explain how to proxy /users and /tasks from Nginx to microservices with docker compose"
- **Output used:** General routing block structure and explanation (no direct copy)
- **File and lines:** `api-gateway/nginx.conf` (routing logic structure only, implementation written manually)
- **Modifications:** Wrote my own server blocks and upstream logic; changed names, ports, and config format

### Interaction 2
- **Purpose:** Fix load balancing across Docker-compose-scaled microservice replicas
- **Prompt:** "Nginx not round robin with docker compose scaling — how to reload DNS or use resolver?"
- **Output used:** Concept of using `resolver 127.0.0.11` and `proxy_pass` trailing slash for prefix-stripping behavior
- **File and lines:** `api-gateway/nginx.conf`
- **Modifications:** Wrote own upstream + location blocks; adjusted to FastAPI/compose layout; added proper health routes

### Interaction 3
- **Purpose:** Correct FastAPI service-to-service call returning tasks + user details
- **Prompt:** "How can I return a user object and tasks list together in FastAPI from another microservice?"
- **Output used:** Pattern for returning a dict with `"user": {...}, "tasks": [...]`
- **File and lines:** `user-service/app/main.py`, `get_user_tasks` function
- **Modifications:** Implemented entirely myself with my Redis schema, fields, and async httpx call

### Interaction 4 (repeated multiple times)
- **Purpose:** Troubleshoot Docker compose healthchecks and test flakiness
- **Prompt:** "Why does /tasks/health time out in pytest when Nginx proxies?"
- **Output used:** Reasoning about dependency startup and prefix rewrite; no direct code copied
- **File and lines:** None directly — advice only
- **Modifications:** Added correct `proxy_pass` form and ensured services healthy before tests

*(Repeated small clarifications/chat guidance N≈10, but no direct code pasted.)*

## 4. Non-AI sources
- Official FastAPI docs — reference for startup/shutdown events and response models: https://fastapi.tiangolo.com
- Docker docs for healthcheck syntax: https://docs.docker.com/engine/reference/builder/#healthcheck
- Nginx docs for `proxy_pass` prefix behavior: https://nginx.org/r/proxy_pass

## 5. Originality statement

I affirm that I understand the course policy on authorized assistance.  
All external and AI assistance is fully documented above.  
I take responsibility for the submitted code and can explain it.

**Signature:** Kamal Gurbanov  
**Date:** 11.03.2025
