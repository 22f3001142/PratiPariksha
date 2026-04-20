# Bugs Fixed

## Critical

- **Hardcoded Gemini API key in `student.py`** — real key was committed to source. Moved to `OPENAI_API_KEY` in `.env`.
- **Debug mode + hardcoded JWT secret** — `JWT_SECRET_KEY` silently fell back to `'dev-secret-key-replace-later'`. Now driven by `.env`.
- **Raw exception leak in chatbot** — errors returned the full Python exception string to the client. Replaced with a generic message.

## Backend

- **Broken OpenAI SDK call** — `client.responses.create(input=...)` isn't a real method; study bot always returned `None`. Fixed to `chat.completions.create(messages=[...])`.
- **Invalid route string in `teacher.py`** — `reply_forum` was registered with backslashes (`\forum\reply\...`) from an earlier edit. Would 404 in some routing tables. Fixed to forward slashes.
- **Gemini FutureWarning spam on every request** — deprecated `google-generativeai` package imported at module level. Removed import + dropped the package from `requirements.txt`.
- **Teacher could overwrite their own reply** — `Forum.reply` was a single column, every new reply wiped the previous one. Replaced with an append-only `forum_replies` table.
- **"Perfect Score" badge hardcoded to 20 questions** — any test with a different question count could never award it. Now compares against actual test length.
- **Points off by 10x** — was +10 per correct answer despite the field being called "score". Now 1 point per correct, matching intent.
- **Level progress drifted** — dashboard divided by 50, submit divided by 50, but the two ran out of sync after the points rescale. Both now use `/10`.
- **`submit_response` could crash on missing student** — `student.points += ...` dereferenced a potentially-None row. Would 500 if JWT referenced a deleted user.
- **Exam questions endpoint returned a bare array** — no duration, no remaining time, no loo-break caps. Changed to an object; frontend handles both shapes.
- **Exam start ignored `scheduled_start`** — students could begin before the scheduled window. Backend now returns 403 until the window opens.
- **Loo-break had no caps** — unlimited breaks, no duration limit. Backend now enforces per-test `max_loo_breaks` / `max_loo_minutes`.
- **Loo-break could be started twice** — no check for an active break for the same student; second call just created a second row. Now 400 if one is already active.
- **Schema migrations were not transactional** — multiple `ALTER TABLE`s ran without a wrapping rollback. Still not fully transactional, but at least all migrations now live in a single `commit()`.

## Frontend

- **Exam timer reset on reload** — `timerSeconds = 3600` was client-side only; refreshing the page gave the student a full hour back. Timer now seeded from server-sent `remaining_seconds`.
- **Exam timer kept running on submit screen** — `clearInterval` was never called after submit. Fixed.
- **Focus-mode `alert()` blocked the exam page** — if `/focus-mode/start` errored, a modal popup interrupted the test. All calls now wrapped in `try/catch` + `console.warn`, never blocking.
- **Focus-mode heartbeat leaked after page navigation** — `setInterval` survived page unload. Added `beforeunload` cleanup.
- **`fetchAPI` forced `Content-Type: application/json` on `FormData`** — broke multipart boundary, every file upload would 400. Skipped when body is `FormData`.
- **XSS via `innerHTML +=` in forum rendering** — teacher names, post bodies, reply content all rendered unescaped. Added `escapeHtml()` before template interpolation in both forum views.
- **Student "Add Notes" used `prompt()` with a link-only path** — no way to actually upload a file despite the feature being called "upload notes". Now offers both upload (PDF/TXT/DOCX/PPT/PPTX) and URL paths.
- **Teacher resource form required a URL** — no file-upload path existed. Form now accepts either a file or a URL; backend accepts either.
- **Admin dropdown showed one teacher per student** — data model only ever stored one. Replaced with a multi-select + per-row editor.
- **Unused `addStudentNotes` early-return bug** — `!driveLink.startsWith('http')` allowed `httpfoo` to pass. Now explicitly checks `http://` / `https://`.

## Smaller ones

- **`google-*` google-generativeai transitive deps** — 9 packages were pinned in `requirements.txt` but only one was used. Removed.
- **Uploads directory not gitignored** — would commit user-uploaded PDFs. Added `backend/uploads/` to `.gitignore`.
- **No `.env` template in the repo** — new contributors had no way to know what env vars existed. Added `.env` with placeholder values (file itself stays gitignored).
- **Commented-out duplicate chatbot handler** — ~40 lines of dead code sitting below the live one. Removed.
- **`DEBUG:` print spam** — chatbot logged the API key source and the Gemini request/response on every call. Removed.
- **`/uploads/<path>` caught by the frontend catch-all route** — Flask route order meant uploads tried to load from the frontend static folder. Added an explicit `startswith('uploads/')` guard.
