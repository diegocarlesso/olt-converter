"""
Bridge module for supervisor compatibility.
Supervisor expects `server:app` — this re-exports from the actual entrypoint.
"""
from app.main import app  # noqa: F401
