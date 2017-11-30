version = '2.98.0'

try:
    from newrelic.build import build_number
except ImportError:
    build_number = 0

version_info = list(map(int, version.split('.'))) + [build_number]
version = '.'.join(map(str, version_info))
