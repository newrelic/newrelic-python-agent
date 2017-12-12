#!/usr/bin/env python3

import argparse
import ast
import multiprocessing
import functools
import glob
import json
import pkgutil
import os.path
import subprocess
import sys

PYTHON_LIBRARIES = {'os', 'sys', 're', 'logging', 'weakref', 'time',
        'traceback', 'asyncio', 'inspect', 'urlparse', 'urllib.parse',
        'collections', 'functools', 'threading', 'types', 'multiprocessing',
        'string', 'imp', 'json', 'base64', 'warnings', '__future__',
        '__builtin__', 'StringIO', 'io', 'zlib', 'hashlib', 'copy', 'random',
        'thread', 'importlib', 'socket', 'subprocess', 'cProfile',
        'configparser', 'ConfigParser', 'pprint', 'exceptions', 'atexit',
        'platform', 'timeit', 'Queue', 'builtins', 'cgi', 'cmd', 'code',
        'distutils.sysconfig', 'glob', 'pwd', 'ssl', 'itertools', 'optparse',
        'operator', 'shlex', 'queue', 'resource'}
SPECIAL_FILES = {'tox.ini', 'tests.sh', 'setup.py', 'tox-admin.ini'}


def extract_hook_mappings():
    """Extract import hooks from newrelic/config.py

    This function returns a dictionary in the format of
    {package_name: newrelic_hook_file}

    It also enumerates the import hooks against the list of feature flags that
    exist since import hooks can change with feature flags.

    The purpose of getting this dictionary is to map imports in a test file to
    hooks that would be imported at runtime.

    :rtype: dict
    """
    from newrelic.config import (_process_module_builtin_defaults,
            _FEATURE_FLAGS)
    from newrelic.common.object_wrapper import wrap_function_wrapper
    from newrelic.api.settings import settings
    _settings = settings()
    orig = _settings.feature_flag

    hooks = {}

    def record_builtin_defaults(wrapped, instance, args, kwargs):
        def bind_params(target, module, function='instrument'):
            return (target, module)

        target, module = bind_params(*args, **kwargs)
        hook_list = hooks.setdefault(target, [])
        hook_list.append(module)

        # don't actually call wrapped you fool
        return

    wrap_function_wrapper('newrelic.config', '_process_module_definition',
            record_builtin_defaults)

    for flag in _FEATURE_FLAGS:
        _settings.feature_flag = {flag}
        _process_module_builtin_defaults()

    _settings.feature_flag = orig

    return hooks


class ImportVisitor(ast.NodeVisitor):
    """Extract imported modules from an AST

    This visits all ImportFrom and Import statements in the AST and records the
    module that was imported in the modules attribute.
    """
    def __init__(self, *args, **kwargs):
        super(ImportVisitor, self).__init__(*args, **kwargs)
        self.modules = set()

    def visit_ImportFrom(self, node):
        module = node.module
        if module:
            self.modules.add(module)

    def visit_Import(self, node):
            modules = {m.name for m in node.names if m.name}
            self.modules.update(modules)


def get_imports(source, hooks):
    """Return a list of modules imported by python source text

    Some modules have hooks associated with them that will import at runtime.
    Those modules will be mapped to newrelic hook files in addition to the raw
    module.

    :param source: Python source file string to extract imports from.
    :type source: str
    :param hooks: dictionary of module names to newrelic hook module names
    :type hooks: dict

    :rtype: list
    """
    visitor = ImportVisitor()

    # Parse the source string into an AST
    tree = ast.parse(source)

    # Recursively walk the tree
    visitor.visit(tree)

    # Determine if any hooks will fire and add them to the imported modules
    modules = visitor.modules
    final_modules = []
    for module in modules:
        final_modules.append(module)
        if module in hooks:
            final_modules.extend(hooks[module])

    # Return the extracted modules
    return final_modules


def translate_modules_to_filenames(modules):
    """Translate module names to filenames.

    This function will attempt to find a loader for each module and will yield
    the filename associated with that module if found. This function returns a
    generator yielding those filenames.

    :param modules: iterable containing strings of module names
    :type modules: list or set
    :param hooks: dictionary of module names to newrelic hook module names
    :type hooks: dict

    :rtype: generator
    """
    filenames = set()

    for module in modules:
        try:
            result = pkgutil.find_loader(module)
        except ImportError as e:
            continue

        # Some modules can't be found. That's cool.
        if result:
            if hasattr(result, 'get_filename'):
                filename = result.get_filename()

                if not filename:
                    continue

                if filename not in filenames:
                    yield filename
                filenames.add(filename)


def traverse_imports(initial_filenames, nr_path, hooks):
    """Recursive traversal of the import tree for a set of files

    Given a set of filenames, travese the import tree and yield the filenames
    of the imported files.

    This allows the caller to progressively check if a file in the import path
    has been changed and to then make a logical decision about that
    information.

    :param initial_filenames: Set of filenames to start the traversal (top of
                              tree)
    :type initial_filenames: list or set
    :param nr_path: Path to the top level directory for the New Relic repo
    :type nr_path: str
    :param hooks: dictionary of module names to newrelic hook module names
    :type hooks: dict

    :rtype: generator
    """
    filenames_imported = set(initial_filenames)
    need_extraction = list(initial_filenames)

    while need_extraction:
        to_extract = need_extraction.pop()

        try:
            with open(to_extract, 'r') as f:
                source = f.read()
        except Exception as e:
            continue

        modules_imported_by_source = get_imports(source, hooks)

        # order modules that are newrelic first
        modules_imported_sorted = sorted(modules_imported_by_source,
                key=lambda x: 0 if 'newrelic' in x else 1)

        # ignore modules that are known to be python libraries
        modules_filtered = [_ for _ in modules_imported_sorted
                if _ not in PYTHON_LIBRARIES]

        filenames_imported_by_source = translate_modules_to_filenames(
                modules_filtered)

        for filename_imported in filenames_imported_by_source:

            # do not extract files already extracted files
            if filename_imported in filenames_imported:
                continue

            # completely ignore files not in nr_path
            if not filename_imported.startswith(nr_path):
                continue

            yield filename_imported

            # store the extracted file
            filenames_imported.add(filename_imported)

            # add files that need to be extracted
            need_extraction.append(filename_imported)


