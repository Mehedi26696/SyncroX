"""
Persistent Execution History Manager
Stores all code executions room-wise in JSON files for historical tracking.
"""

import os
import json
import time
import threading
from typing import List, Dict, Any, Optional
from pathlib import Path

# Default directory for storing execution history
DEFAULT_HISTORY_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "exec_history"
)


class ExecHistoryManager:
    """
    Manages persistent execution history storage.
    Each room has its own history file containing all executions.
    """
    
    def __init__(self, history_dir: str = DEFAULT_HISTORY_DIR, max_records_per_room: int = 500):
        """
        Initialize the history manager.
        
        Args:
            history_dir: Directory to store history files
            max_records_per_room: Maximum records to keep per room (oldest removed first)
        """
        self.history_dir = history_dir
        self.max_records = max_records_per_room
        self._lock = threading.Lock()
        
        # Create directory if it doesn't exist
        os.makedirs(self.history_dir, exist_ok=True)
    
    def _get_history_file(self, room: str) -> str:
        """Get the path to a room's history file."""
        safe_room = str(room).replace("/", "_").replace("\\", "_")
        return os.path.join(self.history_dir, f"room_{safe_room}_history.json")
    
    def _load_room_history(self, room: str) -> List[Dict[str, Any]]:
        """Load history for a specific room from disk."""
        filepath = self._get_history_file(room)
        if not os.path.exists(filepath):
            return []
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("executions", [])
        except (json.JSONDecodeError, IOError) as e:
            print(f"[ExecHistory] Error loading history for room {room}: {e}")
            return []
    
    def _save_room_history(self, room: str, history: List[Dict[str, Any]]) -> bool:
        """Save history for a specific room to disk."""
        filepath = self._get_history_file(room)
        
        try:
            data = {
                "room": room,
                "last_updated": time.time(),
                "total_executions": len(history),
                "executions": history
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"[ExecHistory] Error saving history for room {room}: {e}")
            return False
    
    def add_execution(
        self,
        room: str,
        user: str,
        language: str,
        code: str,
        stdin: str,
        stdout: str,
        stderr: str,
        return_code: int,
        success: bool,
        time_ms: float,
        timestamp: Optional[float] = None
    ) -> bool:
        """
        Add an execution record to the history.
        
        Returns:
            True if saved successfully, False otherwise
        """
        record = {
            "id": f"{room}_{int(time.time() * 1000)}_{user}",
            "timestamp": timestamp or time.time(),
            "room": str(room),
            "user": user,
            "language": language,
            "code": code,
            "stdin": stdin or "",
            "stdout": stdout or "",
            "stderr": stderr or "",
            "return_code": return_code,
            "success": success,
            "time_ms": time_ms,
        }
        
        with self._lock:
            history = self._load_room_history(room)
            history.append(record)
            
            # Trim to max records (keep newest)
            if len(history) > self.max_records:
                history = history[-self.max_records:]
            
            return self._save_room_history(room, history)
    
    def get_room_history(
        self,
        room: str,
        language: Optional[str] = None,
        user: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get execution history for a room with optional filters.
        
        Args:
            room: Room ID to get history for
            language: Filter by language (optional)
            user: Filter by user (optional)
            limit: Maximum number of records to return (optional)
        
        Returns:
            List of execution records, newest first
        """
        with self._lock:
            history = self._load_room_history(room)
        
        # Apply filters
        if language:
            history = [r for r in history if r.get("language") == language]
        if user:
            history = [r for r in history if r.get("user") == user]
        
        # Sort by timestamp (newest first)
        history.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        
        # Apply limit
        if limit:
            history = history[:limit]
        
        return history
    
    def get_all_rooms(self) -> List[str]:
        """Get list of all rooms that have execution history."""
        rooms = []
        try:
            for filename in os.listdir(self.history_dir):
                if filename.startswith("room_") and filename.endswith("_history.json"):
                    # Extract room name from filename
                    room = filename[5:-13]  # Remove "room_" prefix and "_history.json" suffix
                    rooms.append(room)
        except IOError:
            pass
        return sorted(rooms)
    
    def get_all_history(
        self,
        language: Optional[str] = None,
        user: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get execution history across all rooms.
        
        Args:
            language: Filter by language (optional)
            user: Filter by user (optional)
            limit: Maximum number of records to return (optional)
        
        Returns:
            List of execution records from all rooms, newest first
        """
        all_history = []
        
        for room in self.get_all_rooms():
            room_history = self.get_room_history(room, language=language, user=user)
            all_history.extend(room_history)
        
        # Sort by timestamp (newest first)
        all_history.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        
        # Apply limit
        if limit:
            all_history = all_history[:limit]
        
        return all_history
    
    def get_unique_users(self, room: Optional[str] = None) -> List[str]:
        """Get list of unique users from history."""
        users = set()
        
        if room:
            history = self.get_room_history(room)
            for record in history:
                if record.get("user"):
                    users.add(record["user"])
        else:
            for r in self.get_all_rooms():
                history = self.get_room_history(r)
                for record in history:
                    if record.get("user"):
                        users.add(record["user"])
        
        return sorted(users)
    
    def get_unique_languages(self, room: Optional[str] = None) -> List[str]:
        """Get list of unique languages from history."""
        languages = set()
        
        if room:
            history = self.get_room_history(room)
            for record in history:
                if record.get("language"):
                    languages.add(record["language"])
        else:
            for r in self.get_all_rooms():
                history = self.get_room_history(r)
                for record in history:
                    if record.get("language"):
                        languages.add(record["language"])
        
        return sorted(languages)
    
    def get_stats(self, room: Optional[str] = None) -> Dict[str, Any]:
        """
        Get execution statistics.
        
        Args:
            room: Room to get stats for (or None for all rooms)
        
        Returns:
            Dictionary with statistics
        """
        if room:
            history = self.get_room_history(room)
        else:
            history = self.get_all_history()
        
        if not history:
            return {
                "total_executions": 0,
                "successful": 0,
                "failed": 0,
                "by_language": {},
                "by_user": {},
                "avg_time_ms": 0,
            }
        
        successful = sum(1 for r in history if r.get("success"))
        by_language = {}
        by_user = {}
        total_time = 0
        
        for record in history:
            lang = record.get("language", "unknown")
            user = record.get("user", "unknown")
            
            by_language[lang] = by_language.get(lang, 0) + 1
            by_user[user] = by_user.get(user, 0) + 1
            total_time += record.get("time_ms", 0)
        
        return {
            "total_executions": len(history),
            "successful": successful,
            "failed": len(history) - successful,
            "success_rate": (successful / len(history) * 100) if history else 0,
            "by_language": by_language,
            "by_user": by_user,
            "avg_time_ms": total_time / len(history) if history else 0,
        }
    
    def clear_room_history(self, room: str) -> bool:
        """Clear all history for a room."""
        filepath = self._get_history_file(room)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
            return True
        except IOError as e:
            print(f"[ExecHistory] Error clearing history for room {room}: {e}")
            return False


# Global instance for easy access
_history_manager: Optional[ExecHistoryManager] = None


def get_history_manager() -> ExecHistoryManager:
    """Get the global history manager instance."""
    global _history_manager
    if _history_manager is None:
        _history_manager = ExecHistoryManager()
    return _history_manager
