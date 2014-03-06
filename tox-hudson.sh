#!/bin/bash

source /home/hudson/PythonSetupHome/agent_env/bin/activate

pwd

if [ -e report ]
then
        rm -rf report
fi
mkdir report


cd ./docker

./packnsend  run tox -c tests/memcache_memcache/tox.ini > ../report/memcache_tox.log 2>&1 & 
./packnsend  run tox -c tests/database_sqlite/tox.ini > ../report/sqlite_tox.log 2>&1 &

