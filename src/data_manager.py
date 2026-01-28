import json
import uuid
import logging
from datetime import datetime
from threading import Lock
from typing import Dict, List, Optional
from .config import TASKS_FILE, DATA_DIR
import os

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
        self.daily_records_dir = DATA_DIR / "daily_records"
        self.stats_file = self.daily_records_dir / "stats.json"
        self.tag_stats_file = self.daily_records_dir / "tag_stats.json"
        self._ensure_file_exists()
        self._ensure_stats_exists()

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

    def _ensure_stats_exists(self):
        if not self.daily_records_dir.exists():
            try:
                os.makedirs(self.daily_records_dir)
            except OSError as e:
                logging.error(f"Error creating directory: {e}")

        if not self.stats_file.exists():
            self._save_stats({})
            
        if not self.tag_stats_file.exists():
            # Pre-fill with some default examples so user can test the UI immediately
            default_tags = {
                "专注工作": 5,
                "阅读学习": 3,
                "锻炼身体": 2
            }
            self._save_tag_stats(default_tags)

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

    def _load_stats(self) -> Dict:
        try:
            if not self.stats_file.exists():
                return {}
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_stats(self, data: Dict):
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Error saving stats: {e}")

    def _load_tag_stats(self) -> Dict:
        try:
            if not self.tag_stats_file.exists():
                return {}
            with open(self.tag_stats_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_tag_stats(self, data: Dict):
        try:
            with open(self.tag_stats_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Error saving tag stats: {e}")

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

    def record_pomodoro(self, task_name=None):
        """Record a completed pomodoro for today."""
        # 1. Date Stats
        stats = self._load_stats()
        today = datetime.now().strftime("%Y-%m-%d")
        
        if today in stats:
            stats[today] += 1
        else:
            stats[today] = 1
            
        self._save_stats(stats)
        
        # 2. Tag Stats
        if task_name:
            # Clean task name: Remove icons or status text if any, usually passed clean
            # but user might input mixed stuff. We assume task_name is what user typed.
            t_stats = self._load_tag_stats()
            # Simple normalization
            name = task_name.strip()
            if name:
                t_stats[name] = t_stats.get(name, 0) + 1
                self._save_tag_stats(t_stats)
        
        return stats[today]

    def get_daily_stats(self) -> Dict[str, int]:
        """Get the history of pomodoro counts per day."""
        return self._load_stats()

    def get_tag_stats(self) -> List[tuple]:
        """Get top tags sorted by count. Returns list of (name, count)."""
        stats = self._load_tag_stats()
        # Sort by count desc
        sorted_tags = sorted(stats.items(), key=lambda x: x[1], reverse=True)
        return sorted_tags

    def clear_tag_stats(self):
        """Reset tag statistics."""
        self._save_tag_stats({})
