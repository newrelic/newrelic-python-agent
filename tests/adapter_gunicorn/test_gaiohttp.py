import os
import pytest
import time

from newrelic.packages import requests
from testing_support.fixtures import (Environ, TerminatingPopen)


def _locate(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)


@pytest.mark.parametrize('nr_enabled', [True, False])
def test_gunicorn_gaiohttp_worker(nr_enabled):

    # Run gunicorn (commandline) in a subprocess, set to terminate
    # at end of test. Both runner and commandline tool require string
    # path to gunicorn-- locate this with os.walk to support running
    # with tox.
    gunicorn = _locate('gunicorn', '.tox')
    cmd = '%s -b 127.0.0.1:8000 -k gaiohttp wsgi:app' % gunicorn
    if nr_enabled:
        cmd = ' '.join(('NEW_RELIC_CONFIG_FILE=gunicorn_gaiohttp.ini',
                'newrelic-admin run-python', cmd))

    with Environ(NEW_RELIC_CONFIG_FILE='gunicorn_gaiohttp.ini'):
        with TerminatingPopen(cmd, shell=True):
            time.sleep(1)
            resp = requests.get('http://127.0.0.1:8000/ping')
            assert resp.status_code == 200
            assert resp.text == 'PONG'
