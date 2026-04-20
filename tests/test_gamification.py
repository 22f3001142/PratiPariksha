"""Gamification: 1 point per correct, Perfect Score at N==total, level math."""
from _client import request, login, ensure_seed, check, summary_and_exit

print("== Gamification ==")
ensure_seed()
admin_tok = login("admin", "admin", "admin123")
teacher_tok = login("teacher", "T201", "teach123")
student_tok = login("student", "S101", "stud123")

# Snapshot of existing points so we can assert a +N delta
_, dash_before = request("GET", "/api/student/dashboard", token=student_tok)
pts_before = dash_before.get("points", 0) if isinstance(dash_before, dict) else 0
badges_before = dash_before.get("badges", []) if isinstance(dash_before, dict) else []
print(f"  points before = {pts_before}, badges = {badges_before}")

# Build a small 2-question test and run it with both answered correctly
_, qs = request("GET", "/api/teacher/questions", token=teacher_tok)
q_ids = [q["id"] for q in qs[:2]]
_, created = request("POST", "/api/teacher/tests", token=teacher_tok, body={
    "title": "Gamification Smoke",
    "topic": "Mathematics",
    "duration_minutes": 30,
    "max_loo_breaks": 0,
    "max_loo_minutes": 0,
    "question_ids": q_ids,
})
test_id = created.get("test_id") if isinstance(created, dict) else None
request("POST", "/api/admin/exam-toggle", token=admin_tok,
        body={"status": "started", "test_id": test_id})

_, live = request("GET", "/api/exam/questions", token=student_tok)
answers = []
for q in live.get("questions", []) if isinstance(live, dict) else []:
    if q["question"].startswith("2+2"):
        answers.append({"question_id": q["id"], "answer": "4"})
    elif q["question"].startswith("3+3"):
        answers.append({"question_id": q["id"], "answer": "6"})

status, submit = request("POST", "/api/exam/submit", token=student_tok,
                         body={"responses": answers})
check("submit 200", status == 200)
if isinstance(submit, dict):
    check("2/2 correct => score=2", submit.get("score") == 2, f"submit={submit}")
    check("2/2 correct => points_earned=2 (1 per correct)",
          submit.get("points_earned") == 2, f"submit={submit}")
    check("new_total_points == previous + 2",
          submit.get("new_total_points") == pts_before + 2,
          f"submit={submit} pts_before={pts_before}")

# Perfect Score badge should now be attached (test had 2 questions, student got 2)
_, dash_after = request("GET", "/api/student/dashboard", token=student_tok)
badges_after = dash_after.get("badges", []) if isinstance(dash_after, dict) else []
check("Perfect Score badge awarded when correct_count == total",
      "Perfect Score" in badges_after, f"badges={badges_after}")

# level_progress is out of 10 (rescale)
if isinstance(dash_after, dict):
    lp = dash_after.get("level_progress")
    check("level_progress in [0,9] (mod 10 scale)",
          isinstance(lp, int) and 0 <= lp <= 9, f"level_progress={lp}")

request("POST", "/api/admin/exam-toggle", token=admin_tok, body={"status": "stopped"})

summary_and_exit()
