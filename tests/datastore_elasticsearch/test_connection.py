from elasticsearch.connection.base import Connection


def test_connection_default():
    conn = Connection()
    assert conn._nr_host_port == ('localhost', '9200')

def test_connection_host_arg():
    conn = Connection('the_host')
    assert conn._nr_host_port == ('the_host', '9200')

def test_connection_args():
    conn = Connection('the_host', 9999)
    assert conn._nr_host_port == ('the_host', '9999')

def test_connection_kwargs():
    conn = Connection(host='foo', port=8888)
    assert conn._nr_host_port == ('foo', '8888')
