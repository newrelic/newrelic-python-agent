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

"""
This module implements functions for creating a unique identity from a name and set of tags for use in dimensional metrics.
"""

from newrelic.packages import six


def create_metric_identity(name, tags=None):
    if tags:
        if isinstance(tags, dict):
            tags = frozenset(six.iteritems(tags)) if tags is not None else None
        elif not isinstance(tags, frozenset):
            tags = frozenset(tags)
    elif tags is not None:
        tags = None  # Set empty iterables to None

    return (name, tags)
