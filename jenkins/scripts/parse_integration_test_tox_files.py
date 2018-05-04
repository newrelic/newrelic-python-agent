#!/usr/bin/env python2.7

import argparse
import json
import os
import tox.config

try:
    import ConfigParser
except ImportError:
    import configparser as ConfigParser


def str2bool(val):
    bools_dict = {
        '1': True, 'true': True, 'yes': True,
        '0': False, 'false': False, 'no': False,
    }

    val = str(val).lower()

    return bools_dict[val]


def parse_args():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('-s', '--test-suffix',
        default='__integration_test',
        help=('A suffix name to give to each test, defaults to '
            '"__integration_test"'),
    )
    parser.add_argument('--most-recent-only',
        default='false',
        choices=['true', 'false'],
        help=('Return only the environments that test the most recent '
            'package version, defaults to False'),
    )
    parser.add_argument('--max-group-size',
        default=14,
        type=int,
        help=('The maximum number of tox environments to include in a given '
            'jenkins test, defaults to 14'),
    )
    parser.add_argument('--workspace',
        help=('The jenkins workspace, helpful for finding the test files, '
              'defaults to current working directory'),
    )
    parser.add_argument('--include-cext',
        default=True,
        choices=[True, False],
        type=str2bool,
        help='Include tox environments that contain `with-extensions`'
    )

    args = parser.parse_args()

    return args


def test_dirs(workspace):
    """
    Generate a list of the directories under the 'tests' directory
    """
    tests_dir = '%s/tests' % workspace
    for test_dir in os.listdir(tests_dir):
        name = '%s/%s' % (tests_dir, test_dir)
        if os.path.isdir(name):
            yield name


def get_envs(tox_file, restrict_to=None, include_cext=True):
    """
    Use the tox API to get the list of environments defined in the given tox
    file. If requesting most_recent_only, return only those environments that
    test the most recent package version.
    """
    envs = tox.config.parseconfig(['-c', tox_file]).envlist
    if restrict_to:
        envs = [env for env in envs if restrict_to in env]
    if not include_cext:
        envs = [env for env in envs if 'with-extensions' not in env]
    return envs


def get_compose_path_if_exists(test_dir):
    if 'docker-compose.yml' in os.listdir(test_dir):
        return '%s/docker-compose.yml' % test_dir
    return None


def get_tox_path_if_exists(test_dir):
    for file_name in os.listdir(test_dir):
        if file_name.endswith('tox.ini'):
            return os.path.join(test_dir, file_name)
    return None


def create_test_name(test_dir, group_name, test_suffix):
    dir_basename = os.path.basename(test_dir)
    name = '_'.join([dir_basename, group_name, test_suffix])
    return name


def possibly_group_envs(test_envs, max_group_size):
    """
    Given a list of envs and the max size for each group, return a list of
    tuples of (envlist, group name)
    """
    num_groups = int(len(test_envs) / max_group_size)
    if len(test_envs) % max_group_size != 0:
        num_groups += 1

    groups = [([], 'group%s' % index) for index in range(num_groups)]
    for index, env in enumerate(test_envs):
        groups[index % num_groups][0].append(env)

    groups = [(','.join(group[0]), group[1]) for group in groups]
    return groups


def strip_workspace(path):
    if not path:
        return None

    test_dir_path = os.path.dirname(path)
    test_dir_name = os.path.basename(test_dir_path)
    test_dir_dir = os.path.basename(os.path.dirname(test_dir_path))
    file_name = os.path.basename(path)
    relpath = os.path.join(test_dir_dir, test_dir_name, file_name)
    return relpath


def parse_tox_file(tox_path):
    """
    Given a path to a tox file, return some test settings from that file.

    Return tuple: most recent version of test or None if not set, boolean if
    the test is disabled or False if not set
    """
    config_object = ConfigParser.RawConfigParser()
    config_object.read([tox_path])

    most_recent = None
    is_disabled = False
    max_group_size = None

    if config_object.has_section('jenkins'):
        try:
            most_recent = config_object.get('jenkins', 'mostrecent')
        except ConfigParser.NoOptionError:
            pass

        try:
            is_disabled_str = config_object.get('jenkins', 'disabled')
            is_disabled = str2bool(is_disabled_str)
        except ConfigParser.NoOptionError:
            pass

        try:
            max_group_size_str = config_object.get('jenkins', 'max_group_size')
            max_group_size = int(max_group_size_str)
        except ConfigParser.NoOptionError:
            pass

    return most_recent, is_disabled, max_group_size


def get_tests(test_suffix, most_recent_only, max_group_size_global, test_dir,
        include_cext=True):
    """
    Get a list of tests to run found in the given test_dir. Returns list of
    lists representing a test.
    """
    tests = []

    tox_path = get_tox_path_if_exists(test_dir)
    if not tox_path:
        return tests

    most_recent, is_disabled, max_group_size_local = parse_tox_file(tox_path)
    if is_disabled:
        return tests

    restrict_to = most_recent_only and most_recent
    max_group_size = max_group_size_local or max_group_size_global

    test_envs = get_envs(tox_path, restrict_to=restrict_to,
            include_cext=include_cext)
    for env_group, group_name in possibly_group_envs(test_envs,
            max_group_size):
        test_name = create_test_name(test_dir, group_name, test_suffix)
        compose_path = get_compose_path_if_exists(test_dir)

        tests.append([
            test_name,
            strip_workspace(tox_path),
            env_group,
            strip_workspace(compose_path),
        ])

    return tests


def main(args):
    test_suffix = args.test_suffix
    most_recent_only = str2bool(args.most_recent_only)
    max_group_size = args.max_group_size
    workspace = args.workspace or os.getcwd()
    include_cext = args.include_cext

    tests = []

    for test_dir in test_dirs(workspace):
        tests.extend(get_tests(test_suffix, most_recent_only, max_group_size,
            test_dir, include_cext))
    return json.dumps(tests)


if __name__ == '__main__':
    args = parse_args()
    tests = main(args)
    print(tests)
