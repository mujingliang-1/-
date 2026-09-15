"""运行：python -m display_inspect"""
import os

import uvicorn

from display_inspect.app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
