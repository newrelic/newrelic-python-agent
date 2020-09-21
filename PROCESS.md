Development Processes
=====================

This document lists various information related to development on and
release of the Python agent.

Setting the Agent Version
-------------------------

The agent version is keyed off the version attribute in the file::

    newrelic/__init__.py

The agent uses a version number consisting of 4 digits in the form
``A.B.C.D``. These represent:

* Major version number.
* Minor version number.
* Patch level revision number.
* Build number.

When setting the version attribute in the ``newrelic/__init__.py`` file
the string should only list the first three number components. That is,
``A.B.C``. The build number will be automatically substituted.

In the case of working on a local development box the build number will
always be ``0``. For a build performed from Jenkins it will be set to the
Jenkins job build number.

Release Numbering Scheme
------------------------

Since version ``2.0.0`` of the Python agent an odd/even numbering scheme
has been used.

What this means is that the minor revision number being odd indicates that
it is an internal development version. An even number for the minor revision
number indicates an official release version.

Internal development versions would normally never be handed out to any
customers. An exception may be made if the only way to determine if a bug
fix is working is for the customer themselves to test it prior to an
official release being made. Approval needs to be sought before making
available any development version.

Only versions with an even number for the minor version number should ever
be placed up for download via PyPi or the ``releases`` directory of the
New Relic download site for the Python agent.

In either case, only tarballs created from the Jenkins jobs for ``develop``
and ``master`` branches of the Python agent repository should ever be used
when providing versions to customers.

Verifying Package Builds
------------------------

To build the Python agent for release it is necessary to use the script::

    build.sh

The script expects to be able to find the ``python`` executable in your
``PATH`` or that of the Jenkins user when this script is executed on the
Jenkins build slaves.

The result of running this script will be a tar ball placed in the ``dist``
sub directory. It will be named with the form::

    newrelic-A.B.C.D.tar.gz

The ``A.B.C`` component of the version will come from the version string
defined in the ``newrelic/__init__.py`` file. These correspond to the
major, minor and patch level revision numbers as explained above.

The ``D`` component of the version is the build number and will be ``0``
for local development or the Jenkins build number when the script is run
under Jenkins.

The build script will also run source code license validation checks to
ensure that all code files have been marked up appropriately as to what
license applies to them.

After creating the release package, you can verify that it can be installed
into a Python virtual environment by running::

    pip install dist/newrelic-A.B.C.D.tar.gz

This is necessary as the creation of the tar ball only collects the files
into a Python source package and doesn't actually compile any of the Python
code files into byte code nor compile any C extensions.

Jenkins Build Jobs
------------------

Although the ``build.sh`` script can be run on a local development system,
only tar balls produced by the Jenkins build jobs should ever be handed
out to customers.

The jenkins job [build-and-archive-package][build-and-archive] is used to
produce the tar ball for an official release and upload it to Artifactory. It
currently only builds from the master branch.

For more details on the Jenkins jobs and configuration, see the [Jenkins README][readme].

[build-and-archive]: https://python-agent-build.pdx.vm.datanerd.us/view/PY_Deploy/job/build-and-archive-package/
[readme]: jenkins/README.md

Downloadable Releases
---------------------

Official releases are made available via the Python Package Index (PyPi).
The page for the New Relic Python agent is:

* https://pypi.python.org/pypi/newrelic

A second copy of the official releases are also available from our own
download site at:

* http://download.newrelic.com/python_agent/release/

Details for obtaining access to our account on PyPi can be found at:

