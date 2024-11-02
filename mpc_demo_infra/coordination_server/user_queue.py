import threading
import secrets
from dataclasses import dataclass
from typing import Optional, Tuple
import time

@dataclass
class User:
    access_key: str
    computation_key: Optional[str] = None
    _time_at_queue_head: Optional[int] = None

class UserQueue:
    def __init__(self, max_size: int, queue_head_timeout: int):
        self.users: list[User] = []
        self.max_size = max_size
        self.queue_head_timeout = queue_head_timeout
        self.lock = threading.Lock()
        self.user_positions = {}

    def _get_time() -> int:
        return int(time.time())

    def _set_queue_head_data_if_needed(self):
        if len(self.users) > 0 and self.users[0]._time_at_queue_head is None:
            user = self.users[0]
            user._time_at_queue_head = int(time.time())
            user.computation_key = secrets.token_urlsafe(16)

    def build_position_map(self) -> None:
        self.user_positions = {user.access_key: (i, user) for i, user in enumerate(self.users)}

    def validate_computation_key(self, computation_key: str) -> bool:
        with self.lock:
            return len(self.users) > 0 and self.users[0].computation_key == computation_key

    def finish_computation(self, computation_key: str) -> bool:
        with self.lock:
            if len(self.users) > 0 and self.users[0].computation_key == computation_key:
                user = self.users.pop(0)
                self._set_queue_head_data_if_needed()
                self.build_position_map()
                return True
            else:
                return False

    # returns (postion, computations_key)
    def get_position(self, access_key: str) -> Tuple[Optional[int], Optional[str]]:
        with self.lock:
            # reject if max_size has been reached
            if len(self.users) == self.max_size:
                return None, None

            # if user at queue head times out, remove the user
            if len(self.users) > 0 and self.users[0]._time_at_queue_head is not None:
                queue_head_time = UserQueue._get_time() - self.users[0]._time_at_queue_head
                if queue_head_time > self.queue_head_timeout:
                    user = self.users.pop(0)
                    self.build_position_map()

            position, user = self.user_positions.get(access_key, (None, None))

            # if the user is not in the queue, add the user
            if position is None:
                user = User(access_key=access_key)
                self.users.append(user)
                rebuild_position_map = True
                position = len(self.users) - 1
                self.build_position_map()

            self._set_queue_head_data_if_needed()
            position, user = self.user_positions[access_key]

            return (position, None if position != 0 else user.computation_key)

