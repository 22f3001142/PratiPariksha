"""Resources: teacher POST (JSON + multipart), student notes (URL + upload), /uploads serving."""
import io
import uuid
from _client import request, login, ensure_seed, check, summary_and_exit, BASE_URL
import urllib.request
import urllib.error

print("== Resources ==")
ensure_seed()
teacher_tok = login("teacher", "T201", "teach123")
student_tok = login("student", "S101", "stud123")


def multipart(fields, files):
    """Encode a simple multipart/form-data body.

    fields: list of (name, value) text fields
    files:  list of (name, filename, content_bytes, mime)
    Returns (content_type, body_bytes).
    """
    boundary = "----pratiboundary" + uuid.uuid4().hex
    out = io.BytesIO()
    for name, value in fields:
        out.write(f"--{boundary}\r\n".encode())
        out.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        out.write(str(value).encode())
        out.write(b"\r\n")
    for name, filename, content, mime in files:
        out.write(f"--{boundary}\r\n".encode())
        out.write(
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode()
        )
        out.write(f"Content-Type: {mime}\r\n\r\n".encode())
        out.write(content)
        out.write(b"\r\n")
    out.write(f"--{boundary}--\r\n".encode())
    return f"multipart/form-data; boundary={boundary}", out.getvalue()


# 1. Teacher creates a resource via legacy JSON (URL only)
status, _ = request("POST", "/api/teacher/resources", token=teacher_tok, body={
    "title": "Smoke JSON Resource",
    "topic": "Mathematics",
    "file_url": "https://example.com/smoke.pdf",
})
check("teacher JSON resource returns 201", status == 201, f"status={status}")

# 2. Teacher creates a resource via multipart file upload
ct, body = multipart(
    fields=[("title", "Smoke Upload"), ("topic", "Mathematics")],
    files=[("file", "notes.pdf", b"%PDF-1.4 smoke", "application/pdf")],
)
status, payload = request("POST", "/api/teacher/resources", token=teacher_tok,
                          raw_body=body, content_type=ct)
check("teacher multipart resource returns 201", status == 201, f"status={status} payload={payload}")
uploaded_url = payload.get("file_url") if isinstance(payload, dict) else None
check("server returned file_url under /uploads/",
      isinstance(uploaded_url, str) and uploaded_url.startswith("/uploads/"),
      f"file_url={uploaded_url}")

# 3. Rejecting unsupported extension
ct2, body2 = multipart(
    fields=[("title", "Bad Ext"), ("topic", "Mathematics")],
    files=[("file", "malware.exe", b"MZ...", "application/octet-stream")],
)
status, payload = request("POST", "/api/teacher/resources", token=teacher_tok,
                          raw_body=body2, content_type=ct2)
check("teacher rejects .exe upload (400)", status == 400, f"status={status} payload={payload}")

# 4. Empty form rejected
ct3, body3 = multipart(fields=[("title", "Empty")], files=[])
status, payload = request("POST", "/api/teacher/resources", token=teacher_tok,
                          raw_body=body3, content_type=ct3)
check("teacher rejects form with no file and no url (400)", status == 400,
      f"status={status} payload={payload}")

# 5. Student sees resources and notes_url field
status, sres = request("GET", "/api/student/resources", token=student_tok)
check("/student/resources returns 200", status == 200)
check("all student resources include notes_url",
      isinstance(sres, list) and all("notes_url" in r for r in sres),
      f"payload={sres}")

if isinstance(sres, list) and sres:
    rid = sres[0]["id"]

    # 6. Student attaches notes via URL
    status, _ = request("POST", f"/api/student/resources/{rid}/notes",
                        token=student_tok,
                        body={"notes_url": "https://drive.example.com/my-notes"})
    check("student notes URL accepted (200)", status == 200, f"status={status}")

    # 7. Bad URL rejected
    status, _ = request("POST", f"/api/student/resources/{rid}/notes",
                        token=student_tok, body={"notes_url": "javascript:alert(1)"})
    check("student notes rejects non-http URL (400)", status == 400, f"status={status}")

    # 8. Student uploads notes file
    ct_n, body_n = multipart(fields=[], files=[("file", "my-notes.txt", b"hi", "text/plain")])
    status, payload = request("POST", f"/api/student/resources/{rid}/notes-upload",
                              token=student_tok, raw_body=body_n, content_type=ct_n)
    check("student notes upload returns 200", status == 200, f"status={status} payload={payload}")
    notes_url = payload.get("notes_url") if isinstance(payload, dict) else None
    check("uploaded notes_url points at /uploads/notes/",
          isinstance(notes_url, str) and notes_url.startswith("/uploads/notes/"),
          f"notes_url={notes_url}")

    # 9. /uploads/... actually serves the file
    if notes_url:
        try:
            with urllib.request.urlopen(BASE_URL + notes_url, timeout=5) as resp:
                served_ok = resp.status == 200 and resp.read() == b"hi"
        except urllib.error.HTTPError as e:
            served_ok = False
        check("uploaded file is served via /uploads/ static route", served_ok,
              f"url={notes_url}")

# 10. /uploads on a missing file -> 404
status, _ = request("GET", "/uploads/resources/does-not-exist.pdf")
check("/uploads/ 404 for missing files", status == 404, f"status={status}")

summary_and_exit()
