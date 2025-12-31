import os
from pathlib import Path

# Project Root
PROJECT_ROOT = Path(__file__).parent.parent

# Data Directory
DATA_DIR = PROJECT_ROOT / "data"
if not DATA_DIR.exists():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

# Assets Directory
ASSETS_DIR = PROJECT_ROOT / "assets"

# Tasks File
TASKS_FILE = DATA_DIR / "tasks.json"

# App Config
APP_NAME = "TaskPulse"
APP_ICON_PATH = ASSETS_DIR / "icon.png"
APP_ICON_ICO_PATH = ASSETS_DIR / "icon.ico"
