unreleased
----------

- Removed previously deprecated APIs

  The following APIs have been removed:
    - transaction (use current_transaction)
    - name_transaction (use set_transaction_name)
    - Application.record_metric (use Application.record_custom_metric)
    - Application.record_metrics (use Application.record_custom_metrics)
    - Transaction.notice_error (use Transaction.record_exception)
    - Transaction.record_metric (use Transaction.record_custom_metric)

- Deprecate Transaction.add_user_attribute

  Transaction.add_user_attribute has been deprecated in favor of
  Transaction.add_custom_parameter. Transaction.add_user_attribute will be
  removed in a future release.

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
