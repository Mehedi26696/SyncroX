"""
Persistent Chat History Manager
Stores all chat messages room-wise and user-wise in JSON files.
"""

import os
import json
import time
import threading
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

# Default directory for storing chat history
DEFAULT_HISTORY_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "chat_history"
)


class ChatHistoryManager:
    """
    Manages persistent chat message storage.
    - Room-wise: Each room has its own history file
    - User-wise: Messages are tagged with username for filtering
    """
    
    def __init__(self, history_dir: str = DEFAULT_HISTORY_DIR, max_messages_per_room: int = 1000):
        """
        Initialize the chat history manager.
        
        Args:
            history_dir: Directory to store history files
            max_messages_per_room: Maximum messages to keep per room (oldest removed first)
        """
        self.history_dir = history_dir
        self.max_messages = max_messages_per_room
        self._lock = threading.Lock()
        
        # Create directory if it doesn't exist
        os.makedirs(self.history_dir, exist_ok=True)
    
    def _get_room_file(self, room: str) -> str:
        """Get the path to a room's chat history file."""
        safe_room = str(room).replace("/", "_").replace("\\", "_")
        return os.path.join(self.history_dir, f"room_{safe_room}_chat.json")
    
    def _get_user_file(self, username: str) -> str:
        """Get the path to a user's chat history file."""
        safe_user = str(username).replace("/", "_").replace("\\", "_").replace(" ", "_")
        return os.path.join(self.history_dir, f"user_{safe_user}_chat.json")
    
    def _load_room_history(self, room: str) -> List[Dict[str, Any]]:
        """Load chat history for a specific room from disk."""
        filepath = self._get_room_file(room)
        if not os.path.exists(filepath):
            return []
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("messages", [])
        except (json.JSONDecodeError, IOError) as e:
            print(f"[ChatHistory] Error loading history for room {room}: {e}")
            return []
    
    def _save_room_history(self, room: str, messages: List[Dict[str, Any]]) -> bool:
        """Save chat history for a specific room to disk."""
        filepath = self._get_room_file(room)
        
        try:
            data = {
                "room": room,
                "last_updated": time.time(),
                "last_updated_readable": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_messages": len(messages),
                "messages": messages
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"[ChatHistory] Error saving history for room {room}: {e}")
            return False
    
    def _load_user_history(self, username: str) -> List[Dict[str, Any]]:
        """Load chat history for a specific user from disk."""
        filepath = self._get_user_file(username)
        if not os.path.exists(filepath):
            return []
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("messages", [])
        except (json.JSONDecodeError, IOError) as e:
            print(f"[ChatHistory] Error loading history for user {username}: {e}")
            return []
    
    def _save_user_history(self, username: str, messages: List[Dict[str, Any]]) -> bool:
        """Save chat history for a specific user to disk."""
        filepath = self._get_user_file(username)
        
        try:
            data = {
                "username": username,
                "last_updated": time.time(),
                "last_updated_readable": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_messages": len(messages),
                "messages": messages
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"[ChatHistory] Error saving history for user {username}: {e}")
            return False
    
    def add_message(
        self,
        room: str,
        username: str,
        message: str,
        msg_type: str = "text"  # "text", "image", "system"
    ) -> bool:
        """
        Add a new message to both room and user history.
        
        Args:
            room: Room code
            username: Username of sender
            message: Message content (text or base64 for images)
            msg_type: Type of message ("text", "image", "system")
        
        Returns:
            True if saved successfully
        """
        timestamp = time.time()
        record = {
            "id": f"{room}_{username}_{int(timestamp * 1000)}",
            "timestamp": timestamp,
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "room": room,
            "username": username,
            "message": message,
            "type": msg_type
        }
        
        with self._lock:
            # Save to room history
            room_messages = self._load_room_history(room)
            room_messages.append(record)
            
            # Trim if exceeds max
            if len(room_messages) > self.max_messages:
                room_messages = room_messages[-self.max_messages:]
            
            room_saved = self._save_room_history(room, room_messages)
            
            # Save to user history (only for non-system messages)
            user_saved = True
            if msg_type != "system":
                user_messages = self._load_user_history(username)
                user_messages.append(record)
                
                # Trim user history too
                if len(user_messages) > self.max_messages:
                    user_messages = user_messages[-self.max_messages:]
                
                user_saved = self._save_user_history(username, user_messages)
        
        return room_saved and user_saved
    
    def get_room_history(
        self,
        room: str,
        limit: int = 50,
        before_timestamp: Optional[float] = None,
        msg_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get chat history for a room.
        
        Args:
            room: Room code
            limit: Maximum number of messages to return
            before_timestamp: Only get messages before this timestamp (for pagination)
            msg_type: Filter by message type
        
        Returns:
            List of message records (newest last)
        """
        with self._lock:
            messages = self._load_room_history(room)
        
        # Apply filters
        if before_timestamp:
            messages = [m for m in messages if m["timestamp"] < before_timestamp]
        
        if msg_type:
            messages = [m for m in messages if m.get("type") == msg_type]
        
        # Return last N messages
        return messages[-limit:]
    
    def get_user_history(
        self,
        username: str,
        limit: int = 50,
        room: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get chat history for a specific user.
        
        Args:
            username: Username
            limit: Maximum number of messages to return
            room: Filter by room (optional)
        
        Returns:
            List of message records (newest last)
        """
        with self._lock:
            messages = self._load_user_history(username)
        
        if room:
            messages = [m for m in messages if m.get("room") == room]
        
        return messages[-limit:]
    
    def get_room_stats(self, room: str) -> Dict[str, Any]:
        """Get statistics for a room's chat history."""
        with self._lock:
            messages = self._load_room_history(room)
        
        if not messages:
            return {
                "room": room,
                "total_messages": 0,
                "unique_users": 0,
                "users": [],
                "first_message": None,
                "last_message": None
            }
        
        users = list(set(m["username"] for m in messages if m.get("type") != "system"))
        
        return {
            "room": room,
            "total_messages": len(messages),
            "unique_users": len(users),
            "users": users,
            "first_message": messages[0]["datetime"] if messages else None,
            "last_message": messages[-1]["datetime"] if messages else None,
            "message_types": {
                "text": len([m for m in messages if m.get("type") == "text"]),
                "image": len([m for m in messages if m.get("type") == "image"]),
                "system": len([m for m in messages if m.get("type") == "system"])
            }
        }
    
    def search_messages(
        self,
        query: str,
        room: Optional[str] = None,
        username: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search messages containing a query string.
        
        Args:
            query: Search query (case-insensitive)
            room: Filter by room (optional)
            username: Filter by user (optional)
            limit: Maximum results
        
        Returns:
            List of matching messages
        """
        results = []
        query_lower = query.lower()
        
        with self._lock:
            # Search in room history if room specified
            if room:
                messages = self._load_room_history(room)
                for m in messages:
                    if query_lower in m.get("message", "").lower():
                        if username is None or m.get("username") == username:
                            results.append(m)
            
            # Search in user history if only username specified
            elif username:
                messages = self._load_user_history(username)
                for m in messages:
                    if query_lower in m.get("message", "").lower():
                        results.append(m)
            
            # Search all rooms (slower)
            else:
                for filename in os.listdir(self.history_dir):
                    if filename.startswith("room_") and filename.endswith("_chat.json"):
                        room_code = filename[5:-10]  # Extract room code
                        messages = self._load_room_history(room_code)
                        for m in messages:
                            if query_lower in m.get("message", "").lower():
                                results.append(m)
        
        # Sort by timestamp and limit
        results.sort(key=lambda x: x["timestamp"])
        return results[-limit:]
    
    def delete_room_history(self, room: str) -> bool:
        """Delete all chat history for a room."""
        filepath = self._get_room_file(room)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
            return True
        except IOError as e:
            print(f"[ChatHistory] Error deleting room history: {e}")
            return False
    
    def list_rooms_with_history(self) -> List[str]:
        """List all rooms that have chat history."""
        rooms = []
        for filename in os.listdir(self.history_dir):
            if filename.startswith("room_") and filename.endswith("_chat.json"):
                room_code = filename[5:-10]
                rooms.append(room_code)
        return sorted(rooms)


# Singleton instance for easy import
_chat_history_manager: Optional[ChatHistoryManager] = None
_manager_lock = threading.Lock()


def get_chat_history_manager() -> ChatHistoryManager:
    """Get or create the singleton ChatHistoryManager instance."""
    global _chat_history_manager
    with _manager_lock:
        if _chat_history_manager is None:
            _chat_history_manager = ChatHistoryManager()
        return _chat_history_manager
