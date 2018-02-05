#!/bin/bash -ex

./docker/packnsend build_nocache cache
./docker/packnsend push cache
