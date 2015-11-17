import unittest

from newrelic.core.config import global_settings, DEFAULT_RESERVOIR_SIZE
from newrelic.core.stats_engine import StatsEngine


class TestStatsEngineCustomEvents(unittest.TestCase):

    def setUp(self):
        self.settings = global_settings()

    def test_custom_events_initial_values(self):
        stats = StatsEngine()
        self.assertEqual(stats.custom_events.capacity, 100)
        self.assertEqual(stats.custom_events.num_samples, 0)
        self.assertEqual(stats.custom_events.num_seen, 0)

    def test_custom_events_after_reset_stats(self):
        stats = StatsEngine()
        self.assertEqual(stats.custom_events.capacity, 100)

        self.settings.custom_insights_events.max_samples_stored = 500
        stats.reset_stats(self.settings)

        self.assertEqual(stats.custom_events.capacity, 500)

    def test_custom_events_capacity_same_as_transaction_events(self):
        stats = StatsEngine()

        ce_settings = self.settings.custom_insights_events
        ce_settings.max_samples_stored = DEFAULT_RESERVOIR_SIZE
        stats.reset_stats(self.settings)

        self.assertEqual(stats.custom_events.capacity,
                stats.transaction_events.capacity)


if __name__ == '__main__':
    unittest.main()
