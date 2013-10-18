from __future__ import print_function

from newrelic.admin import command, usage

@command('rum-header', '',
"""Prints out the RUM header.""", hidden=True)
def rum_header(args):
    import sys

    if len(args) != 0:
        usage('rum-header')
        sys.exit(1)

    from newrelic.api.web_transaction import _rum_header_fragment as header

    print(header)
