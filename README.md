# PratiPariksha

PratiPariksha is a computer-based testing platform with separate admin, teacher, and student portals. It includes question-bank management, exam control, student analytics, resources, a study bot, and a Focus Mode feature for distraction-aware exam sessions.

## Modules

- `backend/app`: Main Flask application, APIs, models, and services
- `backend/focus_mode`: Standalone Focus Mode module with its own blueprint, service, storage, and Windows device-control agent
- `frontend`: Static portal pages for admin, teacher, student, and exam flows

## Key Features

- Admin exam control and user management
- Teacher question bank, tests, forum replies, and resources
- Student dashboard, leaderboard, shop, study bot, and exam client
- Focus Mode APIs and frontend controls on the student dashboard and exam page

## Focus Mode

Focus Mode is implemented as a separate module so it can be embedded with minimal impact on the rest of the codebase.

Backend routes:

- `POST /api/focus-mode/start`
- `POST /api/focus-mode/stop`
- `GET /api/focus-mode/status`
- `POST /api/focus-mode/heartbeat`
- `GET /api/focus-mode/active`

Frontend controls:

- Student dashboard: toggle Focus Mode before an exam
- Exam page: toggle Focus Mode during a test

Notes:

- The current UI starts backend Focus Mode sessions immediately.
- OS-level blocking of distractions is designed for Windows and may require administrator permissions when enabled by the embedding app.

## Local Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the backend:

```bash
python backend/run.py
```

4. Open the frontend through the Flask app, typically at:

```text
http://127.0.0.1:5000/
```

## Default Login

Admin account created on startup:

- Username: `admin`
- Password: `admin123`

## Repository Notes

- `main` is intended to be the clean branch for sharing.
- The Focus Mode work is preserved without removing existing application modules.
- The separate `backend/focus_mode` package makes future team integration easier.
