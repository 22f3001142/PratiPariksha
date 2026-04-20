# PratiPariksha

A full-stack Computer-Based Testing (CBT) platform with role-based portals for admins, teachers, and students. Built with Flask (Python) on the backend and vanilla HTML/CSS/JS on the frontend.

---

## Features

### Admin
- Create and manage student/teacher accounts
- Start and stop live exams; assign a test paper to each session
- Monitor loo-break usage across all students
- Assign students to one or more teachers

### Teacher
- Build a question bank (MCQ, MSQ, Numerical Answer Type) with topics, difficulty levels, and explanations
- Assemble timed test papers from the question bank; schedule start/end windows
- Configure per-test loo-break caps (count and max duration)
- Upload study resources (PDF files or external links)
- View student performance analytics by topic
- Moderate the student forum

### Student
- Take timed computer-based exams in a secure interface
- Request timed loo breaks during an exam (subject to per-test limits)
- Browse study resources and attach personal notes (file or URL)
- Participate in a Q&A forum with teacher replies and voting
- Chat with an AI study bot for concept explanations
- Earn points and level up; purchase emoji avatars from a shop; collect badges
- View the class leaderboard

### Focus Mode
- Windows-level distraction blocker that activates during an exam
- Heartbeat-based session management (30-second keep-alive)
- Graceful start/stop with automatic session cleanup

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3, Flask |
| ORM | SQLAlchemy (Flask-SQLAlchemy) |
| Database | SQLite (default) — swappable to PostgreSQL via `DATABASE_URL` |
| Authentication | JWT (Flask-JWT-Extended) |
| AI Study Bot | OpenAI API (`gpt-4.1-mini`) |
| Password hashing | Werkzeug (pbkdf2:sha256) |
| Analytics | Pandas, NumPy, SciPy |
| Frontend | Vanilla HTML5 / CSS3 / JavaScript (no build step) |
| CORS | Flask-CORS |

---

## Project Structure

```
PratiPariksha/
├── backend/
│   ├── app/
│   │   ├── __init__.py          # App factory & DB initialisation
│   │   ├── models.py            # SQLAlchemy models (12 tables)
│   │   ├── services.py          # Scoring, analytics, study-bot logic
│   │   ├── uploads.py           # File upload helpers
│   │   └── api/
│   │       ├── auth.py          # Login & test-user seeding
│   │       ├── admin.py         # Admin endpoints
│   │       ├── teacher.py       # Teacher endpoints
│   │       ├── student.py       # Student endpoints
│   │       └── exam.py          # Live exam flow
│   ├── focus_mode/              # Distraction-blocker module (Windows)
│   │   ├── __init__.py
│   │   ├── api.py
│   │   ├── service.py
│   │   ├── storage.py
│   │   └── windows_agent.py
│   ├── instance/                # Auto-created; holds pratipariksha.db
│   ├── uploads/                 # User-uploaded files
│   └── run.py                   # Entry point
├── frontend/
│   ├── index.html               # Landing page
│   ├── login.html               # Role-based login
│   ├── admin_portal.html        # Admin dashboard
│   ├── teacher_portal.html      # Teacher dashboard
│   ├── student_portal.html      # Student dashboard
│   ├── cbt_exam.html            # Exam interface
│   ├── about.html
│   └── public/
│       ├── css/style.css
│       ├── js/common.js         # Shared fetchAPI client & auth helpers
│       └── images/
├── tests/                       # Smoke-test suite (9 scripts)
├── requirements.txt
├── init_db.py                   # Manual DB init with sample data
├── check_db.py                  # Schema verification utility
└── .env                         # Credentials (see below)
```

---

## Setup & Installation

### Prerequisites

- Python 3.10+
- pip

### 1 — Clone the repo

```bash
git clone <repo-url>
cd PratiPariksha
```

### 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### 3 — Configure environment variables

Create `backend/.env`:

```env
OPENAI_API_KEY=sk-...           # Required for the AI study bot
OPENAI_CHATBOT_MODEL=gpt-4.1-mini

# Optional overrides (all have sensible defaults)
PORT=8391
JWT_SECRET_KEY=change-me-in-production
DATABASE_URL=sqlite:///instance/pratipariksha.db
```

> **Production note:** Change `JWT_SECRET_KEY` to a long random string before deploying.

### 4 — Run the backend

```bash
cd backend
python run.py
```

The server starts on `http://127.0.0.1:8391` by default. On first run it automatically:
- Creates the SQLite database and all tables
- Seeds a default admin account (`admin` / `admin123`)

The frontend is served statically by Flask — just open the URL above in a browser.

---

## Default Credentials

| Role | Username / ID | Password |
|------|--------------|----------|
| Admin | `admin` | `admin123` |
| Demo student (after `init_db.py`) | `S101` | `password123` |
| Demo teacher (after `init_db.py`) | `T201` | `teach123` |

To seed additional demo data:

```bash
python init_db.py
```

---

## API Reference

All endpoints require a Bearer JWT token in the `Authorization` header (obtained from `/api/auth/login`), except the login route itself.

### Auth — `/api/auth`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/login` | Login with `{ role, username, password }` |
| POST | `/setup-test-users` | Seed demo users |

### Admin — `/api/admin`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/users` | List all students and teachers |
| POST | `/users` | Create a student or teacher account |
| POST | `/exam-toggle` | Start or stop the live exam |
| GET | `/tests` | List all test papers |
| PATCH | `/tests/<id>` | Edit test metadata / scheduling |
| PUT | `/students/<id>/teachers` | Assign teachers to a student |
| GET | `/loo-breaks` | Loo-break usage analytics |
| GET | `/analytics` | Platform-wide statistics |

### Teacher — `/api/teacher`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/analytics` | Student performance by topic |
| GET | `/questions` | List teacher's questions |
| POST | `/questions` | Create a question (MCQ / MSQ / NAT) |
| GET | `/tests` | List teacher's test papers |
| POST | `/tests` | Create a test paper |
| PATCH | `/tests/<id>` | Update test settings |
| GET | `/resources` | List uploaded resources |
| POST | `/resources` | Upload a PDF or add a link |
| GET | `/forum` | Forum posts (with moderation view) |
| POST | `/forum/reply/<id>` | Reply to a forum post |

### Student — `/api/student`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/dashboard` | Profile, rank, topic stats, badges |
| GET | `/leaderboard` | Top-10 leaderboard |
| GET | `/profile` | Student info |
| GET | `/study-plan` | Upcoming tests & weak areas |
| GET | `/upcoming-tests` | Tests sorted by scheduled date |
| GET | `/resources` | Study resources available to student |
| POST | `/resources/<id>/notes` | Attach a note URL to a resource |
| POST | `/resources/<id>/notes-upload` | Upload a note file |
| GET | `/forum` | Forum posts |
| POST | `/forum` | Create a post |
| POST | `/forum/<id>/reply` | Reply to a post |
| POST | `/forum/<id>/vote` | Upvote or downvote a post |
| POST | `/chatbot` | Query the AI study bot |
| POST | `/shop/buy` | Purchase an avatar |

### Exam — `/api/exam`

| Method | Path | Description |
|--------|------|-------------|
| GET | `/questions` | Fetch exam questions (validates schedule) |
| POST | `/submit` | Submit all answers; auto-graded |
| POST | `/loo-break/start` | Begin a loo break |
| POST | `/loo-break/end` | End a loo break |
| POST | `/mood` | Log confidence/mood |
| GET | `/status` | Current exam state |

### Focus Mode — `/api/focus-mode`

| Method | Path | Description |
|--------|------|-------------|
| POST | `/start` | Activate distraction blocking |
| POST | `/stop` | Deactivate blocking |
| GET | `/status` | Current session status |
| POST | `/heartbeat` | Keep session alive |
| GET | `/active` | List active sessions (admin/teacher only) |

