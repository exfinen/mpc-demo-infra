import threading
from dataclasses import dataclass
from typing import Optional
from time import time

@dataclass
class User:
    voucher_code: str
    time_at_queue_head: Optional[int] = None
    pop_key: Optional[str] = None

class UserQueue:
    users: list[User] = []

    def __init__(self, max_size: int, queue_head_timeout: int):
        self.max_size = max_size
        self.queue_head_timeout = queue_head_timeout
        self.lock = threading.Lock()

    @classmethod
    def _get_time() -> int:
        return int(time.time())

    def _set_time_at_queue_head_if_needed(self):
        if len(self.users) > 0 and self.users[0].time_at_queue_head is None:
            self.users[0].time_at_queue_head = int(time.time())

    def pop_user(self, pop_key: str) -> bool:
        with self.lock:
            if len(self.users) == 0 or self.users[0].pop_key != pop_key:
                return False
            else:
                user = users.pop(0)
                self._set_time_at_queue_head_if_needed()
                return True

    def get_position(self, voucher_code: str) -> int:
        with self.lock:
            # if the user with voucher is not in the queue, add the user
            if not any(user.voucher_code == voucher_code for user in self.users):
                user = User(voucher_code=voucher_code)
                self.users.append(user)

            # if user[0] is staying there too long, move the user to the end
            now = UserQueue._get_time()
            if now - self.users[0].time_at_queue_head > self.queue_head_timeout:
                user = self.users.pop(0)
                user.time_at_queue_head = None
                self.users.append(user)
                self._set_time_at_queue_head_if_needed()

            # return the position of the user with the voucher
            for i, user in enumerate(self.clients):
                if user.voucher_code == voucher_code:
                    return i

