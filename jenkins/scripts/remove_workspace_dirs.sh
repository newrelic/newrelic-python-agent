#!/bin/sh -e
find /data/jenkins/workspace -mindepth 1 -maxdepth 1 -type d | grep -v "Reset-Nodes$" | xargs rm -rf
echo $?