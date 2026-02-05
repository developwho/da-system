# Patch Summary (Stability/Security)

## What changed and why

### Access control
- Added API key enforcement for all REST routes and WebSocket handshakes to prevent unauthenticated access.
- New shared dependency in `app/api/deps.py`; routes now require `x-api-key` (WS also accepts `?api_key=`).
- Updated CORS to use the configured list (`allowed_origins_list`) and added `API_KEY` to `.env.example`.

### Runtime stability
- Fixed sync/async mismatch by running `SessionStore` operations in a threadpool from async routes.
- Made session updates atomic with Redis `WATCH` to prevent lost updates under concurrency.
- Repaired research aggregation task: removed invalid `asyncio.run()` usage and replaced missing timestamp helper.

### Path/ID safety
- Enforced UUID validation for `session_id`/`file_id` in route params.
- Added safe report path resolution to prevent path traversal.
- Normalized `file_id` in `FileManager` to ensure only valid UUIDs are used.

### Orchestration reliability
- Persisted `workflow_state` in session context and implemented true resume logic from the current state.

### Data pipeline guardrails
- Added target column existence checks and safe datetime monotonic checks.
- Prevented division-by-zero in profiler metrics.
- Added file existence check before loading.
- Replaced bare `except:` with explicit exceptions and logging.

## New/Updated files
- `app/api/deps.py` (API key guards)
- `app/api/routes/*` (auth + UUID validation)
- `app/storage/session_store.py` (atomic updates)
- `app/tasks/research_tasks.py` (aggregation fix)
- `app/agents/orchestrator.py` (resume/persist state)
- `app/core/data_pipeline/*` (guardrails)
- `.env.example` (API_KEY)
- `test_security.py` (sanity checks)

## Notes
- Set `API_KEY` in `.env` and call APIs with `x-api-key`.
- WebSocket auth: `x-api-key` header or `?api_key=...` query parameter.
