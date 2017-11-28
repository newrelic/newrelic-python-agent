unreleased
----------

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


2.96.0.80 (2017-10-16)
----------------------

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


2.94.0.79 (2017-09-19)
----------------------

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

2.92.0.78 (2017-09-06)
----------------------

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