* [Python Agent Managing the Package Index](https://newrelic.atlassian.net/wiki/display/eng/Python+Agent+Managing+The+Package+Index)

Details for obtaining access to our own download site can be found at:

* [Python Agent Managing The Download Site](https://newrelic.atlassian.net/wiki/display/eng/Python+Agent+Managing+The+Download+Site)

In cases where it is necessary to provide a test version to a customer prior
to an official release, these would generally be made available via:

* http://download.newrelic.com/python_agent/testing/

Pre-Release Steps
-----------------

0. Review this document and update it with any required changes. Create a pull request
if necessary.

1.  Create drafts of any new or changed documentation. Notify the "Documentation"
heroes about each changed document, and let them know when we plan to release, so
that they can plan to release the new documentation immediately after we release.

    Getting to "final copy" on the documentation can take a bit of back and forth,
so the earlier this step can be done, the better.

2.  Draft the release notes. These are
hosted at: https://docs.newrelic.com/docs/release-notes/agent-release-notes/python-release-notes.

    To create a draft of the release notes, log in to the documentation site
(through Onelogin), go to the release notes for the previous release, and
click the 'Clone Content' link. Be sure to take 'Clone of' out of the page title.
There are also at least three places where the version number must be updated in the
page. Increment the build number by one from the previous release. Most likely,
that will be the build number for the release version. If it isn't, it will
need to be changed during the release process.

3.  Draft the Support notes for the release. This is where we describe key things that
Support will need to know about the release, but aren't necessarily in the public
documentation, such as specific problems to look out for, new configuration settings,
etc. Include links to the release notes and any changed or new documentation.

Performing a Standard Release
-----------------------------

Once work has finished on a development version and all testing has been
performed and the code approved for release, the following steps should be
carried out to do the actual release.

1. Create a new google spreadsheet and share it with the team. Add items from this document as checklist items. This command will gather the first two lines of each numbered item and copy to the clipboard.

    ```
    cat PROCESS.md | grep -A1 '^\d' |
    awk '/--/{if (NR!=1)print "";next}{printf $0}END{print "";}' |
    sed 's/$/.../' | pbcopy
    ```

2. Merge the external repo's ``main`` branch into develop by creating a branch ``merge-external-repo`` off of the ``develop`` branch.
This can be done with ``git remote add external https://github.com/newrelic/newrelic-python-agent.git``,
``git fetch external``, ``git merge external/main``. Open a PR as described below.

    1. The body of the PR should contain the text `[skip-ci]` so that
    jenkins doesn't trigger a job against this PR to verify its contents
    2. The PR should be titled:
        ```
        Merge external/main into develop for release A.B.C
        ```

[integration-master]: https://python-agent-build.pdx.vm.datanerd.us/view/PY_Tests/job/_INTEGRATION-TESTS-master_/
[unit-master]: https://python-agent-build.pdx.vm.datanerd.us/view/PY_Tests/job/_UNIT-TESTS-master_/

3. Create a PR from ``develop`` to ``master``. The pull request will contain
the following:

    1. The body of the PR should contain the text `[skip-ci]` so that
    jenkins doesn't trigger a job against this PR to verify its contents
    2. The PR should be titled:
        ```
        Merge develop into master for release A.B.C
        ```
    3. Get a buddy to sidekick and merge the PR from ``develop`` to ``master``.

    * Note: Merging the PR will trigger the following Jenkins jobs. Confirm they
    have triggered. If not, run them manually. In a later step these will be
    checked and confirmed to have passed successfully.

        1. [`_INTEGRATION-TESTS-master_`][integration-master]
        2. [`_UNIT-TESTS-master_`][unit-master]

4. Switch back to the ``develop`` branch and perform a merge from
``master`` back into the ``develop`` branch.

    * Note: This is to synchronize the two branches so git doesn't keep tracking them
    as completely parallel paths of development with consequent strange results
    when trying to compare branches.
    <br>

    1. Confirm that you are on the `develop` branch
    2. Run: `git fetch && git merge origin/master`
        * Confirm this command results in a fast-forward operation, as noted on stdout.
        Stop and debug if it does not.

5. Push the ``develop`` branch back to the GIT repo.

    From the command line:

        git push origin develop

[releases]: https://github.com/newrelic/newrelic-python-agent/releases

6. Tag the release in the ``develop`` branch on the GIT repo with tag of
the form ``vA.B.C`` and ``vA.B.C.D``, where ``D`` is the build number. This
value is the next number in the sequence of releases. Refer to [github releases][releases].

    From the command line:

        # Create tags
        git tag vA.B.C
        git tag vA.B.C.D

        # Tags don't get pushed to GHE automatically, so you must do it.
        git push origin vA.B.C
        git push origin vA.B.C.D

7. Reconcile external repo with internal repo. Any changes on the internal repo that need to be ported out to the external repo
should be committed with ``newrelic <opensource@newrelic.com>`` as the author.

    .gitconfig:

    ```
    [user]
        name = newrelic
        email = opensource@newrelic.com
    ```

    While there aren't any standard steps involved in this process, the goal is
    to match the state of the external repo to the state of the internal repo.

    Steps that may be taken to achieve that goal:

    * git diff to retrieve files that have changed since last release
    * copy files from internal repo to external repo

8. Draft release notes on public github. The title and tag should both be set to the release version prefixed by a v (example v5.20.0.149).
The release notes should contain a link to the full release notes on the docs page. Click "save draft".

9. Pause here, regroup before continuing

    1. Wait for release notes to be completed
    2. Check in with the rest of the team (mention @here in #python-agent-dev)

10. Publish the release notes on public github. Naviagate to [github releases][releases] and click on the draft. Click "publish release".

11. Update the ``python_agent_version`` configuration to ``A.B.C.D`` in APM
systems configuration pages at: https://rpm-admin.newrelic.com/admin/system_configurations
and https://rpm-admin.eu.newrelic.com/admin/system_configurations.

    If we need to notify existing users to update their older agents, also
update the ``min_python_agent_version`` to ``A.B.C.D``.

    Additionally, if we have a new feature in the agent, and we want to make
sure APM is gated to the correct version, put in a PR to the [Agent Feature
Service](https://source.datanerd.us/APM/agent_feature_service).

12. Make the "Release Notes" public. (You don't need to have the Documentation
Team do this step. We have the authority to publish release notes.)

13. Contact the Documentation team so they can release any new or changed
public documentation.

14. Send an email to ``agent-releases@newrelic.com`` notifying them about
the release. This will go to agent-team, partnership-team, and other
interested parties. Include a copy of the public release notes, plus a
separate section if necessary with additional details that may be relevant
to internal parties.

15. Send an email to ``gts-python@newrelic.com`` with the Support notes
drafted in the pre-release steps.

16. Notify Python Agent Slack channel that release is out! ``@channel Python Agent 5.20.0.149 is released!``

17. Make sure that all JIRA stories associated with the release version have
been updated as having been released.


Performing a Hotfix Release
---------------------------

A "hotfix" release is one that contains an urgent bug fix that needs to be released before the
`develop` branch is ready for release. A `hotfix` branch is created off of the `master` branch, and
once it is released, the `hotfix` branch is merged back into the `develop` branch.

The procedure for preparing a hotfix release differs in some ways from a normal release.

1. Create a hotfix branch

        # Make sure master is up-to-date
        $ git checkout master
        $ git pull master

        # Create a hotfix branch with the version number as the name. Increment the "patch
        # number" in the version string (the 3rd element).
        $ git-flow hotfix start 2.80.1

2. Add a commit with the bugfix.

3. Add a commit to bump the "patch number" in the version in ``newrelic/__init__.py``. The commit
   message should be:

        Increment version to 2.80.1 for hotfix release.

4. Run `./build.sh` locally to run license validation script and ensure package builds.

5. Run `./tests.sh` locally.

6. Create a PR against the `master` branch.

7. Sidekick and merge the PR into the `master` branch.

Once these steps have been completed, begin following the standard release procedure, starting at
step 11 (merge `master` back into `develop`).


Creating a Custom Build for a Customer
--------------------------------------

When providing a custom build of the agent to a customer, we will typically build off of the `develop` branch. (If we have created a custom branch for the customer rather than using `develop`, adjust the instructions below accordingly.)

1. On Jenkins (JAAS-1), manually edit the "build-and-archive" job through the Jenkins UI so that it builds from the `develop` branch. (Right now, it can only build from `master`.) This will produce a version number with an odd minor number, which indicates that it is not a public release. It will also add the Jenkins build job number as the fourth element of the version number, just like we have for regular releases. It's important to build the job on Jenkins so that we archive this version of the agent. Even though it is not a public release, we still want to archive any version of the agent which we release in any way.

2. After running the "build-and-archive" job successfully, revert the change you made in step #1: re-edit the job so that it will build from the `master` branch for future runs.

3. Tag the latest commit on `develop`. The tag will contain the version in the same format as our normal release. For example, the tag might be: `v2.79.0.59`. Verify that the minor version ("79") is an odd number, and that the build number ("59") matches the build number from the Jenkins job.

        $ git tag v2.79.0.59

4. Push the tag to GHE.

        $ git push origin v2.79.0.59

5. Download the tarball from Artifactory. Run manual smoke tests to verify that the agent is working as expected. Manually testing with an application is a good idea. Running `newrelic-admin validate-config newrelic.ini` is also helpful.

6. Work with the Product Manager to send the custom build to the customer.

Undeploying an Agent
--------------------

Removing an agent is something that should be carefully considered prior taking
action. Keep in mind that undeploying an agent will very likely result in
broken customer builds. Those problems may exceed the scope of the original
issue. When practical, it's best to "roll forward" by redeploying the previous
release as a new version.

1. Notify the team's manager and group lead prior to proceeding with unpublishing the agent. If after hours, page the manager on-call.

2. Notify the #python-agent room with the following message:
   ```
   @channel The process to unpublish agent version A.B.C.D is starting.
   ```

3. Replace content from the [release notes](https://docs.newrelic.com/docs/release-notes/agent-release-notes/python-release-notes) with "Removed" and republish them.

4. Notify the #documentation channel hero and ask them to unpublish the [release notes](https://docs.newrelic.com/docs/release-notes/agent-release-notes/python-release-notes)

5. Update the ``python_agent_version`` configuration to ``A.B.C.D`` in APM [systems configuration page](https://rpm-admin.newrelic.com/admin/system_configurations) and [eu systems configuration page](https://rpm-admin.eu.newrelic.com/admin/system_configurations) to point to the previous agent version.

6. Run the [undeploy-from-s3](https://python-agent-build.pdx.vm.datanerd.us/view/PY_Deploy/job/undeploy-from-s3/) job on Jenkins using the most recent agent version. Use the full version number (in the form of ``A.B.C.D``).

7. Verify that the bad version is removed from the [downloads](http://download.newrelic.com/python_agent/release/) site.

8. Log in to [pypi](https://pypi.org/account/login/) using the credentials stored in lastpass under the Shared #python-agent folder.

9. Navigate to the release page https://pypi.org/manage/project/newrelic/release/A.B.C.D (replace ``A.B.C.D`` with the version number of the bad version)

10. Click the Delete Release button. **There is no going back** Once a package has been removed from PyPI, it can not be redeployed at the same version number. After this point, the procedure must be completed.

11. Verify that pip install works and that [legacy pypi](https://pypi.python.org/pypi?%3Aaction=pkg_edit&name=newrelic) shows the previous package version as "Hide? No" (when a new version is deployed, the previous version will be automatically hidden). Verify that `pip install --no-cache newrelic` now installs the correct version.

12. Notify the #python-agent room with the following message:
    ```
    @channel Agent version A.B.C.D removed from PyPI and downloads.newrelic.com
    ```

13. Update [docker-state](https://source.datanerd.us/container-fabric/docker-state/blob/master/requirements.txt) to point to the previously released agent version.
