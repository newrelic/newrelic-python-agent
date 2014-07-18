import re

_body_start_p = b"""(?P<body><body[^>]*>)"""

_body_start_re = re.compile(b""".*""" + _body_start_p + b""".*""",
        re.IGNORECASE | re.DOTALL)


def verify_body_exists(data):

	return _body_start_re.match(data) != -1