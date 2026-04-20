"""Admin: user management, multi-teacher assignment, exam toggle."""
from _client import request, login, ensure_seed, check, summary_and_exit

print("== Admin ==")
ensure_seed()
admin_tok = login("admin", "admin", "admin123")

status, users = request("GET", "/api/admin/users", token=admin_tok)
check("/admin/users returns 200", status == 200)
check("/admin/users response has students[] and teachers[]",
      isinstance(users, dict) and isinstance(users.get("students"), list) and isinstance(users.get("teachers"), list))
s101 = next((s for s in users.get("students", []) if s["admission_id"] == "S101"), None)
check("S101 present in users list", s101 is not None)
check("S101 row exposes assigned_teacher_ids list",
      s101 is not None and isinstance(s101.get("assigned_teacher_ids"), list),
      f"row={s101}")

# Multi-teacher assignment round-trip
status, _ = request("PUT", "/api/admin/students/S101/teachers",
                    token=admin_tok, body={"teacher_ids": ["T201"]})
check("PUT /admin/students/S101/teachers returns 200", status == 200, f"status={status}")

status, users2 = request("GET", "/api/admin/users", token=admin_tok)
s101b = next((s for s in users2.get("students", []) if s["admission_id"] == "S101"), None)
check("S101 assigned_teacher_ids reflects write",
      s101b is not None and s101b.get("assigned_teacher_ids") == ["T201"],
      f"row={s101b}")

# Clearing with empty list works
status, _ = request("PUT", "/api/admin/students/S101/teachers",
                    token=admin_tok, body={"teacher_ids": []})
check("PUT with empty teacher_ids returns 200", status == 200, f"status={status}")

# Put back for downstream tests
request("PUT", "/api/admin/students/S101/teachers",
        token=admin_tok, body={"teacher_ids": ["T201"]})

# Unknown student -> 404
status, _ = request("PUT", "/api/admin/students/UNKNOWN/teachers",
                    token=admin_tok, body={"teacher_ids": []})
check("PUT for unknown student returns 404", status == 404, f"status={status}")

# Exam toggle
status, _ = request("POST", "/api/admin/exam-toggle", token=admin_tok,
                    body={"status": "stopped"})
check("exam toggle to 'stopped' returns 200", status == 200, f"status={status}")

# Non-admin cannot toggle
from _client import login as _login
student_tok = _login("student", "S101", "stud123")
status, _ = request("POST", "/api/admin/exam-toggle", token=student_tok,
                    body={"status": "started"})
check("student cannot toggle exam (403)", status == 403, f"status={status}")

# Analytics endpoint
status, analytics = request("GET", "/api/admin/analytics", token=admin_tok)
check("/admin/analytics returns 200", status == 200)
check("analytics has core counters",
      isinstance(analytics, dict) and
      all(k in analytics for k in ("total_students", "total_teachers", "active_exams", "available_tests")),
      f"payload={analytics}")

summary_and_exit()
