import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PACKAGES_DIR = BASE_DIR / ".packages"

if PACKAGES_DIR.exists():
    sys.path.insert(0, str(PACKAGES_DIR))

import uvicorn


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
