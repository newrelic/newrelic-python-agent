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

3.  Draft the New & Noteworthy update for Foglights for each Foglights project that
is being released. This should be a short summary of what the feature is, focusing
on how it benefits our customers, and written in a way that will make sense to both
Engineering and Sales/Marketing.

    An image (usually a screenshot) **MUST** be included in each New & Noteworthy.

4.  Draft the Support notes for the release. This is where we describe key things that
Support will need to know about the release, but aren't necessarily in the public
documentation, such as specific problems to look out for, new configuration settings,
etc. Include links to the release notes and any changed or new documentation.

5. Review this document and update it with any required changes. Create a pull request
if necessary.

Performing a Standard Release
-----------------------------

Once work has finished on a development version and all testing has been
performed and the code approved for release, the following steps should be
carried out to do the actual release.

0. Create a new google spreadsheet and share it with the team. Add items from this document as checklist items. This command will gather the first two lines of each numbered item and prints it to a single line.

  ```
  cat PROCESS.md | grep -A1 '^\d' | awk '/--/{if (NR!=1)print "";next}{printf $0}END{print "";}' | sed 's/$/.../'
  ```

1. Check out the ``develop`` branch of the Python agent repository and
update the version number in ``newrelic/__init__.py`` for the release.

    With our odd/even numbering scheme, this means you should be incrementing
the ``B`` component of the ``A.B.C`` version number from the odd number used
during development to the even number used for the release.

2. Run locally ``./build.sh`` to force the licence validation script to be
run and ensure package builds.

3. Run locally ``./tests.sh`` to ensure that all base level unit tests pass.

    This test can also be run in docker, with `packnsend`:

        packnsend run /data/tests.sh

4. Perform any other final adhoc local tests deemed necessary for the release.

5. Create a release branch

6. Commit change made to ``newrelic/__init__.py`` into the release
branch you just created. Format the commit message like this:

        Increment version to A.B.C for release.

7. Push that branch up, and create a pull request from the release branch to
``develop``. Get someone to add the "sidekick:approved" label and merge. This is
necessary because no changes can to added to the code without being side-kick
approved. Security will keep sending you emails if you don't do this.

8. Create a PR from ``develop`` to ``master``. The PR should be titled:

        Merge develop into master for release A.B.C

9. Get a buddy to sidekick and merge this PR.

10. Switch back to the ``develop`` branch and perform a merge from
``master`` back into the ``develop`` branch.

    Confirm that you are on the `develop` branch, then run:

        git merge master

    This is to synchronize the two branches so git doesn't keep tracking them
as completely parallel paths of development with consequent strange results
when trying to compare branches.

11. Push both the ``develop`` and ``master`` branches back to the GIT repo.

    From the command line:

        git push origin develop
        git push origin master

    This action will also trigger the Jenkins
    [`oldstyle-tests-develop`][test-develop] and
    [`oldstyle-tests-master`][test-master] jobs. If the automatic trigger does
    not work, then run the tests manually in [Jenkins][Jenkins].

[Jenkins]: https://python-agent-build.pdx.vm.datanerd.us

    In addition, run the [`_PYTHON-AGENT-DOCKER-TESTS_`][docker-tests] tests
    manually for the `master` branch. Click `Build with parameters` and set the
    branch to `master`.

12. Check that the [`oldstyle-tests-develop`][test-develop] and [`oldstyle-tests-master`][test-master] jobs in Jenkins run and all tests pass okay.

[test-develop]: https://python-agent-build.pdx.vm.datanerd.us/view/PY_Tests/job/oldstyle-tests-develop/
[test-master]: https://python-agent-build.pdx.vm.datanerd.us/view/PY_Tests/job/oldstyle-tests-master/
[docker-tests]: https://python-agent-build.pdx.vm.datanerd.us/view/PY_Tests/job/_PYTHON-AGENT-DOCKER-TESTS_/

