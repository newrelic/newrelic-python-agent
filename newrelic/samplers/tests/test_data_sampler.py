import unittest

from newrelic.common.object_names import callable_name
from newrelic.samplers.decorators import (data_source_generator,
        data_source_factory)
from newrelic.samplers.data_sampler import DataSampler

@data_source_generator(name='NAME', version='VERSION', guid='GUID')
def data_source_generator_1():
    data_source_generator_1.counter += 1
    yield ('Custom/Name', data_source_generator_1.counter)
data_source_generator_1.counter = 0

@data_source_generator()
def data_source_generator_2():
    data_source_generator_2.counter += 1
    yield ('Custom/Name', data_source_generator_2.counter)
data_source_generator_2.counter = 0

@data_source_factory(name='NAME', version='VERSION', guid='GUID')
class data_source_factory_1(object):
    def __init__(self, settings, environ):
        self.initial = 0
        self.counter = self.initial
    def start(self):
        self.counter = self.initial
    def stop(self):
        self.initial += 100
        pass
    def __call__(self):
        self.counter += 1
        yield ('Custom/Name', self.counter)

def data_source_broken_1(settings):
    def metrics():
        data_source_broken_1.counter += 1
        yield ('Custom/Name', data_source_1.counter)
    def factory(environ):
        # Deliberately return None for instance.
        return None
    properties = {}
    properties['name'] = None
    properties['factory'] = factory
    return properties
data_source_broken_1.counter = 0

