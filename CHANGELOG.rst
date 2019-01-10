unreleased
----------

4.10.0 (2019-01-10)
------------------

- Add ability to exclude attributes from span events and transaction segments

  This release adds support to exclude attributes from span events (via the
  span_events.include/exclude options) and from transaction segments (via the
  transaction_segments.include/exclude option).

  As with other attribute destinations, these new options will inherit values
  from the top-level attributes.include/exclude settings. See the documentation
  for more information.

  This feature also includes filtering of url parameters from span events and
  transaction segments.


- Transaction counts were not reported for aiohttp's built-in error pages

  When a built-in error route was reached in aiohttp (such as a 404 due to a
  missing route), transactions were not recorded. As a result, the transaction
  counts may have been artificially low. aiohttp system route traffic will now
  be reported.

- aiohttp cross application tracing linking to non-Python applications may have been
  omitted if using multidict<3.0

  For aiohttp users using multidict versions less than 3.0, cross application
  tracing HTTP headers may have been generated in a way that was incompatible
  with non-Python applications. Headers are now generated in a format
  compatible with all New Relic agents.

- aiohttp 3.5.x versions generated agent instrumentation errors

  The agent previously failed to instrument aiohttp applications running
  versions 3.5.0 and greater. The agent now supports aiohttp versions up to
  3.5.1.

- Add public add_custom_parameters API

  The method add_custom_parameters on Transaction is now exposed through
  newrelic.agent.add_custom_parameters

4.8.0 (2018-12-03)
------------------

- "newrelic-admin record_deploy" now functions with proxies.

  The "newrelic-admin record_deploy" command previously did not function when
  a proxy was defined by the newrelic.ini configuration file or the
  NEW_RELIC_PROXY_* environment variables. This bug has now been fixed.

- Add support for Falcon web framework

  This release adds support for the Falcon web framework. Data will now
  be automatically collected for applications using Falcon framework. The data
  will appear in both APM and Insights and will include performance details as
  well as information on application errors.

- Cross Application Tracing HTTP response headers were inserted on a 304 response

  When cross application tracing is enabled and the agent received a HTTP
  request from an application utilizing cross application tracing, the agent
  may have inserted additional response headers on a 304 HTTP response. The
  agent will no longer insert headers on a 304 response.


4.6.0 (2018-11-12)
------------------

- Monitoring of Lambda functions

  This release includes changes to the agent to enable monitoring of Lambda
  functions. If you are interested in learning more or previewing New Relic
  Lambda monitoring please email lambda_preview@newrelic.com.

- Improve naming of Sanic HTTPMethodView view handlers

  Sanic views that were defined using the HTTPMethodView class were previously
  all named HTTPMethodView.as_view.<locals>.view regardless of the actual class
  in use. The agent will now name transactions after the actual view handler
  class.

- Fix ignored error reporting in CherryPy instrumention

  When missing query parameters, unexpected query parameters, unexpected positional
  arguments, or duplicate arguments were present in the CherryPy framework, a
  TypeError exception was recorded even when an ignored response status code
  (such as a 404) was generated. An error is no longer recorded when it results in
  the generation of an ignored status code.

- Excluding `request.uri` from transaction trace attributes hides it in the UI

  When `request.uri` is added to either `attributes.exclude` or
  `transaction_tracer.attributes.exclude`, the value will now no longer appear
  in the APM UI for transaction traces.

- Ability to disable sending `request.uri` as part of error traces

  Error traces will now respect excluding `request.uri` when added to the
  attributes.exclude list in the newrelic.ini configuration file.

- Fix tracing of functions returning generators

  When tracing generators whose parent traces have ended an error was seen
  in the logs "Transaction ended but current_node is not Sentinel." This has
  now been fixed.


4.4.1 (2018-09-21)
------------------

- The creation of sampled events sometimes raised an exception in Python 3

  When more events (Transaction, Transaction Error, Custom, or Span) were
  created than allowed per harvest period in Python 3, sometimes a `TypeError:
  '<' not supported between instances of 'dict' and 'dict'` was raised. This
  issue has now been fixed.


