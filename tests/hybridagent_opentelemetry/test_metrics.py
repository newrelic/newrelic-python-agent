# Copyright 2010 New Relic, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from testing_support.validators.validate_otel_dimensional_metrics import validate_otel_dimensional_metrics

"""
export_request = 
[resource_metrics {
  resource {
    attributes {
      key: "telemetry.sdk.language"
      value {
        string_value: "python"
      }
    }
    attributes {
      key: "telemetry.sdk.name"
      value {
        string_value: "opentelemetry"
      }
    }
    attributes {
      key: "telemetry.sdk.version"
      value {
        string_value: "1.45.1"
      }
    }
    attributes {
      key: "service.instance.id"
      value {
        string_value: "702f4b16-3ea1-44dc-8fb5-140cb64a990f"
      }
    }
    attributes {
      key: "service.name"
      value {
        string_value: "Python Agent Test (Hybrid Agent)"
      }
    }
    attributes {
      key: "licenseKey"
      value {
        string_value: "3408070e"
      }
    }
    attributes {
      key: "tags.account"
      value {
        string_value: "Account 11159259"
      }
    }
    attributes {
      key: "instanceName"
      value {
        string_value: "Y05963HPD6 Python Agent Test (Hybrid Agent)"
      }
    }
    attributes {
      key: "tags.accountId"
      value {
        string_value: "11159259"
      }
    }
    attributes {
      key: "appName"
      value {
        string_value: "Python Agent Test (Hybrid Agent)"
      }
    }
    attributes {
      key: "host"
      value {
        string_value: "Y05963HPD6"
      }
    }
    attributes {
      key: "entity.guid"
      value {
        string_value: "MTExNTkyNTl8QVBNfEFQUExJQ0FUSU9OfDE4NzU0NTcyOQ"
      }
    }
    attributes {
      key: "host.displayName"
      value {
        string_value: "Y05963HPD6"
      }
    }
    attributes {
      key: "agent.version"
      value {
        string_value: "14.0.1.dev14+g1705b718f.d20261028"
      }
    }
    attributes {
      key: "realAgentId"
      value {
        string_value: "358083107"
      }
    }
    attributes {
      key: "tags.trustedAccountId"
      value {
        string_value: "11159259"
      }
    }
  }
  scope_metrics {
    scope {
      name: "test_meter"
    }
    metrics {
      name: "test_counter"
      description: "A test counter"
      unit: "1"
      sum {
        data_points {
          start_time_unix_nano: 1793224669695262000
          time_unix_nano: 1793224669695459000
          as_int: 5
        }
        data_points {
          start_time_unix_nano: 1793224669695340000
          time_unix_nano: 1793224669695459000
          as_int: 4
          attributes {
            key: "attribute_key"
            value {
              string_value: "attribute_value"
            }
          }
        }
        aggregation_temporality: AGGREGATION_TEMPORALITY_DELTA
        is_monotonic: true
      }
    }
  }
}
]
"""



@validate_otel_dimensional_metrics(counter_expected=[(4, {"attribute_key": "attribute_value"}), (5, {})])
def test_counter(meter_provider):
    meter = meter_provider.get_meter("test_meter")
    counter = meter.create_counter(
        name="test_counter",
        description="A test counter",
        unit="1",
    )
    counter.add(2)
    counter.add(4, {"attribute_key": "attribute_value"})
    counter.add(3)




