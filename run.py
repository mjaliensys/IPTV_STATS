# run.py

import uvicorn
from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=5000,
        reload=False,
        workers=1,  # Single worker - required for in-memory sessions
    )