---

## Database Schema

| Table | Key Fields |
|-------|-----------|
| `admin` | `admin_id`, `password` |
| `students` | `admission_id`, `name`, `email`, `password`, `points`, `level`, `badges`, `assigned_teacher_id` |
| `teachers` | `employee_id`, `name`, `email`, `password`, `subject` |
| `student_teachers` | `student_id`, `teacher_id` (many-to-many) |
| `questions` | `id`, `text`, `type` (MCQ/MSQ/NAT), `options`, `correct_answer`, `difficulty`, `topic`, `subtopic`, `explanation` |
| `test_papers` | `id`, `title`, `topic`, `duration_minutes`, `scheduled_start`, `scheduled_end`, `max_loo_breaks`, `max_loo_minutes` |
| `test_paper_questions` | `test_id`, `question_id` |
| `exams` | `id`, `status`, `test_id`, `started_at` |
| `responses` | `id`, `student_id`, `question_id`, `answer` |
| `loo_break` | `id`, `student_id`, `start_time`, `end_time` |
| `forum` | `id`, `student_id`, `text`, `votes`, `timestamp` |
| `forum_replies` | `id`, `post_id`, `author_role`, `author_id`, `body`, `timestamp` |
| `resources` | `id`, `title`, `url`, `file_path`, `topic`, `notes_url`, `uploaded_by` |
| `moods` | `id`, `student_id`, `mood`, `timestamp` |

---

## Scoring & Gamification

| Mechanic | Detail |
|----------|--------|
| Points | 1 point per correct answer |
| Level | `(total_points // 10) + 1` |
| Badge — Perfect Score | Awarded when a student scores 100% on any test |
| Avatar shop | Emoji avatars purchasable with points |
| Leaderboard | Ranked by total points |

**Answer matching:**
- MCQ / NAT: case-insensitive string comparison after stripping whitespace
- MSQ: comma-separated values compared as unordered sets

---

## Loo Break System

Each test paper stores `max_loo_breaks` (count) and `max_loo_minutes` (total duration cap). During an exam:

1. Student requests a break via `POST /api/exam/loo-break/start`
2. Backend checks remaining allowance; returns 400 if exhausted
3. Student ends the break via `POST /api/exam/loo-break/end`
4. Duration is logged; subsequent requests deduct from the remaining budget

---

## Running Tests

The `tests/` directory contains 9 standalone smoke scripts that hit the live server:

```bash
# Start the server first
cd backend && python run.py &

# Run each test
cd ../tests
python test_auth.py
python test_admin.py
python test_exam_flow.py
python test_loo_breaks.py
python test_forum.py
python test_resources.py
python test_gamification.py
python test_focus_mode.py
python test_schema.py
```

Set `BASE_URL` to point at a different server:

```bash
BASE_URL=http://localhost:8391 python test_auth.py
```

---

## Environment Variable Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | Required for the AI study bot |
| `OPENAI_CHATBOT_MODEL` | `gpt-4.1-mini` | OpenAI model used by the study bot |
| `PORT` | `8391` | Flask server port |
| `JWT_SECRET_KEY` | `dev-secret-key-replace-later` | JWT signing secret (**change in production**) |
| `DATABASE_URL` | SQLite at `backend/instance/pratipariksha.db` | Full SQLAlchemy DB URI |
| `SQLALCHEMY_DATABASE_URI` | Same as above | Alternative name for the DB URI |

---

## Notes

- The frontend is served directly by Flask as static files — no separate server or build step is needed.
- Focus Mode (`backend/focus_mode/`) is Windows-only; the module loads gracefully on other platforms but OS-level blocking calls are no-ops.
- The SQLite database is auto-created on first run inside `backend/instance/`. For production, point `DATABASE_URL` at a PostgreSQL instance (`psycopg2-binary` is already in `requirements.txt`).
- All uploaded files are stored under `backend/uploads/` and are excluded from version control via `.gitignore`.
