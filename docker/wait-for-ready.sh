#!/bin/bash


TIMEOUT="30"  # in seconds

test_it() {
    # determine how to test it by checking the global variable WAIT_FOR
    case "$WAIT_FOR" in
        postgresql)
            test_postgresql $@
            ;;
    *)
        echo "Value \"$WAIT_FOR\" not found"
        exit 1
        ;;
    esac
}

test_postgresql() {
    HOST=$1
    PORT=$2

    # test readiness by attempting to list databases
    export PGPASSWORD="python_agent"
    psql -h "$HOST" -p "$PORT" -U "python_agent" -c '\l' -w > /dev/null 2>&1
}

wait_for_ready() {
    for HOST_PORT in $(echo $HOSTS_PORTS | tr "," "\n")
    do

        HOST=${HOST_PORT%:*}
        PORT=${HOST_PORT#*:}

        echo -n "Waiting for $HOST to be available on port $PORT."

        start=$(date +"%s.%6N")

        for ((i=1;i<=TIMEOUT;i++))
        do

            test_it $HOST $PORT
            result=$?

            if [[ $result -eq 0 ]]; then
                end=$(date +"%s.%6N")
                total_time=`python2.7 -c "print $end - $start"`
                echo
                echo "$HOST available after $total_time seconds"
                break
            else
                echo -n "."
                sleep 1
            fi

        done

        # if timeout exceeded exit with failure
        if [[ $result != 0 ]]
        then
            echo
            echo "Unable to connect to $HOST after $TIMEOUT seconds!"
            exit $result
        fi

    done
}

usage() {
    echo
    echo "Wait for any number of services to be ready before executing a command."
    echo "The first positional argument to this script should be a comma separated list"
    echo "of the hosts and ports to check, after that comes the command and its options."
    echo
    echo "USAGE: ./wait-for-ready.sh [OPTIONS] HOST1:PORT1[HOST2:PORT2,HOST3:PORT3...] command options"
    echo "  Options:"
    echo "      --postgresql    Wait for a postgresql database to become ready"
}

OPTION=$1

case "$OPTION" in
    --postgresql)
        WAIT_FOR=postgresql
        shift
        ;;
    *)
        usage
        exit 1
        ;;
esac

HOSTS_PORTS=$1
shift
CMD="$@"

wait_for_ready

# run original command
echo
exec $CMD
