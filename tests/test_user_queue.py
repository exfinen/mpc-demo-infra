from mpc_demo_infra.coordination_server.user_queue import UserQueue
import time

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

    # add 2 users
    position, pop_key_1 = q.get_position('mpc')
    assert position == 0
    position, _ = q.get_position('apple') # pop_key is None here
    assert position == 1

    # pop 2 users
    assert q.pop_user(pop_key_1) == True
    position, pop_key_2 = q.get_position('apple')
    # trying to pop w/ invalid key should fail
    assert q.pop_user(pop_key_1) == False
    # popping w/ valid key should succed
    assert q.pop_user(pop_key_2) == True

def test_get_position_2_users_invalid_pop():
    q = get_queue()
    position, pop_key_1 = q.get_position('mpc')
    assert position == 0
    position, pop_key_2 = q.get_position('apple')
    assert position == 1
    assert q.pop_user(pop_key_2) == False

def test_queue_head_timeout():
    q = get_queue(queue_head_timeout=1)
    position, pop_key_1 = q.get_position('mpc')
    position, _ = q.get_position('apple')

    time.sleep(2)

    # popping mpc should fail since apple should be at the top
    position, pop_key_1_2 = q.get_position('mpc')
    assert position == 1
    assert pop_key_1_2 is None
    assert q.pop_user(pop_key_1) == False

    position, pop_key_2  = q.get_position('apple')
    assert q.pop_user(pop_key_2) == True

def test_pop_user_empty_queue_after_pops():
    q = get_queue()

    # add 2 users
    position, pop_key_1 = q.get_position('mpc')
    assert position == 0
    position, _ = q.get_position('apple') # pop_key is None here
    assert position == 1

    # pop 2 users
    assert q.pop_user(pop_key_1) == True
    position, pop_key_2 = q.get_position('apple')
    assert q.pop_user(pop_key_2) == True

    # should not be able to pop anymore
    assert q.pop_user(pop_key_1) == False
    assert q.pop_user(pop_key_2) == False

def test_pop_user_twice():
    q = get_queue()

    # add user
    position, pop_key_1 = q.get_position('mpc')
    assert position == 0

    # pop user
    assert q.pop_user(pop_key_1) == True

    # popping user again should fail
    assert q.pop_user(pop_key_1) == False

