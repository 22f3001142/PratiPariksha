"""
Drop-in wiring example for your team.

This file is intentionally separate so your existing code remains untouched.
When your team is ready, they can copy the few lines below into the Flask app
factory or another bootstrap file.
"""

from flask import Flask

from backend.focus_mode import FocusModeConfig, FocusModeService, create_focus_mode_blueprint


def attach_focus_mode(app: Flask) -> Flask:
    config = FocusModeConfig()
    service = FocusModeService(config=config)
    app.register_blueprint(create_focus_mode_blueprint(service), url_prefix="/api/focus-mode")
    return app


if __name__ == "__main__":
    demo_app = Flask(__name__)
    attach_focus_mode(demo_app)
    demo_app.run(debug=True, port=5055)
