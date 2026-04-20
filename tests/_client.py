"""Shared helpers for the smoke-test suite.

All scripts hit a live backend (default http://127.0.0.1:8391). Start the
server first: `python backend/run.py`.
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8391")

_PASS = 0
_FAIL = 0


def request(method, path, token=None, body=None, raw_body=None, content_type=None):
    url = BASE_URL + path
    data = None
    headers = {}
    if raw_body is not None:
        data = raw_body
        if content_type:
            headers["Content-Type"] = content_type
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            raw = resp.read()
            ctype = resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as e:
        status = e.code
        raw = e.read()
        ctype = e.headers.get("Content-Type", "") if e.headers else ""
    except urllib.error.URLError as e:
        print(f"  ! cannot reach {url}: {e.reason}")
        sys.exit(2)
    if ctype.startswith("application/json"):
        try:
            payload = json.loads(raw) if raw else None
        except Exception:
            payload = raw
    else:
        payload = raw
    return status, payload


def login(role, username, password):
    status, payload = request("POST", "/api/auth/login",
                              body={"role": role, "username": username, "password": password})
    if status != 200 or not isinstance(payload, dict) or "access_token" not in payload:
        print(f"  ! login failed ({role}={username}): HTTP {status} {payload}")
        sys.exit(2)
    return payload["access_token"]


def ensure_seed():
    """Seed admin/T201/S101 and two math questions if missing. Idempotent."""
    import pathlib
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    backend = repo_root / "backend"
    sys.path.insert(0, str(backend))
    try:
        from app import create_app
        from app.models import db, Admin, Teacher, Student, Question
        from werkzeug.security import generate_password_hash
    except Exception as exc:
        print(f"  ! cannot import app: {exc}")
        sys.exit(2)
    app = create_app()
    with app.app_context():
        if not Admin.query.filter_by(username="admin").first():
            db.session.add(Admin(
                username="admin",
                password=generate_password_hash("admin123", method="pbkdf2:sha256")
            ))
        if not Teacher.query.filter_by(employee_id="T201").first():
            db.session.add(Teacher(
                employee_id="T201", name="Smoke Teacher",
                email="t201@smoke.local",
                password=generate_password_hash("teach123", method="pbkdf2:sha256"),
                subject="Mathematics"
            ))
        if not Student.query.filter_by(admission_id="S101").first():
            db.session.add(Student(
                admission_id="S101", name="Smoke Student",
                email="s101@smoke.local",
                password=generate_password_hash("stud123", method="pbkdf2:sha256"),
                assigned_teacher_id="T201"
            ))
        if Question.query.filter_by(topic="Mathematics").count() < 2:
            db.session.add(Question(question="2+2?", type="NAT", options=None,
                                    correct_answer="4", topic="Mathematics"))
            db.session.add(Question(question="3+3?", type="NAT", options=None,
                                    correct_answer="6", topic="Mathematics"))
        db.session.commit()


def check(label, condition, detail=None):
    global _PASS, _FAIL
    if condition:
        _PASS += 1
        print(f"  PASS  {label}")
    else:
        _FAIL += 1
        print(f"  FAIL  {label}" + (f"  -- {detail}" if detail else ""))


def summary_and_exit():
    print(f"\n{_PASS} passed, {_FAIL} failed")
    sys.exit(0 if _FAIL == 0 else 1)
