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
out to customers. The two relevant Jenkins build jobs are:

* https://pdx-hudson.datanerd.us/view/Python/job/Python_Agent-MASTER

    This is used to produce the tar ball for an official release.

* https://pdx-hudson.datanerd.us/view/Python/job/Python_Agent-DEVELOP

    This is used to produce the tar balls for development versions. These
    are internal versions and would not normally be handed out to customers
    except in approved circumstance where a customer is needed to test a
    change before an official release can be made.

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

2.  Schedule the release with the [CAB Tool](https://upboard.datanerd.us/changes).
Ideally, this should be done at least a day in advance. The key pieces of information that
you'll need to fill out the release form are:

  1. Link to the release notes (draft version is OK.)
  2. Risk level assessment (Low, Medium or High)
  3. Brief description of feature(s) in release

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

Performing a Standard Release
-----------------------------

Once work has finished on a development version and all testing has been
performed and the code approved for release, the following steps should be
carried out to do the actual release.

0. Schedule the release with the [CAB Tool](https://upboard.datanerd.us/changes).
Ideally, this should be done a day in advance. The key pieces of information that
you'll need to fill out the release form are:

  1. Link to the release notes (draft version is OK.)
  2. Risk level assessment (Low, Medium or High)
  3. Brief description of feature(s) in release

1. Check out the ``develop`` branch of the Python agent repository and
update the version number in ``newrelic/__init__.py`` for the release.

    With our odd/even numbering scheme, this means you should be incrementing
the ``B`` component of the ``A.B.C`` version number from the odd number used
during development to the even number used for the release.

2. Run locally ``./build.sh`` to force the licence validation script to be
run and ensure package builds.

3. Run locally ``./tests.sh`` to ensure that all base level unit tests pass.

4. Perform any other final adhoc local tests deemed necessary for the release.

5. Commit change made to ``newrelic/__init__.py`` into the ``develop``
branch. Format the commit message like this:

        Increment version to A.B.C for release.

6. Follow git-flow procedure to create a release branch with name
``vA.B.C``.

    With our odd/even numbering scheme, ``B`` should always be even. This
string will become the final tag git-flow will add when finishing the
release.

    From the command line:

        git flow release start vA.B.C

7. If necessary, push release branch back to github for further testing by
the rest of the Python agent team. Wait for confirmation before proceeding
if such testing is required.

8. Follow git-flow procedure to finish the release branch.

    From the command line:

        git flow release finish vA.B.C

9. Switch back to the ``develop`` branch and perform a merge from
``master`` back into the ``develop`` branch.

    This is to synchronize the two branches so git doesn't keep tracking them
as completely parallel paths of development with consequent strange results
when trying to compare branches.

10. In the ``develop`` branch, increment the version number in
``newrelic/__init__.py`` to be that of next development release number.

    That is, increment ``B`` if next version is minor version. With our
odd/even numbering scheme, ``B`` should always be odd after this change.

11. Commit change made to ``newrelic/__init__.py`` into the ``develop``
branch. Format the commit message like this:

        Increment version to A.B.C for development.

12. Push both the ``develop`` and ``master`` branches back to the GIT repo.

    This action will also trigger the Jenkins ``Python_Agent-MASTER`` and
``Python_Agent-DEVELOP`` jobs.

13. Check that ``Python_Agent-MASTER-TESTS`` in Jenkins runs and all tests
pass okay.

14. Tag the release in the ``master`` branch on the GIT repo with tag of
the form ``vA.B.C.D``, where ``D`` is now the build number from
``Python_Agent-MASTER`` and make sure the tag is pushed to github master.
This should be the same commit as already had the tag ``vA.B.C`` which was
added by git-flow.

    From the command line:

        # Create tag
        git tag vA.B.C.D

        # Tags don't get pushed to GHE automatically, so you must do it.
        git push origin vA.B.C.D

15. In Jenkins mark the corresponding build in ``Python_Agent-MASTER`` as
keep forever.

16. Upload the package to the ``release`` directory for ``python_agent`` on
hosts used by ``download.newrelic.com``. Generate a file in the same
directory for the download with an ``.md5`` extension which contains the MD5
hash of the package.

    For more details on working with the New Relic download site and
transferring files across see: [Managing the Download Site][download].

[download]: https://newrelic.atlassian.net/wiki/display/eng/Python+Agent+Managing+The+Download+Site

17. Update the ``python_agent_version`` configuration to ``A.B.C.D`` in APM
systems configuration page at: https://rpm.newrelic.com/admin/system_configurations.

    If we need to notify existing users to update their older agents, also
update the ``min_python_agent_version`` to ``A.B.C.D``.

18. Create a new Python package index (PyPi) entry for the new release and
attach the tar ball.

    Validate that ``pip install`` of package into a virtual environment works
and that a ``newrelic-admin validate-config`` test runs okay.

19. Make the "Release Notes" public. (You don't need to have the Documentation
Team do this step. We have the authority to publish release notes.)

20. Make sure any documentation specific to the release is marked as ready
for publication and a JIRA issue created in DOCS project to have it
released. Ask someone in the DOCS team to perform the update to production
if important to get to production quickly.

21. Send an email to ``agent-releases@newrelic.com`` notifying them about
the release. This will go to agent-team, partnership-team, and other
interested parties. Include a copy of the public release notes, plus a
separate section if necessary with additional details that may be relevant
to internal parties.

22. Send an email to ``python-support@newrelic.com`` with the Support notes
drafted in the pre-release steps.

23. Add New & Noteworthy entries (multiple) via Fog Lights for the key
feature(s) or improvement(s) in the release.

24. Make sure that all JIRA stories associated with the release version have
been updated as having been released. The current agent dashboard can be
found at: https://newrelic.atlassian.net/secure/Dashboard.jspa?selectPageId=11912

25. Switch over JIRA Python agent filters for current/next/next+1 releases
so current dashboard now shows issues for next release.
