from mpc_demo_infra.coordination_server.user_queue import UserQueue

def test_pop_user_empty_from_empty_queue():
    q = UserQueue(max_size=10, queue_head_timeout=60)
    assert q.pop_user('mpc') == False
