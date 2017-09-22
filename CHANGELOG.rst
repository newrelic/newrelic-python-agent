unreleased
----------

- Add support for displaying Heroku dyno names.

  Heroku-friendly logic can now be applied to how dyno names are displayed.
  This includes being able to collapse dynos based on prefix.


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
