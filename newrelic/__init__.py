version = '0.5.41'

try:
    from newrelic.build import build_number
except:
    build_number = 0

version_info = map(int, version.split('.')) + [build_number]
