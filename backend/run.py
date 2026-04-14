import os

from app import create_app


app = create_app()
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "38473"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=BACKEND_PORT, debug=True)
