#!/bin/sh

# Seed the devpi-server cache with all of the packages that the tox tests
# need. This should eliminate the need to download any packages from PyPI,
# greatly speeding up our tests.

# Seeding the cache is done by installing and uninstalling all packages in a
# virtualenv. Using the '-p requirements.txt' option to 'pip install' isn't
# possible, because you can't install multiple versions of the same package
# in the same virtualenv, hence the need to install/uninstall one at a time.

set -e

# Install most packages in python 2.7 virtualenv
while read PACKAGE
do
    /root/venv/bin/pip install -i http://localhost:3141/root/pypi/ -U $PACKAGE
    /root/venv/bin/pip uninstall -y $PACKAGE
done < /root/packages-py2.txt

# Some packages must be installed in python 3 virtualenv
while read PACKAGE
do
    /root/venv-py3/bin/pip install -i http://localhost:3141/root/pypi/ -U $PACKAGE
    /root/venv-py3/bin/pip uninstall -y $PACKAGE
done < /root/packages-py3.txt