def git_files_changed(nr_path, merge_target):
    """Extract files that have changed relative to the merge_target branch

    This function queries GIT for information about which files have changed
    relative to a target branch.

    :param nr_path: Path to the top level directory for the New Relic repo
    :type nr_path: str
    :param merge_target: Name of the target branch to compare against.
    :type merge_target: str

    :rtype: set
    """
    cwd = os.getcwd()
    os.chdir(nr_path)
    try:
        merge_base = subprocess.check_output(
                ['git', 'merge-base', merge_target, 'HEAD'])

        if type(merge_base) is not str:
            merge_base = merge_base.decode('utf-8')

        # remove any newlines
        merge_base = merge_base.strip()

        files_changed = subprocess.check_output(
                ['git', 'diff', ('%s..' % merge_base), '--name-only'])

        if type(files_changed) is not str:
            files_changed = files_changed.decode('utf-8')

        if not files_changed:
            return set()

        # create a set of files changed
        files_changed = set([os.path.join(nr_path, _)
                for _ in files_changed.strip().split('\n')])
    finally:
        os.chdir(cwd)

    return files_changed


def should_test(testdir, nr_path, hooks, changed_files):
    """Determines if a test directory should be tested given a list of changes

    Returns True if the files in testdir import files that have changed.

    :param testdir: Directory to traverse for import changes
    :type testdir: str
    :param nr_path: Path to the top level directory for the New Relic repo
    :type nr_path: str
    :param hooks: dictionary of module names to newrelic hook module names
    :type hooks: dict
    :param changed_files: Set of files that have changed (used in determining
                          if a test should be run)
    :type changed_files: set

    :rtype: bool
    """
    # Check if any changed files are in the test directory
    # If yes, the test must be run.
    for changed_file in changed_files:
        if changed_file.startswith(testdir):
            return True

    filenames = set()

    # Add the directory of the file to the path
    sys.path.insert(0, testdir)

    try:
        # Extract all top level python files in the testdir
        # NOTE: this does not do a walk so nested tests are not extracted This
        # is intentional since tests are (currently) only at the top level and
        # import from subdirectories.
        files_in_dir = os.listdir(testdir)
        for filename in files_in_dir:
            filename = os.path.join(testdir, filename)

            if filename.endswith('.py'):
                filenames.add(filename)

        for filename_imported in traverse_imports(
                filenames, nr_path, hooks):
            if filename_imported in changed_files:
                # As soon as a changed file is detected, return True
                return True
    finally:
        sys.path.remove(testdir)

    return False


def main(testdirs, nr_path, merge_target):
    changed_files = git_files_changed(nr_path, merge_target)
    if not changed_files:
        print(json.dumps([]))
        return 0

    # Add the agent to sys path
    sys.path.insert(0, nr_path)
    hooks = extract_hook_mappings()

    # Add the tests directory to the path
    test_path = os.path.join(nr_path, 'tests')
    sys.path.insert(0, test_path)

    # create a pool to run test evaluation in parallel
    pool = multiprocessing.Pool(10)

    _should_test = functools.partial(should_test,
            nr_path=nr_path, hooks=hooks, changed_files=changed_files)

    # normalize testdir paths
    testdirs = [_ if os.path.isabs(_) else os.path.join(nr_path, _)
            for _ in testdirs]

    tests = {_ for _ in testdirs if os.path.isdir(_)}

    if not tests:
        sys.stderr.write("No tests found\n")
        return 1

    tests_to_run = []

    # Check for changed "special" top level files
    for SPECIAL_FILE in SPECIAL_FILES:
        if os.path.join(nr_path, SPECIAL_FILE) in changed_files:
            # Add something to the tests to run (non-empty)
            tests_to_run.append('.')
            break

    # NOTE: C files are not explored since they won't be able to be imported
    # until they're compiled. This needs some thought in the future.
    # TODO: figure out how to explore C file changes (and map them to the
    # appropriate test runs)
    for test, run in zip(tests, pool.map(_should_test, tests)):
        if run:
            rel_test_path = os.path.relpath(test, nr_path)
            tests_to_run.append(rel_test_path)

    print(json.dumps(tests_to_run))

    return 0


def parse_args():
    nr_path_default = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))
    parser = argparse.ArgumentParser(
            description='Report modules imported by a file.')
    parser.add_argument('-nr_path', type=str,
            default=nr_path_default,
            nargs='?',
            help='Path to new relic (default: %s)' % nr_path_default)
    parser.add_argument('-branch', type=str,
            default=os.environ.get('ghprbTargetBranch', 'origin/develop'),
            nargs='?',
            help='Branch target for a merge')
    parser.add_argument('testdirs', type=str,
            nargs='+',
            help='List of test directories to traverse '
                 'for dependency changes.')

    args = parser.parse_args()

    # parse globs
    final_testdirs = []
    for d in args.testdirs:
        if '*' in d:
            final_testdirs.extend(glob.glob(d))
        else:
            final_testdirs.append(d)
    args.testdirs = final_testdirs

    return args


if __name__ == '__main__':
    args = parse_args()
    exit_code = main(args.testdirs, args.nr_path, args.branch)
    sys.exit(exit_code)
