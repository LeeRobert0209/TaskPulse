import json
import uuid
import logging
from datetime import datetime
from threading import Lock
from typing import Dict, List, Optional
from .config import TASKS_FILE

class DataManager:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DataManager, cls).__new__(cls)
                    cls._instance._init_data()
        return cls._instance

    def _init_data(self):
        self.data_file = TASKS_FILE
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not self.data_file.exists():
            default_data = {
                "tasks": [],
                "user_config": {
                    "engineer_mode": False,
                    "auto_start": False
                },
                "meta": {
                    "version": "1.0.0",
                    "created_at": datetime.now().isoformat()
                }
            }
            self._save_json(default_data)

    def _load_json(self) -> Dict:
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logging.error(f"Error loading tasks: {e}")
            return {"tasks": [], "user_config": {}}

    def _save_json(self, data: Dict):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Error saving tasks: {e}")

    # --- Public API ---

    def get_all_tasks(self) -> List[Dict]:
        data = self._load_json()
        return data.get("tasks", [])

    def add_task(self, title: str, task_type: str, params: Dict = None) -> str:
        data = self._load_json()
        if params is None:
            params = {}
        
        task_id = str(uuid.uuid4())
        new_task = {
            "id": task_id,
            "title": title,
            "type": task_type,
            "params": params,
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        data["tasks"].append(new_task)
        self._save_json(data)
        return task_id

    def delete_task(self, task_id: str) -> bool:
        data = self._load_json()
        tasks = data.get("tasks", [])
        original_count = len(tasks)
        tasks = [t for t in tasks if t["id"] != task_id]
        
        if len(tasks) < original_count:
            data["tasks"] = tasks
            self._save_json(data)
            return True
        return False

    def get_config(self) -> Dict:
        data = self._load_json()
        return data.get("user_config", {})

    def update_config(self, key: str, value):
        data = self._load_json()
        if "user_config" not in data:
            data["user_config"] = {}
        data["user_config"][key] = value
        self._save_json(data)
