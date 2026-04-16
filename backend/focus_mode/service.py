import uuid

from .config import FocusModeConfig
from .storage import FocusModeStore
from .windows_agent import WindowsFocusAgent


class FocusModeService:
    def __init__(self, config: FocusModeConfig | None = None):
        self.config = config or FocusModeConfig()
        self.store = FocusModeStore(self.config.db_path)
        self.windows_agent = WindowsFocusAgent(self.config)

    def start_focus_mode(
        self,
        student_id: str,
        exam_id: str | None = None,
        source: str = "manual",
        apply_device_controls: bool = False,
        commit_system_changes: bool = False,
    ) -> dict:
        existing = self.store.get_active_session(student_id)
        if existing:
            return {
                "ok": True,
                "already_active": True,
                "session": existing,
                "device_controls": existing["metadata"].get("device_controls", {}),
            }

        session_id = str(uuid.uuid4())
        device_controls = {"applied": False, "actions": [], "warnings": []}
        blocked_domains = list(self.config.blocked_domains)

        if apply_device_controls:
            device_controls = self.windows_agent.apply(
                blocked_domains=blocked_domains,
                commit=commit_system_changes,
            ).to_dict()

        metadata = {
            "device_controls": device_controls,
            "commit_system_changes": commit_system_changes,
        }
        self.store.create_session(
            session_id=session_id,
            student_id=student_id,
            exam_id=exam_id,
            source=source,
            blocked_domains=blocked_domains,
            metadata=metadata,
        )
        session = self.store.get_session(session_id)
        return {
            "ok": True,
            "already_active": False,
            "session": session,
            "device_controls": device_controls,
        }

    def stop_focus_mode(
        self,
        student_id: str,
        commit_system_changes: bool = False,
    ) -> dict:
        session = self.store.get_active_session(student_id)
        if not session:
            return {"ok": False, "msg": "No active focus mode session found for this student."}

        device_controls = {"applied": False, "actions": [], "warnings": []}
        if session["metadata"].get("commit_system_changes"):
            device_controls = self.windows_agent.release(commit=commit_system_changes).to_dict()

        ended = self.store.end_session(
            session_id=session["session_id"],
            metadata={"release_controls": device_controls},
        )
        return {
            "ok": ended,
            "session_id": session["session_id"],
            "device_controls": device_controls,
        }

    def heartbeat(self, session_id: str) -> dict:
        updated = self.store.update_heartbeat(session_id)
        return {"ok": updated, "session_id": session_id}

    def get_status(self, student_id: str) -> dict:
        session = self.store.get_active_session(student_id)
        return {
            "ok": True,
            "active": bool(session),
            "session": session,
        }

    def list_active_sessions(self) -> dict:
        return {
            "ok": True,
            "sessions": self.store.list_active_sessions(),
        }
