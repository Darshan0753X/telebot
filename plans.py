"""
plans.py — Plan limits and enforcement
"""

from config import FREE_DAILY_LIMIT

class PlanManager:
    def __init__(self, db):
        self.db = db

    def daily_limit(self, plan: str) -> int:
        """Returns -1 for unlimited."""
        if plan == "premium":
            return -1
        return FREE_DAILY_LIMIT

    def can_download(self, user_id: int, plan: str) -> bool:
        limit = self.daily_limit(plan)
        if limit == -1:
            return True
        today_count = self.db.get_today_count(user_id)
        return today_count < limit

    def record_download(self, user_id: int):
        """Called after successful download."""
        pass  # Already handled in bot.py via increment_stat

    def features(self, plan: str) -> dict:
        if plan == "premium":
            return {
                "max_size_mb": 10000,
                "audio_quality": "320kbps",
                "ads": False,
                "batch": True,
                "priority": "HIGH",
                "history": True,
            }
        return {
            "max_size_mb": 50,
            "audio_quality": "128kbps",
            "ads": True,
            "batch": False,
            "priority": "Normal",
            "history": False,
        }
