import unittest

from newrelic.samplers.decorators import (data_source_generator,
        data_source_factory)

# This initial data source is here just to demonstrate in a long handed
# way what the decorators being tested effectively encapsulate.

def data_source_1(settings):
    assert settings['setting'] == 'VALUE'
    def metrics():
        data_source_1.counter += 1
        yield ('Custom/Name', data_source_1.counter)
    def factory(environ):
        assert environ['value'] == 'VALUE'
        return metrics
    properties = {}
    properties['name'] = 'NAME'
    properties['version'] = 'VERSION'
    properties['guid'] = 'GUID'
    properties['factory'] = factory
    return properties
data_source_1.counter = 0

@data_source_generator(name='NAME', version='VERSION', guid='GUID')
def data_source_generator_1():
    data_source_generator_1.counter += 1
    yield ('Custom/Name', data_source_generator_1.counter)
data_source_generator_1.counter = 0

@data_source_factory(name='NAME', version='VERSION', guid='GUID')
def data_source_factory_1(settings, environ):
    assert settings['setting'] == 'VALUE'
    assert environ['value'] == 'VALUE'
    def metrics():
        data_source_factory_1.counter += 1
        yield ('Custom/Name', data_source_factory_1.counter)
    return metrics
data_source_factory_1.counter = 0

@data_source_factory(name='NAME', version='VERSION', guid='GUID')
class data_source_factory_2(object):
    def __init__(self, settings, environ):
        assert settings['setting'] == 'VALUE'
        assert environ['value'] == 'VALUE'
        self.counter = 0
    def __call__(self):
        self.counter += 1
        yield ('Custom/Name', self.counter)

class TestDataSourceDecorators(unittest.TestCase):

    def validate_data_source(self, properties):
        self.assertEqual(properties['name'], 'NAME')
        self.assertEqual(properties['version'], 'VERSION')
        self.assertEqual(properties['guid'], 'GUID')

        self.assertTrue(callable(properties['factory']))

        environ = { 'value': 'VALUE' }
        instance = properties['factory'](environ)

        metrics = list(instance())
        self.assertEqual(metrics, [('Custom/Name', 1)])

        metrics = list(instance())
        self.assertEqual(metrics, [('Custom/Name', 2)])

    def test_data_source_1(self):
        settings = { 'setting': 'VALUE' }
        properties = data_source_1(settings)
        self.validate_data_source(properties)

    def test_data_source_generator_1(self):
        settings = { 'setting': 'VALUE' }
        properties = data_source_generator_1(settings)
        self.validate_data_source(properties)

    def test_data_source_factory_1(self):
        settings = { 'setting': 'VALUE' }
        properties = data_source_factory_1(settings)
        self.validate_data_source(properties)

    def test_data_source_factory_2(self):
        settings = { 'setting': 'VALUE' }
        properties = data_source_factory_2(settings)
        self.validate_data_source(properties)

        settings = { 'setting': 'VALUE' }
        properties = data_source_factory_2(settings)
        self.validate_data_source(properties)

if __name__ == '__main__':
    unittest.main()
