"""
ESIG app.py - Entry point for FastAPI application
This file is used by HuggingFace Spaces and serves the FastAPI app.
"""
from server.main import app

__all__ = ["app"]


def main() -> None:
    """Run the FastAPI server."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
