"""Exam flow: scheduled_start gating, questions shape, submit scoring."""
from datetime import datetime, timedelta, timezone
from _client import request, login, ensure_seed, check, summary_and_exit

print("== Exam flow ==")
ensure_seed()
admin_tok = login("admin", "admin", "admin123")
teacher_tok = login("teacher", "T201", "teach123")
student_tok = login("student", "S101", "stud123")

# Get some question ids
_, qs = request("GET", "/api/teacher/questions", token=teacher_tok)
q_ids = [q["id"] for q in qs[:2]] if isinstance(qs, list) else []
check("at least 2 questions available", len(q_ids) >= 2, f"got {q_ids}")

# Create a test paper
status, created = request("POST", "/api/teacher/tests", token=teacher_tok, body={
    "title": "Exam Flow Smoke",
    "topic": "Mathematics",
    "description": "",
    "duration_minutes": 30,
    "scheduled_start": None,
    "max_loo_breaks": 0,
    "max_loo_minutes": 0,
    "question_ids": q_ids,
})
check("POST /teacher/tests returns 201", status == 201, f"status={status} payload={created}")
test_id = created.get("test_id") if isinstance(created, dict) else None

# Teacher test list returns scheduling fields
_, tlist = request("GET", "/api/teacher/tests", token=teacher_tok)
if isinstance(tlist, list) and tlist:
    t = next((x for x in tlist if x["id"] == test_id), tlist[0])
    for k in ("duration_minutes", "scheduled_start", "scheduled_end", "max_loo_breaks", "max_loo_minutes"):
        check(f"teacher tests row has {k}", k in t, f"row={t}")

# Set a future scheduled_start and start exam to test gating
future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
request("PATCH", f"/api/admin/tests/{test_id}", token=admin_tok,
        body={"scheduled_start": future})
request("POST", "/api/admin/exam-toggle", token=admin_tok,
        body={"status": "started", "test_id": test_id})

status, payload = request("GET", "/api/exam/questions", token=student_tok)
check("questions blocked before scheduled_start (403)", status == 403, f"status={status} payload={payload}")

# Clear scheduled_start -> should now return 200
request("PATCH", f"/api/admin/tests/{test_id}", token=admin_tok,
        body={"scheduled_start": None})

status, payload = request("GET", "/api/exam/questions", token=student_tok)
check("questions available after clearing start (200)", status == 200)
check("response is the dict shape (not bare array)",
      isinstance(payload, dict) and "questions" in payload,
      f"type={type(payload).__name__}")
if isinstance(payload, dict):
    for k in ("remaining_seconds", "duration_minutes", "max_loo_breaks", "max_loo_minutes"):
        check(f"exam response has {k}", k in payload, f"payload keys={list(payload.keys())}")
    check("remaining_seconds is non-negative int",
          isinstance(payload.get("remaining_seconds"), int) and payload["remaining_seconds"] >= 0)

# Submit mixed answers and check 1-point-per-correct
qs = payload["questions"] if isinstance(payload, dict) else []
answers = []
for q in qs:
    if q["question"].startswith("2+2"):
        answers.append({"question_id": q["id"], "answer": "4"})    # correct
    elif q["question"].startswith("3+3"):
        answers.append({"question_id": q["id"], "answer": "99"})   # wrong

status, submit = request("POST", "/api/exam/submit", token=student_tok,
                         body={"responses": answers})
check("submit returns 200", status == 200, f"status={status} payload={submit}")
if isinstance(submit, dict):
    check("score == 1 correct", submit.get("score") == 1, f"submit={submit}")
    check("points_earned == 1 (not 10)", submit.get("points_earned") == 1, f"submit={submit}")

# Stop exam for cleanup
request("POST", "/api/admin/exam-toggle", token=admin_tok, body={"status": "stopped"})

summary_and_exit()
