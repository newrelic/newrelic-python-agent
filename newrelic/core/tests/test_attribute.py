import newrelic.tests.test_cases

from newrelic.core.config import finalize_application_settings

from newrelic.core.attribute import (create_agent_attributes,
        _TRANSACTION_EVENT_DEFAULT_ATTRIBUTES, _DESTINATIONS,
        _DESTINATIONS_WITH_EVENTS, Attribute)


class TestAttributeFilter(newrelic.tests.test_cases.TestCase):
    def setUp(self):
        self.settings = finalize_application_settings({})

    def test_attribute_filter_applies_proper_destination(self):
        default_attr_name = next(iter(_TRANSACTION_EVENT_DEFAULT_ATTRIBUTES))

        attribute_list = create_agent_attributes({
            default_attr_name: 'f',
            'blah': 'w'
        }, self.settings.attribute_filter)

        self.assertIn(Attribute('blah', 'w', _DESTINATIONS), attribute_list)
        self.assertIn(
                Attribute(default_attr_name, 'f', _DESTINATIONS_WITH_EVENTS),
                attribute_list)

    def test_attribute_filter_removes_none_values(self):
        attribute_list = create_agent_attributes({
            'blah': 'w',
            'blahNone': None
        }, self.settings.attribute_filter)

        self.assertIn(Attribute('blah', 'w', _DESTINATIONS), attribute_list)
        self.assertEqual(len(attribute_list), 1)
