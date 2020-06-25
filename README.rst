|header|

.. |header| image:: https://github.com/newrelic/opensource-website/raw/master/src/images/categories/Community_Project.png
    :target: https://opensource.newrelic.com/oss-category/#community-project

======================
New Relic Python Agent
======================

The ``newrelic`` package instruments your application for performance monitoring and advanced performance analytics with `New Relic`_.

Pinpoint and solve Python application performance issues down to the line of code. `New Relic APM`_ is the only tool you'll need to see everything in your Python application, from the end user experience to server monitoring. Trace problems down to slow database queries, slow 3rd party APIs and web services, caching layers, and more. Monitor your app in a production environment and make sure your app can stand a big spike in traffic by running scalability reports.

Visit `Python Application Performance Monitoring with New Relic`_ to learn more.

.. _New Relic: http://newrelic.com
.. _New Relic APM: http://newrelic.com/application-monitoring
.. _Python Application Performance Monitoring with New Relic: http://newrelic.com/python

Installation
------------

.. code:: bash

    $ pip install newrelic

Usage
-----

(These instructions can also be found online: `Python Agent Quick Start`_.)

1. Generate the agent configuration file with your `license key`_.

   .. code:: bash

      $ newrelic-admin generate-config $YOUR_LICENSE_KEY newrelic.ini

2. Validate the agent configuration and test the connection to our data collector service.

   .. code:: bash

      $ newrelic-admin validate-config newrelic.ini

3. Integrate the agent with your web application.

   If you control how your web application or WSGI server is started, the recommended way to integrate the agent is to use the ``newrelic-admin`` `wrapper script`_. Modify the existing startup script, prefixing the existing startup command and options with ``newrelic-admin run-program``.

   Also, set the `NEW_RELIC_CONFIG_FILE` environment variable to the name of the configuration file you created above:

   .. code:: bash

      $ NEW_RELIC_CONFIG_FILE=newrelic.ini newrelic-admin run-program $YOUR_COMMAND_OPTIONS

   Examples:

   .. code:: bash

      $ NEW_RELIC_CONFIG_FILE=newrelic.ini newrelic-admin run-program gunicorn -c config.py test_site.wsgi

      $ NEW_RELIC_CONFIG_FILE=newrelic.ini newrelic-admin run-program uwsgi uwsgi_config.ini

   Alternatively, you can also `manually integrate the agent`_ by adding the following lines at the very top of your python WSGI script file. (This is useful if you're using ``mod_wsgi``.)

   .. code:: python

      import newrelic.agent
      newrelic.agent.initialize('/path/to/newrelic.ini')

4. Start or restart your Python web application or WSGI server.

5. Done! Check your application in the `New Relic UI`_ to see the real time statistics generated from your application.

.. _Python Agent Quick Start: https://docs.newrelic.com/docs/agents/python-agent/getting-started/python-agent-quick-start
.. _license key: https://docs.newrelic.com/docs/accounts-partnerships/accounts/account-setup/license-key
.. _wrapper script: https://docs.newrelic.com/docs/agents/python-agent/installation-configuration/python-agent-integration#wrapper-script
.. _manually integrate the agent: https://docs.newrelic.com/docs/agents/python-agent/installation-configuration/python-agent-integration#manual-integration
.. _New Relic UI: https://rpm.newrelic.com

Resources
---------

* `New Relic for Python Documentation <https://docs.newrelic.com/docs/agents/python-agent>`_
* `New Relic for Python Release Notes <https://docs.newrelic.com/docs/release-notes/agent-release-notes/python-release-notes>`_
* `New Relic Forum <http://discuss.newrelic.com>`_
