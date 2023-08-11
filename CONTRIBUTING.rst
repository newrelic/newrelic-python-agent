##################################
 Contributing to the Python Agent
##################################

Thanks for your interest in contributing to the ``New Relic Python
Agent``! We look forward to engaging with you.

*******************
 How to Contribute
*******************

Contributions are always welcome. Before contributing please read the
`code of conduct
<https://github.com/newrelic/.github/blob/master/CODE_OF_CONDUCT.md>`__
and `search the issue tracker <../../issues>`__; your issue may have
already been discussed or fixed in `main`. To contribute, `fork
<https://help.github.com/articles/fork-a-repo/>`__ this repository,
commit your changes, and `send a Pull Request
<https://help.github.com/articles/using-pull-requests/>`__.

Note that our `code of conduct
<https://github.com/newrelic/.github/blob/master/CODE_OF_CONDUCT.md>`__
applies to all platforms and venues related to this project; please
follow it in all your interactions with the project and its
participants.

**********************************
 How to Get Help or Ask Questions
**********************************

Do you have questions or are you experiencing unexpected behaviors after
modifying this Open Source Software? Please engage with the “Build on
New Relic” space in the `Explorers Hub
<https://discuss.newrelic.com/c/build-on-new-relic/Open-Source-Agents-SDKs>`__,
New Relic's Forum. Posts are publicly viewable by anyone, please do not
include PII or sensitive information in your forum post.

***************************************
 Contributor License Agreement (“CLA”)
***************************************

We'd love to get your contributions to improve the Python Agent! Keep in
mind that when you submit your Pull Request, you'll need to sign the CLA
via the click-through using CLA-Assistant. You only have to sign the CLA
one time per project. If you'd like to execute our corporate CLA, or if
you have any questions, please drop us an email at
opensource@newrelic.com.

For more information about CLAs, please check out Alex Russell's
excellent post, `Why Do I Need to Sign This?
<https://infrequently.org/2008/06/why-do-i-need-to-sign-this/>`__.

******************
 Feature Requests
******************

Feature requests should be submitted in the `Issue tracker
<../../issues>`__, with a description of the expected behavior & use
case, where they'll remain closed until sufficient interest, `e.g. :+1:
reactions
<https://help.github.com/articles/about-discussions-in-issues-and-pull-requests/>`__,
has been `shown by the community
<../../issues?q=label%3A%22votes+needed%22+sort%3Areactions-%2B1-desc>`__.
Before submitting an Issue, please search for similar ones in the
`closed issues
<../../issues?q=is%3Aissue+is%3Aclosed+label%3Aenhancement>`__.

*****************************
 Filing Issues & Bug Reports
*****************************

We use GitHub issues to track public issues and bugs. If possible,
please provide a link to an example app or gist that reproduces the
issue. When filing an issue, please ensure your description is clear and
includes the following information.

-  Project version (ex: 1.4.0)
-  Custom configurations (ex: flag=true)
-  Any modifications made to the Python Agent

A note about vulnerabilities
============================

New Relic is committed to the security of our customers and their data.
We believe that providing coordinated disclosure by security researchers
and engaging with the security community are important means to achieve
our security goals.

If you believe you have found a security vulnerability in this project
or any of New Relic's products or websites, we welcome and greatly
appreciate you reporting it to New Relic through `HackerOne
<https://hackerone.com/newrelic>`__.

*****************************
 Setting Up Your Environment
*****************************

This Open Source Software can be used in a large number of environments,
all of which have their own quirks and best practices. As such, while we
are happy to provide documentation and assistance for unmodified Open
Source Software, we cannot provide support for your specific
environment.

*******************************
 Developing Inside a Container
*******************************

To avoid the issues involved with setting up a local environment,
consider using our prebuilt development container to easily create an
environment on demand with a wide selection of Python versions
installed. This also comes with the `tox
<https://github.com/tox-dev/tox>`__ tool (See Testing Guidelines) and a
few packages preinstalled.

While we cannot provide direct support in setting up your environment to
work with this container, we develop it in the open and provide this
documentation to help reduce the setup burden on new contributors.

