# run.py
import uvicorn
from src.lurnic.api import app

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Lurnic Web Server Starting...")
    print("=" * 50)
    print(f"📍 Local: http://localhost:8000")
    print(f"📍 API Docs: http://localhost:8000/docs")
    print("=" * 50)
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )