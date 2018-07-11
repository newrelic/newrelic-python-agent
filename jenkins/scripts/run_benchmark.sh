#!/usr/bin/env bash

# Install asv
/venvs/py36/bin/pip install asv

cat <<EOF > ~/.asv-machine.json
{
    "jenkins": {
        "arch": "x86_64",
        "cpu": "",
        "machine": "jenkins",
        "os": "Linux",
        "ram": ""
    },
    "version": 1
}
EOF


for venv in $(find /venvs -maxdepth 1 -type d | grep -v "/venvs$"); do
    # Install the agent
    $venv/bin/pip install -e .

    # Run asv
    /venvs/py36/bin/asv run -E existing:$venv/bin/python
done
