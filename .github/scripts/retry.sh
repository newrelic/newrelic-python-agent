#!/bin/bash
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


# Time in seconds to backoff after the initial attempt.
INITIAL_BACKOFF=10

# Grab first arg as number of retries
retries=$1
shift

# Use for loop to repeatedly try the wrapped command, breaking on success
for i in $(seq 1 $retries); do
    echo "Running: $@"

    # Exponential backoff
    if [[ i -gt 1 ]]; then
        # Starts with the initial backoff then doubles every retry.
        backoff=$(($INITIAL_BACKOFF * (2 ** (i - 2))))
        echo "Command failed, retrying in $backoff seconds..."
        sleep $backoff
    fi
    
    # Run wrapped command, and exit on success
    $@ && break
    result=$?
done

# Exit with status code of wrapped command
exit $result