13. Tag the release in the ``master`` branch on the GIT repo with tag of
the form ``vA.B.C`` and ``vA.B.C.D``, where ``D`` is now the build number. Push
the tags to Github master.

    From the command line:

        # Create tags
        git tag vA.B.C
        git tag vA.B.C.D

        # Tags don't get pushed to GHE automatically, so you must do it.
        git push origin vA.B.C
        git push origin vA.B.C.D

14. In Jenkins, build and upload the release to Artifactory.

    1. Log in and go to [build-and-archive-package][build].
    2. From the menu on the left select "Build with Parameters"
    3. Type in the version number INCLUDING the next build that will be created when you push the build button
    4. Push the build button

    This will build and upload the package to artifactory

[build]: https://python-agent-build.pdx.vm.datanerd.us/view/PY_Deploy/job/build-and-archive-package/

15. Check Artifactory upload

    1. Go to [Artifactory][artifactory].
    2. In the navigator on the left, go to ``pypi-newrelic``->``A.B.C.D``->``newrelic-A.B.C.D.tar.gz``. Check that the Checksum for MD5 says ""(Uploaded: Identical)""

[artifactory]:http://pdx-artifacts.pdx.vm.datanerd.us:8081/artifactory/webapp/browserepo.html?0

16. Upload from Artifactory to PyPI

    1. Go back to Jenkins, and select the other project, [deploy-to-pypi][deploy-pypi]
    2. From the menu on the left select "Build with Parameters"
    3. From the drop down menu `PYPI_REPOSITORY`, select pypi-production. Type in the version number, including the build in the `AGENT_VERSION` box.
    4. Push the build button
    5. Go to PyPI and check that the version uploaded. Validate that ``pip install`` of package into a virtual environment works and that a ``newrelic-admin validate-config`` test runs okay

[deploy-pypi]: https://python-agent-build.pdx.vm.datanerd.us/view/PY_Deploy/job/deploy-to-pypi/

17. Upload from Artifactory to Amazon S3

  1. Go back to Jenkins, and select the other project, [deploy-to-s3][deploy-s3]
  2. From the menu on the left select "Build with Parameters"
  3. From the drop down menu `S3_RELEASE_TYPE`, select "release". Type in the version number, including the build in the `AGENT_VERSION` box.
  4. Push the build button
  5. Make sure the job finishes successfully

[deploy-s3]: https://python-agent-build.pdx.vm.datanerd.us/view/PY_Deploy/job/deploy-to-s3/

18. Update the ``python_agent_version`` configuration to ``A.B.C.D`` in APM
systems configuration page at: https://rpm-admin.newrelic.com/admin/system_configurations.

    If we need to notify existing users to update their older agents, also
update the ``min_python_agent_version`` to ``A.B.C.D``.

19. Verify that the build number is correct in the version string in the release notes. If
it needs to change, edit the release notes, but get in touch with the Documentation team so
that they can change the URL for the release notes page.

20. Make the "Release Notes" public. (You don't need to have the Documentation
Team do this step. We have the authority to publish release notes.)

21. Contact the Documentation team so they can release any new or changed
public documentation.

22. Send an email to ``agent-releases@newrelic.com`` notifying them about
the release. This will go to agent-team, partnership-team, and other
interested parties. Include a copy of the public release notes, plus a
separate section if necessary with additional details that may be relevant
to internal parties.

23. Send an email to ``python-support@newrelic.com`` with the Support notes
drafted in the pre-release steps.

24. Notify Python Agent Slack channel that release is out!

25. Add New & Noteworthy entries (multiple) via Fog Lights for the key
feature(s) or improvement(s) in the release.

26. Create a branch off ``develop`` to increment the version number for development.

27. Update the version number in``newrelic/__init__.py`` to be that of next development release number.

    That is, increment ``B`` if next version is minor version. With our
odd/even numbering scheme, ``B`` should always be odd after this change.

    Format the commit message like this:

        Increment version to A.B.C for development.

28. Create a PR for merging in the increment branch into ``develop``.

29. Get a buddy to sidekick and merge this PR.

30. Make sure that all JIRA stories associated with the release version have
been updated as having been released.
