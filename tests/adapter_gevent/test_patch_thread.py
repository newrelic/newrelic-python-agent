import gevent.monkey


def test_patch_thread():
    gevent.monkey.patch_thread()
