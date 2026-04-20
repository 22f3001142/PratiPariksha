# Smoke test suite

Nine standalone scripts that exercise the backend against a live server.

## Running

1. Start the backend in another terminal:

   ```bash
   python backend/run.py
   ```

2. Run any individual script:

   ```bash
   python tests/test_auth.py
   python tests/test_exam_flow.py
   python tests/test_forum.py
   ```

3. Or run them all:

   ```bash
   for f in tests/test_*.py; do python "$f" || break; done
   ```

Each script exits `0` on pass, `1` on assertion failure, `2` on setup failure
(server unreachable, missing schema, etc.).

## Environment

- `BASE_URL` (default `http://127.0.0.1:8391`) — override if the server runs elsewhere.
- Scripts seed their own users (`admin/admin123`, `T201/teach123`, `S101/stud123`)
  and sample questions. Safe to run against an already-populated DB — inserts
  are idempotent.

## The scripts

| File | What it covers |
| --- | --- |
| `test_auth.py` | login flows for all three roles, 401 without token, 403 on wrong role |
| `test_admin.py` | user list, multi-teacher assignment round-trip, exam toggle, analytics |
| `test_exam_flow.py` | `scheduled_start` gating, question-response shape, submit scoring |
| `test_loo_breaks.py` | start/end, concurrent-break guard, per-test cap, 0-cap denial |
| `test_forum.py` | threaded replies, teacher + student append, empty rejected, voting |
| `test_resources.py` | JSON + multipart upload, extension guard, notes URL + upload, `/uploads/` serving |
| `test_gamification.py` | 1 point per correct, Perfect Score badge, `level_progress` in range |
| `test_focus_mode.py` | start/stop/status/heartbeat resilience, graceful double-stop |
| `test_schema.py` | verifies every new column/table is present in the live DB |

`_client.py` is the shared helper — `request()`, `login()`, `ensure_seed()`,
`check()`, `summary_and_exit()`. Not a test itself.
