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
import time
from newrelic.core import attribute
from newrelic.core.attribute_filter import DST_SPAN_EVENTS, DST_TRANSACTION_SEGMENTS


class GenericNodeMixin:
    def __init__(self, *args, **kwargs):
        self.ids = []

    @property
    def processed_user_attributes(self):
        if hasattr(self, "_processed_user_attributes"):
            return self._processed_user_attributes

        self._processed_user_attributes = u_attrs = {}
        user_attributes = getattr(self, "user_attributes", u_attrs)
        for k, v in user_attributes.items():
            k, v = attribute.process_user_attribute(k, v)
            # Only record the attribute if it passes processing.
            # Failures return (None, None).
            if k:
                u_attrs[k] = v
        return u_attrs

    def get_trace_segment_params(self, settings, params=None):
        _params = attribute.resolve_agent_attributes(
            self.agent_attributes, settings.attribute_filter, DST_TRANSACTION_SEGMENTS
        )

        if params:
            _params.update(params)

        _params.update(
            attribute.resolve_user_attributes(
                self.processed_user_attributes, settings.attribute_filter, DST_TRANSACTION_SEGMENTS
            )
        )

        _params["exclusive_duration_millis"] = 1000.0 * self.exclusive
        return _params

    def span_event(self, settings, base_attrs=None, parent_guid=None, attr_class=dict, ct_exit_spans=None, ct_processing_time=None):
        if ct_exit_spans is None:
            ct_exit_spans = {}
        i_attrs = base_attrs and base_attrs.copy() or attr_class()
        i_attrs["type"] = "Span"
        i_attrs["name"] = i_attrs.get("name") or self.name
        i_attrs["guid"] = self.guid
        i_attrs["timestamp"] = int(self.start_time * 1000)
        i_attrs["duration"] = self.duration
        i_attrs["category"] = i_attrs.get("category") or "generic"
        # TODO: limit intrinsic attributes but this likely requires changes in the pipeline.
        #if settings.distributed_tracing.minimize_attributes.enabled:
        #    i_ct_attrs = {"type", "name", "guid", "parentId", "transaction.name", "traceId", "timestamp", "duration", "nr.entryPoint", "transactionId"}
        #    i_attrs = {key: value for key, value in i_attrs.items() if key in i_ct_attrs}

        if parent_guid:
            i_attrs["parentId"] = parent_guid

        a_attrs = attribute.resolve_agent_attributes(
            self.agent_attributes, settings.attribute_filter, DST_SPAN_EVENTS, attr_class=attr_class
        )
        u_attrs = self.processed_user_attributes
        if settings.distributed_tracing.unique_spans.enabled:
            # ids is the list of span guids that share this unqiue exit span.
            u_attrs["ids"] = self.ids

        u_attrs = attribute.resolve_user_attributes(
            u_attrs, settings.attribute_filter, DST_SPAN_EVENTS, attr_class=attr_class
        )

        start_time = time.time()
        if settings.distributed_tracing.drop_inprocess_spans.enabled or settings.distributed_tracing.unique_spans.enabled:
            exit_span_attrs_present = attribute.SPAN_ENTITY_RELATIONSHIP_ATTRIBUTES & set(a_attrs)
            # If this is the entry node, always return it.
            if i_attrs.get("nr.entryPoint"):
                ct_processing_time[0] += (time.time() - start_time)
                return [i_attrs, u_attrs, {}] if settings.distributed_tracing.minimize_attributes.enabled else [i_attrs, u_attrs, a_attrs]
            # If the span is not an exit span, skip it by returning None.
            if not exit_span_attrs_present:
                ct_processing_time[0] += (time.time() - start_time)
                return None
            # If the span is an exit span but unique spans is enabled, we need to check
            # for uniqueness before returning it.
            if settings.distributed_tracing.unique_spans.enabled:
                a_minimized_attrs = attr_class({key: a_attrs[key] for key in exit_span_attrs_present})
                # Combine all the entity relationship attr values into a string to be
                # used as the hash to check for uniqueness.
                # TODO: use attr value name rather than str casting for infinite tracing.
                span_attrs = "".join([str(a_minimized_attrs[key]) for key in exit_span_attrs_present])
                new_exit_span = span_attrs not in ct_exit_spans
                # If this is a new exit span, add it to the known ct_exit_spans and return it.
                if new_exit_span:
                    ct_exit_spans[span_attrs] = self.ids
                    ct_processing_time[0] += (time.time() - start_time)
                    return [i_attrs, u_attrs, a_minimized_attrs] if settings.distributed_tracing.minimize_attributes.enabled else [i_attrs, u_attrs, a_attrs]
                # If this is an exit span we've already seen, add it's guid to the list
                # of ids on the seen span and return None.
                # For now add ids to user attributes list
                ct_exit_spans[span_attrs].append(self.guid)
                ct_processing_time[0] += (time.time() - start_time)
                return None
        elif settings.distributed_tracing.minimize_attributes.enabled:
            # Drop all non-entity relationship attributes from the span.
            exit_span_attrs_present = attribute.SPAN_ENTITY_RELATIONSHIP_ATTRIBUTES & set(a_attrs)
            a_attrs = attr_class({key: a_attrs[key] for key in exit_span_attrs_present})
        ct_processing_time[0] += (time.time() - start_time)
        return [i_attrs, u_attrs, a_attrs]

    def span_events(self, settings, base_attrs=None, parent_guid=None, attr_class=dict, ct_exit_spans=None, ct_processing_time=None):
        span = self.span_event(settings, base_attrs=base_attrs, parent_guid=parent_guid, attr_class=attr_class, ct_exit_spans=ct_exit_spans, ct_processing_time=ct_processing_time)
        parent_id = parent_guid
        if span:  # span will be None if the span is an inprocess span or repeated exit span.
            yield span
            parent_id = self.guid
        for child in self.children:
            for event in child.span_events(  # noqa: UP028
                settings, base_attrs=base_attrs, parent_guid=parent_id, attr_class=attr_class, ct_exit_spans=ct_exit_spans, ct_processing_time=ct_processing_time
            ):
                if event:  # event will be None if the span is an inprocess span or repeated exit span.
                    yield event


