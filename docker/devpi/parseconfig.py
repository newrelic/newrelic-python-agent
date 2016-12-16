#!/usr/bin/env python
from ConfigParser import ConfigParser, NoOptionError
import string
import os.path
import sys

def extract_packages(tox_files, exclude_packages):
    packages = {} # stores py27/py26/etc
    for tox_file in tox_files:
        tox_file_packages = set([])
        tox_file_envs = []
        parser = ConfigParser()
        parser.read(tox_file)
        sections = parser.sections()
        for section in sections:
            try:
                deps_section = parser.get(section, 'deps')
            except NoOptionError:
                continue
            deps = deps_section.strip().split('\n')
            env_name = section.split('-')[0]
            if ':' in env_name:
                py_name = env_name.split(':')[1]
                tox_file_envs.append(py_name)

            # PEP 0426
            # https://www.python.org/dev/peps/pep-0426/#name
            #
            # Distribution names MUST start and end with an ASCII letter
            # or digit.
            deps = [d for d in deps if d and
                    d[0] in (string.letters + string.digits) and
                    d not in exclude_packages]
            tox_file_packages |= set(deps)

        if not tox_file_envs:
            env_pkgs = packages.setdefault('all', set([]))
            env_pkgs |= tox_file_packages
        else:
            for env in tox_file_envs:
                env_pkgs = packages.setdefault(env, set([]))
                env_pkgs |= tox_file_packages

    return packages

def generate_package_lists(packages):
    env_all = packages.pop('all', None)

    package_lists = {
        'py2' : set([]),
        'py3' : set([]),
    }

    if env_all:
        package_lists['py2'] |= env_all

    pkg_memberships = {}

    for env in packages:
        for pkg in packages[env]:
            membership = pkg_memberships.setdefault(pkg, set([]))
            if env.startswith('py2'):
                membership |= set(['py2'])
            elif env.startswith('py3'):
                membership |= set(['py3'])

    for pkg in pkg_memberships:
        pkg_m = pkg_memberships[pkg]
        pkg_l = 'py2'

        # "both" will map to py2
        if 'py2' in pkg_m and 'py3' in pkg_m:
            pkg_l = 'py2'
        elif 'py3' in pkg_m:
            pkg_l = 'py3'

        package_lists[pkg_l] |= set([pkg])

    package_lists['py2'] = list(package_lists['py2'])
    package_lists['py3'] = list(package_lists['py3'])

    return package_lists

def create_package_list_files(package_lists, out_dir, source_only_packages):
    for pkg_l in package_lists:
        out = '\n'.join(package_lists[pkg_l])
        out_filename = os.path.join(out_dir, 'packages-%s.txt' % pkg_l)
        with open(out_filename, 'w') as f:
            f.write(out)

    out_filename = os.path.join(out_dir, 'packages-source.txt')
    out = '\n'.join(source_only_packages)
    with open(out_filename, 'w') as f:
        f.write(out)

def create_wheel_build_files(packages, out_dir):
    for env in packages:
        out = '\n'.join(list(packages[env]))
        out_filename = os.path.join(out_dir, 'wheels-%s.txt' % env)
        with open(out_filename, 'w') as f:
            f.write(out)

def main(tox_files, exclude_packages, source_only_packages, out_dir):
    packages = extract_packages(tox_files, exclude_packages)
    package_lists = generate_package_lists(packages)
    create_package_list_files(package_lists, out_dir, source_only_packages)
    create_wheel_build_files(packages, out_dir)
    return 0

if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Fetch tox file dependencies.')
    parser.add_argument('-o', metavar='DIR', type=str,
                        default='docker/devpi/package-lists',
                        help='Output Directory')
    parser.add_argument('-e', metavar='PKG', type=str, nargs='+',
                        help='Packages to exclude')
    parser.add_argument('-s', metavar='PKG', type=str, nargs='+',
                        help='Source only packages')
    parser.add_argument('files', metavar='FILE', type=str, nargs='+',
                        help='List of tox files to parse')
    args = parser.parse_args()
    sys.exit(main(args.files, args.e, args.s, args.o))
