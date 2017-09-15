Unreleased
----------

- Add instrumentation for aiohttp client

  Outbound HTTP requests through the aiohttp library are now recorded. aiohttp
  Cross Application Tracing is now supported for outbound requests. In addition
  to Service Maps, applications accessed through the aiohttp client will now
  appear in transaction traces.

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
