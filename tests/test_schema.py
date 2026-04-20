"""Schema: every migration-applied column and new table exists in the live DB."""
import pathlib
import sys

from _client import check, summary_and_exit

print("== Schema ==")
repo_root = pathlib.Path(__file__).resolve().parents[1]
backend = repo_root / "backend"
sys.path.insert(0, str(backend))

try:
    from app import create_app
    from app.models import db
    from sqlalchemy import inspect
except Exception as exc:
    print(f"  ! cannot import app: {exc}")
    sys.exit(2)

app = create_app()
with app.app_context():
    insp = inspect(db.engine)
    tables = set(insp.get_table_names())

    # Tables we added
    for t in ("student_teachers", "forum_replies"):
        check(f"table {t} exists", t in tables, f"tables={sorted(tables)}")

    # Columns added to test_papers
    tp_cols = {c["name"] for c in insp.get_columns("test_papers")}
    for col in ("duration_minutes", "scheduled_start", "scheduled_end",
                "max_loo_breaks", "max_loo_minutes"):
        check(f"test_papers.{col} exists", col in tp_cols,
              f"columns={sorted(tp_cols)}")

    # Column added to resources
    res_cols = {c["name"] for c in insp.get_columns("resources")}
    check("resources.notes_url exists", "notes_url" in res_cols,
          f"columns={sorted(res_cols)}")

    # Existing columns we rely on haven't regressed
    for tbl, col in [
        ("students", "assigned_teacher_id"),
        ("teachers", "subject"),
        ("exams", "test_id"),
        ("questions", "topic"),
        ("questions", "subtopic"),
        ("questions", "explanation"),
    ]:
        cols = {c["name"] for c in insp.get_columns(tbl)}
        check(f"{tbl}.{col} exists", col in cols, f"columns={sorted(cols)}")

summary_and_exit()
