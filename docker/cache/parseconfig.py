#!/usr/bin/env python
from ConfigParser import ConfigParser, NoOptionError
import os.path
import string
import sys


def extract_packages(tox_files):
    # Packages is a set of package dependencies for all the tests
    packages = set(extra_packages)

    for tox_file in tox_files:

        # Parse tox file into ConfigParser
        parser = ConfigParser()
        parser.read(tox_file)
        sections = parser.sections()

        for section in sections:
            # Extract a list of dependencies
            try:
                deps_section = parser.get(section, 'deps')
            except NoOptionError:
                continue
            deps = deps_section.strip().split('\n')

            # Remove any conditions from dependencies
            stripped_deps = [d.split(':')[-1].strip() for d in deps]

            # PEP 0426
            # https://www.python.org/dev/peps/pep-0426/#name
            #
            # Distribution names MUST start and end with an ASCII letter
            # or digit.
            filtered_deps = [d for d in stripped_deps if d and
                    d[0] in (string.letters + string.digits) and
                    d[-1] in (string.letters + string.digits)]
            packages |= set(filtered_deps)

    return packages


def create_package_list_file(out_filename, packages):
    out = '\n'.join(packages)
    with open(out_filename, 'w') as f:
        f.write(out)


def main(tox_files, exclude_packages,
        source_only_packages, extra_packages, out_dir):

    # Extract all packages from tox files
    compile_packages = extract_packages(tox_files)

    # Remove excluded packages
    compile_packages.difference_update(set(exclude_packages))

    # Remove source only packages
    compile_packages.difference_update(set(source_only_packages))

    # Add extra packages
    compile_packages.update(set(extra_packages))

    # Create a compiled package list
    compiled_package_filename = os.path.join(out_dir, 'packages-compiled.txt')
    create_package_list_file(compiled_package_filename, compile_packages)

    # Create a source only package list
    source_package_filename = os.path.join(out_dir, 'packages-source.txt')
    create_package_list_file(source_package_filename, source_only_packages)

    return 0


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Fetch tox file dependencies')
    parser.add_argument('-o', metavar='DIR', type=str,
                        default='docker/cache/package-lists',
                        help='Output Directory')
    parser.add_argument('-e', metavar='PKG', type=str, nargs='+',
                        help='Packages to exclude')
    parser.add_argument('-s', metavar='PKG', type=str, nargs='+',
                        help='Source only packages')
    parser.add_argument('-x', metavar='PKG', type=str, nargs='+',
                        help='Extra Packages (py2 used)')
    parser.add_argument('files', metavar='FILE', type=str, nargs='+',
                        help='List of tox files to parse')
    args = parser.parse_args()
    exclude_packages = args.e or []
    source_only_packages = args.s or []
    extra_packages = args.x or []
    sys.exit(main(args.files, exclude_packages,
            source_only_packages, extra_packages, args.o))
