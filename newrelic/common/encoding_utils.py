"""This module implements assorted utility functions for encoding/decoding
of data.

"""

import base64

def xor_cipher_genkey(key, length=None):
    """Generates a byte array for use in XOR cipher encrypt and decrypt
    routines. In Python 2 either a byte string or Unicode string can be
    provided for the key. In Python 3, it must be a Unicode string. In
    either case, characters in the string must be within the ASCII
    character range.

    """

    return bytearray(key[:length], encoding='ascii')

def xor_cipher_encrypt(text, key):
    """Encrypts the text using an XOR cipher where the key is provided
    as a byte array. The key cannot be an empty byte array. Where the
    key is shorter than the text to be encrypted, the same key will
    continually be reapplied in succession. In Python 2 either a byte
    string or Unicode string can be provided for the text input. In
    Python 3 only a Unicode string can be provided for the text input.
    In either case where a Unicode string is being provided, characters
    must have an ordinal value less than 256. The result will be a byte
    array.

    """

    return bytearray([ord(c) ^ key[i % len(key)] for i, c in enumerate(text)])

def xor_cipher_decrypt(text, key):
    """Decrypts the text using an XOR cipher where the key is provided
    as a byte array. The key cannot be an empty byte array. Where the
    key is shorter than the text to be encrypted, the same key will
    continually be reapplied in succession. The input text must be in
    the form of a byte array. The result will in turn also be a byte
    array.

    """

    return bytearray([c ^ key[i % len(key)] for i, c in enumerate(text)])

def xor_cipher_encrypt_base64(text, key):
    """Encrypts the UTF-8 encoded representation of the text using an
    XOR cipher using the key. The key can be a byte array generated
    using xor_cipher_genkey() or an appropiate string of the correct
    type and composition, in which case if will be converted to a byte
    array using xor_cipher_genkey(). The key cannot be an empty byte
    array or string. Where the key is shorter than the text to be
    encrypted, the same key will continually be reapplied in succession.
    In Python 2 either a byte string or Unicode string can be provided
    for the text input. In the case of a byte string, it will be
    interpreted as having Latin-1 encoding. In Python 3 only a Unicode
    string can be provided for the text input. Having being encrypted,
    the result will then be base64 encoded with the result being a
    Unicode string.

    """

    if not isinstance(key, bytearray):
        key = xor_cipher_genkey(key)

    # The input to xor_cipher_encrypt() must be a Unicode string, but
    # where each character has an ordinal value less than 256. This
    # means that where the text to be encrypted is a Unicode string, we
    # need to encode it to UTF-8 and then back to Unicode as Latin-1
    # which will preserve the encoded byte string as is. Where the text
    # to be encrypted is a byte string, we will not know what encoding
    # it may have. What we therefore must do is first convert it to
    # Unicode as Latin-1 before doing the UTF-8/Latin-1 conversion. This
    # needs to be done as when decrypting we assume that the input will
    # always be UTF-8. If we do not do this extra conversion for a byte
    # string, we could later end up trying to decode a byte string which
    # isn't UTF-8 and so fail with a Unicode decoding error.

    if isinstance(text, bytes):
        text = text.decode('latin-1')
    text = text.encode('utf-8').decode('latin-1')

    result = base64.b64encode(bytes(xor_cipher_encrypt(text, key)))
 
    # The result from base64 encoding will be a byte string but since
    # dealing with byte strings in Python 2 and Python 3 is quite
    # different, it is safer to return a Unicode string for both. We can
    # use ASCII when decoding the byte string as base64 encoding only
    # produces characters within that codeset.

    return result.decode('ascii')

def xor_cipher_decrypt_base64(text, key):
    """Decrypts the text using an XOR cipher where the key is provided
    as a byte array. The key cannot be an empty byte array. Where the
    key is shorter than the text to be encrypted, the same key will
    continually be reapplied in succession. The input text must be in
    the form of a base64 encoded byte string with a UTF-8 encoding. The
    base64 string itself can be either a byte string or Unicode string.
    The final result of decrypting the input will be a Unicode string.

    """

    if not isinstance(key, bytearray):
        key = xor_cipher_genkey(key)

    result = xor_cipher_decrypt(bytearray(base64.b64decode(text)), key)

    return bytes(result).decode('utf-8')

obfuscate = xor_cipher_encrypt_base64
deobfuscate = xor_cipher_decrypt_base64