4.4.0 (2018-09-11)
------------------

- Add instrumentation for Sanic framework

  Data is now automatically collected for applications using the Sanic
  framework. Data for Sanic applications will appear in both APM and Insights.
  Additionally, cross application tracing and distributed tracing is supported
  for incoming requests for Sanic applications. In addition to service maps,
  Sanic applications will now show the calling application in transaction
  traces.

- Explain plans were not generated when using psycopg2 named cursors

  When using named cursors in psycopg2, the agent attempted to generate an
  explain plan using the same named cursor. This resulted in a syntax error
  when the query was issued to the database. When using the default connection
  and cursor factories, the agent will now execute the explain query using only
  unnamed cursors.

- Convert bytes-like SQL statements to strings before obfuscating

  If a bytes-like object is used instead of a string when making a SQL call, a
  traceback was seen in the logs with `TypeError: cannot use a string pattern
  on a bytes-like object`. This issue has now been fixed.

- Save settings to `MessageTrace` objects

  If an external call using an instrumented http external library (for example
  `requests`) was used within a `MessageTrace`, a traceback was seen in the
  logs with `AttributeError: 'MessageTrace' object has no attribute
  'settings'`. This issue has now been fixed.


4.2.0 (2018-07-31)
------------------

- Distributed Tracing support

  Distributed tracing lets you see the path that a request takes as it travels
  through your distributed system. By showing the distributed activity through
  a unified view, you can troubleshoot and understand a complex system better
  than ever before.

  Distributed tracing is available with an APM Pro or equivalent subscription.
  To see a complete distributed trace, you need to enable the feature on a set
  of neighboring services. Enabling distributed tracing changes the behavior of
  some New Relic features, so carefully consult the [transition
  guide](https://docs.newrelic.com/docs/transition-guide-distributed-tracing)
  before you enable this feature.

  To enable distributed tracing, add `distributed_tracing.enabled = true` to
  your newrelic.ini file or use the environment variable
  `NEW_RELIC_DISTRIBUTED_TRACING_ENABLED=true`.

- Add support for tracing Pyramid tweens

  [Pyramid tweens](https://docs.pylonsproject.org/projects/pyramid/en/latest/glossary.html#term-tween)
  are now automatically timed and added to the transaction detail view. The
  time spent in a Pyramid tween will be displayed in the transaction breakdown
  table and in the trace details of a transaction trace.

- Custom Insights event data attached to transactions in excess of 100 events
  were omitted

  The agent may have failed to send custom event data (record_custom_event) to
  insights when recorded as part of a Transaction containing over 100 custom
  events. This issue has now been corrected.

- Provide configuration option for custom CA bundle.

  Customers can now use the `ca_bundle_path` configuration option or set the
  `NEW_RELIC_CA_BUNDLE_PATH` environment variable to set the path to a local CA
  bundle. This CA bundle will be used to validate the SSL certificate presented
  by New Relic's data collection service.


4.0.0 (2018-07-23)
------------------

- Remove support for Python 2.6 / Python 3.3

  Python 2.6 and Python 3.3 are no longer supported by the Python Agent.

- Remove add_user_attribute APIs from the agent.

  The add_user_attribute and add_user_attributes APIs have been removed from
  the agent.  These APIs have been replaced with
  newrelic.agent.add_custom_parameter and newrelic.agent.add_custom_parameters.

- Remove wrap_callable API from the agent.

  The wrap_callable API has been removed from the agent. This API has been
  replaced with newrelic.agent.FunctionWrapper.


3.4.0 (2018-07-12)
------------------

- Agent raises a KeyError: 'NEW_RELIC_ADMIN_COMMAND' exception causing a crash

  Under certain conditions, using the newrelic-admin wrapper script could cause
  an application to crash shortly after startup with a KeyError exception. The
  cause of the crash has been addressed.

- Agent raises an AttributeError on Python 3 when using WSGI overrides with
  multiple app names

  When using WSGI environ overrides to specify multiple app names as described
  in the docs
  https://docs.newrelic.com/docs/agents/manage-apm-agents/app-naming/use-multiple-names-app
  the agent will raise an AttributeError. This error has been corrected.

- Agent raises an AttributeError exception under rare conditions when halting
  a trace

  Under certain rare conditions, the agent might raise an exception when trying
  to trace an external call in a transaction that has been forcibly halted.
  The cause of the exception has been addressed.

- Agent raises a RuntimeError exception under particular conditions
  when using the Tornado r3 instrumentation

  When attempting to yield many times from a wrapped tornado.gen.coroutine
  when using Tornado's r3 instrumentation, a RuntimeError due to hitting
  the maximum recursion limit can occur. The cause of this exception has
  been patched.

- Support Python 3.7

  The New Relic Python Agent now supports Python 3.7.


3.2.2 (2018-06-11)
------------------

- Improved handling of celery max-tasks-per-child

  Data recorded by the Python Agent may not have been reported when
  celery was operated with the max-tasks-per-child setting. All data is now
  reported independent of the max tasks per child setting.

- Improve support for PyMongo v3.x

  PyMongo v3 added many new methods on the `pymongo.Collection` object that did
  not exist in v2. These methods have now been instrumented. Calls to these
  methods will now appear in APM.

- Scheduling tasks that run after a transaction ends causes an error

  Coroutines scheduled to execute after a transaction ends using create_task or
  ensure_future may have caused the runtime instrumentation error:
     The transaction already completed meaning a child called complete trace
     after the trace had been finalized.
  and subsequent crash. Coroutines that execute beyond the end of a transaction
  will no longer cause an error.


3.2.1 (2018-05-16)
------------------

- Do not run explain plans for psycopg2 connections using the `async_` kwarg

  As "async" is now a keyword in Python 3.7, psycopg2 now allows "async_" as an
  alias for its "async" kwarg for psycopg2.connect as of psycopg2 v2.7.4.
  Previously, explain plans were attempted for these connections and a
  traceback would be seen in the logs. This has now been fixed.

- Fix traceback when using callbacks as partials in pika consumers

  When passing a callback that is a functools partial to pika channel
  consumers, a traceback occurred in some instances. This issue has now been
  fixed.

- cx_Oracle database calls that use SessionPool objects were not recorded

  When using the cx_Oracle SessionPool interace, database transactions made
  through the acquired pool connection may not have been reported. Database
  transactions that using connections generated by SessionPool are now reported
  as expected.

- SQL targets for call statements may contain a period

  For a SQL command like `CALL foo.bar(:baz)`, APM would show metrics under the
  target name `foo` instead of the full name `foo.bar`. This has been fixed.


3.2.0 (2018-04-04)
------------------

- Fix CherryPy ignore by status code for exceptions using reason phrases

  CherryPy accepts string values for `HTTPError` status (reason phrases). When
  creating `HTTPError` exceptions in this way, responses were not properly
  ignored by status code. Responses generated by `HTTPError` exceptions using
  reason phrases are now properly ignored.

- Record Flask RESTful and Flask RestPlus exceptions

  Since Flask RESTful and Flask RestPlus handle all errors that are raised in
  their handlers, these errors were not being captured by the normal Flask
  instrumentation in the Python agent. Exception handling has now been added
  for these two components.

- Add request.uri attribute to transaction and error events

  The Python agent will now report request.uri as an attribute on transaction
  events and error events. To disable this feature, add request.uri to the
  attributes.exclude list in the newrelic.ini configuration file.

- Using send_file with Flask Compress middleware may have caused an application
  crash

  When using browser monitoring auto instrumentation on an application using
  Flask Compress, the use of the Flask send_file helper to send html files
  resulted in an application crash. This issue has now been resolved.

- Fix incorrect parenting for traces of coroutines scheduled with asyncio
  gather/ensure_future

  Coroutines scheduled with asyncio gather/ensure_future may have been reported
  as being a child of the wrong function. This issue has now been corrected.

- Add instrumentation hooks for the Cheroot WSGI server

  Any customers using Cheroot with an unsupported application framework will
  now see data reported in New Relic APM.


3.0.0 (2018-03-14)
------------------

- Removed previously deprecated APIs

  The following APIs have been removed:
    - transaction (use current_transaction)
    - name_transaction (use set_transaction_name)
    - Application.record_metric (use Application.record_custom_metric)
    - Application.record_metrics (use Application.record_custom_metrics)
    - Transaction.notice_error (use Transaction.record_exception)
    - Transaction.record_metric (use Transaction.record_custom_metric)
    - Transaction.name_transaction (use Transaction.set_transaction_name)

- Deprecate Transaction.add_user_attribute

  Transaction.add_user_attribute has been deprecated in favor of
  Transaction.add_custom_parameter. Transaction.add_user_attribute will be
  removed in a future release.

- Deprecate Transaction.add_user_attributes

  Transaction.add_user_attributes has been deprecated in favor of
  Transaction.add_custom_parameters. Transaction.add_user_attributes will be
  removed in a future release.

- Deprecate wrap_callable

  wrap_callable has been deprecated in favor of FunctionWrapper.
  wrap_callable will be removed in a future release.

- Remove data-source admin command

  The platform API (used by newrelic-admin data-source) has been removed.
  Please use data sources
  (https://docs.newrelic.com/docs/agents/python-agent/supported-features/
  python-custom-metrics#registering-a-data-source) in place of the platform
  API.

- SSL connections to New Relic are now mandatory.

  Prior to this version, using an SSL connection to New Relic was the default
  behavior. SSL connections are now enforced (not overrideable).

- Add automatic tracing of AIOHTTP 3 middleware

  In addition to the old-style middleware previously supported, the AIOHTTP 3
  style middleware is now automatically traced as part of the AIOHTTP
  instrumentation package.


2.106.0 (2018-02-28)
--------------------

- Support for AIOHTTP 3

  AIOHTTP major version 3 is now supported by the New Relic Python agent.


2.104.0 (2018-02-20)
--------------------

- Using asyncio.gather or asyncio.ensure_future now tracks transaction context.

  Prior to this release, using asyncio.gather or asyncio.ensure_future may
  result in certain traces (such as external calls) not being reported in the
  transaction. Traces scheduled with asyncio.gather or asyncio.ensure_future
  from within the context of a transaction should now be properly attributed to
  the transaction.

- Disabling SSL connections to New Relic has been deprecated

  SSL connections are enabled by default. In a future release, the option to
  disable SSL will be removed.


2.102.0 (2018-02-05)
--------------------

- Time trace APIs (such as function_trace) can now be used with coroutines.

  The following decorator APIs can now be used with native coroutines and generators:

  * function_trace
  * database_trace
  * datastore_trace
  * external_trace
  * message_trace
  * memcache_trace

  Example:

.. code-block:: python

  @function_trace(name='my_coroutine')
  async def my_coroutine():
    await asyncio.sleep(0.1)

- gRPC instrumentation used on Python 2.x can cause a memory leak

  When using gRPC on Python 2, gRPC futures would not be garbage collected
  resulting in a memory leak. gRPC futures will now be garbage collected.

- Instrumentation for Dropbox v8.0 and newer caused error log messages

  Dropbox client version 8.0 or higher raised instrumentation errors. These
  errors did not prevent metrics on Dropbox from being sent. These errors have
  been removed.

- Values from negated ranges were sometimes added to ignore_status_codes

  Negated status codes not found in the current ignore_status_codes were 
  added if they were part of a range of values. This issue has been addressed.


2.100.0 (2017-01-09)
--------------------

- Security Updates

  See the associated `security bulletin <https://docs.newrelic.com/docs/accounts-partnerships/accounts/security-bulletins/security-bulletin-nr18-01>`_.

- Using the aiohttp client results in an application crash

  Under certain circumstances, using the aiohttp client may have resulted in an
  application crash. This issue has been addressed.

- Database queries made with psycopg2 may not have been recorded

  When using the "with" statement to create a cursor, time spent on database
  calls may not have been properly recorded. This issue has been addressed.

- Usage of the pika library resulted in a memory leak

  When using the pika library with New Relic, Channel objects would not be
  cleared from memory as expected. This would result in abnormally high memory
  utilization in some cases. The memory leak has now been fixed.


2.98.0 (2017-11-30)
-------------------

- Enabled reporting of handled exceptions in Django REST Framework

  Exceptions handled by Django REST Framework are now reported if the resulting
  response code is not ignored (see
  https://docs.newrelic.com/docs/agents/python-agent/configuration/python-agent-configuration#error-ignore-status-codes
  for details on ignored status codes).

- Servicing aiohttp websocket requests results in an application crash

  Servicing a websocket request in an aiohttp application may have resulted in
  an application crash when using the New Relic python agent. The application
  will now operate as expected when handling a websocket request.

- Ignore incomplete aiohttp transactions

  In aiohttp, connections can be terminated prior to the HTTP response being
  generated and sent. In those cases, the request handler may be cancelled.
  These transactions are no longer reported.

- Add support for the error_collector.ignore_status_codes setting in Django

  Ignoring exceptions in Django was previously limited to the
  error_collector.ignore_errors configuration option. Ignoring exceptions by
  response status code is now supported for Django through the use of the
  error_collector.ignore_status_codes configuration option.

- Fix to include HTTP status for Tornado transactions

  HTTP status would fail to be added to Tornado transaction events and
  transaction traces. Now http status is automatically added to Tornado
  transaction events in Insights and transaction traces in APM.

- Fix reporting of concurrent external requests in Tornado

  External requests that execute in parallel in a tornado application may
  not have been recorded. This issue has been addressed.


2.96.0 (2017-10-16)
-------------------

- Add instrumentation for aiohttp framework

  Data is now automatically collected for applications using the aiohttp
  framework. Data for aiohttp applications will appear in both APM and
  Insights. Additionally, cross application tracing is supported for incoming
  requests for aiohttp applications. In addition to service maps, aiohttp
  applications will now show the calling application in transaction traces.

- Fix crash for gunicorn gaiohttp driver

  Using gunicorn's gaiohttp worker with New Relic browser monitoring enabled
  may have resulted in an application crash. This crash has been fixed and the
  gaiohttp worker is now fully supported with the New Relic Python Agent.

- Add support for displaying Heroku dyno names.

  Heroku-friendly logic can now be applied to how dyno names are displayed.
  This includes being able to collapse dynos based on prefix.

- Fix crash for pika versions 0.9.x and earlier

  Using the agent with pika versions 0.9.x and earlier could have resulted in
  an application crash. This issue has now been fixed.


2.94.0 (2017-09-19)
-------------------

- Add instrumentation for aiohttp client

  Outbound HTTP requests through the aiohttp library are now recorded. aiohttp
  Cross Application Tracing is now supported for outbound requests. In addition
  to Service Maps, applications accessed through the aiohttp client will now
  appear in transaction traces.

- Fix crash when using psycopg2 v2.7 composable queries

  The psycopg2 library introduced a module to generate SQL dynamically
  (psycopg2.sql) in version 2.7. Passing a Composable type object
  (psycopg2.sql.Composable) to execute or executemany resulted in an
  application crash. The agent now correctly handles psycopg2 Composable
  objects.


2.92.0 (2017-09-06)
-------------------

- Add API for cross application tracing of non-HTTP external services

  A new API is now exposed for implementing cross application tracing in custom
  instrumentation of non-HTTP transport libraries. For usage of this API see
  https://docs.newrelic.com/docs/agents/python-agent/supported-features/cross-application-tracing

- Add instrumentation for gRPC client calls

  Outbound gRPC requests will now show up in APM under the External Services
  tab and in transaction traces.

- Fixes erroneous recording of TastyPie `NotFound` exceptions

  When a TastyPie API view raised a `NotFound` exception resulting in a 404
  response, the agent may have erroneously recorded the exception. This has now
  been fixed.
