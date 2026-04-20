"""Loo breaks: start/end/cap/concurrent-break guard."""
from _client import request, login, ensure_seed, check, summary_and_exit

print("== Loo breaks ==")
ensure_seed()
admin_tok = login("admin", "admin", "admin123")
teacher_tok = login("teacher", "T201", "teach123")
student_tok = login("student", "S101", "stud123")

# Build a test with cap=2, 1 minute per break
_, qs = request("GET", "/api/teacher/questions", token=teacher_tok)
q_ids = [q["id"] for q in qs[:2]] if isinstance(qs, list) else []

_, created = request("POST", "/api/teacher/tests", token=teacher_tok, body={
    "title": "Loo Cap Smoke",
    "topic": "Mathematics",
    "duration_minutes": 30,
    "max_loo_breaks": 2,
    "max_loo_minutes": 1,
    "question_ids": q_ids,
})
test_id = created.get("test_id") if isinstance(created, dict) else None
check("test created for loo test", test_id is not None)

request("POST", "/api/admin/exam-toggle", token=admin_tok,
        body={"status": "started", "test_id": test_id})

# Start #1
status, _ = request("POST", "/api/exam/loo-break/start", token=student_tok)
check("first loo-break/start returns 201", status == 201, f"status={status}")

# Starting again while already active -> 400
status, _ = request("POST", "/api/exam/loo-break/start", token=student_tok)
check("second start while one is active returns 400", status == 400, f"status={status}")

# End
status, _ = request("POST", "/api/exam/loo-break/end", token=student_tok)
check("loo-break/end returns 200", status == 200, f"status={status}")

# Start #2
status, _ = request("POST", "/api/exam/loo-break/start", token=student_tok)
check("second fresh start returns 201", status == 201, f"status={status}")
request("POST", "/api/exam/loo-break/end", token=student_tok)

# Cap reached
status, payload = request("POST", "/api/exam/loo-break/start", token=student_tok)
check("third start hits cap (403)", status == 403, f"status={status} payload={payload}")

# Test with 0-break cap refuses starts outright
_, created2 = request("POST", "/api/teacher/tests", token=teacher_tok, body={
    "title": "No Breaks",
    "topic": "Mathematics",
    "duration_minutes": 30,
    "max_loo_breaks": 0,
    "max_loo_minutes": 0,
    "question_ids": q_ids,
})
tid2 = created2.get("test_id") if isinstance(created2, dict) else None
request("POST", "/api/admin/exam-toggle", token=admin_tok,
        body={"status": "started", "test_id": tid2})
status, _ = request("POST", "/api/exam/loo-break/start", token=student_tok)
check("0-cap test refuses any break (403)", status == 403, f"status={status}")

# Admin can see active breaks list
status, active = request("GET", "/api/admin/loo-breaks", token=admin_tok)
check("/admin/loo-breaks returns 200", status == 200)
check("response is a list", isinstance(active, list), f"type={type(active).__name__}")

# Cleanup
request("POST", "/api/admin/exam-toggle", token=admin_tok, body={"status": "stopped"})

summary_and_exit()