class TestDataSampler(unittest.TestCase):

    def test_data_sampler_configuration(self):
        settings = { 'setting': 'VALUE' }
        sampler = DataSampler('Unit Test', data_source_generator_1,
                name=None, settings=settings)

        self.assertEqual(sampler.name, 'NAME')
        self.assertEqual(sampler.version, 'VERSION')
        self.assertEqual(sampler.guid, 'GUID')

        self.assertEqual(sampler.group, None)

        settings = sampler.settings

        self.assertEqual(settings['setting'], 'VALUE')

        source_properties = sampler.source_properties

        self.assertEqual(source_properties['name'], 'NAME')
        self.assertEqual(source_properties['version'], 'VERSION')
        self.assertEqual(source_properties['guid'], 'GUID')

        self.assertTrue(callable(source_properties['factory']))

        merged_properties = sampler.merged_properties

        self.assertEqual(merged_properties['name'], 'NAME')
        self.assertEqual(merged_properties['version'], 'VERSION')
        self.assertEqual(merged_properties['guid'], 'GUID')

        self.assertTrue(callable(merged_properties['factory']))

        self.assertEqual(sampler.factory, source_properties['factory'])
        self.assertEqual(sampler.factory, merged_properties['factory'])

        environ = sampler.environ

        self.assertEqual(environ['consumer.name'], 'Unit Test')
        self.assertEqual(environ['consumer.vendor'], 'New Relic')
        self.assertEqual(environ['producer.name'], 'NAME')
        self.assertEqual(environ['producer.version'], 'VERSION')
        self.assertEqual(environ['producer.guid'], 'GUID')
        self.assertEqual(environ['producer.group'], None)

    def test_data_sampler_overrides(self):
        settings = { 'setting': 'VALUE' }
        sampler = DataSampler('Unit Test', data_source_generator_1,
                name='OVERRIDE-NAME', settings=settings,
                version='OVERRIDE-VERSION', guid='OVERRIDE-GUID',
                group='OVERRIDE-GROUP')

        self.assertEqual(sampler.name, 'OVERRIDE-NAME')
        self.assertEqual(sampler.version, 'OVERRIDE-VERSION')
        self.assertEqual(sampler.guid, 'OVERRIDE-GUID')

        self.assertEqual(sampler.group, 'OVERRIDE-GROUP')

        settings = sampler.settings

        self.assertEqual(settings['setting'], 'VALUE')

        source_properties = sampler.source_properties

        self.assertEqual(source_properties['name'], 'NAME')
        self.assertEqual(source_properties['version'], 'VERSION')
        self.assertEqual(source_properties['guid'], 'GUID')

        self.assertTrue(callable(source_properties['factory']))

        merged_properties = sampler.merged_properties

        # The 'name' value is a separate argument to the DataSampler
        # constructor and not part of the kwargs properties. Thus the
        # override isn't reflected in the merged properties. This is
        # okay as these cached values for properties are all intended
        # for internal usage only and even then more for support this
        # testing. The direct attributes of the sampler are the values
        # that should be used for external usage.

        self.assertEqual(merged_properties['name'], 'NAME')
        self.assertEqual(merged_properties['version'], 'OVERRIDE-VERSION')
        self.assertEqual(merged_properties['guid'], 'OVERRIDE-GUID')

        self.assertEqual(merged_properties['group'], 'OVERRIDE-GROUP')

        self.assertTrue(callable(merged_properties['factory']))

        self.assertEqual(sampler.factory, source_properties['factory'])
        self.assertEqual(sampler.factory, merged_properties['factory'])

        environ = sampler.environ

        self.assertEqual(environ['consumer.name'], 'Unit Test')
        self.assertEqual(environ['consumer.vendor'], 'New Relic')
        self.assertEqual(environ['producer.name'], 'OVERRIDE-NAME')
        self.assertEqual(environ['producer.version'], 'OVERRIDE-VERSION')
        self.assertEqual(environ['producer.guid'], 'OVERRIDE-GUID')
        self.assertEqual(environ['producer.group'], 'OVERRIDE-GROUP')

    def test_no_data_source_configuration(self):
        settings = { 'setting': 'VALUE' }
        sampler = DataSampler('Unit Test', data_source_generator_2,
                name=None, settings=settings)

        name = callable_name(data_source_generator_2)

        self.assertEqual(sampler.name, name)
        self.assertEqual(sampler.version, None)
        self.assertEqual(sampler.guid, None)

        self.assertEqual(sampler.group, None)

        settings = sampler.settings

        self.assertEqual(settings['setting'], 'VALUE')

        source_properties = sampler.source_properties

        self.assertEqual(source_properties['name'], None)
        self.assertFalse('version' in source_properties)
        self.assertFalse('guid' in source_properties)

        self.assertTrue(callable(source_properties['factory']))

        merged_properties = sampler.merged_properties

        self.assertEqual(merged_properties['name'], None)
        self.assertFalse('version' in merged_properties)
        self.assertFalse('guid' in merged_properties)

        self.assertTrue(callable(merged_properties['factory']))

        self.assertEqual(sampler.factory, source_properties['factory'])
        self.assertEqual(sampler.factory, merged_properties['factory'])

        environ = sampler.environ

        self.assertEqual(environ['consumer.name'], 'Unit Test')
        self.assertEqual(environ['consumer.vendor'], 'New Relic')
        self.assertEqual(environ['producer.name'], name)
        self.assertEqual(environ['producer.version'], None)
        self.assertEqual(environ['producer.guid'], None)
        self.assertEqual(environ['producer.group'], None)

    def test_data_sampler_metrics_generator(self):
        sampler = DataSampler('Unit Test', data_source_generator_1,
                name=None, settings={})

        self.assertEqual(sampler.instance, None)

        sampler.start()

        metrics = list(sampler.metrics())
        self.assertEqual(metrics, [('Custom/Name', 1)])

        metrics = list(sampler.metrics())
        self.assertEqual(metrics, [('Custom/Name', 2)])

        sampler.stop()

        self.assertEqual(sampler.instance, None)

        sampler.start()

        metrics = list(sampler.metrics())
        self.assertEqual(metrics, [('Custom/Name', 3)])

        metrics = list(sampler.metrics())
        self.assertEqual(metrics, [('Custom/Name', 4)])

        sampler.stop()

    def test_data_sampler_metrics_factory_persistent(self):
        sampler = DataSampler('Unit Test', data_source_factory_1,
                name=None, settings={})

        self.assertEqual(sampler.instance, None)

        sampler.start()

        metrics = list(sampler.metrics())
        self.assertEqual(metrics, [('Custom/Name', 1)])

        metrics = list(sampler.metrics())
        self.assertEqual(metrics, [('Custom/Name', 2)])

        sampler.stop()

        self.assertNotEqual(sampler.instance, None)

        sampler.start()

        metrics = list(sampler.metrics())
        self.assertEqual(metrics, [('Custom/Name', 101)])

        metrics = list(sampler.metrics())
        self.assertEqual(metrics, [('Custom/Name', 102)])

        sampler.stop()

    def test_data_sampler_metrics_factory_group_prefix(self):
        sampler = DataSampler('Unit Test', data_source_factory_1,
                name=None, settings={}, group='Group')

        self.assertEqual(sampler.instance, None)

        sampler.start()

        metrics = list(sampler.metrics())
        self.assertEqual(metrics, [('Group/Custom/Name', 1)])

        metrics = list(sampler.metrics())
        self.assertEqual(metrics, [('Group/Custom/Name', 2)])

        sampler.stop()

    def test_data_sampler_metrics_broken(self):
        sampler = DataSampler('Unit Test', data_source_broken_1,
                name=None, settings={})

        self.assertEqual(sampler.instance, None)

        sampler.start()

        metrics = list(sampler.metrics())
        self.assertEqual(metrics, [])

        sampler.stop()

if __name__ == '__main__':
    unittest.main()
