from newrelic.packages import six
import base64

def _encode(name, key):
    s = []

    # Convert name and key into bytes which are treated as integers.

    key = list(six.iterbytes(six.b(key)))
    for i, c in enumerate(six.iterbytes(six.b(name))):
        s.append(chr(c ^ key[i % len(key)]))
    return s

if six.PY3:
    def obfuscate(name, key):
        if not (name and key):
            return ''

        # Always pass name and key as str to _encode()

        return str(base64.b64encode(six.b(''.join(_encode(name, key)))),
                   encoding='Latin-1')
else:
    def obfuscate(name, key):
        if not (name and key):
            return ''

        # Always pass name and key as str to _encode()

        return base64.b64encode(six.b(''.join(_encode(name, key))))

def deobfuscate(name, key):
    if not (name and key):
        return ''

    # Always pass name and key as str to _encode()

    return ''.join(_encode(six.text_type(base64.b64decode(six.b(name)),
        encoding='Latin-1'), key))
