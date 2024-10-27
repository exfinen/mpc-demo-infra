from mpc_demo_infra.coordination_server.user_queue import UserQueue

def get_queue(max_size: int = 10, queue_head_timeout: int=60) -> UserQueue:
    return UserQueue(max_size=max_size, queue_head_timeout=queue_head_timeout)

def test_pop_user_empty_queue():
    q = get_queue()
    assert q.pop_user('mpc') == False

def test_get_position_1_user():
    q = get_queue()
    position, _ = q.get_position('mpc')
    assert position == 0

def test_get_position_2_users():
    q = get_queue()
    position = q.get_position('mpc')
    assert position, _ == 0
    position = q.get_position('apple')
    assert position, _ == 1

def test_get_position_2_users_valid_pop():
    q = get_queue()
    position, pop_key_1 = q.get_position('mpc')
    assert position == 0
    position, pop_key_2 = q.get_position('apple')
    assert position == 1
    assert q.pop_user(pop_key_1) == True

def test_get_position_2_users_invalid_pop():
    q = get_queue()
    position, pop_key_1 = q.get_position('mpc')
    assert position == 0
    position, pop_key_2 = q.get_position('apple')
    assert position == 1
    assert q.pop_user(pop_key_2) == False

