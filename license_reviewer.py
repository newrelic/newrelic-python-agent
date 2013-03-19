import os
import sys
import argparse
import fileinput
import json
import hashlib
import time
import subprocess
import re
from argparse import RawDescriptionHelpFormatter
import shutil
import filecmp
import tempfile
import cgi
import ConfigParser
from datetime import datetime

# stuff to do:
# -------------------------------------------------------
# Figure out what to do with wix

ignored_files = {}

script_dir = ""
license_reviewer_metafile_path = ""

ignore_filename = 'license_ignore.txt'
license_source_map_filename = 'license_source_map.json'
license_info_filename = 'license_info.json'
license_config_filename = 'license_config.ini'

# gets read in from the ini file
projectname = ""
permalink = ""

new_relic_library = "New Relic"

class NR_Error(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def review_command(args):
    print("Validating licenses...\n")

    license_info_file = os.path.join(license_reviewer_metafile_path, license_info_filename)
    license_source_map_file = os.path.join(license_reviewer_metafile_path, license_source_map_filename)
    ignore_file = os.path.join(license_reviewer_metafile_path, ignore_filename)

    license_info = load_license_info_file(license_info_file)
    license_error_filename = os.path.join(license_reviewer_metafile_path, "license_errors.txt")

    ignored_files = get_ignored_files(ignore_file)
    license_source_map = load_source_map_file(license_source_map_file)

    root_dir = "."

    repo_files = get_git_repo_files()
    flattened_file_list = get_flattened_file_list(root_dir, ignored_files, repo_files)

    error_count = 0
    errors = []

    f = open(license_error_filename, "w")

    errors = check_for_missing_source_files(license_source_map) 
    print_and_write_errors("Source files tracked in manifest but no longer in working dir", errors, f)
    error_count += len(errors)

    errors = check_for_orphaned_libraries(license_info, license_source_map)
    print_and_write_errors("Libraries that are no longer referenced by any source files", errors, f)
    error_count += len(errors)

    errors = check_for_missing_licenses(license_info)
    print_and_write_errors("Libraries that reference licenses that aren't tracked in the license file", errors, f)
    error_count += len(errors)

    errors = check_local_license_urls(license_info)
    print_and_write_errors("Licenses that are included as local files but have local files that don't exist", errors, f)
    error_count += len(errors)

    errors = check_for_orphaned_licenses(license_info)
    print_and_write_errors("Licenses that are no longer referenced by any libraries", errors, f)
    error_count += len(errors)

    errors = check_for_source_files_not_in_manifest(flattened_file_list, license_source_map)
    print_and_write_errors("Source files that are in the git repo that are not in the license_source_map file", errors, f)
    error_count += len(errors)

    errors = check_for_changed_source_files(flattened_file_list, license_source_map)
    print_and_write_errors("Source files that return a different hash value than the last time the setlicense command was called", errors, f)
    error_count += len(errors)

    f.flush()
    f.close()

    if error_count > 0:
        print("See '"+license_error_filename+"' for a list of any source files that have errors.")

    return error_count

def add_library_command(args):
    print("Adding new 3rd party library...\n")

    license_info_file = os.path.join(license_reviewer_metafile_path, license_info_filename)
    uniqueid = args.id
    name = args.name
    url = args.url.strip()

    license_info = load_license_info_file(license_info_file)

    try:
        add_library(license_info, uniqueid, name, url)
        save_license_info_file(license_info_file, license_info)
    except NR_Error as e:
        print(e.value)
        return -1

    return 0

def add_library(license_info, uniqueid, name, url):
    # if we've never added a library, then create the entry in our map
    if "libraries" not in license_info:
        license_info["libraries"] = {}

    license_info["libraries"][uniqueid] = {
        "name" : name,
        "url": url,
        "licenses":[]
    }

def add_license_command(args):
    print("Adding new 3rd party license...\n")

    license_info_file = os.path.join(license_reviewer_metafile_path, license_info_filename)
    uniqueid = args.id
    name = args.name
    url = args.url.strip()

    license_info = load_license_info_file(license_info_file)

    try:
        add_license(license_info, uniqueid, name, url)
        save_license_info_file(license_info_file, license_info)
    except NR_Error as e:
        print(e.value)
        return -1

    return 0

def add_license(license_info, uniqueid, name, url):
    # if the license url being referenced isn't a remote url, then make sure
    # we have a copy of the file that's referenced
    license_file = os.path.join(license_reviewer_metafile_path, url)

    if not is_url(url):
        # if it's not a remote url, assume it's a local path
        if not os.path.exists(license_file):
            raise NR_Error("[FAIL] License file does not exist: "+license_file)

    # if we've never added a license, then create the entry in our map
    if "licenses" not in license_info:
        license_info["licenses"] = {}

    license_info["licenses"][uniqueid] = {
        "name" : name,
        "url": url
    }

def set_licenses_command(args):
    print("Mapping license to library...\n")

    license_info_file = os.path.join(license_reviewer_metafile_path, license_info_filename)
    library = args.libraryid
    licenses = args.licenseid

    license_info = load_license_info_file(license_info_file)

    try:
        set_licenses(license_info, library, licenses)
        save_license_info_file(license_info_file, license_info)
    except NR_Error as e:
        print(e.value)
        return -1

    return 0 

def set_licenses(license_info, library, licenses):
    # check to make sure the library they passed is already in our libraries file
    if library not in license_info["libraries"]:
        raise NR_Error("[ERROR] could not find library: "+library+" in license_info file. Try using the addlibrary command.")
       
    # check to make sure we already know about all the licenses they passed to us
    for license in licenses:
        if license not in license_info["licenses"]:
            raise NR_Error("[ERROR] could not find license: "+license+" in license_info file. Try using the addlicense command.")

    # add the list of licenses to the library in our license info file
    license_info["libraries"][library]["licenses"] = licenses

def set_libraries_command(args):
    print("Mapping source file to library...\n")

    license_info_file = os.path.join(license_reviewer_metafile_path, license_info_filename)
    license_source_map_file = os.path.join(license_reviewer_metafile_path, license_source_map_filename)
    source_file = args.source
    libraries = args.libraryid
    ignore_file = os.path.join(license_reviewer_metafile_path, ignore_filename)

    ignored_files = get_ignored_files(ignore_file)
    license_info = load_license_info_file(license_info_file)
    source_map = load_source_map_file(license_source_map_file)

    repo_files = get_git_repo_files()

    try:
        set_libraries(license_info, source_map, repo_files, ignored_files, source_file, libraries)
        save_license_source_map_file(license_source_map_file, source_map)
    except NR_Error as e:
        print(e.value)
        return -1

    return 0

def set_libraries(license_info, source_map, repo_files, ignored_files, source_file, libraries):
    if not os.path.exists(source_file):
        raise NR_Error("[ERROR] source file does not exist: "+source_file)

    if source_file in ignored_files:
        raise NR_Error("[ERROR] Not setting library for: "+source_file+" because it's in the ignore list")

    for library in libraries:
        if library not in license_info["libraries"]:
            raise NR_Error("[ERROR] could not find library: "+library+" in license_info file")

    # if it's a directory, we'll s
    if os.path.isdir(source_file):
        files = get_flattened_file_list(source_file, ignored_files, repo_files)
        for f in files:
            set_libraries_for_source_file(f, libraries, source_map)
    else:
        set_libraries_for_source_file(source_file, libraries, source_map)

    return 0

def set_libraries_for_source_file(source_file, libraries, source_map):
    hash_key = ""

    # if there's only one library specified and it's the New Relic library, don't hash the source file
    if len(libraries) == 1 and libraries[0] == new_relic_library:
        hash_key = "n/a"
    else:
        hash_key = hash_file(source_file)

    source_map[source_file] = {
        "libraries" : libraries,
        "hash" : hash_key
    }

def remove_source_command(args):
    print("Removing source file from license_source_map manifest...\n")

    license_source_map_file = os.path.join(license_reviewer_metafile_path, license_source_map_filename)
    source_file = args.source

    source_map = load_source_map_file(license_source_map_file)

    try:
        remove_source(source_map, source_file)
        save_license_source_map_file(license_source_map_file, source_map)
    except NR_Error as e:
        print(e.value)
        return -1

    return 0

def remove_source(source_map, source_file):
    if source_file not in source_map:
        raise NR_Error("[ERROR] source file not in manifest: "+source_file)

    del source_map[source_file]

def check_clean_git_articles_dir(articles_dir):
    cmd = ["git", "diff-index", "--quiet", "--cached", "HEAD"]
    p = subprocess.Popen(cmd, cwd=articles_dir)
    return_code = p.wait()

    if return_code != 0:
        print("[ERROR] docs repo has staged but uncommitted changes.")
        return return_code

    cmd = ["git", "diff-files", "--quiet"]
    p = subprocess.Popen(cmd, cwd=articles_dir)
    return_code = p.wait()

    if return_code != 0:
        print("[ERROR] docs repo has changes in the working tree.")
        return return_code

    return 0

def get_latest_git_articles_dir(articles_dir):
    cmd = ["git", "pull", "upstream", "master"]
    p = subprocess.Popen(cmd, cwd=articles_dir)
    return_code = p.wait()

    if return_code != 0:
        print("[ERROR] failure pulling the latest copy of the docs repo down.")
        return return_code

    return 0

def gen_docs_site_doc(license_info):
    lines = []

    lines.append("<%#")
    lines.append("---")
    lines.append("article:")
    lines.append("  permalink: "+permalink)
    lines.append("  title: "+projectname+" Licenses")
    lines.append("  keywords: general")
    lines.append("  beta: false")
    lines.append("  sub_category: Licenses")
    lines.append("  meta_description: Lists third-party licenses we use in the "+projectname)
    lines.append("---")
    lines.append("%>")
    lines.append("We love open-source software, and use the following in the "+projectname+". Thank you, open-source community, for making these fine tools! Some of these are listed under multiple software licenses, and in that case we have listed the license we've chosen to use.")

    lines.append("<table>")

    for library in sorted(license_info["libraries"]):
        if library == new_relic_library:
            # skip the New Relic library
            continue

        library_name = license_info["libraries"][library]["name"]
        library_url = license_info["libraries"][library]["url"]

        lines.append("  <tr>")
        lines.append("    <td><a href=\""+library_url+"\">"+library_name+"</a></td>")
        lines.append("    <td>")

        for license in sorted(license_info["libraries"][library]["licenses"]):
            license_name = license_info["licenses"][license]["name"]
            license_url = license_info["licenses"][license]["url"]

            # if the url ends in .html.erb, we strip it so it works with the docs site.
            # we also will append a "/"
            # this is kinda-hacky, but not sure of a better solution
            erb_index = license_url.find(".html.erb")

            if erb_index != -1:
                license_url = "/"+license_url[:erb_index]

            lines.append("      <div><a href=\""+license_url+"\">"+license_name+"</a></div>")

        lines.append("    </td>")
        lines.append("  </tr>")
    lines.append("</table>")

    lines.append("The remainder of the code is covered by the New Relic License agreement found in the LICENSE file.")

    return lines

def gen_installer_doc(license_info):
    lines = []

    for library in sorted(license_info["libraries"]):
        if library == new_relic_library:
            # skip the New Relic library
            continue

        library_name = license_info["libraries"][library]["name"]
        library_url = license_info["libraries"][library]["url"]

        lines.append("----------------------------------------------------------------")
        lines.append("")
        lines.append("This product includes '"+library_name+"', which is released under the following license(s):")

        for license_id in sorted(license_info["libraries"][library]["licenses"]):
            license_name = license_info["licenses"][license_id]["name"]
            license_url = license_info["licenses"][license_id]["url"]

            # if the url ends in .html.erb, we strip it so it works with the docs site.
            # we also will append a "/"
            # this is kinda-hacky, but not sure of a better solution
            erb_index = license_url.find(".html.erb")

            if erb_index != -1:
                license_file = os.path.join(license_reviewer_metafile_path, license_url)

                for line in read_list_from_file(license_file):
                    lines.append("    "+line)

            else:
                lines.append("    "+license_name+" <"+license_url+">")
        lines.append("")

    current_year = datetime.now().year

    lines.append("----------------------------------------------------------------")
    lines.append("")
    lines.append("All other components of this product are: Copyright (c) 2010-"+str(current_year)+" New Relic, Inc. All rights reserved.")
    lines.append("")
    lines.append("Certain inventions disclosed in this file may be claimed within patents owned or patent applications")
    lines.append("filed by New Relic, Inc. or third parties. Subject to the terms of this notice, New Relic grants you")
    lines.append("a nonexclusive, nontransferable license, without the right to sublicense, to (a) install and execute")
    lines.append("one copy of these files on any number of workstations owned or controlled by you and (b) distribute")
    lines.append("verbatim copies of these files to third parties. As a condition to the foregoing grant, you must")
    lines.append("provide this notice along with each copy you distribute and you must not remove, alter, or obscure")
    lines.append("this notice.")
    lines.append("")
    lines.append("All other use, reproduction, modification, distribution, or other exploitation of these")
    lines.append("files is strictly prohibited, except as may be set forth in a separate written license agreement")
    lines.append("between you and New Relic. The terms of any such license agreement will control over this notice. The")
    lines.append("license stated above will be automatically terminated and revoked if you exceed its scope or violate")
    lines.append("any of the terms of this notice.")
    lines.append("")
    lines.append("This License does not grant permission to use the trade names, trademarks, service marks, or product")
    lines.append("names of New Relic, except as required for reasonable and customary use in describing the origin of")
    lines.append("this file and reproducing the content of this notice. You may not mark or brand this file with any")
    lines.append("trade name, trademarks, service marks, or product names other than the original brand (if any) provided")
    lines.append("by New Relic.")
    lines.append("")
    lines.append("Unless otherwise expressly agreed by New Relic in a separate written license agreement, these files")
    lines.append("are provided AS IS, WITHOUT WARRANTY OF ANY KIND, including without any implied warranties of")
    lines.append("MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE, or NON-INFRINGEMENT. As a condition to your")
    lines.append("use of these files, you are solely responsible for such use. New Relic will have no liability to you")
    lines.append("for direct, indirect, consequential, incidental, special, or punitive damages or for lost profits or")
    lines.append("data.")

    return lines 

def write_lines_to_file_if_diff(lines, filename):
    tmp_file = tempfile.NamedTemporaryFile("w", delete=False)

    for line in lines:
        tmp_file.write(line+"\n")

    tmp_file.close()

    replace_file_if_diff(tmp_file.name, filename)

    os.remove(tmp_file.name)


def gen_installer_doc_command(args):
    print("Generating doc file for installer...\n")

    noreview = args.noreview
    if not noreview:
        # first, let's do a review to make sure all files, libraries, and licenses are correct
        # and up-to-date
        review_results = review_command(args)
        if review_results != 0:
            print("[FAIL] could not generate documentation because license review failed")
            return review_results

    license_info_file = os.path.join(license_reviewer_metafile_path, license_info_filename)
    license_info = load_license_info_file(license_info_file)

    output_filename = args.output

    file_lines = gen_installer_doc(license_info)
    write_lines_to_file_if_diff(file_lines, output_filename)

    return 0

def gen_docs_site_doc_command(args):
    print("Generating doc files for docs site...\n")

    noreview = args.noreview
    if not noreview:
        # first, let's do a review to make sure all files, libraries, and licenses are correct
        # and up-to-date
        review_results = review_command(args)
        if review_results != 0:
            print("[FAIL] could not generate documentation because license review failed")
            return review_results

    license_info_file = os.path.join(license_reviewer_metafile_path, license_info_filename)
    license_info = load_license_info_file(license_info_file)

    output_filename = args.output

    file_lines = gen_docs_site_doc(license_info)
    write_lines_to_file_if_diff(file_lines, output_filename)

    return 0

def load_license_info_file(license_info_file):
    json_file = open(license_info_file)

    license_info = json.load(json_file)

    json_file.close()

    return license_info


def save_license_info_file(license_info_file, license_info):
    json_file = open(license_info_file, "w")

    json.dump(license_info, json_file, sort_keys=True, indent=4, separators=(',', ': '))

    json_file.flush()
    json_file.close()


def load_source_map_file(license_source_map_file):
    json_file = open(license_source_map_file)

    license_source_map = json.load(json_file)

    json_file.close()

    return license_source_map

def save_license_source_map_file(license_source_map_file, license_source_map):
    json_file = open(license_source_map_file, "w")

    json.dump(license_source_map, json_file, sort_keys=True, indent=4, separators=(',', ': '))

    json_file.flush()
    json_file.close()

def get_ignored_files(ignore_file):
    ignored_files = {}

    f = open(ignore_file, "U")

    for line in f.read().splitlines():
        relative_path = line.strip()

        # strip out comments
        comment_index = line.find("#")
        if comment_index != -1:
            relative_path = line[:comment_index].strip()
            
        if len(relative_path) > 0:
           full_path = os.path.normpath(relative_path)
           ignored_files[full_path] = full_path

    f.close()

    return ignored_files

def get_git_repo_files():
    # TODO: deal with the b' that gets outputted here
    # get a map of all the files that are in the git repo. We're only going to pay attention to those
    git_output = subprocess.check_output(["git", "ls-files"])
    file_list = str(git_output).split("\n")
    repo_files = {}

    # convert to map for fast lookup
    for file_name in file_list:
        norm_path = os.path.normpath(file_name)
        repo_files[norm_path] = norm_path

    return repo_files

def get_flattened_file_list(root_dir, ignored_files, repo_files):
    flattened_file_list = []

    # now check the source files
    for root, dirs, files in os.walk(root_dir):
        for name in files:
            # get the path to the file from the root_dir since we normalize everything from there
            full_path = os.path.normpath(os.path.join(root, name))

            if full_path in ignored_files:
                pass
            elif full_path not in repo_files:
                pass
            else:
                flattened_file_list.append(full_path)

        # note: the directories can't be removed while looping over them or the list
        # gets funky/out of sync
        dirs_to_remove = []

        for name in dirs:
            full_path = os.path.normpath(os.path.join(root, name))

            # if this is a directory we're ignoring, don't traverse it
            if full_path in ignored_files:
                dirs_to_remove.append(name)

        # remove any ignored directories from the list to be traversed
        for dir_to_remove in dirs_to_remove:
            dirs.remove(dir_to_remove)

    return flattened_file_list 

def check_for_missing_source_files(license_source_map):
    # verify that all files in our license_source_map file actually exist in the working dir.

    errors = []

    for source_file in license_source_map:
        # verify that the source file actually exists
        if not os.path.exists(source_file):
            full_path = os.path.normpath(source_file)
            errors.append(full_path)

    return errors

def check_for_orphaned_libraries(license_info, license_source_map):
    # checks for libraries that are no longer referenced by any source files

    errors = []

    # transpose the license_source_map file such that the key is the
    # library name and the values are a list of source files
    # we do this so we can easily do a check to see that all libraries
    # in the libraries file are actually in use
    source_files_by_library = {}
    for source_file in license_source_map:
        for library in license_source_map[source_file]["libraries"]:
            if library not in source_files_by_library:
                source_files_by_library[library] = []

            source_files_by_library[library].append(source_file)

    # check that all the libraries in our source file reference licenses that are also in our source file
    for library in license_info["libraries"]:
        if library not in source_files_by_library or len(source_files_by_library[library]) == 0:
            errors.append(library)

    return errors

def check_for_missing_licenses(license_info):
    # checks for libraries that reference licenses that aren't in our licenses list
    errors = []

    for library in license_info["libraries"]:
        for license in license_info["libraries"][library]["licenses"]:
            if license not in license_info["licenses"]:
                errors.append(library)

    return errors

def check_local_license_urls(license_info):
    # for all licenses in our source file that reference urls by a file path,
    # check that we have a copy of the file that is referenced
    errors = []

    for license in license_info["licenses"]:
        # the url can either be a full remote url or a relative path on the new relic site.
        # decode it and see what type it is
        url = license_info["licenses"][license]["url"]
        if is_url(url):
            pass
        else:
            # if it's not a remote url, let's make sure we have a copy of the
            # license file locally
            license_file = os.path.join(license_reviewer_metafile_path, url)

            if not os.path.exists(license_file):
                errors.append(license_file)

    return errors

def check_for_orphaned_licenses(license_info):
    errors = []

    # check that all the licenses in our source file have valid references
    for license in license_info["licenses"]:
        license_in_use = False
        for library in license_info["libraries"]:
            for lib_license in license_info["libraries"][library]["licenses"]:
                if lib_license == license:
                    license_in_use = True
                    break
            if license_in_use:
                break

        if not license_in_use:
            errors.append(license)
 
    return errors

def check_for_source_files_not_in_manifest(flattened_file_list, license_source_map):
    errors = []

    for full_path in flattened_file_list:
        if full_path not in license_source_map:
            errors.append(full_path)

    return errors

def check_for_changed_source_files(flattened_file_list, license_source_map):
    errors = []

    for full_path in flattened_file_list:
        if full_path in license_source_map:
            libraries = license_source_map[full_path]["libraries"]

            # if the file only references one library, and it's "New Relic"
            # then don't do the hash check. We don't care if it has changed
            if len(libraries) == 1 and libraries[0] == new_relic_library:
                pass
            else:
                # get the old hash key from our manifest
                old_hash_key = license_source_map[full_path]["hash"]
 
                # get a hash of the existing file
                hash_key = hash_file(full_path)
 
                if hash_key != old_hash_key:
                    errors.append(full_path)

    return errors

def print_and_write(line, open_file):
    print(line)
    open_file.write(line+"\n")

def print_and_write_errors(subject, errors, open_file):
    if len(errors) > 0:
        print_and_write("[FAIL] "+subject+" ("+str(len(errors))+" errors)", open_file)

        for error in sorted(errors):
            print_and_write("  "+error, open_file)
    
def write_list_to_file(file_name, contents):
    f = open(file_name, "w")

    for line in contents:
        f.write(line+"\n")

    f.flush()
    f.close()

def read_list_from_file(filename):
    lines = []

    f = open(filename, "U")

    lines = f.read().splitlines()

    f.close()

    return lines

def replace_file_if_diff(source_filename, dest_filename):
    if not os.path.exists(dest_filename):
        # TODO: test this case
        shutil.copy(source_filename, dest_filename)

    if not filecmp.cmp(source_filename, dest_filename):
        shutil.copy(source_filename, dest_filename)

def hash_file(file_name):
    f = open(file_name, "rb")

    m = hashlib.md5()

    while True:
        chunk = f.read(8192)
        
        if not chunk:
            break
        m.update(chunk)

    f.close()

    return str(m.hexdigest())

def is_url(test_str):
    # shamelessly stole this regex from django
    url_regex = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    return url_regex.match(test_str)

def load_environ():
    global license_reviewer_metafile_path

    errors = []

    if "LICENSE_REVIEWER_METAFILE_PATH" in os.environ:
        license_reviewer_metafile_path = os.path.realpath(os.environ["LICENSE_REVIEWER_METAFILE_PATH"])
        print("metafile path: "+license_reviewer_metafile_path)
    else:
        errors.append("LICENSE_REVIEWER_METAFILE_PATH environment variable must be set. It should be a path relative to the repo root, e.g. Agent\\thirdparty")

    for error in errors:
        print("[ERROR] "+error)

    return len(errors)

def load_config_file():
    global projectname
    global permalink

    errors = []

    license_config_file = os.path.join(license_reviewer_metafile_path, license_config_filename)

    config = ConfigParser.ConfigParser()

    if os.path.exists(license_config_file):
        config.readfp(open(license_config_file))

        try:
            projectname = config.get("LicenseReviewerConfig", "projectname")
            if len(projectname) == 0:
                errors.append("projectname variable not set in: "+license_config_file)
    
            permalink = config.get("LicenseReviewerConfig", "permalink")
            if len(permalink) == 0:
                errors.append("permalink variable not set in: "+license_config_file)
    
        except ConfigParser.NoOptionError as e:
            errors.append("error reading: "+license_config_file)

    else:
        errors.append(license_config_file+" file does not exist")

    for error in errors:
        print("[ERROR] "+error)

    return len(errors)

def get_and_run_command():
    parser = argparse.ArgumentParser(description="Ensures that all 3rd party license files are properly accounted for")

    subparsers = parser.add_subparsers()

    review_command_parser = subparsers.add_parser("review", description="Review source files for any license violations")
    review_command_parser.set_defaults(func=review_command)

    add_license_command_parser = subparsers.add_parser("addlicense", description="Add a new license to the license info file")
    add_license_command_parser.add_argument("id", help="Unique ID for the license")
    add_license_command_parser.add_argument("name", help="Name of the license")
    add_license_command_parser.add_argument("url", help="URL for the license")
    add_license_command_parser.set_defaults(func=add_license_command)

    add_library_command_parser = subparsers.add_parser("addlibrary", description="Add a new library to the library info file")
    add_library_command_parser.add_argument("id", help="Unique ID for the library")
    add_library_command_parser.add_argument("name", help="Name of the library")
    add_library_command_parser.add_argument("url", help="URL for the library. Set to \" \" if one doesn't exist")
    add_library_command_parser.set_defaults(func=add_library_command)

    set_licenses_command_parser = subparsers.add_parser("setlicense", description="Map a given library file to a specified license")
    set_licenses_command_parser.add_argument("libraryid", help="The library you want to set licenses on")
    set_licenses_command_parser.add_argument("licenseid", nargs="+", help="Licenses used by the library")
    set_licenses_command_parser.set_defaults(func=set_licenses_command)

    set_libraries_command_parser = subparsers.add_parser("setlibrary", description="Map a given source file to a specified 3rd party library")
    set_libraries_command_parser.add_argument("source", help="The source file you want to set libraries on")
    set_libraries_command_parser.add_argument("libraryid", nargs="+", help="Libraries used by the source file")
    set_libraries_command_parser.set_defaults(func=set_libraries_command)

    gen_installer_doc_command_parser = subparsers.add_parser("geninstallerdoc", description="Generates a plain text file to be used by an installer based on current license information")
    gen_installer_doc_command_parser.add_argument("--noreview", dest="noreview", action="store_true", help="Do not do a license review before generating the document. WARNING: only do this if you know the metafiles are correct. This should only be used for automation purposes.")
    gen_installer_doc_command_parser.add_argument("output", help="The output file that will be replaced with the new installer doc license file")
    gen_installer_doc_command_parser.set_defaults(func=gen_installer_doc_command)

    gen_docs_site_doc_command_parser = subparsers.add_parser("gendocssitedoc", description="Generates a license file to be used by the New Relic docs site based on current license information")
    gen_docs_site_doc_command_parser.add_argument("--noreview", dest="noreview", action="store_true", help="Do not do a license review before generating the document. WARNING: only do this if you know the metafiles are correct. This should only be used for automation purposes.")
    gen_docs_site_doc_command_parser.add_argument("output", help="The output file that will be replaced with the docs site doc license file")
    gen_docs_site_doc_command_parser.set_defaults(func=gen_docs_site_doc_command)

    remove_source_command_parser = subparsers.add_parser("removesource", description="Removes a source file from the license_source_map manifest file")
    remove_source_command_parser.add_argument("source", help="The source file to remove from the manifest file")
    remove_source_command_parser.set_defaults(func=remove_source_command)

    args = parser.parse_args()

    exit_code = 0

    if len(sys.argv) == 1:
        parser.print_help()
    else:
        start_time_ms = int(round(time.time() * 1000))
        exit_code = args.func(args)
        end_time_ms = int(round(time.time() * 1000))

        print("Time to execute command: "+str(end_time_ms - start_time_ms)+"ms")
        print("Exiting with code: "+str(exit_code))

    return exit_code

def get_git_root_dir():
    git_root_dir = ""

    # make sure we're at the top of the git working directory
    git_output = subprocess.check_output(["git", "rev-parse", "--show-toplevel"])
    file_list = str(git_output).split("\\n")

    count = 0
    for f in file_list:
        f_clean = f
        if count == 0:
            # note: this is a bit of a hack. not sure why lines start with b'
            if f.startswith("b'"):
                f_clean = f[2:]
                git_root_dir = f_clean.strip()
            else:
                git_root_dir = f.strip()
        else:
            break

    return git_root_dir

def main():
    global script_dir

    working_dir = os.path.realpath(os.getcwd())
    script_dir = os.path.realpath(os.path.dirname(__file__))

    if load_environ() != 0:
        sys.exit(-1)

    if load_config_file() != 0:
        sys.exit(-1)

    git_root_dir = get_git_root_dir()

    if git_root_dir == "":
        print("git not in path or not working correctly")        
        sys.exit(-1)

    # make sure the user runs this script from a git repo root directory
    # otherwise things get weird when they start passing in files relative to their
    #   original working directory
    if os.path.realpath(working_dir) != os.path.realpath(git_root_dir):
        print("[ERROR] script must be run from: "+git_root_dir)
        sys.exit(-1)

    sys.exit(get_and_run_command())

if __name__ == "__main__":
    main()
