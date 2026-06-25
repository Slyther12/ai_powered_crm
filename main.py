"""
NexuSolve CRM — Application entry point.
Starts the FastAPI server with uvicorn.
"""
import uvicorn

from backend.config import HOST, PORT, DEBUG


def main():
    uvicorn.run(
        "backend.app:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
    )


if __name__ == "__main__":
    main()
