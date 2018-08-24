import sys
import newrelic.hooks.framework_django as framework_django
from benchmarks.util import TimeInstrumentBase, MagicMock

sys.modules['django'] = MagicMock()


class TimeDjangoInstrument(TimeInstrumentBase(framework_django)):
    pass
