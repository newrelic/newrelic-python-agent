import re
import cornice

def _to_int(version_str):
    m = re.match(r'\d+', version_str)
    return int(m.group(0)) if m else 0

def version2tuple(version_str, parts_count=2):
    """Convert version, even if it contains non-numeric chars.

    >>> version2tuple('9.4rc1.1')
    (9, 4)

    """

    parts = version_str.split('.')[:parts_count]
    return tuple(map(_to_int, parts))

CORNICE_VERSION = version2tuple(cornice.__version__, parts_count=3)
