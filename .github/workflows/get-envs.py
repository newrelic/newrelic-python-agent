#!/usr/bin/env python3.8
import fileinput
import os

GROUP_NUMBER = int(os.environ["GROUP_NUMBER"]) - 1
TOTAL_GROUPS = int(os.environ["TOTAL_GROUPS"])


def main(f):
    environments = [e.rstrip() for e in f]
    filtered_envs = environments[GROUP_NUMBER::TOTAL_GROUPS]
    print(",".join(filtered_envs))


if __name__ == "__main__":
    with fileinput.input() as f:
        main(f)
