from mpc_demo_infra.coordination_server.user_queue import UserQueue

def get_queue() -> UserQueue:
    return UserQueue(max_size=10, queue_head_timeout=60)

def test_pop_user_empty_queue():
    q = get_queue()
    assert q.pop_user('mpc') == False

def test_get_position_empty_queue():
    q = get_queue()
    position = q.get_position('mpc')
    assert position == 0
