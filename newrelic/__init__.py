#vi: set sw=4 expandtab :

from _newrelic import *

import sys
sys.meta_path.insert(0, ImportFinder())

import fixups_django
