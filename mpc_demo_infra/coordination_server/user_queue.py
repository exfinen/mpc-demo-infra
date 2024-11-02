from dataclasses import dataclass
from readerwriterlock import rwlock
import secrets
import time
from typing import Optional, Self, Tuple

@dataclass
class User:
    access_key: str
    computation_key: Optional[str] = None
    _time_at_queue_head: Optional[int] = None
    next: Optional[Self] = None

class UserQueue:
    def __init__(self, max_size: int, queue_head_timeout: int):
        self.users_head: User = None
        self.users_tail: User = None
        self.users_len: int = 0
        self.max_size = max_size
        self.queue_head_timeout = queue_head_timeout
        self.user_positions = {}
        self.locker = rwlock.RWLockWrite()

    def _add_user(self, user: User) -> None:
        if self.users_head == None:
            self.users_head = user
            user.next = None
            self.users_tail = user
        else:
            self.users_tail.next = user
            user.next = None
            self.users_tail = user
        self.users_len += 1

    def _pop_user(self) -> User:
        if self.users_head == None:
            return None
        else:
            head = self.users_head
            self.users_head = head.next
            head.next = None
            self.users_len -= 1
            return head

    def _get_time() -> int:
        return int(time.time())

    def _set_queue_head_data_if_needed(self):
        if self.users_len > 0 and self.users_head._time_at_queue_head is None:
            user = self.users_head
            user._time_at_queue_head = int(time.time())
            user.computation_key = secrets.token_urlsafe(16)

    def build_position_map(self) -> None:
        user = self.users_head
        self.user_positions = {}
        position = 0
        while user is not None: 
            self.user_positions[user.access_key] = (position, user)
            position += 1
            user = user.next

    def validate_computation_key(self, computation_key: str) -> bool:
        with self.locker.gen_rlock():
            return self.users_len > 0 and self.users_head.computation_key == computation_key

    def finish_computation(self, computation_key: str) -> bool:
        with self.locker.gen_wlock():
            head = self
            if self.users_len > 0 and self.users_head.computation_key == computation_key:
                user = self._pop_user()
                self._set_queue_head_data_if_needed()
                self.build_position_map()
                return True
            else:
                return False

    # returns (postion, computations_key)
    def get_position(self, access_key: str) -> Tuple[Optional[int], Optional[str]]:
        with self.locker.gen_wlock():
            # reject if max_size has been reached
            if self.users_len == self.max_size:
                return None, None

            # if user at queue head times out, remove the user
            if self.users_len > 0 and self.users_head._time_at_queue_head is not None:
                queue_head_time = UserQueue._get_time() - self.users_head._time_at_queue_head
                if queue_head_time > self.queue_head_timeout:
                    self._pop_user()
                    self.build_position_map()

            position, user = self.user_positions.get(access_key, (None, None))

            # if the user is not in the queue, add the user
            if position is None:
                user = User(access_key=access_key)
                self._add_user(user)
                position = self.users_len - 1
                self.user_positions[access_key] = (position, user)

            self._set_queue_head_data_if_needed()
            position, user = self.user_positions[access_key]

            return (position, None if position != 0 else user.computation_key)

