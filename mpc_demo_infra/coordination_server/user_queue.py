from dataclasses import dataclass
from enum import Enum
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

class AddResult(Enum):
    SUCCEEDED = 0
    ALREADY_IN_QUEUE = 1
    QUEUE_IS_FULL = 2

class UserQueue:
    def __init__(self, max_size: int, queue_head_timeout: int):
        self.users_head: User = None
        self.users_tail: User = None
        self.users_len: int = 0
        self.max_size = max_size
        self.queue_head_timeout = queue_head_timeout
        self.user_positions = {}
        self.locker = rwlock.RWLockWrite()

    def _print_queue(self) -> None:
        users = []
        user = self.users_head
        while user is not None:
            users.append(user.access_key)
            user = user.next
        print(users)
    
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
            user = self.users_head
            self.users_head = user.next
            user.next = None
            self.users_len -= 1
            return user

    def _get_time() -> int:
        return int(time.time())

    def _set_queue_head_data_if_needed(self):
        if self.users_len > 0 and self.users_head._time_at_queue_head is None:
            user = self.users_head
            user._time_at_queue_head = int(time.time())
            user.computation_key = secrets.token_urlsafe(16)

    def _build_position_map(self) -> None:
        user = self.users_head
        self.user_positions = {}
        position = 0
        while user is not None: 
            self.user_positions[user.access_key] = (position, user)
            position += 1
            user = user.next

    def _timeout_head_user(self) -> None:
        with self.locker.gen_wlock():
            head = self.users_head
            if head is None or head._time_at_queue_head is None:
                return
            queue_head_time = UserQueue._get_time() - head._time_at_queue_head
            if queue_head_time <= self.queue_head_timeout:
                return
            self._pop_user()
            self._build_position_map()
            self._set_queue_head_data_if_needed()

    def add_user(self, access_key: str) -> AddResult:
        with self.locker.gen_rlock():
            # fail if max_size has been reached
            if self.users_len == self.max_size:
                return AddResult.QUEUE_IS_FULL

            # fail if the user is already in the queue
            if self.user_positions.get(access_key, None) is not None:
                return AddResult.ALREADY_IN_QUEUE

        user = User(access_key=access_key)
        with self.locker.gen_wlock():
            self._add_user(user)
            position = self.users_len - 1
            self.user_positions[access_key] = (position, user)
            self._set_queue_head_data_if_needed()

        return AddResult.SUCCEEDED

    def get_position(self, access_key: str) -> Optional[int]:
        with self.locker.gen_rlock():
            position, _ = self.user_positions.get(access_key, (None, None))
            return position

    def get_computation_key(self, access_key: str) -> Optional[str]:
        self._timeout_head_user()
        with self.locker.gen_rlock():
            position, user = self.user_positions.get(access_key, (None, None))
            if position is not None and position == 0:
                self._set_queue_head_data_if_needed()
                return user.computation_key
            else:
                return None

    def validate_computation_key(self, access_key: str, computation_key: str) -> bool:
        self._timeout_head_user()
        with self.locker.gen_rlock():
            position, user = self.user_positions.get(access_key, (None, None))
            return position is not None and position == 0 and user.computation_key == computation_key

    def finish_computation(self, access_key: str, computation_key: str) -> bool:
        with self.locker.gen_wlock():
            position, user = self.user_positions.get(access_key, (None, None))
            if position is not None and position == 0 and user.computation_key == computation_key:
                user = self._pop_user()
                self._set_queue_head_data_if_needed()
                self._build_position_map()
                return True
            else:
                return False

