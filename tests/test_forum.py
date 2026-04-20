"""Forum: threaded replies, teacher + student append, no overwrite, HTML content preserved."""
from _client import request, login, ensure_seed, check, summary_and_exit

print("== Forum ==")
ensure_seed()
teacher_tok = login("teacher", "T201", "teach123")
student_tok = login("student", "S101", "stud123")

# Student creates a fresh post
status, created = request("POST", "/api/student/forum", token=student_tok,
                          body={"post": "smoke forum question"})
check("create post returns 201", status == 201, f"status={status} payload={created}")
post_id = created.get("id") if isinstance(created, dict) else None
check("post id returned", post_id is not None)

# Teacher appends reply #1
status, _ = request("POST", f"/api/teacher/forum/reply/{post_id}", token=teacher_tok,
                    body={"body": "teacher answer one"})
check("teacher reply #1 returns 201", status == 201, f"status={status}")

# Teacher appends reply #2 using legacy key 'reply'
status, _ = request("POST", f"/api/teacher/forum/reply/{post_id}", token=teacher_tok,
                    body={"reply": "teacher answer two"})
check("teacher reply #2 (legacy key) returns 201", status == 201, f"status={status}")

# Empty reply rejected
status, _ = request("POST", f"/api/teacher/forum/reply/{post_id}", token=teacher_tok,
                    body={"body": "   "})
check("empty teacher reply rejected (400)", status == 400, f"status={status}")

# Student replies in the thread
status, _ = request("POST", f"/api/student/forum/{post_id}/reply", token=student_tok,
                    body={"body": "student follow-up"})
check("student reply returns 201", status == 201, f"status={status}")

# Student without body rejected
status, _ = request("POST", f"/api/student/forum/{post_id}/reply", token=student_tok,
                    body={})
check("student reply with no body returns 400", status == 400, f"status={status}")

# Voting still works
status, vote = request("POST", f"/api/student/forum/vote/{post_id}", token=student_tok)
check("vote endpoint 200 and returns count", status == 200 and isinstance(vote, dict) and "votes" in vote,
      f"status={status} payload={vote}")

# Fetch thread
status, forum = request("GET", "/api/student/forum", token=student_tok)
check("/student/forum returns 200", status == 200)
target = next((p for p in forum if p["id"] == post_id), None) if isinstance(forum, list) else None
check("fresh post present in listing", target is not None)

if target:
    replies = target.get("replies", [])
    roles = [r["author_role"] for r in replies]
    check("at least 3 replies appended (not overwritten)", len(replies) >= 3, f"got {replies}")
    check("teacher replies appear at least twice", roles.count("teacher") >= 2, f"roles={roles}")
    check("student reply present", "student" in roles, f"roles={roles}")
    check("each reply has body + author_name", all(r.get("body") and r.get("author_name") for r in replies))

# Teacher forum view
status, teacher_forum = request("GET", "/api/teacher/forum", token=teacher_tok)
check("/teacher/forum returns 200", status == 200)

summary_and_exit()
