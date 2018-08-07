#!/usr/bin/env bash

# Install asv
/venvs/py36/bin/pip install asv virtualenv

cat <<EOF > ~/.asv-machine.json
{
    "$HOST_MACHINE": {
        "arch": "x86_64",
        "cpu": "",
        "machine": "$HOST_MACHINE",
        "os": "Linux",
        "ram": ""
    },
    "version": 1
}
EOF

/venvs/py36/bin/asv run HEAD~..HEAD
/venvs/py36/bin/asv publish
