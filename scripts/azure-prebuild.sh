#!/bin/sh

###########################################
# This script is used to prebuild the New
# Relic Python agent for Azure Web Apps.
# It is executed in the Azure Web App 
# environment before the app is started.
###########################################

# Retrieve files to use in startup script:
curl -L https://raw.githubusercontent.com/newrelic/newrelic-agent-init-container/refs/heads/main/src/python/newrelic_k8s_operator.py > newrelic_k8s_operator.py
curl -L https://raw.githubusercontent.com/newrelic/newrelic-agent-init-container/refs/heads/main/src/python/requirements-vendor.txt > requirements-vendor.txt
curl -L https://raw.githubusercontent.com/newrelic/newrelic-agent-init-container/refs/heads/main/src/python/requirements-builder.txt > requirements-builder.txt

cd /home/

pip install -r requirements-builder.txt

export NEW_RELIC_EXTENSIONS=false
export WRAPT_DISABLE_EXTENSIONS=true

pip install newrelic --target=./workspace/newrelic

mkdir -p ./workspace/vendor
pip install --target=./workspace/vendor -r requirements-vendor.txt

cp ./workspace/* /home/
cp /home/workspace/newrelic/newrelic/bootstrap/sitecustomize.py /home/sitecustomize.py

cd /home/site/wwwroot