Prerequisites:
==============

#. Install `Docker <https://www.docker.com/>`__ for you local operating
   system.

#. Login to the `GitHub Container Registry
   <https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry#authenticating-with-a-personal-access-token-classic>`__
   through Docker.

#. Install Either:
      -  `VS Code <https://code.visualstudio.com/>`__ onto your local
         system (recommended).

      -  The `Dev Container CLI
         <https://github.com/devcontainers/cli>`__ in your terminal.
         (Requires a local copy of `npm
         <https://docs.npmjs.com/downloading-and-installing-node-js-and-npm>`__.)

Steps for VS Code:
==================

#. Ensure Docker is running.

#. Install the `VS Code Extension for Dev Containers
   <https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers>`__
   into VS Code.

#. In VS Code, open the command pallette (Ctrl-Shift-P on Windows/Linux
   or Cmd-Shift-P on Mac) and search for and run "Dev Containers:
   Rebuild and Reopen in Container".

#. Wait for the container to build and start. This may take a long time
   to pull the first time the container is run, subsequent runs should
   be faster thanks to caching.

#. To update your container, open the command pallette and run "Dev
   Containers: Rebuild Without Cache and Reopen in Container".

Steps for Command Line Editor Users (vim, etc.):
================================================

#. Ensure Docker is running.

#. From the root of this repository, run ``devcontainer up
   --workspace-folder=.`` to start the container. The running container
   ID will be displayed, which is useful for subsequent steps.

#. To gain shell access to the container, run ``docker exec -it
   <container-id> /bin/bash``. Alternative shells include ``zsh`` and
   ``fish``.

#. Navigate to the ``/workspaces`` folder to find your source code.

#. To stop the container, run ``exit`` on any open shells and then run
   ``docker stop <container-id>``. ``docker ps`` may be helpful for
   finding the ID if you've lost it.

Personalizing Your Container:
=============================

#. If you use a dotfiles repository (such as `chezmoi
   <https://www.chezmoi.io/>`__), you can configure your container to
   clone and install your dotfiles using `VS Code dotfile settings
   <https://code.visualstudio.com/docs/devcontainers/containers#_personalizing-with-dotfile-repositories>`__.

#. To install extra packages and features, you can edit your local copy
   of the .devcontainer/devcontainer.json file to use specific `Dev
   Container Features <https://containers.dev/features>`__. A few common
   needs are already included but commented out.

*************************
 Pull Request Guidelines
*************************

Before we can accept a pull request, you must sign our `Contributor
Licensing Agreement <#contributor-license-agreement-cla>`__, if you have
not already done so. This grants us the right to use your code under the
same Apache 2.0 license as we use for this project in general.

Minimally, the `test suite <#testing-guidelines>`__ must pass for us to
accept a PR. Ideally, we would love it if you also added appropriate
tests if you're implementing a feature!

Please note that integration tests will be run internally before
contributions are accepted.

Additionally:

#. Ensure any install or build dependencies are removed before the end
   of the layer when doing a build.

#. Increase the version numbers in any examples files and the README.md
   to the new version that this Pull Request would represent. The
   versioning scheme we use is `SemVer <http://semver.org/>`__.

#. You may merge the Pull Request in once you have the sign-off of two
   other developers, or if you do not have permission to do that, you
   may request the second reviewer to merge it for you.

********************
 Testing Guidelines
********************

The Python Agent uses `tox <https://github.com/tox-dev/tox>`__ for
testing. The repository uses tests in tests/.

You can run these tests by entering the tests/ directory and then
entering the directory of the tests you want to run. Then, run the
following command:

``tox -c tox.ini -e [test environment]``

*******
 Slack
*******

We host a public Slack with a dedicated channel for contributors and
maintainers of open source projects hosted by New Relic. If you are
contributing to this project, you're welcome to request access to the
#oss-contributors channel in the newrelicusers.slack.com workspace. To
request access, please use this `link
<https://join.slack.com/t/newrelicusers/shared_invite/zt-1ayj69rzm-~go~Eo1whIQGYnu3qi15ng/>`__.
