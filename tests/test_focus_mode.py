"""Focus mode: start/stop/status/heartbeat resilience."""
from _client import request, login, ensure_seed, check, summary_and_exit

print("== Focus mode ==")
ensure_seed()
student_tok = login("student", "S101", "stud123")

# Start with device controls disabled (no OS hooks in CI)
status, start = request("POST", "/api/focus-mode/start", token=student_tok, body={
    "source": "smoke",
    "apply_device_controls": False,
    "commit_system_changes": False,
})
check("/focus-mode/start returns 200", status == 200, f"status={status} payload={start}")
session_id = None
if isinstance(start, dict):
    session_id = (start.get("session") or {}).get("session_id")
    check("start payload exposes session.session_id", session_id is not None,
          f"payload={start}")

# Status reports active=True
status, st = request("GET", "/api/focus-mode/status", token=student_tok)
check("/focus-mode/status returns 200", status == 200)
check("status reports active=True", isinstance(st, dict) and bool(st.get("active")),
      f"payload={st}")

# Heartbeat does not error
if session_id:
    status, _ = request("POST", "/api/focus-mode/heartbeat", token=student_tok,
                        body={"session_id": session_id})
    check("/focus-mode/heartbeat returns 200", status == 200, f"status={status}")

# Stop
status, _ = request("POST", "/api/focus-mode/stop", token=student_tok,
                    body={"commit_system_changes": False})
check("/focus-mode/stop returns 200", status == 200, f"status={status}")

# Status now inactive
status, st2 = request("GET", "/api/focus-mode/status", token=student_tok)
check("after stop, active=False",
      isinstance(st2, dict) and not st2.get("active"), f"payload={st2}")

# Stopping twice should not crash the server
status, _ = request("POST", "/api/focus-mode/stop", token=student_tok,
                    body={"commit_system_changes": False})
check("double-stop does not crash (2xx/4xx, not 500)",
      200 <= status < 500, f"status={status}")

# Heartbeat with unknown session id should respond gracefully
status, _ = request("POST", "/api/focus-mode/heartbeat", token=student_tok,
                    body={"session_id": "does-not-exist"})
check("heartbeat for unknown session returns non-5xx",
      200 <= status < 500, f"status={status}")

summary_and_exit()
