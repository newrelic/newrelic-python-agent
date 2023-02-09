#!/bin/sh

# Grab first arg as number of retries
retries=$1
shift

# Use for loop to repeatedly try the wrapped command, breaking on success
for i in $(seq 1 $retries); do
    echo "Running: $@"

    # Exponential backoff
    if [[ i -gt 1 ]]; then
        # Start with 10 seconds, then double every retry.
        backoff=$((1 * (2 ** (i - 2))))
        echo "Command failed, retrying in $backoff seconds..."
        sleep $backoff
    fi
    
    # Run wrapped command, and exit on success
    $@ && break
    result=$?
done

# Exit with status code of wrapped command
exit $?
