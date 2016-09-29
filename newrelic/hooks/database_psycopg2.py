import re
from newrelic.agent import (wrap_object, ObjectProxy, wrap_function_wrapper,
        register_database_client, FunctionTrace, callable_name,
        DatabaseTrace, current_transaction)

from newrelic.api.database_trace import enable_datastore_instance_feature

from .database_dbapi2 import (ConnectionWrapper as DBAPI2ConnectionWrapper,
        ConnectionFactory as DBAPI2ConnectionFactory)

try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote
try:
    from urlparse import parse_qsl
except ImportError:
    from urllib.parse import parse_qsl

class ConnectionWrapper(DBAPI2ConnectionWrapper):

    def __enter__(self):
        transaction = current_transaction()
        name = callable_name(self.__wrapped__.__enter__)
        with FunctionTrace(transaction, name):
            self.__wrapped__.__enter__()

        # Must return a reference to self as otherwise will be
        # returning the inner connection object. If 'as' is used
        # with the 'with' statement this will mean no longer
        # using the wrapped connection object and nothing will be
        # tracked.

        return self

    def __exit__(self, exc, value, tb):
        transaction = current_transaction()
        name = callable_name(self.__wrapped__.__exit__)
        with FunctionTrace(transaction, name):
            if exc is None:
                with DatabaseTrace(transaction, 'COMMIT',
                        self._nr_dbapi2_module, self._nr_connect_params):
                    return self.__wrapped__.__exit__(exc, value, tb)
            else:
                with DatabaseTrace(transaction, 'ROLLBACK',
                        self._nr_dbapi2_module, self._nr_connect_params):
                    return self.__wrapped__.__exit__(exc, value, tb)

class ConnectionFactory(DBAPI2ConnectionFactory):

    __connection_wrapper__ = ConnectionWrapper

# This URI parsing is directly from RFC 3896 Appendix B
# http://www.ietf.org/rfc/rfc3986.txt
#
# The reason for this RE is urlparse appears to be broken in some earlier
# versions of Python 2.7 (2.7.3 for example).
# Related Python bug: https://bugs.python.org/issue9374
#
# According to PGSQL, connect URIs are in the format of RFC 3896
# See: https://www.postgresql.org/docs/9.5/static/libpq-connect.html#LIBPQ-CONNSTRING
#
URI_RE = re.compile(
        r'^(?:(?P<scheme>[^:/?#]+):)?'
        r'(?://(?P<authority>[^/?#]*))?'
        r'(?P<path>[^?#]*)'
        r'(?:\?(?P<query>[^#]*))?'
        r'(?:#(?P<fragment>.*))?'
)

def instance_info(args, kwargs):
    try:
        arg_str = args and args[0] or ''

        # Attempt URI parse
        scheme = ''
        parsed_uri = URI_RE.match(arg_str)
        if parsed_uri:
            uri_info = parsed_uri.groupdict()
            scheme = uri_info['scheme'] or ''
            authority = uri_info['authority'] or ''
            path = uri_info['path'] or ''
            query = uri_info['query'] or ''

        # if URI scheme is postgresql or postgres, parse as valid URI
        if scheme == 'postgresql' or scheme == 'postgres':
            netloc_and_port = authority.split('@')[-1].strip()
            netloc_and_port = unquote(netloc_and_port)
            db = path.lstrip('/') or None
            host, port = (netloc_and_port, None)
            # IPV6 always ends with ] if there's no port
            if not netloc_and_port.endswith(']'):
                # rsplit handles both ipv6 and ipv4
                host_port = netloc_and_port.rsplit(':', 1)
                if len(host_port)==2:
                    host, port = host_port
            # query params always override everything
            d = dict(parse_qsl(query))
            host = d.get('host') or host or None
            port = d.get('port') or port
            db = d.get('dbname') or db
        elif args:
            arg_qsl = '&'.join(arg_str.split())
            d = dict(parse_qsl(arg_qsl, strict_parsing=True))
            host = d.get('hostaddr') or d.get('host')
            port = d.get('port')
            db = d.get('dbname')
        else:
            host = kwargs.get('hostaddr') or kwargs.get('host')
            port = kwargs.get('port')
            db = kwargs.get('database')
            host = host and str(host)
            port = port and str(port)
            db = db and str(db)
    except Exception:
        host, port, db = ('unknown', 'unknown', 'unknown')

    return (host, port, db)

def _add_defaults(parsed_host, parsed_port):
    if parsed_host is None:
        host = 'localhost'
        port = 'default'
    elif parsed_host.startswith('/'):
        host = 'localhost'
        port = '%s/.s.PGSQL.%s' % (parsed_host, parsed_port or '5432')
    else:
        host = parsed_host
        port = parsed_port or '5432'

    return (host, port)

def instrument_psycopg2(module):
    register_database_client(module, database_product='Postgres',
            quoting_style='single', explain_query='explain',
            explain_stmts=('select', 'insert', 'update', 'delete'),
            instance_info=instance_info)

    enable_datastore_instance_feature(module)

    wrap_object(module, 'connect', ConnectionFactory, (module,))

def wrapper_psycopg2_register_type(wrapped, instance, args, kwargs):
    def _bind_params(obj, scope=None):
        return obj, scope

    obj, scope = _bind_params(*args, **kwargs)

    if isinstance(scope, ObjectProxy):
        scope = scope.__wrapped__

    if scope is not None:
        return wrapped(obj, scope)
    else:
        return wrapped(obj)

# As we can't get in reliably and monkey patch the register_type()
# function in psycopg2._psycopg2 before it is imported, we also need to
# monkey patch the other references to it in other psycopg2 sub modules.
# In doing that we need to make sure it has not already been monkey
# patched by checking to see if it is already an ObjectProxy.

def instrument_psycopg2__psycopg2(module):
    if hasattr(module, 'register_type'):
        if not isinstance(module.register_type, ObjectProxy):
            wrap_function_wrapper(module, 'register_type',
                    wrapper_psycopg2_register_type)

def instrument_psycopg2_extensions(module):
    if hasattr(module, 'register_type'):
        if not isinstance(module.register_type, ObjectProxy):
            wrap_function_wrapper(module, 'register_type',
                    wrapper_psycopg2_register_type)

def instrument_psycopg2__json(module):
    if hasattr(module, 'register_type'):
        if not isinstance(module.register_type, ObjectProxy):
            wrap_function_wrapper(module, 'register_type',
                    wrapper_psycopg2_register_type)

def instrument_psycopg2__range(module):
    if hasattr(module, 'register_type'):
        if not isinstance(module.register_type, ObjectProxy):
            wrap_function_wrapper(module, 'register_type',
                    wrapper_psycopg2_register_type)
