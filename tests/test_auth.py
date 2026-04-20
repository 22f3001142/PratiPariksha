"""Auth: login flows, JWT role claims, 401/403 gates."""
from _client import request, login, ensure_seed, check, summary_and_exit

print("== Auth ==")
ensure_seed()

status, payload = request("POST", "/api/auth/login",
                          body={"role": "admin", "username": "admin", "password": "admin123"})
check("admin login returns 200 + access_token",
      status == 200 and isinstance(payload, dict) and "access_token" in payload,
      f"status={status} payload={payload}")

status, _ = request("POST", "/api/auth/login",
                    body={"role": "admin", "username": "admin", "password": "WRONG"})
check("wrong password rejected (401)", status == 401, f"status={status}")

status, _ = request("POST", "/api/auth/login",
                    body={"role": "student", "username": "DOES_NOT_EXIST", "password": "x"})
check("unknown user rejected (401)", status == 401, f"status={status}")

student_tok = login("student", "S101", "stud123")
teacher_tok = login("teacher", "T201", "teach123")
admin_tok = login("admin", "admin", "admin123")
check("all three roles log in", all([student_tok, teacher_tok, admin_tok]))

status, _ = request("GET", "/api/student/dashboard")
check("JWT-protected route returns 401 without token", status == 401, f"status={status}")

status, _ = request("GET", "/api/admin/users", token=student_tok)
check("student hitting /admin/users returns 403", status == 403, f"status={status}")

status, _ = request("GET", "/api/teacher/forum", token=student_tok)
check("student hitting /teacher/forum returns 403", status == 403, f"status={status}")

status, payload = request("GET", "/api/student/dashboard", token=student_tok)
check("student token accesses /student/dashboard (200)",
      status == 200 and isinstance(payload, dict) and "points" in payload,
      f"status={status}")

summary_and_exit()
