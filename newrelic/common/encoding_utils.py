# vim: set fileencoding=utf-8 :
from newrelic.packages import six
import base64

if six.PY2:
    # In python 2 unicode strings are stored as bytes. So iterating over a
    # unicode name will yield each byte (0-255).
    #
    # >>> a = '√'
    # >>> a
    # '\xe2\x88\x9a'
    # >>> for i, c in enumerate(a):
    #    ...     print i, ord(c)
    #    ...
    #    0 226
    #    1 136
    #    2 154

    def _encode(name, key):
        """Takes name and key as (byte) strings. xors the key and name and
        returns a bytestring.

        """
        # Convert each byte char to int using ord() and XOR with the Key.  The
        # list of ints are then coverted back to bytes char.

        s = [chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(name)]
        return ''.join(s)

    def obfuscate(name, key):
        """Takes a (byte) string name and key pair. Obfuscates the name with
        the key and returns the (byte) string of the obfuscated name.

        """
        if not (name and key):
            return ''

        byte_s = _encode(name, key)
        encoded_byte_s = base64.b64encode(byte_s)
        return encoded_byte_s

    def deobfuscate(name, key):
        """Takes a (byte) string name and key pair. Obfuscates the name with
        the key and returns the (byte) string of the obfuscated name.

        """
        if not (name and key):
            return ''

        decoded_byte_s = base64.b64decode(name)
        byte_s = _encode(decoded_byte_s, key)
        return byte_s
else:
    def _encode(name, key):
        """Takes name and key as bytes. xors the key and name and returns
        bytes.

        """
        # The name and key are passed in as bytes (encoded using utf-8). XOR
        # each byte and return the result as bytes.

        return bytes([c ^ key[i % len(key)] for i, c in enumerate(name)])

    def obfuscate(name, key):
        """Takes a unicode name and key pair. Obfuscates the name with the key
        and returns the unicode of the obfuscated name.

        """
        if not (name and key):
            return ''

        # Python 3 stores strings as unicode (not bytes). Explicitly convert
        # them into bytes before encoding.

        byte_s = _encode(name.encode('utf-8'), key.encode('utf-8'))
        encoded_byte_s = base64.b64encode(byte_s)

        # Since strings are stored as unicode in Python 3, the obfuscated and
        # encoded name has to be coverted back to unicode before returning.

        return encoded_byte_s.decode('utf-8')

    def deobfuscate(name, key):
        """Takes a unicode name and key pair. deObfuscates the name with the
        key and returns the unicode of the deobfuscated name.

        """
        if not (name and key):
            return ''

        # Python 3 stores strings as unicode (not bytes). Explicitly convert
        # them into bytes before base64 decoding.

        decoded_byte_s = base64.b64decode(name.encode('utf-8'))
        byte_s = _encode(decoded_byte_s, key.encode('utf-8'))

        # The deobfuscated name is represented as bytes which is converted to
        # unicode using utf-8 before returning.

        return byte_s.decode('utf-8')
