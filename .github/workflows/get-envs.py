#!/usr/bin/env python3.8
import fileinput
import os

GROUP_NUMBER = int(os.environ["GROUP_NUMBER"]) - 1
TOTAL_GROUPS = int(os.environ["TOTAL_GROUPS"])


def main(f):
    environments = [e.rstrip() for e in f]
    total_environments = len(environments)
    envs_per_group = total_environments // TOTAL_GROUPS
    start = GROUP_NUMBER * envs_per_group
    end = start + envs_per_group
    print(",".join(environments[start:end]))


if __name__ == "__main__":
    with fileinput.input() as f:
        main(f)
