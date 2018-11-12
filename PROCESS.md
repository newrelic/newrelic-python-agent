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

2. Check out the ``develop`` branch of the Python agent repository and
update the version number in ``newrelic/__init__.py`` for the release.

    * Note: With our odd/even numbering scheme, this means you should be
    incrementing the ``B`` component of the ``A.B.C`` version number from
    the odd number used during development to the even number used for the
    release.

3. Update ``CHANGELOG.rst`` to change ``unreleased`` to the to be released
version including today's date.

    ```
    2.94.0 (2017-09-19)
    -------------------
    ```

4. Perform any other final adhoc local tests deemed necessary for the release.

5. Create a release branch with `git checkout -b release/vA.B.C`

6. Commit change made to ``newrelic/__init__.py`` and ``CHANGELOG.rst``
into the release branch you just created. Format the commit message like this:

    ```
    Increment version to A.B.C for release.
    ```

7. Push the release/vA.B.C branch up and create a pull request. The pull
request will contain the following:

    1. The PR will be merged against the ``develop`` branch
    2. The body of the PR should contain the text `[skip-ci]` so that
    jenkins doesn't trigger a job against this PR to verify its contents
    3. Get someone to add the `sidekick:approved` label and merge
        * Note: The `sidekick:approved` label is necessary because no changes
        can be added to the code without being side-kick approved. Security
        will keep sending you emails if you don't do this.

8. Create a PR from ``develop`` to ``master``. The pull request will contain
the following:

    1. The body of the PR should contain the text `[skip-ci]` so that
    jenkins doesn't trigger a job against this PR to verify its contents
    2. The PR should be titled:
        ```
        Merge develop into master for release A.B.C
        ```

