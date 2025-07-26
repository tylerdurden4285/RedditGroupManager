import os
from dotenv import load_dotenv
from api_main import app

load_dotenv()

HOST = os.getenv("API_HOST", "0.0.0.0")
PORT = int(os.getenv("API_PORT", 8015))
LOG_LEVEL = os.getenv("LOG_LEVEL", "info").lower()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, log_level=LOG_LEVEL)
