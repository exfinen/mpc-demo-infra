from mpc_demo_infra.coordination_server.user_queue import UserQueue, AddResult
import time

def get_queue(max_size: int = 10, queue_head_timeout: int=60) -> UserQueue:
    return UserQueue(max_size=max_size, queue_head_timeout=queue_head_timeout)

def test_get_position_empty_queue():
    q = get_queue()
    pos = q.get_position('mpc')
    assert pos is None

def test_get_position_multiple_users():
    q = get_queue()
    assert q.add_user('mpc') == AddResult.SUCCEEDED
    assert q.add_user('apple') == AddResult.SUCCEEDED
    assert q.add_user('orange') == AddResult.SUCCEEDED

    pos1 = q.get_position('mpc')
    assert pos1 == 0
    pos2 = q.get_position('apple')
    assert pos2 == 1
    pos3 = q.get_position('orange')
    assert pos3 == 2

def test_2_users_get_pop_finish_succ():
    q = get_queue()

    # add 2 users
    assert q.add_user('mpc') == AddResult.SUCCEEDED
    assert q.add_user('apple') == AddResult.SUCCEEDED
    pos1 = q.get_position('mpc')
    assert pos1 == 0
    pos2 = q.get_position('apple')
    assert pos2 == 1

    # validate user1 computaion
    key1 = q.get_computation_key('mpc')
    assert key1 is not None
    assert q.validate_computation_key('mpc', key1) == True

    # user2 should get the computation key
    key2 = q.get_computation_key('apple')
    assert key2 is None

    # invalid computation key should be considered invalid
    assert q.validate_computation_key('mpc', None) == False
    assert q.validate_computation_key('mpc', key1 + 'abc') == False

    # invalid access key should be considered invalid
    assert q.validate_computation_key('cpm', key1) == False

    # finish user1 computation
    assert q.finish_computation('mpc', key1) == True

    # after finishing computation, key1 should no longer be valid
    assert q.validate_computation_key('mpc', key1) == False

    # let user2 get the computation key
    pos2 = q.get_position('apple')
    assert pos2 == 0
    key2 = q.get_computation_key('apple')
    assert key2 is not None

    # user1 key should no longer be valid
    assert q.validate_computation_key('mpc', key1) == False

    # user1 is no longer able to finish computation
    assert q.finish_computation('mpc', key1) == False

    # user2 should be able to validate its computation
    assert q.validate_computation_key('apple', key2) == True

    # user2 can finishe its computation
    assert q.finish_computation('apple', key2) == True

    # after finishing, user2 key should no longer be valid
    assert q.validate_computation_key('apple', key2) == False

def test_queue_head_timeout():
    # set the timeout to 1 second
    q = get_queue(queue_head_timeout=1)

    assert q.add_user('mpc') == AddResult.SUCCEEDED
    assert q.add_user('apple') == AddResult.SUCCEEDED
    assert q.add_user('orange') == AddResult.SUCCEEDED

    pos1 = q.get_position('mpc')
    assert pos1 == 0
    pos2 = q.get_position('apple')
    assert pos2 == 1
    pos3 = q.get_position('orange')
    assert pos3 == 2

    # user1 is at the head of the queue
    key1 = q.get_computation_key('mpc')
    assert key1 is not None

    time.sleep(2)

    # user1 should have been removed from the the queue
    key1 = q.get_computation_key('mpc')
    assert key1 is None
    pos1 = q.get_position('mpc')
    assert pos1 is None
    assert q.validate_computation_key('mpc', key1) == False

    # user2 should be at the front of the queue
    key2 = q.get_computation_key('apple')
    assert key2 is not None
    pos2 = q.get_position('apple')
    assert pos2 is not None and pos2 == 0
    assert q.validate_computation_key('apple', key2) == True

def test_finish_computation_twice():
    q = get_queue()

    assert q.add_user('mpc') == AddResult.SUCCEEDED
    assert q.add_user('apple') == AddResult.SUCCEEDED

    # add 2 users
    pos1 = q.get_position('mpc')
    assert pos1 == 0
    pos2 = q.get_position('apple')
    assert pos2 == 1

    # finish computation of both users
    # each user should finish computation only once
    key1 = q.get_computation_key('mpc')
    assert q.finish_computation('mpc', key1) == True
    assert q.finish_computation('mpc', key1) == False

    key2 = q.get_computation_key('apple')
    assert q.finish_computation('apple', key2) == True
    assert q.finish_computation('apple', key2) == False

def test_add_user():
    q = get_queue(max_size=1)

    assert q.add_user('mpc') == AddResult.SUCCEEDED
    assert q.add_user('mpc') == AddResult.QUEUE_IS_FULL

    q = get_queue(max_size=2)
    assert q.add_user('mpc') == AddResult.SUCCEEDED
    assert q.add_user('mpc') == AddResult.ALREADY_IN_QUEUE
    assert q.add_user('apple') == AddResult.SUCCEEDED
    assert q.add_user('orange') == AddResult.QUEUE_IS_FULL

def test_add_priority_user():
    q = get_queue(max_size=6)

    # add to empty queue w/ priority
    assert q.add_priority_user('mpc') == AddResult.SUCCEEDED
    assert q.users_len == 1
    assert q.users_head.access_key == 'mpc'
    assert q.users_tail.access_key == 'mpc'
    assert q.get_position('mpc') == 0

    # add to queue of length 1 w/ priority
    assert q.add_priority_user('zk') == AddResult.SUCCEEDED
    assert q.users_len == 2
    assert q.users_head.access_key == 'mpc'
    assert q.users_tail.access_key == 'zk'
    assert q.get_position('mpc') == 0
    print(q.get_position('zk'))
    assert q.get_position('zk') == 1

    # add to queue of length 2 normally
    assert q.add_user('fhe') == AddResult.SUCCEEDED
    assert q.users_len == 3
    assert q.users_head.access_key == 'mpc'
    assert q.users_tail.access_key == 'fhe'
    assert q.get_position('mpc') == 0
    assert q.get_position('zk') == 1
    assert q.get_position('fhe') == 2

    # add to queue of length 3 w/ priority
    assert q.add_priority_user('ot') == AddResult.SUCCEEDED
    assert q.users_len == 4
    assert q.users_head.access_key == 'mpc'
    assert q.users_tail.access_key == 'fhe'
    assert q.get_position('mpc') == 0
    assert q.get_position('ot') == 1
    assert q.get_position('zk') == 2
    assert q.get_position('fhe') == 3

    # add to queue of length 4 normally
    assert q.add_user('gc') == AddResult.SUCCEEDED
    assert q.users_len == 5
    assert q.users_head.access_key == 'mpc'
    assert q.users_tail.access_key == 'gc'
    assert q.get_position('mpc') == 0
    assert q.get_position('ot') == 1
    assert q.get_position('zk') == 2
    assert q.get_position('fhe') == 3
    assert q.get_position('gc') == 4

    # add to queue of length 5 w/ priority
    assert q.add_priority_user('yao') == AddResult.SUCCEEDED
    assert q.users_len == 6
    assert q.users_head.access_key == 'mpc'
    assert q.users_tail.access_key == 'gc'
    assert q.get_position('mpc') == 0
    assert q.get_position('yao') == 1
    assert q.get_position('ot') == 2
    assert q.get_position('zk') == 3
    assert q.get_position('fhe') == 4
    assert q.get_position('gc') == 5

