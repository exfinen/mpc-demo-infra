from mpc_demo_infra.coordination_server.user_queue import UserQueue
import time

def get_queue(max_size: int = 10, queue_head_timeout: int=60) -> UserQueue:
    return UserQueue(max_size=max_size, queue_head_timeout=queue_head_timeout)

def test_validate_invalid_computation_key():
    q = get_queue()
    assert q.validate_computation_key('bad_key') == False

def test_get_position_single_user():
    q = get_queue()
    pos, key = q.get_position('mpc')
    assert pos == 0 and key is not None

def test_get_position_multiple_users():
    q = get_queue()
    pos1, key1 = q.get_position('mpc')
    assert pos1 == 0 and key1 is not None
    pos2, key2 = q.get_position('apple')
    assert pos2 == 1 and key2 is None
    pos3, key3 = q.get_position('orange')
    assert pos3 == 2 and key3 is None

def test_2_users_get_pop_finish_succ():
    q = get_queue()

    # add 2 users
    pos1, key1 = q.get_position('mpc')
    assert pos1 == 0 and key1 is not None
    pos2, key2 = q.get_position('apple')
    assert pos2 == 1 and key2 is None

    # validate user1 computaion
    assert q.validate_computation_key(key1) == True

    # invalid key should be considered invalid
    assert q.validate_computation_key(None) == False
    assert q.validate_computation_key(key1 + 'abc') == False

    # finish user1 computation
    assert q.finish_computation(key1) == True

    # after finishing computation, key1 should no longer be valid
    assert q.validate_computation_key(key1) == False

    # let user2 get the computation key
    pos2, key2 = q.get_position('apple')

    # user1 key should no longer be valid
    assert q.validate_computation_key(key1) == False

    # user1 cannot finish computation either
    assert q.finish_computation(key1) == False

    # user2 should be able to validate its computation
    assert q.validate_computation_key(key2) == True

    # user2 finishes computation
    assert q.finish_computation(key2) == True

    # user2 key should no longer be valid
    assert q.validate_computation_key(key2) == False

def test_queue_head_timeout():
    # set the timeout to 1 second
    q = get_queue(queue_head_timeout=1)

    pos1, key1 = q.get_position('mpc')
    _, _ = q.get_position('apple')
    _, _ = q.get_position('orange')

    time.sleep(2)

    # user1 should have been removed from the the queue
    pos1, key1 = q.get_position('mpc')
    assert pos1 == 2 and key1 is None
    assert q.validate_computation_key(key1) == False

    # user2 should be at the front of the queue
    pos2, key2  = q.get_position('apple')
    assert pos2 == 0 and key2 is not None
    assert q.validate_computation_key(key2) == True

def test_finish_computation_twice():
    q = get_queue()

    # add 2 users
    pos1, key1 = q.get_position('mpc')
    assert pos1 == 0 and key1 is not None
    pos2, key2 = q.get_position('apple')
    assert pos2 == 1 and key2 is None

    # finish computation of both users
    # each user should finish computation only once
    assert q.finish_computation(key1) == True
    assert q.finish_computation(key1) == False

    _, key2 = q.get_position('apple')
    assert q.finish_computation(key2) == True
    assert q.finish_computation(key2) == False

def test_full_queue():
    q = get_queue(max_size=1)

    pos1, key1 = q.get_position('mpc')
    assert pos1 == 0 and key1 is not None

    pos2, key2 = q.get_position('apple')
    assert pos2 is None and key2 is None


