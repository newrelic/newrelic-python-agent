import os
import pytest
import time
import socket
from newrelic.packages import requests
from testing_support.fixtures import TerminatingPopen

pytest.importorskip('aiohttp')


@pytest.mark.parametrize('nr_enabled', [True, False])
def test_gunicorn_gaiohttp_worker(nr_enabled):

    bin_dir = os.path.join(os.environ['TOX_ENVDIR'], 'bin', 'gunicorn')
    cmd = [bin_dir, '-b', '127.0.0.1:8000', '-k', 'gaiohttp',
            'app:application']

    with TerminatingPopen(cmd):
        for _ in range(10):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.connect(('127.0.0.1', 8000))
                break
            except socket.error:
                pass

            time.sleep(0.1)
        else:
            assert False, "Server never started"

        resp = requests.get('http://127.0.0.1:8000')
        assert resp.status_code == 200
        assert resp.text == 'PONG'
