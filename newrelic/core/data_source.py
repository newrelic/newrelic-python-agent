"""This module implements data recording and reporting for a data source.

"""

import functools
import logging

from newrelic.api.object_wrapper import callable_name

_logger = logging.getLogger(__name__)

class DataSampler(object):

    def __init__(self, consumer, source, name, settings, **properties):
        self.consumer = consumer

        self.properties = source(settings)

        self.factory = self.properties['factory']
        self.instance =  None

        self.properties.update(properties)

        self.name = (name or self.properties.get('name') or
                callable_name(source))

        self.group = self.properties.get('group')

        if self.group:
            self.group = self.group.rstrip('/')

        environ = {}

        environ['consumer.name'] = consumer
        environ['consumer.vendor'] = 'New Relic'
        environ['producer.name'] = self.name
        environ['producer.group'] = self.group

        self.environ = environ

        _logger.debug('Initialising data sampler for %r.', self.environ)

    def start(self):
        if self.instance is None:
            self.instance = self.factory(self.environ)
        if hasattr(self.instance, 'start'):
            self.instance.start()

    def stop(self):
        if hasattr(self.instance, 'stop'):
            self.instance.stop()
        else:
            self.instance = None

    def metrics(self):
        assert self.instance is not None
        if self.group:
            return (('%s/%s' % (self.group, key), value)
                    for key, value in self.instance())
        else:
            return self.instance()

def data_source_generator(name=None, **properties):
    def _decorator(func):
        @functools.wraps(func)
        def _properties(settings):
            def _factory(environ):
                return func
            d = dict(properties)
            d['name'] = name
            d['factory'] = _factory
            return d
        return _properties
    return _decorator

def data_source_factory(name=None, **properties):
    def _decorator(func):
        @functools.wraps(func)
        def _properties(settings):
            def _factory(environ):
                return func(settings, environ)
            d = dict(properties)
            d['name'] = name
            d['factory'] = _factory
            return d
        return _properties
    return _decorator

@data_source_generator(name='Python Objects')
def python_objects_data_source():
    import gc

    yield ('Component/Python/Objects', len(gc.get_objects()))

def memory_metrics_data_source(settings):
    import os, psutil

    def memory_metrics():
        pid = os.getpid()
        p = psutil.Process(os.getpid())
        m = p.get_memory_info()

        yield ('Component/Memory/Physical', float(m.rss)/(1024*1024))
        yield ('Component/Memory/Virtual', float(m.vms)/(1024*1024))

    def memory_metrics_factory(environ):
        return memory_metrics

    properties = {}
    properties['name'] = 'Memory Usage'
    properties['factory'] = memory_metrics_factory

    return properties

@data_source_factory(name='CPU Usage')
def cpu_metrics_data_source_1(settings, environ):
    import os, time, multiprocessing

    state = {}
    state['last_timestamp'] = time.time()
    state['times'] = os.times()

    def cpu_metrics():
        now = time.time()
        new_times = os.times()
        elapsed_time = now - state['last_timestamp']
        user_time = new_times[0] - state['times'][0]
        utilization = user_time / (elapsed_time*multiprocessing.cpu_count())
        state['last_timestamp'] = now
        state['times'] = new_times

        yield ('Component/CPU/User Time', user_time)
        yield ('Component/CPU/User/Utilization', utilization)

    return cpu_metrics

class CPUMetricsDataSource_2(object):

    def __init__(self, settings, environ):
        import os, time

        self.last_timestamp = time.time()
        self.times = os.times()

    def __call__(self):
        import os, time, multiprocessing

        now = time.time()
        new_times = os.times()
        elapsed_time = now - self.last_timestamp
        user_time = new_times[0] - self.times[0]
        utilization = user_time / (elapsed_time*multiprocessing.cpu_count())
        self.last_timestamp = now
        self.times = new_times

        yield ('Component/CPU/User Time', user_time)
        yield ('Component/CPU/User/Utilization', utilization)

cpu_metrics_data_source_2 = data_source_factory(
        name='CPU Usage')(CPUMetricsDataSource_2)

class CPUMetricsDataSource_3(object):

    def __init__(self, settings, environ):
        self._last_timestamp = None
        self._times = None

    def start(self):
        import os, time

        self._last_timestamp = time.time()
        try:
            self._times = os.times()
        except:
            self._times = None

    def stop(self):
        self._last_timestamp = None
        self._times = None

    def __call__(self):
        import os, time, multiprocessing

        if self._times is None:
            return

        now = time.time()
        new_times = os.times()

        elapsed_time = now - self._last_timestamp

        user_time = new_times[0] - self._times[0]

        utilization = user_time / (elapsed_time*multiprocessing.cpu_count())

        self._last_timestamp = now
        self._times = new_times

        yield ('Component/CPU/User Time', user_time)
        yield ('Component/CPU/User/Utilization', utilization)

cpu_metrics_data_source_3 = data_source_factory(
        name='CPU Usage')(CPUMetricsDataSource_3)
