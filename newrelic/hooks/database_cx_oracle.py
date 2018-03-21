from newrelic.api.database_trace import register_database_client
from newrelic.common.object_wrapper import wrap_object, ObjectProxy

from newrelic.hooks.database_dbapi2 import ConnectionFactory


class AcquireProxy(ObjectProxy):
    def __init__(self, pool, dbapi2_module):
        super(AcquireProxy, self).__init__(pool)
        self._nr_dbapi2_module = dbapi2_module

    def acquire(self, *args, **kwargs):
        return ConnectionFactory(
                self.__wrapped__.acquire,
                self._nr_dbapi2_module)(*args, **kwargs)


class SessionPoolProxy(ObjectProxy):

    def __init__(self, pool_init, dbapi2_module):
        super(SessionPoolProxy, self).__init__(pool_init)
        self._nr_dbapi2_module = dbapi2_module

    def __call__(self, *args, **kwargs):
        pool = self.__wrapped__(*args, **kwargs)
        return AcquireProxy(pool, self._nr_dbapi2_module)


def instrument_cx_oracle(module):
    register_database_client(module, database_product='Oracle',
            quoting_style='single+oracle')

    wrap_object(module, 'connect', ConnectionFactory, (module,))
    wrap_object(module, 'SessionPool', SessionPoolProxy, (module,))
