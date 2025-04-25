#!/bin/sh
# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#######################################################################
# This script is used to prebuild the New Relic Python agent for Azure Web Apps.
# It is executed in the Azure Web App environment before the app is started.
#######################################################################

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