9. Get a buddy to sidekick and merge the PR from ``develop`` to ``master``.

    * Note: Merging the PR will trigger the following Jenkins jobs. Confirm they
    have triggered. If not, run them manually. In a later step these will be
    checked and confirmed to have passed successfully.

        1. [`_INTEGRATION-TESTS-master_`](https://python-agent-build.pdx.vm.datanerd.us/view/PY_Tests/job/_INTEGRATION-TESTS-master_/)
        2. [`_UNIT-TESTS-master_`](https://python-agent-build.pdx.vm.datanerd.us/view/PY_Tests/job/_UNIT-TESTS-master_/)

10. Switch back to the ``develop`` branch and perform a merge from
``master`` back into the ``develop`` branch.

    * Note: This is to synchronize the two branches so git doesn't keep tracking them
    as completely parallel paths of development with consequent strange results
    when trying to compare branches.
    <br>

    1. Confirm that you are on the `develop` branch
    2. Run: `git fetch && git merge origin/master`
        * Confirm this command results in a fast-forward operation, as noted on stdout.
        Stop and debug if it does not.

11. Push the ``develop`` branch back to the GIT repo.

    From the command line:

        git push origin develop

12. Tag the release in the ``develop`` branch on the GIT repo with tag of
the form ``vA.B.C`` and ``vA.B.C.D``, where ``D`` is the build number. This
value is the next number in the Build History section of
[build-and-archive-package][build]. Push the tags to Github master.

    From the command line:

        # Create tags
        git tag vA.B.C
        git tag vA.B.C.D

        # Tags don't get pushed to GHE automatically, so you must do it.
        git push origin vA.B.C
        git push origin vA.B.C.D

[build]: https://python-agent-build.pdx.vm.datanerd.us/view/PY_Deploy/job/build-and-archive-package/


13. Create a branch off ``develop`` to increment the version number for
development by running `git checkout -b increment-development-version-A.B.C`

    Increment ``B`` to the next minor version. With our odd/even numbering
    scheme, ``B`` should always be odd after this change.

14. Update the version number in``newrelic/__init__.py`` by incrementing ``B``
as described in the previous step.

    Format the commit message like this:

        Increment version to A.B.C for development.

15. Push the `increment-development-version-A.B.C` branch from steps #13/#14.

    From the command line:

        git push origin increment-development-version-A.B.C

16. Create a PR for merging in the `increment-development-version-A.B.C` branch into ``develop``. The body
of the pull request should contain the text `[skip-ci]` so that jenkins doesn't
trigger a job against this PR to verify its contents.

17. Get a buddy to sidekick and merge the `increment-development-version-A.B.C` PR.

18. In Jenkins, build and upload the release to Artifactory.

    1. Log in and go to [build-and-archive-package][build].
    2. From the menu on the left select "Build with Parameters".
    3. Type in the version number INCLUDING the next build that will be created when you push the build button.
    4. Push the build button.

    This will build and upload the package to artifactory.
    If the build fails, you must add a new tag for `vA.B.C.D` (see the previous step).

[build]: https://python-agent-build.pdx.vm.datanerd.us/view/PY_Deploy/job/build-and-archive-package/

19. Check Artifactory upload

    1. Go to [Artifactory][artifactory].
    2. In the navigator on the left, go to ``pypi-newrelic``->``A.B.C.D``->``newrelic-A.B.C.D.tar.gz``. Check that the Checksum for MD5 says ""(Uploaded: Identical)"".
    3. Download the tarball and validate that a `pip install /path/to/package` works.
    4. Confirm that a `newrelic-admin validate-config` test runs okay.
    5. Create a small test app and confirm that starting it with `newrelic-admin run-program` runs okay.

[artifactory]:https://artifacts.datanerd.us/webapp/#/artifacts/browse/tree/General/pypi-newrelic/newrelic

20. Pause here, regroup before continuing

    1. Wait for release notes to be completed
    2. Wait for [`_INTEGRATION-TESTS-master_`][integration-master] and [`_UNIT-TESTS-master_`][unit-master] tests to be completed successfully
    3. Check in with the rest of the team (mention @team in slack)

[integration-master]: https://python-agent-build.pdx.vm.datanerd.us/view/PY_Tests/job/_INTEGRATION-TESTS-master_/
[unit-master]: https://python-agent-build.pdx.vm.datanerd.us/view/PY_Tests/job/_UNIT-TESTS-master_/

21. Upload from Artifactory to PyPI

    1. Go back to Jenkins, and select the other project, [deploy-to-pypi][deploy-pypi].
    2. From the menu on the left select "Build with Parameters".
    3. From the drop down menu `PYPI_REPOSITORY`, select pypi. Type in the version number, including the build in the `AGENT_VERSION` box.
    4. Push the build button.
    5. Go to [PyPI][pypi] and check that the version uploaded.
    6. Validate that ``pip install`` of package into a virtual environment works.
    7. Validate that a ``newrelic-admin validate-config`` test runs okay.
    8. Create a small test app and confirm that starting it with `newrelic-admin run-program` runs okay.

[pypi]: https://pypi.python.org/pypi/newrelic
[deploy-pypi]: https://python-agent-build.pdx.vm.datanerd.us/view/PY_Deploy/job/deploy-to-pypi/

22. Upload from Artifactory to Amazon S3

    1. Go back to Jenkins, and select the other project, [deploy-to-s3][deploy-s3].
    2. From the menu on the left select "Build with Parameters".
    3. From the drop down menu `S3_RELEASE_TYPE`, select "release". Type in the version number, including the build in the `AGENT_VERSION` box.
    4. Push the build button.
    5. Make sure the job finishes successfully.

[deploy-s3]: https://python-agent-build.pdx.vm.datanerd.us/view/PY_Deploy/job/deploy-to-s3/

23. Update the ``python_agent_version`` configuration to ``A.B.C.D`` in APM
systems configuration pages at: https://rpm-admin.newrelic.com/admin/system_configurations
and https://rpm-admin.eu.newrelic.com/admin/system_configurations.

    If we need to notify existing users to update their older agents, also
update the ``min_python_agent_version`` to ``A.B.C.D``.

    Additionally, if we have a new feature in the agent, and we want to make
sure APM is gated to the correct version, put in a PR to the [Agent Feature
Service](https://source.datanerd.us/APM/agent_feature_service).

24. Verify that the build number is correct in the version string in the release notes. If
it needs to change, edit the release notes, but get in touch with the Documentation team so
that they can change the URL for the release notes page.

25. Make the "Release Notes" public. (You don't need to have the Documentation
Team do this step. We have the authority to publish release notes.)

26. Contact the Documentation team so they can release any new or changed
public documentation.

27. Send an email to ``agent-releases@newrelic.com`` notifying them about
the release. This will go to agent-team, partnership-team, and other
interested parties. Include a copy of the public release notes, plus a
separate section if necessary with additional details that may be relevant
to internal parties.

28. Send an email to ``gts-python@newrelic.com`` with the Support notes
drafted in the pre-release steps.

29. Notify Python Agent Slack channel that release is out!

30. Make sure that all JIRA stories associated with the release version have
been updated as having been released.

31. Submit a pull request to [docker-state](https://source.datanerd.us/container-fabric/docker-state/blob/master/requirements.txt)
to upgrade the agent version. Be sure it gets merged and deployed to
production. This way we can immediately have a production app running this most
recent agent version.

32. Upgrade the agent version on [Sidekick Bot](https://source.datanerd.us/python-agent/sidekick-bot/blob/master/requirements.txt)
and [redeploy it to production](https://source.datanerd.us/python-agent/sidekick-bot#deploying-to-grandcentral).

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

1. Notify the #python-agent room with the following message:
   ```
   @channel The process to unpublish agent version A.B.C.D is starting.
   ```

1. Replace content from the [release notes](https://docs.newrelic.com/docs/release-notes/agent-release-notes/python-release-notes) with "Removed" and republish them.

1. Notify the #documentation channel hero and ask them to unpublish the [release notes](https://docs.newrelic.com/docs/release-notes/agent-release-notes/python-release-notes)

1. Update the ``python_agent_version`` configuration to ``A.B.C.D`` in APM [systems configuration page](https://rpm-admin.newrelic.com/admin/system_configurations) and [eu systems configuration page](https://rpm-admin.eu.newrelic.com/admin/system_configurations) to point to the previous agent version.

1. Run the [undeploy-from-s3](https://python-agent-build.pdx.vm.datanerd.us/view/PY_Deploy/job/undeploy-from-s3/) job on Jenkins using the most recent agent version. Use the full version number (in the form of ``A.B.C.D``).

1. Verify that the bad version is removed from the [downloads](http://download.newrelic.com/python_agent/release/) site.

1. Log in to [pypi](https://pypi.org/account/login/) using the credentials stored in lastpass under the Shared #python-agent folder.

1. Navigate to the release page https://pypi.org/manage/project/newrelic/release/A.B.C.D (replace ``A.B.C.D`` with the version number of the bad version)

1. Click the Delete Release button. **There is no going back** Once a package has been removed from PyPI, it can not be redeployed at the same version number. After this point, the procedure must be completed.

1. Verify that pip install works and that [legacy pypi](https://pypi.python.org/pypi?%3Aaction=pkg_edit&name=newrelic) shows the previous package version as "Hide? No" (when a new version is deployed, the previous version will be automatically hidden). Verify that `pip install --no-cache newrelic` now installs the correct version.

1. Notify the #python-agent room with the following message:
   ```
   @channel Agent version A.B.C.D removed from PyPI and downloads.newrelic.com
   ```

1. Update [docker-state](https://source.datanerd.us/container-fabric/docker-state/blob/master/requirements.txt) and [Sidekick Bot](https://source.datanerd.us/python-agent/sidekick-bot/blob/master/requirements.txt) to point to the previously released agent version.
