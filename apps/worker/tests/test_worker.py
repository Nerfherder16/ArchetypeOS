from app.worker import QUEUE


def test_worker_queue_name_is_stable():
    assert QUEUE == "archetypeos:jobs"
