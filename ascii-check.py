#!/usr/bin/env python

# Check that file contains only ASCII characters. Most useful for
# verifying that the README is OK.

import os
import sys


def usage():
    script_name = os.path.basename(sys.argv[0])
    print("Usage: %s <filename>" % script_name)

def main():
    if len(sys.argv) != 2:
        usage()
        sys.exit(1)

    filename = sys.argv[1]

    try:
        open(filename).read().encode('ascii')
    except Exception as e:
        print(e)
        print("%s fails ascii check" % filename)
        sys.exit(1)

if __name__ == '__main__':
    main()