class DatastoreNodeMixin(GenericNodeMixin):
    @property
    def name(self):
        product = self.product
        target = self.target
        operation = self.operation or "other"

        if target:
            name = f"Datastore/statement/{product}/{target}/{operation}"
        else:
            name = f"Datastore/operation/{product}/{operation}"

        return name

    @property
    def db_instance(self):
        if hasattr(self, "_db_instance"):
            return self._db_instance

        db_instance_attr = None
        if self.database_name:
            _, db_instance_attr = attribute.process_user_attribute("db.instance", self.database_name)

        self._db_instance = db_instance_attr
        return db_instance_attr

    def span_event(self, settings, base_attrs=None, parent_guid=None, attr_class=dict, *args, **kwargs):
        a_attrs = self.agent_attributes
        a_attrs["db.instance"] = self.db_instance
        i_attrs = base_attrs and base_attrs.copy() or attr_class()

        i_attrs["category"] = "datastore"
        i_attrs["span.kind"] = "client"

        if self.product:
            i_attrs["component"] = a_attrs["db.system"] = attribute.process_user_attribute("db.system", self.product)[1]
        if self.operation:
            a_attrs["db.operation"] = attribute.process_user_attribute("db.operation", self.operation)[1]
        if self.target:
            a_attrs["db.collection"] = attribute.process_user_attribute("db.collection", self.target)[1]

        if self.instance_hostname:
            peer_hostname = attribute.process_user_attribute("peer.hostname", self.instance_hostname)[1]
        else:
            peer_hostname = "Unknown"

        a_attrs["peer.hostname"] = a_attrs["server.address"] = peer_hostname

        peer_address = f"{peer_hostname}:{self.port_path_or_id or 'Unknown'}"

        a_attrs["peer.address"] = attribute.process_user_attribute("peer.address", peer_address)[1]

        # Attempt to treat port_path_or_id as an integer, fallback to not including it
        try:
            a_attrs["server.port"] = int(self.port_path_or_id)
        except Exception:
            pass

        return super().span_event(settings, base_attrs=i_attrs, parent_guid=parent_guid, attr_class=attr_class, *args, **kwargs)
