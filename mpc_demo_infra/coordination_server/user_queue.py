import threading
import secrets
from dataclasses import dataclass
from typing import Optional, Tuple
import time

@dataclass
class User:
    voucher_code: str
    computation_key: Optional[str] = None
    _time_at_queue_head: Optional[int] = None

class UserQueue:

    def __init__(self, max_size: int, queue_head_timeout: int):
        self.users: list[User] = []
        self.max_size = max_size
        self.queue_head_timeout = queue_head_timeout
        self.lock = threading.Lock()

    def _get_time() -> int:
        return int(time.time())

    def _set_queue_head_data_if_needed(self):
        if len(self.users) > 0 and self.users[0]._time_at_queue_head is None:
            user = self.users[0]
            user._time_at_queue_head = int(time.time())
            user.computation_key = secrets.token_urlsafe(16)

    # for debugging
    def _get_users(self) -> list[User]:
        return self.users

    def validate_computation_key(self, computation_key: str) -> bool:
        with self.lock:
            return len(self.users) > 0 and self.users[0].computation_key == computation_key

    def finish_computation(self, computation_key: str) -> bool:
        with self.lock:
            if len(self.users) > 0 and self.users[0].computation_key == computation_key:
                user = self.users.pop(0)
                self._set_queue_head_data_if_needed()
                return True
            else:
                return False

    def get_position(self, voucher_code: str) -> Tuple[int, Optional[str]]:
        with self.lock:
            # if the user with voucher is not in the queue, add the user
            if not any(user.voucher_code == voucher_code for user in self.users):
                user = User(voucher_code=voucher_code)
                self.users.append(user)

            # if user at queue head times out, move the user to the end
            if self.users[0]._time_at_queue_head is not None:
                queue_head_time = UserQueue._get_time() - self.users[0]._time_at_queue_head
                if queue_head_time > self.queue_head_timeout:
                    user = self.users.pop(0)
                    user._time_at_queue_head = None
                    user.computation_key = None
                    self.users.append(user)

            self._set_queue_head_data_if_needed()

            # return the position and computation_key of the user with the voucher
            for i, user in enumerate(self.users):
                if user.voucher_code == voucher_code:
                    return i, user.computation_key

