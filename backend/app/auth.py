from functools import wraps

from flask import jsonify, request, session


def is_authenticated() -> bool:
    return bool(session.get("is_authenticated"))


def auth_required(handler):
    @wraps(handler)
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            return jsonify({"error": "Unauthorized"}), 401
        return handler(*args, **kwargs)

    return wrapper


def register_auth_routes(app, settings):
    @app.post("/api/auth/login")
    def login():
        body = request.get_json(silent=True) or {}
        password = body.get("password", "")
        if password != settings.app_password:
            return jsonify({"ok": False, "error": "Invalid password"}), 401

        session["is_authenticated"] = True
        session.permanent = True
        return jsonify({"ok": True})

    @app.post("/api/auth/logout")
    def logout():
        session.clear()
        return jsonify({"ok": True})

    @app.get("/api/auth/me")
    def me():
        return jsonify({"isAuthenticated": is_authenticated()})
