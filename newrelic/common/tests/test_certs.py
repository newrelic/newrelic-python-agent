import os

from newrelic.common import certs


def test_where_returns_file_that_exists():
    cert_loc = certs.where()
    assert os.path.isfile(cert_loc)

def test_where_returns_cacert_pem_file():
    cert_loc = certs.where()

    head, tail = os.path.split(cert_loc)
    assert tail == 'cacert.pem'
    assert os.path.basename(head) == 'common'

    parent, _ = os.path.split(head)
    assert os.path.basename(parent) == 'newrelic'
