"""
database.py — Simple JSON-based user database
For production, swap with SQLite or PostgreSQL
"""

import json
import os
from datetime import datetime
from threading import Lock

from config import DB_FILE

class Database:
    def __init__(self):
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
        self._lock = Lock()
        self._load()

    def _load(self):
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r") as f:
                self._data = json.load(f)
        else:
            self._data = {"users": {}, "global": {"downloads": 0}}

    def _save(self):
        with open(DB_FILE, "w") as f:
            json.dump(self._data, f, indent=2)

    def _user(self, user_id: int) -> dict:
        uid = str(user_id)
        if uid not in self._data["users"]:
            self._data["users"][uid] = {
                "plan": "free",
                "stats": {"total": 0, "video": 0, "audio": 0, "photo": 0, "data_mb": 0.0},
                "today_count": 0,
                "today_date": "",
                "joined": datetime.now().isoformat(),
            }
        return self._data["users"][uid]

    def add_user(self, user_id: int, username: str):
        with self._lock:
            u = self._user(user_id)
            u["username"] = username
            self._save()

    def get_user_plan(self, user_id: int) -> str:
        with self._lock:
            return self._user(user_id).get("plan", "free")

    def set_plan(self, user_id: int, plan: str):
        with self._lock:
            self._user(user_id)["plan"] = plan
            self._save()

    def get_user_stats(self, user_id: int) -> dict:
        with self._lock:
            u = self._user(user_id)
            stats = dict(u.get("stats", {}))
            # Today count (reset if new day)
            today = datetime.now().strftime("%Y-%m-%d")
            if u.get("today_date") != today:
                stats["today"] = 0
            else:
                stats["today"] = u.get("today_count", 0)
            return stats

    def increment_stat(self, user_id: int, key: str):
        with self._lock:
            u = self._user(user_id)
            if key == "today":
                today = datetime.now().strftime("%Y-%m-%d")
                if u.get("today_date") != today:
                    u["today_date"] = today
                    u["today_count"] = 0
                u["today_count"] = u.get("today_count", 0) + 1
            else:
                u["stats"][key] = u["stats"].get(key, 0) + 1
            self._data["global"]["downloads"] = self._data["global"].get("downloads", 0) + 1
            self._save()

    def add_data_mb(self, user_id: int, mb: float):
        with self._lock:
            u = self._user(user_id)
            u["stats"]["data_mb"] = u["stats"].get("data_mb", 0.0) + mb
            self._save()

    def get_today_count(self, user_id: int) -> int:
        with self._lock:
            u = self._user(user_id)
            today = datetime.now().strftime("%Y-%m-%d")
            if u.get("today_date") != today:
                return 0
            return u.get("today_count", 0)

    def get_global_stats(self) -> dict:
        with self._lock:
            users = self._data["users"]
            premium = sum(1 for u in users.values() if u.get("plan") == "premium")
            return {
                "users": len(users),
                "premium": premium,
                "downloads": self._data["global"].get("downloads", 0),
            }

    def get_all_user_ids(self) -> list:
        with self._lock:
            return [int(uid) for uid in self._data["users"].keys()]
