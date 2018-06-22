# Distributed Tracing Cross Agent Tests

The `distributed_tracing.json` file included here represents tests for the
[Better CAT]() spec.

The file is in json format and is a list of dictionaries, each dictionary
representing one test.

## Required fields

Each test will include these fields:

+ `test_name`: A string representing the test name.
+ `inbound_payloads`: List representing distributed trace payloads as described
  in the spec. AcceptDistributedTracePayload should be called with each payload
  in turn.
+ `trusted_account_key`: Integer. The earliest ancestor trusted account id.
+ `exact_intrinsics`: Dictionary. Each key, value pair in the dictionary
  represents one intrinsic that should be included on events and traces. The
  key and value should be expected exactly.
+ `expected_intrinsics`: List of strings. These intrinsics should be included
  on events and traces. Since their values are generated dynamically, it is not
  necessary to validate their values.
+ `unexpected_intrinsics`: List of strings. These intrinsics should not be
  included on events or traces.
+ `expected_metrics`: List. Each list item itself is also a list of length two.
  The first item in the list is a metric name (unscoped). The second item is
  the expected number of occurrences of that metric. When a `null` is
  encountered, then the metric is expected to be absent.

## Optional fields

Each test could also include these fields:

+ `comment`: A comment describing the test and anything that may be special
  about it.
  should be base64 encoded or not.
+ `background_task`: Boolean, defaults to false. Whether the test should be run
  as a background task (as opposed to a web transaction).
+ `raises_exception`: Boolean, defaults to false. Whether the test should raise
  and record an exception (thus creating error traces, error events, etc).
+ `feature_flag`: Boolean, defaults to true. Whether the distributed tracing
  feature flag is to be included or not.
+ `second_inbound_payload`: Dictionary representing a distributed trace payload
  as described in the spec. This second payload should be handled using the
  `AcceptDistributedTracePayload` API sometime after the first one.
+ `outbound_payloads_d`: List. For each item in the list, an outgoing request
  should be made during the distributed trace transaction. The list item itself
  represents the key, value pairs that should be asserted on the `data` portion
  of the outgoing distributed tracing payload.
