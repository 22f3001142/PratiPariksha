from flask import Blueprint, jsonify, request

from .service import FocusModeService

try:
    from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
except Exception:  # pragma: no cover
    def jwt_required(*_args, **_kwargs):
        def decorator(fn):
            return fn
        return decorator

    def get_jwt_identity():
        return None

    def get_jwt():
        return {}


def create_focus_mode_blueprint(service: FocusModeService | None = None) -> Blueprint:
    focus_service = service or FocusModeService()
    focus_bp = Blueprint("focus_mode", __name__)

    @focus_bp.route("/start", methods=["POST"])
    @jwt_required()
    def start_focus_mode():
        claims = get_jwt() or {}
        payload = request.get_json() or {}
        student_id = get_jwt_identity() or payload.get("student_id")
        if not student_id:
            return jsonify({"msg": "student_id is required"}), 400

        if claims.get("role") not in {None, "", "student", "admin", "teacher"}:
            return jsonify({"msg": "Unauthorized"}), 403

        result = focus_service.start_focus_mode(
            student_id=str(student_id),
            exam_id=str(payload.get("exam_id")) if payload.get("exam_id") else None,
            source=payload.get("source") or "manual",
            apply_device_controls=bool(payload.get("apply_device_controls")),
            commit_system_changes=bool(payload.get("commit_system_changes")),
        )
        return jsonify(result), 200

    @focus_bp.route("/stop", methods=["POST"])
    @jwt_required()
    def stop_focus_mode():
        payload = request.get_json() or {}
        student_id = get_jwt_identity() or payload.get("student_id")
        if not student_id:
            return jsonify({"msg": "student_id is required"}), 400

        result = focus_service.stop_focus_mode(
            student_id=str(student_id),
            commit_system_changes=bool(payload.get("commit_system_changes")),
        )
        status_code = 200 if result.get("ok") else 404
        return jsonify(result), status_code

    @focus_bp.route("/status", methods=["GET"])
    @jwt_required()
    def focus_mode_status():
        student_id = get_jwt_identity() or request.args.get("student_id")
        if not student_id:
            return jsonify({"msg": "student_id is required"}), 400
        return jsonify(focus_service.get_status(str(student_id))), 200

    @focus_bp.route("/heartbeat", methods=["POST"])
    @jwt_required()
    def focus_mode_heartbeat():
        payload = request.get_json() or {}
        session_id = payload.get("session_id")
        if not session_id:
            return jsonify({"msg": "session_id is required"}), 400
        result = focus_service.heartbeat(str(session_id))
        return jsonify(result), 200 if result.get("ok") else 404

    @focus_bp.route("/active", methods=["GET"])
    @jwt_required()
    def active_sessions():
        claims = get_jwt() or {}
        if claims.get("role") not in {"admin", "teacher"}:
            return jsonify({"msg": "Unauthorized"}), 403
        return jsonify(focus_service.list_active_sessions()), 200

    return focus_bp
