Unreleased
----------

- Add instrumentation for gRPC client calls

  Outbound gRPC requests will now show up in APM under the External Services
  tab and in transaction traces.

- Fixes erroneous recording of TastyPie `NotFound` exceptions

  When a TastyPie API view raised a `NotFound` exception resulting in a 404
  response, the agent may have erroneously recorded the exception. This has now
  been fixed.
