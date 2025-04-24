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

mkdir -p /home/.newrelic
cd /home/.newrelic

export NEW_RELIC_EXTENSIONS=false
export WRAPT_DISABLE_EXTENSIONS=true

pip install 'setuptools>=40.8.0' wheel
pip install newrelic --target=./newrelic
pip install --target=./vendor -r /home/site/wwwroot/requirements-vendor.txt

mv /home/site/wwwroot/newrelic_k8s_operator.py /home/.newrelic/newrelic/
cp /home/.newrelic/newrelic/newrelic/bootstrap/sitecustomize.py /home/sitecustomize.py 

cd /home/site/wwwroot
